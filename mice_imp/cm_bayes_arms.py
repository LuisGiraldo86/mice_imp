#!/usr/bin/env python
"""
Bayesian arms for the WD-FAB-DE Community Mobility missing-data comparison.

Fits three arms on an ALREADY-MASKED CM response frame:

    birt   B-IRT   : GRM with no imputation model. Missing cells contribute
                     exactly 0 to the log-likelihood (marginalised out).
    bmi    B-MI    : GRM with PairwiseOrdinalStackingModel PMFs attached.
                     Missing cells contribute log sum_k q_k p_k(phi)
                     (analytic Rao-Blackwellisation, NOT Rubin-style MI).
    flat   control : GRM with uniform 1/K PMFs attached.

WHY THE FLAT ARM EXISTS
-----------------------
With q_k = 1/K the Rao-Blackwellised contribution of a masked cell is

    log( sum_k (1/K) p(Y=k|phi) ) = log(1/K),

because GRM category probabilities sum to one. It is a constant: its
gradient vanishes, so the flat arm targets EXACTLY the same posterior as
birt. Any difference between `flat` and `birt` is therefore pure Monte
Carlo noise, and gives you the resolution at which a real bmi-vs-birt
difference could be detected. It is also a wiring check: a SYSTEMATIC
flat-vs-birt difference means something in the plumbing is wrong.

DERIVED FROM
------------
J. Chang's 2026-06-01 script (Baseline / Pairwise variants), with IPW,
the BCM block, the multi-scale loop and the cross-scale imputation
predictors removed. See notes in each function.

STATUS (2026-08-13): every call marked `# API` was checked against the
vendored bayesianquilts at commit 7a29ec5 -- names, signatures and return
shapes all match. Nothing here has been RUN end to end, so smoke-test with
--num-warmup 200 --num-samples 200 before committing to full chains.

Input is a masked design frame; `.dta` is loaded via wdfab_io, which reads
numeric codes rather than the German value labels and shifts the raw 1..K
scale onto 0..K-1. Do not hand this script a frame loaded any other way.
"""
from __future__ import annotations

import argparse

import json
import os
from pathlib import Path

os.environ.setdefault("JAX_PLATFORMS", "cpu")
os.environ.setdefault("JAX_ENABLE_X64", "1")

import numpy as np
import pandas as pd

import jax.numpy as jnp

from bayesianquilts.imputation.mixed import PairwiseOnlyImputationModel
from bayesianquilts.imputation.pairwise_stacking import PairwiseOrdinalStackingModel
from bayesianquilts.irt.grm import GRModel

from mice_imp.compat import patch_batchless_training_loop
from mice_imp.wdfab_io import ITEM_KEYS, ITEM_SETS, load_frame


# ----------------------------------------------------------------------------
# Data
# ----------------------------------------------------------------------------
def build_data_dict(df: pd.DataFrame, item_keys: list[str]) -> dict:
    """Frame -> the dict GRModel expects.

    No `sample_weights` key: Chang's IPW corrects for the applicant /
    normative oversampling in the US calibration data. Your design has no
    such stratification, and he told You-Shan to disable it (2026-06-01).

    Responses must already be 0-indexed with missing as NaN -- run
    cm_preflight.py first. The mask inside GRModel is
    (y < 0) | (y >= response_cardinality) | isnan(y), so an out-of-range
    code disappears silently rather than raising.
    """
    data = {k: df[k].to_numpy().astype(np.float64) for k in item_keys}
    data["person"] = np.arange(len(df), dtype=np.float64)
    return data


