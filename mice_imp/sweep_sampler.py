#!/usr/bin/env python
"""
Does B-IRT's divergence rate respond to the step size, or is the geometry bad?

Measured on the CommonItem/nobike smoke run, B-IRT kept only 4.0% / 4.5% of
its transitions non-divergent, on CPU and GPU alike. B-MI, on the same data
and items but at step_size=5e-4 / target_accept=0.98, kept 61.0%.

That is suggestive but not a controlled comparison: B-MI also attaches
imputation PMFs, which changes the posterior geometry itself (CLAUDE.md fact
8 says it makes it HARDER, which is why it was given the gentler sampler).
So B-MI is doing better on a harder problem, and the only way to know whether
the step size is responsible is to vary the step size alone.

Divergences are not merely wasted compute. They cluster in the high-curvature
regions the integrator cannot traverse, so the chain systematically
under-explores exactly those regions -- the posterior comes out BIASED, not
just noisy, and running longer does not fix it. That is why this runs before
any decision about scheduling the grid.

Everything is held fixed -- data, items, seed, warmup, samples, ADVI -- and
only (step_size, target_accept_prob) varies. Each configuration writes to its
own directory so nothing here can clobber a real run.

Two outcomes, and they mean opposite things:

  divergences COLLAPSE at smaller step sizes
      A tuning problem. Change the defaults and the grid is viable. Note the
      cost: a smaller step size means more leapfrog steps per transition, so
      the full runs get SLOWER. Re-estimate the grid before scheduling it.

  divergences PERSIST at 1e-4
      No step size saves you; the geometry itself is pathological. That is
      what thresholds either side of a category holding 2 respondents look
      like -- a flat likelihood ridge with no curvature to sample. The fix
      has to be in the model (collapse the category, tighten the threshold
      prior, or declare those parameters uninterpretable), which is open
      issue E.

    python -m mice_imp.sweep_sampler
    python -m mice_imp.sweep_sampler --design Standard --items full
"""
from __future__ import annotations

import argparse
import contextlib
import os
import re
import sys
import time
from pathlib import Path

os.environ.setdefault("JAX_PLATFORMS", "cpu")
os.environ.setdefault("JAX_ENABLE_X64", "1")

import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402

REPO = Path(__file__).resolve().parent.parent
if str(REPO) not in sys.path:
    sys.path.insert(0, str(REPO))

from mice_imp.run_grid import _Tee, data_path  # noqa: E402
from mice_imp.wdfab_io import ITEM_SETS, load_cm  # noqa: E402

# (step_size, target_accept). The first is the current B-IRT default and is
# the baseline the others have to beat; the second is what B-MI already uses.
CONFIGS = [
    (2e-3, 0.95),
    (5e-4, 0.98),
    (1e-4, 0.98),
]


def _parse(text: str) -> dict:
    """The sampler reports its diagnostics by printing them."""
    ratios = [float(x) for x in re.findall(r"Non-divergent ratio: ([\d.]+)", text)]
    steps = [float(x) for x in re.findall(r"adapted step_size=([\d.eE+-]+)", text)]
    rhat = re.search(r"max R-hat overall: ([\d.]+)", text)
    return {
        "nondiv_min": min(ratios) if ratios else np.nan,
        "nondiv_max": max(ratios) if ratios else np.nan,
        "adapted_step_min": min(steps) if steps else np.nan,
        "adapted_step_max": max(steps) if steps else np.nan,
        "step_spread": (max(steps) / min(steps)) if steps and min(steps) > 0 else np.nan,
        "max_rhat": float(rhat.group(1)) if rhat else np.nan,
    }


def main() -> None:
    ap = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--design", default="CommonItem")
    ap.add_argument("--items", choices=sorted(ITEM_SETS), default="nobike")
    ap.add_argument("--num-chains", type=int, default=2)
    ap.add_argument("--num-warmup", type=int, default=200)
    ap.add_argument("--num-samples", type=int, default=200)
    ap.add_argument("--seed", type=int, default=42)
    ap.add_argument("--out", type=Path, default=REPO / "results" / "_sweep")
    args = ap.parse_args()

    from mice_imp.cm_bayes_arms import fit_arm

    keys = ITEM_SETS[args.items]
    df = load_cm(data_path(args.design), cardinality=5)[keys]
    args.out.mkdir(parents=True, exist_ok=True)

    print(f"sweep: {args.design}/{args.items}, {len(keys)} items, "
          f"{args.num_chains} chains, {args.num_warmup}/{args.num_samples}, "
          f"birt only\n  out: {args.out}")

    rows = []
    for step, accept in CONFIGS:
        tag = f"step{step:g}_acc{accept:g}"
        cfg_dir = args.out / tag
        cfg_dir.mkdir(parents=True, exist_ok=True)
        log = cfg_dir / "sweep.log"
        print(f"\n{'=' * 66}\n  step_size={step:g}  target_accept={accept:g}\n{'=' * 66}",
              flush=True)

        t0 = time.time()
        row = {"step_size": step, "target_accept": accept,
               "status": "running", "minutes": None}
        try:
            with open(log, "w") as fh:
                tee = _Tee(fh, sys.__stdout__)
                with contextlib.redirect_stdout(tee), contextlib.redirect_stderr(tee):
                    fit_arm("birt", df, keys, 5, cfg_dir,
                            imputation_model=None, run_advi=True,
                            num_chains=args.num_chains,
                            num_warmup=args.num_warmup,
                            num_samples=args.num_samples,
                            step_size=step, target_accept_prob=accept,
                            seed=args.seed)
            row["status"] = "ok"
        except Exception as exc:                        # noqa: BLE001
            row["status"] = f"FAILED: {type(exc).__name__}: {exc}"[:120]
            print(f"  FAILED -- see {log}", file=sys.__stdout__, flush=True)

        row["minutes"] = round((time.time() - t0) / 60, 1)
        if log.exists():
            row.update(_parse(log.read_text()))
        rows.append(row)
        pd.DataFrame(rows).to_csv(args.out / "sweep_summary.csv", index=False)

    df_out = pd.DataFrame(rows)
    print("\n" + "=" * 66 + "\nSWEEP RESULT (B-IRT only)\n" + "=" * 66)
    print(df_out.to_string(index=False))

    ok = df_out[df_out.status == "ok"]
    if not ok.empty and ok.nondiv_min.notna().any():
        best = ok.loc[ok.nondiv_min.idxmax()]
        base = ok[ok.step_size == 2e-3]
        print(f"\nbest: step_size={best.step_size:g} acc={best.target_accept:g} "
              f"-> non-divergent {best.nondiv_min:.3f}-{best.nondiv_max:.3f}, "
              f"R-hat {best.max_rhat:.4f}, {best.minutes} min")
        if not base.empty:
            b = base.iloc[0]
            print(f"baseline (2e-3/0.95): non-divergent {b.nondiv_min:.3f}, "
                  f"R-hat {b.max_rhat:.4f}, {b.minutes} min")
            if best.nondiv_min < 0.5:
                print("\nNo configuration reaches a 50% non-divergent rate. That points "
                      "at the geometry rather than the sampler -- open issue E (near-"
                      "empty categories leaving thresholds unidentified) is the live "
                      "explanation, and no step size will fix it.")
            elif best.minutes > 1.5 * b.minutes:
                print(f"\nNote the cost: {best.minutes / b.minutes:.1f}x the baseline "
                      "wall time per arm. Re-estimate the grid before scheduling it.")


if __name__ == "__main__":
    main()
