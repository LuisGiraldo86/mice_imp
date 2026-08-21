#!/usr/bin/env python
"""
Preflight data contract check for the WD-FAB-DE Community Mobility subscale
(20 adapted CM items + 7 German bicycling items, Bike_2 entering as the
corrected `Bike_2_r_cor` -- see wdfab_io.EXCLUDED_ITEMS and CLAUDE.md fact 16)
before fitting GRModel / PairwiseOrdinalStackingModel
in bayesianquilts.

Every check here corresponds to a failure mode that is SILENT downstream.
bayesianquilts masks a response as missing whenever

    (y < 0) | (y >= response_cardinality) | isnan(y)

so an out-of-range code is not an error -- it just disappears from the
likelihood, and your complete-data (CD) reference calibration is quietly no
longer complete.

Usage:
    python -m mice_imp.cm_preflight \
        data_wdfab/WDFAB_ExperimentalData_CMCommonItem_Jul2026.dta
    python -m mice_imp.cm_preflight responses.csv --cardinality 5

`.dta` input is routed through wdfab_io.load_frame, which reads the numeric
codes (not the German value labels) and shifts the raw 1..K scale onto
0..K-1, raising on anything out of range. `.csv` input is assumed already
recoded, so checks 1-2 below are its only guard.
"""
import argparse
import sys

import numpy as np
import pandas as pd

from mice_imp.wdfab_io import (
    BIKE_KEYS, DA_KEYS, FORM_KEY, ITEM_KEYS, describe, load_frame,
)

OK, WARN, FAIL = "  ok  ", " WARN ", " FAIL "


def report(status, msg):
    print(f"[{status}] {msg}")
    return status


def check_presence(df):
    """All declared items must exist, with exactly the expected column names."""
    missing = [k for k in ITEM_KEYS if k not in df.columns]
    if missing:
        report(FAIL, f"{len(missing)} item(s) absent from the frame: {missing}")
        return False
    report(OK, f"all {len(ITEM_KEYS)} CM items present "
               f"({len(DA_KEYS)} adapted + {len(BIKE_KEYS)} bicycling)")

    # The trailing-letter stripper in Chang's advanced_column_merge would
    # rewrite DA062_r -> DA062_ and Bike_2_r -> Bike_2_ , breaking any lookup
    # by the original key.
    reversed_items = [k for k in ITEM_KEYS if k.endswith("_r")]
    if reversed_items:
        report(WARN,
               f"reverse-coded suffixes present ({reversed_items}); do NOT pass "
               "this frame through advanced_column_merge -- it strips trailing "
               "letters and will rename these columns")
    return True


def check_coding(df, cardinality):
    """Responses must be integers in 0..K-1, with missing encoded as NaN."""
    ok = True
    observed_levels = {}

    for k in ITEM_KEYS:
        vals = np.sort(df[k].dropna().unique())
        observed_levels[k] = vals

        non_integer = [v for v in vals if float(v) != int(v)]
        if non_integer:
            report(FAIL, f"{k}: non-integer response codes {non_integer}")
            ok = False

        out_of_range = [v for v in vals if v < 0 or v >= cardinality]
        if out_of_range:
            report(FAIL,
                   f"{k}: codes {out_of_range} fall outside 0..{cardinality - 1} "
                   "and WILL BE SILENTLY TREATED AS MISSING")
            ok = False

    n_levels = {k: len(v) for k, v in observed_levels.items()}
    distinct = sorted(set(n_levels.values()))
    if len(distinct) > 1:
        odd = {k: v for k, v in n_levels.items() if v != max(distinct)}
        report(WARN,
               f"items differ in number of observed categories {distinct}; "
               f"response_cardinality is a SCALAR on GRModel, so sparse items "
               f"must still be codeable on 0..{cardinality - 1}. "
               f"Items below the max: {odd}")
    else:
        report(OK, f"all items show {distinct[0]} distinct observed categories")

    never_zero = [k for k, v in observed_levels.items() if 0 not in v]
    if never_zero:
        report(WARN,
               f"category 0 never observed for {never_zero}; if your raw scale "
               "is 1..K you must subtract 1 before fitting")
    else:
        report(OK, "responses appear 0-indexed (category 0 observed everywhere)")
    return ok