# ----------------------------------------------------------------------------
# Imputation model
# ----------------------------------------------------------------------------
def fit_imputation_model(
    df: pd.DataFrame,
    item_keys: list[str],
    n_top_features: int | None = None,
    seed: int = 42,
    n_jobs: int = 1,
    save_path: Path | None = None,
):
    """Fit the pairwise ordinal stacking imputation model.

    DESIGN DECISION -- restricted predictor set.
    Chang fits this across all eight WD-FAB scales. Doing that here would
    let B-MI impute masked CM responses using BM/UBF/FMF/ME/RS/SR/CC items,
    information the FIML, MG-IRT and SL arms never see. B-MI would then win
    for a reason unrelated to imputation. So `df` must contain the CM items
    ONLY, and n_top_features is capped at len(item_keys) - 1.

    If you want the cross-scale version, run it as an explicitly labelled
    secondary arm -- it answers a real question, just not the one the
    abstract poses.
    """
    max_features = len(item_keys) - 1
    if n_top_features is None:
        n_top_features = max_features
    n_top_features = min(n_top_features, max_features)

    model = PairwiseOrdinalStackingModel(
        prior_scale=1.0,
        pathfinder_num_samples=100,
        pathfinder_maxiter=50,
        batch_size=512,
        verbose=True,
    )
    model.fit(                                                          # API
        df[item_keys],
        n_top_features=n_top_features,
        n_jobs=n_jobs,
        seed=seed,
    )

    if save_path is not None:
        save_path = Path(save_path).expanduser()
        save_path.parent.mkdir(parents=True, exist_ok=True)
        try:
            model.save_to_disk(save_path)
        except AttributeError:
            model.save(str(save_path))
    return model


def load_imputation_model(path: Path):
    path = Path(path).expanduser()
    try:
        return PairwiseOrdinalStackingModel.load_from_disk(path)
    except AttributeError:
        return PairwiseOrdinalStackingModel.load(str(path))


# ----------------------------------------------------------------------------
# PMF attachment
# ----------------------------------------------------------------------------
def attach_imputation_pmfs(model: GRModel, data: dict, verbose: bool = True) -> dict:
    """Attach `_imputation_pmfs` (and weights) to the data dict.

    INSTRUMENTED ON PURPOSE. Inside _compute_batch_pmfs, the per-cell
    imputation call is wrapped in

        except (ValueError, KeyError, AttributeError):
            pmfs[row_idx, i, :] = 1.0 / K

    A flat PMF is mathematically equivalent to no imputation (see module
    docstring), so every fallback silently downgrades that cell to B-IRT.
    Your design maximises the risk: with ~2/3 of non-anchor items masked,
    the predictors the imputation model wants are often masked too.

    If the reported fallback fraction is high, B-MI is not really running
    and a null result would be an artefact.
    """
    out = dict(data)
    if getattr(model, "imputation_model", None) is None:
        return out

    pmfs, weights = model._compute_batch_pmfs(out)                      # API
    if pmfs is not None:
        out["_imputation_pmfs"] = pmfs
    if weights is not None:
        out["_imputation_weights"] = weights

    if verbose and pmfs is not None:
        K = model.response_cardinality
        missing = np.zeros(pmfs.shape[:2], dtype=bool)
        for i, key in enumerate(model.item_keys):
            col = np.asarray(data[key], dtype=np.float64)
            missing[:, i] = np.isnan(col) | (col < 0) | (col >= K)

        n_missing = int(missing.sum())
        if n_missing:
            block = pmfs[missing]
            flat = np.isclose(block, 1.0 / K, atol=1e-9).all(axis=-1).sum()
            unfilled = np.isclose(block.sum(axis=-1), 0.0, atol=1e-12).sum()
            print(f"    PMFs: {n_missing} masked cells | "
                  f"flat fallback {flat} ({flat / n_missing:.1%}) | "
                  f"unfilled {unfilled} ({unfilled / n_missing:.1%})")
            if flat / n_missing > 0.10:
                print("    WARNING: >10% of masked cells fell back to a flat "
                      "PMF. Those cells contribute nothing beyond B-IRT.")
    return out


def flat_imputation_pmfs(data: dict, item_keys: list[str], cardinality: int) -> dict:
    """Uniform 1/K PMFs -- the noise-floor control arm."""
    out = dict(data)
    N = len(data[item_keys[0]])
    I, K = len(item_keys), cardinality
    out["_imputation_pmfs"] = np.full((N, I, K), 1.0 / K, dtype=np.float64)
    out["_imputation_weights"] = np.ones(I, dtype=np.float64)
    return out


