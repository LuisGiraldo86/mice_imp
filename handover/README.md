# WD-FAB-DE Community Mobility — Bayesian arms

Estimates from the Bayesian half of the missing-data comparison: three masked
designs x two item sets, each calibrated with B-IRT, B-MI and the `flat`
control. Produced 2026-08-27 from the design files delivered 2026-08-21.

## Files

- `item_parameters.csv` — one row per (design, itemset, arm, item): `a`,
  `b1..b4` and posterior SDs, plus mirt intercepts `d1..d4`.
- `theta.csv` — one row per (design, itemset, respondent): EAP theta and its
  posterior SD for each arm, keyed on `id_work`.
- `grid_summary.csv` — one row per run: wall time, R-hat per arm, B-MI
  imputation fallback rate, and the noise floor.

423 item rows, 8178 theta rows, 1363 respondents per cell.

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
measured floor is theta RMSE 0.0011-0.0023, which is the
resolution at which a real B-MI effect can be claimed.

**4. Parameter conventions.** `a_i(theta - b_ik)`, thresholds already
cumsum-ed from stored increments, extracted after standardisation. `d_ik =
-a_i*b_ik` is supplied alongside. The exported `d` will NOT reproduce as
`-a*b` from the exported columns: each is a posterior mean of its own
quantity, and the mean of a product is not the product of the means (~0.02
apart here). This is correct; please do not "fix" it.

**5. B-MI imputation fallback rate: 0.0%.** Failed per-cell imputations
degrade silently to a flat PMF, which contributes nothing beyond B-IRT, so a
null B-MI result is uninterpretable without this number. It is 0% in every
run — B-MI really ran on every masked cell.

## Convergence

R-hat per arm is in `grid_summary.csv` and repeated on every row of both CSVs.

**3 arm(s) exceed 1.05 and should carry a caveat:**

| design | itemset | arm | max R-hat |
|---|---|---|---|
| binterlaced | full | bmi | 1.105 |
| commonitem | full | bmi | 1.054 |
| standard | full | bmi | 1.132 |

All of them are B-MI on the 27-item runs; the 20-item counterparts converge. The bicycling block is where B-MI's sampler strains.

## What is not here

CD, FIML, MG-IRT and Stocking-Lord are yours. This repo produced the Bayesian
arms only.