def check_category_sparsity(df, cardinality, warn=40, fail=20):
    """Flag categories that are PRESENT but barely populated.

    check_coding above counts DISTINCT categories, which is what the scalar
    `response_cardinality` requires -- but it says nothing about how those
    categories are filled. A GRM estimates two thresholds around every
    interior category, and a category holding a handful of respondents
    leaves those thresholds effectively unidentified. The posterior then has
    a long flat ridge and NUTS diverges on most transitions, which surfaces
    as an R-hat failure a long way from its cause.

    Established 2026-08-13: on CD, DA068 has 10 responses in category 3,
    DA053 has 13, DA061 has 15. Both CD and the masked designs diverged on
    80-97% of transitions. Under a design that administers an item to one
    form, those counts fall to ~2.

    Counts are reported on the frame as given. On a masked design file that
    is the per-form-thinned count, which is the number that actually governs
    identification, so do not "correct" it back to the CD scale.
    """
    ok = True
    rows = []
    for k in ITEM_KEYS:
        counts = (df[k].value_counts()
                  .reindex(range(cardinality)).fillna(0).astype(int))
        rows.append((int(counts.min()), k, counts))

    flagged = sorted(r for r in rows if r[0] < warn)
    if not flagged:
        report(OK, f"every category of every item holds at least {warn} "
                   "responses")
        return True

    print(f"        items with a category below {warn} responses:")
    for mn, k, counts in flagged:
        marker = "  <-- BELOW %d" % fail if mn < fail else ""
        cells = " ".join(f"{int(c):5d}" for c in counts.values)
        print(f"          {k:10s} {cells}   min={mn}{marker}")

    hard = [k for mn, k, _ in flagged if mn < fail]
    if hard:
        report(FAIL,
               f"{len(hard)} item(s) have a category with fewer than {fail} "
               f"responses: {hard}. The thresholds either side of it are "
               "close to unidentified -- expect divergent transitions and an "
               "R-hat failure that will look like a sampler problem. Decide "
               "explicitly: collapse the category (note response_cardinality "
               "is a SCALAR, so this affects every item), tighten the "
               "threshold prior, or document that these item parameters are "
               "not interpretable.")
        ok = False
    else:
        report(WARN, f"{len(flagged)} item(s) have a thinly populated "
                     "category; watch their thresholds")
    return ok


def check_missingness(df):
    """Baseline missingness, before any simulated masking is applied."""
    sub = df[ITEM_KEYS]
    overall = sub.isna().to_numpy().mean()
    report(OK, f"N = {len(sub)} respondents, overall missing = {overall:.3%}")

    worst = sub.isna().mean().sort_values(ascending=False).head(5)
    print("        highest per-item missingness:")
    for k, v in worst.items():
        print(f"          {k:10s} {v:.3%}")

    complete_rows = int((~sub.isna().any(axis=1)).sum())
    report(OK if complete_rows > 0 else FAIL,
           f"{complete_rows} respondents ({complete_rows / len(sub):.1%}) have "
           "complete CM data -- this is your CD reference sample")
    return complete_rows


def check_structural_missingness(df):
    """
    Compare missingness in the bicycling block against the DA block.

    The CM scale is meant to be COMPLETE data -- it is the reference every
    approach is scored against. Bicycling items are the likely exception: a
    respondent who does not cycle may have skipped them, and that skip is
    plausibly correlated with community mobility itself. That is MNAR with
    respect to theta, not the MCAR your simulated masking assumes.
    """
    da = df[DA_KEYS].isna().to_numpy().mean()
    bike = df[BIKE_KEYS].isna().to_numpy().mean()
    report(OK, f"DA block missing = {da:.3%}   bike block missing = {bike:.3%}")

    for k in BIKE_KEYS:
        print(f"          {k:10s} {df[k].isna().mean():.3%}")

    ok = True
    if bike > max(0.05, 3 * da):
        report(FAIL,
               "bicycling items are far more incomplete than the rest of the "
               "scale. This looks structural ('I do not cycle'), not "
               "incidental. Treating it as ordinary missingness breaks the "
               "MCAR premise of the simulation -- decide explicitly whether to "
               "restrict CD to cyclists, move the bike block to a secondary "
               "analysis, or recode non-cycling as a substantive category.")
        ok = False

    # Is bike-block non-response related to ability? Crude but decisive probe.
    answered = ~df[BIKE_KEYS].isna().all(axis=1)
    da_score = df[DA_KEYS].mean(axis=1, skipna=True)
    if answered.nunique() > 1:
        m1, m0 = da_score[answered].mean(), da_score[~answered].mean()
        s_pool = da_score.std()
        d = (m1 - m0) / s_pool if s_pool > 0 else 0.0
        report(WARN if abs(d) > 0.2 else OK,
               f"DA mean score, bike-answered vs not: {m1:.3f} vs {m0:.3f} "
               f"(standardised difference {d:+.2f}). A large gap means bike "
               "non-response carries information about theta (MNAR).")
    return ok


def check_polarity(df):
    """
    Corrected item-total correlations must all be positive after reverse-scoring.

    A GRM will happily absorb a mis-polarised item into a negative slope, so
    the fit will not complain -- but anchor selection ranks items by average
    reliability, and the imputation model selects predictors by correlation,
    so the error propagates into both arms asymmetrically.
    """
    sub = df[ITEM_KEYS]
    negatives = []
    print("        corrected item-total correlations:")
    for k in ITEM_KEYS:
        rest = sub.drop(columns=[k]).mean(axis=1, skipna=True)
        pair = pd.concat([sub[k], rest], axis=1).dropna()
        if len(pair) < 20:
            report(WARN, f"{k}: too few complete pairs to assess polarity")
            continue
        r = pair.iloc[:, 0].corr(pair.iloc[:, 1])
        print(f"          {k:10s} r = {r:+.3f}"
              f"{'  <-- NEGATIVE' if r < 0 else ''}")
        if r < 0:
            negatives.append(k)

    if negatives:
        report(FAIL,
               f"{len(negatives)} item(s) correlate negatively with the rest of "
               f"the scale: {negatives}. Fix polarity BEFORE fitting either the "
               "GRM or the imputation model, and fit both from the same frame.")
        return False
    report(OK, "all item-total correlations positive; polarity is consistent")
    return True