# ----------------------------------------------------------------------------
# Diagnostics
# ----------------------------------------------------------------------------
def max_rhat(mcmc_samples: dict, verbose: bool = True) -> float:
    """Split-free R-hat across chains, as in Chang's script."""
    worst = 0.0
    for name, samples in mcmc_samples.items():
        arr = np.asarray(samples)
        if arr.ndim < 2 or arr.shape[0] < 2:
            continue
        between = np.var(np.mean(arr, axis=1), axis=0, ddof=1)
        within = np.mean(np.var(arr, axis=1, ddof=1), axis=0)
        n = arr.shape[1]
        r = np.sqrt(((n - 1) / n * within + between) / np.maximum(within, 1e-30))
        worst = max(worst, float(np.max(r)))
        if verbose:
            print(f"    R-hat {name}: mean={np.mean(r):.4f} max={np.max(r):.4f}")
    if verbose:
        print(f"    max R-hat overall: {worst:.4f}")
    return worst


def to_mirt_convention(mcmc_samples: dict) -> dict:
    """Convert posterior item parameters to mirt's parameterisation.

    bayesianquilts:  sigmoid(-a_i * (b_ik - theta))   i.e. a_i(theta - b_ik)
    mirt:            a_i * theta + d_ik

    so   d_ik = -a_i * b_ik.

    Thresholds are stored as INCREMENTS: difficulties0 concatenated with
    ddifficulties, then cumsum. Skipping the cumsum silently gives you
    increments where you wanted thresholds; the slope regression would
    still look fine while the intercept regression became meaningless.

    Extract AFTER standardize_marginal, or the metric will not match
    mirt's theta ~ N(0,1) identification.
    """
    a = np.asarray(mcmc_samples["discriminations"])
    d0 = np.asarray(mcmc_samples["difficulties0"])
    dd = mcmc_samples.get("ddifficulties")

    if dd is not None and np.asarray(dd).shape[-1] > 0:
        b = np.concatenate([d0, np.asarray(dd)], axis=-1)
    else:
        b = d0
    b = np.cumsum(b, axis=-1)

    a_flat = a.reshape(-1, *a.shape[2:])
    b_flat = b.reshape(-1, *b.shape[2:])

    a_sq = np.squeeze(a_flat)
    b_sq = np.squeeze(b_flat)
    d_sq = -a_sq[..., None] * b_sq if b_sq.ndim == a_sq.ndim + 1 else -a_sq * b_sq

    return {
        "a_draws": a_sq,
        "b_draws": b_sq,
        "d_draws": d_sq,
        "a_mean": a_sq.mean(axis=0),
        "b_mean": b_sq.mean(axis=0),
        "d_mean": d_sq.mean(axis=0),
        "a_sd": a_sq.std(axis=0),
        "b_sd": b_sq.std(axis=0),
        "d_sd": d_sq.std(axis=0),
    }


