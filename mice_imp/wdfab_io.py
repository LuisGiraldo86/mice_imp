#!/usr/bin/env python
"""
Loading for the WD-FAB-DE Community Mobility frames.

Both the complete-data (CD) reference and the three masked design files ship
as Stata `.dta`, not CSV, and both encode CM responses as **1..K** with value
labels attached. Two silent failure modes follow, and this module exists to
close them:

1. `pd.read_stata` defaults to `convert_categoricals=True`, which returns the
   German label *strings*. Anything downstream that expects numbers either
   raises somewhere unhelpful or -- worse -- coerces.

2. GRModel masks a response wherever
   `(y < 0) | (y >= response_cardinality) | isnan(y)`.
   Feed it 1..5 with `response_cardinality=5` and every top-category response
   disappears from the likelihood without an error. That is the single most
   damaging thing that can happen to this project, because it corrupts the CD
   reference every other arm is scored against.

So: read with categoricals off, verify the observed range really is 1..K, and
shift explicitly. The shift is *checked*, never assumed -- if an item shows an
unexpected code the loader raises rather than quietly producing a frame that
fits fine and means nothing.

Deliberately NOT using `.cat.codes` (as `load_wdfab_single_pop.py` does):
those codes are 0-indexed relative to the categories *observed in this file*,
so a masked design where some item never shows its lowest category would be
recoded onto a shifted scale, differently per design. Reading the numeric
codes directly is invariant to which categories happen to appear.
"""
from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd

# The 20 items adapted from the English (American) WD-FAB.
DA_KEYS = [
    "DA051", "DA053", "DA054", "DA055", "DA058", "DA060", "DA061",
    "DA062_r", "DA063_r", "DA064", "DA066", "DA067", "DA052", "DA068",
    "DA069_r", "DA070", "DA071", "DA072", "DA073", "DA074",
]

# The bicycling items unique to the German instrument. All seven are in --
# Bike_2 enters as `Bike_2_r_cor`, the corrected recoding shipped 2026-08-21;
# see BIKE2 below.
BIKE_KEYS = [
    "Bike_1", "Bike_2_r_cor", "Bike_3", "Bike_4", "Bike_5", "Bike_6",
    "Bike_7",
]

# Canonical order. Never re-sort: posterior item-parameter arrays are
# positional and get aligned against mirt output.
ITEM_KEYS = DA_KEYS + BIKE_KEYS

# Bike_2 is RESTORED as `Bike_2_r_cor` (2026-08-21), giving 27 items. The
# history matters, because the raw columns are still in the files and picking
# the wrong one is silent:
#
#   The item was originally shipped as two columns, `Bike_2` and
#   `Bike_2_r == 6 - Bike_2`, and the design files treated them as two
#   separate items in the masking pool (form 1 and form 3, disjointly). That
#   made the item unusable either way and it was dropped.
#
#   Both columns were also mis-scored. Verified on the 393 form-3 rows of
#   every design file, the correction is a clean deterministic permutation
#   of `Bike_2`:
#
#       1 -> 4    2 -> 3    3 -> 2    4 -> 1    5 -> 5
#
#   i.e. reverse categories 1..4 and leave category 5 where it is. Category 5
#   is not the top of the 1..4 continuum -- respondents in it have a mean
#   score on the other 26 items of 3.29, against 2.21 / 1.98 / 1.71 / 1.57
#   for categories 1..4. So the raw 1..4 run is reverse-oriented while 5 sits
#   above all of them, and the flat `6 - x` reversal that produced `Bike_2_r`
#   sent those 303 respondents to the bottom of the scale.
#
#   That is why neither original column worked: item-rest correlation was
#   +0.363 for `Bike_2` and -0.363 for `Bike_2_r`. `Bike_2_r_cor` is
#   monotone in the rest-score across all five categories (1.45 / 1.68 /
#   1.97 / 2.17 / 3.29) and correlates +0.614, in line with the other six
#   bicycling items (+0.65..+0.735).
#
# In the current design files `Bike_2_r_cor` carries the design masking
# (form 3, 393 responses, one form in all three designs). `Bike_2` and
# `Bike_2_r` are leftover source columns -- `Bike_2_r` is now unmasked
# (all 1191 responses, every form), the same trap as DA062 / DA063 / DA069
# in RAW_POLARITY_TRAPS. Using either would take the old, wrong coding, and
# `Bike_2_r` would additionally drop the design masking entirely.
EXCLUDED_ITEMS = ["Bike_2", "Bike_2_r"]

