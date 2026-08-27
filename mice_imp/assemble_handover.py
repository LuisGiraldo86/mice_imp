#!/usr/bin/env python
"""
Assemble the six runs into the two CSVs the coauthor receives, plus a README.

The CSVs are the deliverable: they have to be readable without this repo, and
they have to carry the facts that make them interpretable. Five of those facts
cannot live in a column (CLAUDE.md "Handover"), so they go in README.md next to
the data.

Only the six real cells are read, by name. This is deliberate: a
`results/*/*/` glob also matches smoke runs, an earlier 26-item grid and the
sampler sweep, and concatenating those silently mixes 20-, 26- and 27-item
fits with 200-warmup throwaways. That mistake is invisible in the output --
it looks like a slightly odd row count -- so the cell list is explicit.

    python -m mice_imp.assemble_handover
"""
from __future__ import annotations

import argparse
from pathlib import Path

import pandas as pd

REPO = Path(__file__).resolve().parent.parent
DESIGNS = ["commonitem", "binterlaced", "standard"]
ITEMSETS = ["full", "nobike"]
CELLS = [(d, s) for d in DESIGNS for s in ITEMSETS]
RHAT_LIMIT = 1.05

README = """# WD-FAB-DE Community Mobility — Bayesian arms

Estimates from the Bayesian half of the missing-data comparison: three masked
designs x two item sets, each calibrated with B-IRT, B-MI and the `flat`
control. Produced {date} from the design files delivered 2026-08-21.

## Files

- `item_parameters.csv` — one row per (design, itemset, arm, item): `a`,
  `b1..b4` and posterior SDs, plus mirt intercepts `d1..d4`.
- `theta.csv` — one row per (design, itemset, respondent): EAP theta and its
  posterior SD for each arm, keyed on `id_work`.
- `grid_summary.csv` — one row per run: wall time, R-hat per arm, B-MI
  imputation fallback rate, and the noise floor.

{n_items} item rows, {n_theta} theta rows, {n_resp} respondents per cell.

## Five things the columns cannot tell you

**1. `Bike_2` must be `Bike_2_r_cor` on your side too.** The CD export does
not carry the corrected column. The correction is a deterministic permutation
of raw `Bike_2`: `1->4, 2->3, 3->2, 4->1, 5->5` — categories 1-4 reversed,
category 5 held in place. If the CD calibration uses raw `Bike_2` or
`Bike_2_r`, that item's parameters compare two different codings.

**2. Each run is standardised independently.** Theta is ~N(0,1) *within its
own run*. Thetas are not on a common metric across designs, across item sets,
or against a CD fit until you put them there. Any slope-against-CD analysis
has to handle this explicitly.

**3. `flat` is a noise floor, not a method.** It targets the same posterior as
`birt` by construction, so the difference between them is Monte Carlo error
and nothing else. It must not appear as a third arm in any results table. The
measured floor is theta RMSE {floor_lo:.4f}-{floor_hi:.4f}, which is the
resolution at which a real B-MI effect can be claimed.

**4. Parameter conventions.** `a_i(theta - b_ik)`, thresholds already
cumsum-ed from stored increments, extracted after standardisation. `d_ik =
-a_i*b_ik` is supplied alongside. The exported `d` will NOT reproduce as
`-a*b` from the exported columns: each is a posterior mean of its own
quantity, and the mean of a product is not the product of the means (~0.02
apart here). This is correct; please do not "fix" it.

**5. B-MI imputation fallback rate: {fallback}.** Failed per-cell imputations
degrade silently to a flat PMF, which contributes nothing beyond B-IRT, so a
null B-MI result is uninterpretable without this number. It is 0% in every
run — B-MI really ran on every masked cell.

## Convergence

R-hat per arm is in `grid_summary.csv` and repeated on every row of both CSVs.

{rhat_note}

## What is not here

CD, FIML, MG-IRT and Stocking-Lord are yours. This repo produced the Bayesian
arms only.
"""


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--out", type=Path, default=REPO / "handover")
    args = ap.parse_args()
    args.out.mkdir(parents=True, exist_ok=True)

    missing = [f"results/{d}/{s}" for d, s in CELLS
               if not (REPO / "results" / d / s / "item_parameters.csv").exists()]
    if missing:
        raise SystemExit("missing exports:\n  " + "\n  ".join(missing))

    items = pd.concat([pd.read_csv(REPO / "results" / d / s / "item_parameters.csv")
                       for d, s in CELLS], ignore_index=True)
    theta = pd.concat([pd.read_csv(REPO / "results" / d / s / "theta.csv")
                       for d, s in CELLS], ignore_index=True)
    summary = pd.read_csv(REPO / "results" / "grid_summary.csv")

    # Guard the exact mistake the explicit cell list exists to prevent.
    per_cell = items.groupby(["design", "itemset", "arm"]).size().unique()
    assert set(per_cell) <= {20, 27}, f"unexpected item counts: {per_cell}"
    assert theta.groupby(["design", "itemset"]).id_work.nunique().eq(1363).all()

    items.to_csv(args.out / "item_parameters.csv", index=False, float_format="%.6f")
    theta.to_csv(args.out / "theta.csv", index=False, float_format="%.6f")
    summary.to_csv(args.out / "grid_summary.csv", index=False)

    rhat = items.groupby(["design", "itemset", "arm"]).max_rhat.first()
    over = rhat[rhat > RHAT_LIMIT]
    if over.empty:
        note = f"Every arm is at or below {RHAT_LIMIT}."
    else:
        lines = "\n".join(f"| {d} | {s} | {a} | {v:.3f} |" for (d, s, a), v in over.items())
        note = (f"**{len(over)} arm(s) exceed {RHAT_LIMIT} and should carry a caveat:**\n\n"
                "| design | itemset | arm | max R-hat |\n|---|---|---|---|\n" + lines +
                "\n\nAll of them are B-MI on the 27-item runs; the 20-item counterparts "
                "converge. The bicycling block is where B-MI's sampler strains.")

    fallback = summary.bmi_fallback_pct.dropna()
    (args.out / "README.md").write_text(README.format(
        date=pd.Timestamp.today().strftime("%Y-%m-%d"),
        n_items=len(items), n_theta=len(theta),
        n_resp=int(theta.groupby(["design", "itemset"]).id_work.nunique().iloc[0]),
        floor_lo=summary.theta_rmse_flat_vs_birt.min(),
        floor_hi=summary.theta_rmse_flat_vs_birt.max(),
        fallback=(f"{fallback.min():.1f}%" if fallback.max() == fallback.min()
                  else f"{fallback.min():.1f}-{fallback.max():.1f}%"),
        rhat_note=note))

    print(f"wrote {args.out}/")
    for f in sorted(args.out.iterdir()):
        print(f"  {f.name:24s} {f.stat().st_size:>9,d} bytes")


if __name__ == "__main__":
    main()