# ----------------------------------------------------------------------------
# One arm
# ----------------------------------------------------------------------------
def fit_arm(
    arm: str,
    df: pd.DataFrame,
    item_keys: list[str],
    cardinality: int,
    output_dir: Path,
    imputation_model=None,
    init_advi_params=None,
    run_advi: bool = True,
    advi_iterations: int = 100,
    advi_num_samples: int = 32,
    advi_learning_rate: float = 0.00051,
    advi_rank: int = 0,
    num_chains: int = 4,
    num_warmup: int = 3000,
    num_samples: int = 2000,
    # Measured 2026-08-21 by mice_imp/sweep_sampler.py on CommonItem/nobike,
    # B-IRT only, everything else held fixed. Three configurations, six chains:
    #
    #   2e-3 / 0.95   non-divergent 0.055-0.115   R-hat 1.195   2.6 min
    #   5e-4 / 0.98   non-divergent 0.120-0.285   R-hat 1.127   5.7 min
    #   1e-4 / 0.98   non-divergent 0.090-0.105   R-hat 1.148   4.6 min
    #
    # 5e-4 / 0.98 was best on both counts, so it is the default -- it is also
    # what B-MI already used. Two caveats worth keeping in view: the spread
    # between configurations is close to the run-to-run noise (repeat runs of
    # the SAME settings gave 0.040 and 0.115), and no configuration converged
    # at smoke length. Those measurements are at 200 warmup; adaptation has
    # 15x longer in a real run, so they bound the problem rather than predict
    # it.
    step_size: float = 0.0005,
    target_accept_prob: float = 0.98,
    seed: int = 42,
) -> dict:
    """Fit one arm and persist its posterior.

    ADVI is a 100-iteration WARM-START ONLY, never the inference. Chang
    found mean-field ADVI settling into a poor local optimum (2026-03-30)
    and moved to NUTS on item parameters with abilities integrated out on a
    quadrature grid -- which is also why this is tractable: the sampler
    explores ~len(items) * cardinality dimensions, not that plus N.
    """
    print(f"\n=== arm: {arm} ===")
    output_dir = Path(output_dir).expanduser()
    output_dir.mkdir(parents=True, exist_ok=True)

    model = GRModel(                                                    # API
        item_keys=item_keys,
        num_people=len(df),
        response_cardinality=cardinality,
        dim=1,
        imputation_model=imputation_model,
        dtype=jnp.float64,
    )

    if imputation_model is not None:
        try:
            model.validate_imputation_model()                          # API
            print("    imputation model validated")
        except Exception as exc:
            print(f"    imputation validation warning: {exc}")

    data = build_data_dict(df, item_keys)

    if arm == "bmi":
        data = attach_imputation_pmfs(model, data)
    elif arm == "flat":
        data = flat_imputation_pmfs(data, item_keys, cardinality)
    # arm == "birt": nothing attached; masked cells contribute 0.

    advi_params = None
    if run_advi:
        # fit_marginal_advi calls training_loop batchlessly, but training_loop
        # at 7a29ec5 requires data_iterator/steps_per_epoch. Patched here
        # rather than at import so the shim is applied only when ADVI is
        # actually about to run. Idempotent, and a no-op if the installed
        # bayesianquilts no longer needs it.
        patch_batchless_training_loop()
        print(f"    ADVI warm-start ({advi_iterations} iterations)")
        _, advi_params = model.fit_marginal_advi(                      # API
            data,
            num_samples=advi_num_samples,
            num_epochs=advi_iterations,
            learning_rate=advi_learning_rate,
            rank=advi_rank,
            seed=seed,
            verbose=True,
        )
        # fit_marginal_advi stores its result in `self.marginal_params`, but
        # fit_marginal_mcmc warm-starts by scanning `self.params` for keys
        # ending in 'loc'. Without this assignment `self.params` is still None
        # and the chains initialise from the PRIOR -- the warm-start is
        # computed and discarded.
        #
        # That is not merely wasteful. The other two arms are initialised from
        # these same params, so leaving birt on a prior init would make the
        # flat-vs-birt gap a mixture of initialisation and Monte Carlo noise,
        # and the noise floor would no longer measure what it claims to.
        # Look for "Initializing from ADVI solution" in the MCMC output.
        model.params = advi_params
    elif init_advi_params is not None:
        # Chang reuses the Baseline warm-start for the Pairwise arm. Good
        # for comparability -- a shared starting point -- and it is why
        # B-IRT must be run before B-MI. Report it in the methods.
        print("    initialising from supplied ADVI params")
        model.params = init_advi_params
        advi_params = init_advi_params

    print(f"    NUTS: chains={num_chains} warmup={num_warmup} "
          f"samples={num_samples} step={step_size} accept={target_accept_prob}")
    mcmc_samples = model.fit_marginal_mcmc(                            # API
        data,
        theta_grid=None,
        num_chains=num_chains,
        num_warmup=num_warmup,
        num_samples=num_samples,
        target_accept_prob=target_accept_prob,
        step_size=step_size,
        seed=seed + 10_000,
        verbose=True,
    )

    rhat = max_rhat(mcmc_samples)
    if rhat > 1.05:
        print(f"    WARNING: max R-hat {rhat:.4f} > 1.05 -- do not trust these "
              "summaries. Increase warmup and lower step_size.")

    eap_pre = model.compute_eap_abilities(data)                        # API
    stats = model.standardize_marginal(data)                           # API
    eap = model.compute_eap_abilities(data)
    print(f"    theta after standardisation: mean={float(jnp.mean(eap['eap'])):.4f} "
          f"sd={float(jnp.std(eap['eap'])):.4f} "
          f"mean PSD={float(jnp.mean(eap['psd'])):.4f}")

    # Item parameters must be read AFTER standardisation.
    item_params = to_mirt_convention(mcmc_samples)

    out = {
        "arm": arm,
        "eap": np.asarray(eap["eap"]).reshape(-1),
        "psd": np.asarray(eap["psd"]).reshape(-1),
        "eap_pre": np.asarray(eap_pre["eap"]).reshape(-1),
        "max_rhat": rhat,
        "advi_params": advi_params,
        "item_params": item_params,
        "mcmc_samples": mcmc_samples,
        "model": model,
    }

    np.savez(
        output_dir / f"{arm}.npz",
        eap=out["eap"], psd=out["psd"], eap_pre=out["eap_pre"],
        max_rhat=np.asarray(rhat),
        standardize_mu=np.asarray(stats["mu"]),
        standardize_sigma=np.asarray(stats["sigma"]),
        item_keys=np.asarray(item_keys),
        **{f"item_{k}": v for k, v in item_params.items() if k.endswith(("mean", "sd"))},
        **{k: np.asarray(v) for k, v in mcmc_samples.items()},
    )
    print(f"    saved {output_dir / f'{arm}.npz'}")
    return out


