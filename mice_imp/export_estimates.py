#!/usr/bin/env python
"""
Export item parameters and person thetas from the Bayesian arms to CSV.

Reads the per-arm `.npz` written by `cm_bayes_arms.fit_arm` and writes two
flat files per design:

    item_parameters.csv   one row per (arm, item): a, b1..b4 (+ posterior SDs)
    theta.csv             one row per respondent: EAP theta and PSD per arm

WHAT THE NUMBERS ARE
--------------------
Posterior means of the marginal NUTS draws, extracted AFTER
`standardize_marginal`, so the metric is mirt's theta ~ N(0,1)
identification and the values are directly comparable with `mirt` output.

`a` and `b` are on the IRT location parameterisation

    P(Y >= k) = sigmoid( a_i * (theta - b_ik) )

which is what a coauthor asking for "a and b1..b4" means. mirt's own
coef() reports intercepts instead, with d_ik = -a_i * b_ik; those are in
the npz as `item_d_mean` and are emitted here too when --include-d is
passed, so nobody has to redo the conversion (fact 5). Thresholds are
already cumsum-ed from the stored increments -- do not cumsum again.

The exported `d` will NOT reproduce exactly as -a * b from the exported
columns (they differ by up to ~0.02 here). That is not an inconsistency:
each column is the posterior mean of its own quantity, and the posterior
mean of a product is not the product of the posterior means. Use the `d`
column when you want intercepts; do not recompute it.

`theta` is the EAP on the same standardised metric; `theta_se` is the
posterior SD (PSD), the Bayesian analogue of mirt's SE.

RESPONDENT IDs
--------------
`id_work` is read from the source `.dta`, not from the npz: the arms fit
on the item columns only. Rows are order-aligned across the CD export and
all three design files (verified by exact agreement on every unmasked
cell), so positional joining is safe. If the `.dta` is not given, the id
column is a 0-based row index instead and is labelled `row`.

CAVEAT
------
This exports whatever was fitted, including arms whose R-hat failed.
`max_rhat` is carried into both files per arm so a reader cannot silently
use non-converged estimates. Arms above 1.05 are flagged on stderr.
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from mice_imp.wdfab_io import FORM_KEY, ITEM_SETS, read_dta  # noqa: E402

ARMS = ("birt", "bmi", "flat")
RHAT_LIMIT = 1.05


def _load_arm(path: Path) -> dict:
    z = np.load(path, allow_pickle=True)
    return {
        "item_keys": [str(k) for k in z["item_keys"]],
        "a_mean": np.asarray(z["item_a_mean"], dtype=float).reshape(-1),
        "a_sd": np.asarray(z["item_a_sd"], dtype=float).reshape(-1),
        "b_mean": np.atleast_2d(np.asarray(z["item_b_mean"], dtype=float)),
        "b_sd": np.atleast_2d(np.asarray(z["item_b_sd"], dtype=float)),
        "d_mean": np.atleast_2d(np.asarray(z["item_d_mean"], dtype=float)),
        "d_sd": np.atleast_2d(np.asarray(z["item_d_sd"], dtype=float)),
        "eap": np.asarray(z["eap"], dtype=float).reshape(-1),
        "psd": np.asarray(z["psd"], dtype=float).reshape(-1),
        "max_rhat": float(np.asarray(z["max_rhat"])),
    }


def _as_int_if_integral(col: pd.Series) -> np.ndarray | pd.Series:
    """`read_stata` gives float64 ids; write them as integers when they are.

    Purely cosmetic -- but `id_work` is the join key the coauthor will match
    against, and `1.0` vs `1` breaks a naive merge in R.
    """
    values = col.to_numpy()
    if np.issubdtype(values.dtype, np.floating) and np.isfinite(values).all() \
            and np.all(values == np.round(values)):
        return values.astype(np.int64)
    return values


def item_table(arms: dict[str, dict], design: str, itemset: str,
               include_d: bool, variant: str = "main") -> pd.DataFrame:
    """One row per (arm, item), thresholds widened to b1..bK-1."""
    rows = []
    for arm, res in arms.items():
        n_thresh = res["b_mean"].shape[1]
        for i, item in enumerate(res["item_keys"]):
            row = {
                "design": design,
                "variant": variant,
                "itemset": itemset,
                "arm": arm,
                "item": item,
                "item_order": i,
                "a": res["a_mean"][i],
                "a_sd": res["a_sd"][i],
            }
            for k in range(n_thresh):
                row[f"b{k + 1}"] = res["b_mean"][i, k]
            for k in range(n_thresh):
                row[f"b{k + 1}_sd"] = res["b_sd"][i, k]
            if include_d:
                for k in range(n_thresh):
                    row[f"d{k + 1}"] = res["d_mean"][i, k]
                for k in range(n_thresh):
                    row[f"d{k + 1}_sd"] = res["d_sd"][i, k]
            row["max_rhat"] = res["max_rhat"]
            rows.append(row)
    return pd.DataFrame(rows)


def theta_table(
    arms: dict[str, dict], design: str, itemset: str, source: Path | None,
    variant: str = "main",
) -> pd.DataFrame:
    """One row per respondent, one theta/SE column pair per arm."""
    n = {arm: res["eap"].size for arm, res in arms.items()}
    if len(set(n.values())) != 1:
        raise ValueError(f"arms disagree on N: {n}")
    n_rows = next(iter(n.values()))

    out = pd.DataFrame({"design": np.repeat(design, n_rows),
                        "variant": np.repeat(variant, n_rows),
                        "itemset": np.repeat(itemset, n_rows)})
    if source is not None:
        src = read_dta(source)
        if len(src) != n_rows:
            raise ValueError(
                f"{source.name} has {len(src)} rows but the arms hold "
                f"{n_rows} thetas -- wrong source file for this design?"
            )
        if "id_work" not in src.columns:
            raise KeyError(f"{source.name} carries no id_work column")
        out["id_work"] = _as_int_if_integral(src["id_work"])
        if FORM_KEY in src.columns:
            out[FORM_KEY] = _as_int_if_integral(src[FORM_KEY])
    else:
        out["row"] = np.arange(n_rows)

    for arm, res in arms.items():
        out[f"{arm}_theta"] = res["eap"]
        out[f"{arm}_theta_se"] = res["psd"]
    return out


def export(
    results_dir: Path,
    design: str | None = None,
    itemset: str | None = None,
    source: Path | None = None,
    arms: tuple[str, ...] = ARMS,
    include_d: bool = False,
    variant: str = "main",
) -> tuple[Path, Path]:
    # Results live at results/<design>/<itemset>/, so the directory name alone
    # is "full" or "nobike" -- not a design. Fall back to the parent when the
    # leaf names an item set, so the CLI default cannot silently label every
    # design "full".
    if itemset is None:
        itemset = results_dir.name if results_dir.name in ITEM_SETS else ""
    if design is None:
        design = (results_dir.parent.name if results_dir.name in ITEM_SETS
                  else results_dir.name)

    loaded = {}
    for arm in arms:
        path = results_dir / f"{arm}.npz"
        if not path.exists():
            print(f"  skipping {arm}: no {path.name}", file=sys.stderr)
            continue
        loaded[arm] = _load_arm(path)
    if not loaded:
        raise FileNotFoundError(f"no arm .npz files under {results_dir}")

    keys = {arm: tuple(res["item_keys"]) for arm, res in loaded.items()}
    if len(set(keys.values())) != 1:
        raise ValueError(f"arms disagree on item order: {keys}")

    for arm, res in loaded.items():
        if res["max_rhat"] > RHAT_LIMIT:
            print(
                f"  WARNING: {arm} max R-hat {res['max_rhat']:.4f} > "
                f"{RHAT_LIMIT} -- exported but not trustworthy",
                file=sys.stderr,
            )

    items = item_table(loaded, design, itemset, include_d, variant)
    thetas = theta_table(loaded, design, itemset, source, variant)

    item_path = results_dir / "item_parameters.csv"
    theta_path = results_dir / "theta.csv"
    items.to_csv(item_path, index=False, float_format="%.6f")
    thetas.to_csv(theta_path, index=False, float_format="%.6f")

    print(f"  wrote {item_path}  ({len(items)} rows, arms: {', '.join(loaded)})")
    print(f"  wrote {theta_path}  ({len(thetas)} rows)")
    return item_path, theta_path


def main():
    ap = argparse.ArgumentParser(
        description="Export a/b item parameters and person thetas to CSV.")
    ap.add_argument("results_dir", type=Path,
                    help="results/<design>/<itemset>, holding "
                         "{birt,bmi,flat}.npz")
    ap.add_argument("--itemset", default=None,
                    help="item-set label (default: directory name if it names "
                         "one of %s)" % ", ".join(sorted(ITEM_SETS)))
    ap.add_argument("--design", default=None,
                    help="design label for the CSVs (default: directory name)")
    ap.add_argument("--variant", default="main",
                    help="which anchor variant these estimates come from: "
                         "'main' (six anchors) or 'reduced_anchor' (three). "
                         "Goes into a column of both CSVs so the two cannot "
                         "be pooled by accident.")
    ap.add_argument("--source", type=Path, default=None,
                    help="the design .dta, to attach id_work and grp_final")
    ap.add_argument("--arms", default=",".join(ARMS))
    ap.add_argument("--include-d", action="store_true",
                    help="also emit mirt intercepts d_ik = -a_i * b_ik")
    args = ap.parse_args()

    export(
        args.results_dir,
        design=args.design,
        itemset=args.itemset,
        source=args.source,
        arms=tuple(a.strip() for a in args.arms.split(",") if a.strip()),
        include_d=args.include_d,
        variant=args.variant,
    )


if __name__ == "__main__":
    main()