# The corrected recoding, as a map from the raw `Bike_2` code. Applied to any
# frame that lacks `Bike_2_r_cor` -- which is how the CD export gets it, since
# the correction shipped in the design files only. Do not infer this from
# `Bike_2_r`: that column is `6 - Bike_2`, so recovering the correction from
# it requires the same table run backwards, and it is unmasked in the design
# files, which would silently un-mask the item.
BIKE2_RAW = "Bike_2"
BIKE2_CORRECTED = "Bike_2_r_cor"
BIKE2_RECODE = {1: 4, 2: 3, 3: 2, 4: 1, 5: 5}

# Every dataset is run twice: once on the full 27-item scale, once on the 20
# adapted DA items with the bicycling block dropped. The bike items are unique
# to the German instrument, they carry the strongest local dependence on CD
# (Bike_1/Bike_7 r = 0.931, Bike_4/Bike_5 0.921 -- open issue B), and their
# nonresponse is the one place where the MCAR premise is measurably strained
# (open issue A). The no-bike run is what shows whether any conclusion about
# the five calibration approaches depends on them.
#
# Dropping the block does not touch the anchors -- all six are DA items -- so
# form-pair overlap is unchanged (6/6/6, 3/3/0, 2/2/2). Only the single-form
# items thin out, from 7 per form to 14 spread across three forms.
ITEM_SETS = {
    "full": ITEM_KEYS,
    "nobike": DA_KEYS,
}

# Reverse-scored items are carried in `_r` form, and for DA062 / DA063 /
# DA069 that is the column to use: in the design files the un-suffixed
# column is the unmasked source (observed in every form, ~1225-1266 rows)
# while the `_r` column carries the design masking. Using the raw column
# would flip polarity for those items only, and the GRM would absorb it into
# a negative slope without complaining.
RAW_POLARITY_TRAPS = ["DA062", "DA063", "DA069"]

assert not set(ITEM_KEYS) & set(EXCLUDED_ITEMS), \
    "ITEM_KEYS must not contain an excluded item -- see EXCLUDED_ITEMS"
assert not set(ITEM_KEYS) & set(RAW_POLARITY_TRAPS), \
    "ITEM_KEYS must use the _r column for reverse-scored items"

# Person-level variables used for the stratified comparisons. Present in the
# masked design files; the CD export carries Z_SEX / Z_SRH / ALTER instead.
COVARIATE_KEYS = ["grp_final", "sex", "age3cat", "srh3cat", "married"]

# Form assignment under the planned-missingness designs: three near-equal
# groups. Masking is deterministic per form (verified 2026-08-13: within a
# form every item is either fully masked or administered, with only the
# baseline item nonresponse varying between respondents), so this is the
# grouping variable MG-IRT groups on.
FORM_KEY = "grp_final"


def read_dta(path: str | Path) -> pd.DataFrame:
    """Read a WD-FAB `.dta` with numeric response codes preserved."""
    return pd.read_stata(Path(path).expanduser(), convert_categoricals=False)


def recode_items(
    df: pd.DataFrame,
    item_keys: list[str] = ITEM_KEYS,
    cardinality: int = 5,
    raw_min: int = 1,
) -> pd.DataFrame:
    """Shift raw 1..K item codes onto the 0..K-1 range GRModel expects.

    Returns a new frame containing only `item_keys`, as float64 with missing
    as NaN.

    Raises on any code outside `raw_min .. raw_min + cardinality - 1`. That is
    the point of the function: an out-of-range code is invisible to GRModel,
    so it has to be loud here or it is never loud at all.
    """
    absent = [k for k in item_keys if k not in df.columns]
    if absent:
        raise KeyError(f"items absent from frame: {absent}")

    raw_max = raw_min + cardinality - 1
    out = {}
    for k in item_keys:
        col = pd.to_numeric(df[k], errors="coerce").astype(np.float64)

        observed = np.unique(col.dropna().to_numpy())
        non_integer = observed[observed != np.round(observed)]
        if non_integer.size:
            raise ValueError(f"{k}: non-integer response codes {non_integer}")

        bad = observed[(observed < raw_min) | (observed > raw_max)]
        if bad.size:
            raise ValueError(
                f"{k}: codes {bad.tolist()} fall outside the expected raw "
                f"range {raw_min}..{raw_max}. Shifting anyway would push them "
                f"outside 0..{cardinality - 1}, where GRModel drops them "
                "silently. Resolve the coding before loading."
            )

        out[k] = col - raw_min

    return pd.DataFrame(out, index=df.index)[item_keys]