def check_local_dependence(df, threshold=0.75):
    """
    Flag near-duplicate item pairs.

    Each bicycling item was adapted from an existing CM item, so each likely
    has a near-twin. Local dependence violates the GRM's conditional
    independence assumption, distorts anchor selection (two twins carry less
    information than two independent anchors), and hands the imputation arm an
    unusually strong predictor for exactly those items.
    """
    corr = df[ITEM_KEYS].corr(min_periods=30)

    pairs = [(a, b, corr.loc[a, b])
             for i, a in enumerate(ITEM_KEYS)
             for b in ITEM_KEYS[i + 1:]
             if pd.notna(corr.loc[a, b]) and abs(corr.loc[a, b]) >= threshold]

    if not pairs:
        report(OK, f"no item pair correlates above |r| = {threshold}")
        return True

    report(WARN, f"{len(pairs)} near-duplicate pair(s) above |r| = {threshold}:")
    for a, b, r in sorted(pairs, key=lambda t: -abs(t[2])):
        cross = "  [DA-bike pair]" if (a in DA_KEYS) != (b in DA_KEYS) else ""
        print(f"          {a:10s} {b:10s} r = {r:+.3f}{cross}")
    print("        Do not select both members of a pair as anchor items.")
    return True


def check_dimensionality(df):
    """
    Crude unidimensionality signal from the eigenvalues of the item correlation
    matrix on complete cases.

    GRModel is being fitted with dim=1. If the bicycling items form their own
    factor, that specification is misspecified, and the misspecification will
    be attributed to whichever missing-data method you happen to be testing.
    """
    sub = df[ITEM_KEYS].dropna()
    if len(sub) < 5 * len(ITEM_KEYS):
        report(WARN, f"only {len(sub)} complete cases; skipping eigenvalue check")
        return True

    ev = np.linalg.eigvalsh(np.corrcoef(sub.to_numpy().T))[::-1]
    ratio = ev[0] / ev[1] if ev[1] > 0 else np.inf
    report(OK, f"first three eigenvalues: {ev[0]:.2f}, {ev[1]:.2f}, {ev[2]:.2f} "
               f"(lambda1/lambda2 = {ratio:.2f})")
    if ratio < 3:
        report(WARN,
               "lambda1/lambda2 below 3 suggests the scale may not be "
               "unidimensional. Check whether the second factor is the "
               "bicycling block before committing to dim=1.")
    return True


def main():
    ap = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("path", help=".dta or .csv containing the CM item columns")
    ap.add_argument("--cardinality", type=int, default=5,
                    help="response_cardinality you intend to pass to GRModel")
    args = ap.parse_args()

    df = load_frame(args.path, cardinality=args.cardinality)
    print(f"\nLoaded {args.path}: {df.shape[0]} rows x {df.shape[1]} columns\n")

    # Checks 3-7 characterise the CD reference. On a masked design file they
    # still run, but missingness is dominated by the design and the
    # complete-case checks have nothing to work with -- say so rather than
    # letting the output read as if it were a clean bill of health.
    if FORM_KEY in df.columns:
        print(f"NOTE: '{FORM_KEY}' present -- this is a MASKED design file. "
              "Checks 3-7 describe the design, not the data contract. Run "
              "preflight on the CD export for those.\n")
        describe(df)
        print()

    print("--- 1. item presence -------------------------------------------")
    if not check_presence(df):
        sys.exit(1)

    print("\n--- 2. response coding -----------------------------------------")
    coding_ok = check_coding(df, args.cardinality)

    print("\n--- 2b. category sparsity ---------------------------------------")
    sparsity_ok = check_category_sparsity(df, args.cardinality)

    print("\n--- 3. overall missingness -------------------------------------")
    check_missingness(df)

    print("\n--- 4. structural missingness (bicycling block) ----------------")
    structural_ok = check_structural_missingness(df)

    print("\n--- 5. polarity ------------------------------------------------")
    polarity_ok = check_polarity(df)

    print("\n--- 6. local dependence ----------------------------------------")
    check_local_dependence(df)

    print("\n--- 7. dimensionality ------------------------------------------")
    check_dimensionality(df)

    print("\n--- summary ----------------------------------------------------")
    if coding_ok and polarity_ok and structural_ok and sparsity_ok:
        print("Data contract satisfied. Safe to proceed to masking + fitting.")
    else:
        print("Fix the FAIL items above before fitting; the failures listed "
              "are silent downstream, not loud.")
        sys.exit(1)


if __name__ == "__main__":
    main()