# ----------------------------------------------------------------------------
# All three arms
# ----------------------------------------------------------------------------
def run_all_arms(
    df: pd.DataFrame,
    item_keys: list[str],
    cardinality: int,
    output_dir: Path,
    imputation_model_path: Path | None = None,
    refit_imputer: bool = False,
    arms: tuple[str, ...] = ("birt", "bmi", "flat"),
    seed: int = 42,
    bmi_step_size: float = 0.0005,
    bmi_target_accept_prob: float = 0.98,
    **fit_kwargs,
) -> dict:
    """Run B-IRT, then B-MI, then the flat control, in that order.

    The order is not cosmetic: B-MI reuses B-IRT's ADVI warm-start, so
    B-IRT must run first.

    B-MI gets a smaller step size and higher target acceptance (Chang's
    defaults). Attaching PMFs turns masked cells from exact zeros into
    parameter-dependent curvature, which makes the posterior geometry
    harder for NUTS.
    """
    output_dir = Path(output_dir).expanduser()
    output_dir.mkdir(parents=True, exist_ok=True)
    results = {}

    if "birt" not in arms:
        raise ValueError("B-IRT is required: B-MI reuses its ADVI warm-start, "
                         "and it is the control the other arms are read against.")

    results["birt"] = fit_arm(
        "birt", df, item_keys, cardinality, output_dir,
        imputation_model=None, run_advi=True, seed=seed, **fit_kwargs,
    )

    if "bmi" in arms:
        if imputation_model_path is not None and Path(imputation_model_path).exists() \
                and not refit_imputer:
            print(f"\nloading imputation model from {imputation_model_path}")
            pairwise = load_imputation_model(imputation_model_path)
        else:
            print("\nfitting imputation model (CM items only)")
            pairwise = fit_imputation_model(
                df, item_keys, seed=seed, save_path=imputation_model_path,
            )

        results["bmi"] = fit_arm(
            "bmi", df, item_keys, cardinality, output_dir,
            imputation_model=PairwiseOnlyImputationModel(mice_model=pairwise),
            init_advi_params=results["birt"]["advi_params"],
            run_advi=False,
            step_size=bmi_step_size,
            target_accept_prob=bmi_target_accept_prob,
            seed=seed + 1,
            **fit_kwargs,
        )

    if "flat" in arms:
        results["flat"] = fit_arm(
            "flat", df, item_keys, cardinality, output_dir,
            imputation_model=None,
            init_advi_params=results["birt"]["advi_params"],
            run_advi=False,
            seed=seed + 2,
            **fit_kwargs,
        )

    _report_noise_floor(results, output_dir)
    return results