def derive_bike2_correction(df: pd.DataFrame) -> pd.DataFrame:
    """Add `Bike_2_r_cor` from raw `Bike_2` if the frame does not carry it.

    The three design files ship the corrected column; the CD export does not.
    Both have to use the same coding or the comparison is measuring a recode
    (see BIKE2_RECODE, and the fact that the GRM and the imputation model must
    be fit from the same frame -- a re-coding in between permutes the category
    PMFs the imputation model returns).

    A no-op when the column is already present. Never overwrites: if the file
    supplies it, the file wins, and a disagreement is raised rather than
    papered over.
    """
    if BIKE2_CORRECTED in df.columns and BIKE2_RAW in df.columns:
        both = df[BIKE2_CORRECTED].notna() & df[BIKE2_RAW].notna()
        if both.any():
            expected = df.loc[both, BIKE2_RAW].map(BIKE2_RECODE)
            clash = int((expected.to_numpy() != df.loc[both, BIKE2_CORRECTED]
                         .to_numpy()).sum())
            if clash:
                raise ValueError(
                    f"{BIKE2_CORRECTED} disagrees with BIKE2_RECODE applied to "
                    f"{BIKE2_RAW} on {clash} of {int(both.sum())} rows. The "
                    "correction shipped by the collaborators is no longer the "
                    "permutation recorded here -- re-derive it before fitting."
                )
        return df

    if BIKE2_CORRECTED in df.columns or BIKE2_RAW not in df.columns:
        return df

    codes = pd.to_numeric(df[BIKE2_RAW], errors="coerce")
    unknown = sorted(set(codes.dropna().astype(int)) - set(BIKE2_RECODE))
    if unknown:
        raise ValueError(
            f"{BIKE2_RAW}: codes {unknown} have no entry in BIKE2_RECODE"
        )

    out = df.copy()
    out[BIKE2_CORRECTED] = codes.map(BIKE2_RECODE).astype(np.float64)
    return out


def load_cm(
    path: str | Path,
    item_keys: list[str] = ITEM_KEYS,
    cardinality: int = 5,
    raw_min: int = 1,
    keep_covariates: bool = True,
) -> pd.DataFrame:
    """Load a CM frame (CD reference or masked design) ready for fitting.

    Returns the recoded item columns in canonical order, plus whichever of
    `COVARIATE_KEYS` the file happens to carry. Row order is preserved: the
    masked design files are row-aligned with the CD export (verified by exact
    agreement on every unmasked cell), so thetas can be compared positionally.
    """
    df = derive_bike2_correction(read_dta(path))
    items = recode_items(df, item_keys, cardinality, raw_min)

    if not keep_covariates:
        return items

    extra = [c for c in COVARIATE_KEYS if c in df.columns]
    return pd.concat([items, df[extra]], axis=1)


def load_frame(path: str | Path, **kwargs) -> pd.DataFrame:
    """Load from `.dta` or `.csv`, dispatching on suffix.

    CSV is assumed already recoded to 0..K-1 (it would have come from this
    module in the first place); `.dta` goes through the full check.
    """
    path = Path(path).expanduser()
    if path.suffix.lower() == ".dta":
        return load_cm(path, **kwargs)
    return pd.read_csv(path, low_memory=False)


def describe(df: pd.DataFrame, item_keys: list[str] = ITEM_KEYS) -> None:
    """One-screen summary: N, missingness, and the per-form design layout."""
    sub = df[item_keys]
    print(f"N = {len(df)}   items = {len(item_keys)}   "
          f"missing = {sub.isna().to_numpy().mean():.1%}   "
          f"complete rows = {int((~sub.isna().any(axis=1)).sum())}")

    if FORM_KEY not in df.columns:
        return

    print(f"\nadministered items by {FORM_KEY} "
          "(x = administered, . = masked by design):")
    for form, idx in df.groupby(FORM_KEY).groups.items():
        miss = sub.loc[idx].isna().mean()
        row = "".join("." if m > 0.95 else "x" for m in miss)
        n_admin = int((miss <= 0.95).sum())
        print(f"  form {form!s:>4}  n={len(idx):5d}  {row}  ({n_admin} items)")

    admin = {f: {k for k, m in sub.loc[i].isna().mean().items() if m <= 0.95}
             for f, i in df.groupby(FORM_KEY).groups.items()}
    common = set.intersection(*admin.values()) if admin else set()
    print(f"\n  administered in every form ({len(common)}): "
          f"{[k for k in item_keys if k in common]}")


if __name__ == "__main__":
    import argparse

    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("path", help=".dta (or .csv) CM frame")
    ap.add_argument("--cardinality", type=int, default=5)
    args = ap.parse_args()

    frame = load_frame(args.path, cardinality=args.cardinality)
    print(f"\n{args.path}\n")
    describe(frame)