def _report_noise_floor(results: dict, output_dir: Path) -> None:
    """Compare flat against birt: they target the identical posterior."""
    if not {"birt", "flat"} <= results.keys():
        return

    birt, flat = results["birt"], results["flat"]
    theta_rmse = float(np.sqrt(np.mean((birt["eap"] - flat["eap"]) ** 2)))
    a_gap = float(np.max(np.abs(
        birt["item_params"]["a_mean"] - flat["item_params"]["a_mean"])))

    print("\n=== noise floor (flat vs birt: same posterior by construction) ===")
    print(f"    theta RMSE       {theta_rmse:.5f}")
    print(f"    max |delta a|    {a_gap:.5f}")

    summary = {"theta_rmse_flat_vs_birt": theta_rmse, "max_abs_delta_a": a_gap}

    if "bmi" in results:
        bmi = results["bmi"]
        bmi_rmse = float(np.sqrt(np.mean((birt["eap"] - bmi["eap"]) ** 2)))
        summary["theta_rmse_bmi_vs_birt"] = bmi_rmse
        ratio = bmi_rmse / theta_rmse if theta_rmse > 0 else np.inf
        print(f"    B-MI vs B-IRT    {bmi_rmse:.5f}  ({ratio:.1f}x the floor)")
        if ratio < 2:
            print("    B-MI differs from B-IRT by less than twice the Monte "
                  "Carlo floor: not a detectable effect at these settings.")

    with open(output_dir / "noise_floor.json", "w") as fh:
        json.dump(summary, fh, indent=2)


# ----------------------------------------------------------------------------
def main():
    ap = argparse.ArgumentParser(
        description="B-IRT / B-MI / flat-control arms for one masked CM dataset.")
    ap.add_argument("masked_path",
                    help="masked CM frame (.dta design file, or .csv)")
    ap.add_argument("--output-dir", required=True)
    ap.add_argument("--imputation-model-path", default=None)
    ap.add_argument("--cardinality", type=int, default=5)
    ap.add_argument("--items", choices=sorted(ITEM_SETS), default="full",
                    help="which item set to calibrate: 'full' is all 27 CM "
                         "items, 'nobike' drops the 7 bicycling items and "
                         "keeps the 20 adapted DA items. Every dataset gets "
                         "both runs; give them separate --output-dir.")
    ap.add_argument("--arms", default="birt,bmi,flat")
    ap.add_argument("--seed", type=int, default=42)
    ap.add_argument("--num-chains", type=int, default=4)
    ap.add_argument("--num-warmup", type=int, default=3000)
    ap.add_argument("--num-samples", type=int, default=2000)
    ap.add_argument("--refit-imputer", action="store_true")
    args = ap.parse_args()

    item_keys = ITEM_SETS[args.items]
    df = load_frame(args.masked_path, cardinality=args.cardinality)
    print(f"item set '{args.items}': {len(item_keys)} items")
    run_all_arms(
        df=df,
        item_keys=item_keys,
        cardinality=args.cardinality,
        output_dir=Path(args.output_dir),
        imputation_model_path=(Path(args.imputation_model_path)
                               if args.imputation_model_path else None),
        refit_imputer=args.refit_imputer,
        arms=tuple(args.arms.split(",")),
        seed=args.seed,
        num_chains=args.num_chains,
        num_warmup=args.num_warmup,
        num_samples=args.num_samples,
    )


if __name__ == "__main__":
    main()
