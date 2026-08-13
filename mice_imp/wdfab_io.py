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

# The bicycling items unique to the German instrument. Bike_2 is EXCLUDED --
# see EXCLUDED_ITEMS below.
BIKE_KEYS = [
    "Bike_1", "Bike_3", "Bike_4", "Bike_5", "Bike_6", "Bike_7",
]

# Canonical order. Never re-sort: posterior item-parameter arrays are
# positional and get aligned against mirt output.
ITEM_KEYS = DA_KEYS + BIKE_KEYS

# Bike_2 is dropped, leaving 26 items. Established 2026-08-13:
#
#   In the CD export, Bike_2_r == 6 - Bike_2 exactly (r = -1.000, perfect
#   anti-diagonal crosstab) -- one item stored in two columns. Bike_2 is the
#   correctly oriented one (+0.363 against the rest of the scale); Bike_2_r
#   is flipped (-0.363).
#
#   The design files then treated the two columns as TWO SEPARATE ITEMS in
#   the masking pool: Bike_2 was administered to form 1 (397 observed) and
#   Bike_2_r to form 3 (393 observed), disjointly, in all three designs.
#
# So there is no way to use this item that is both complete and faithful to
# the design. Merging the columns recovers all 790 responses but makes the
# item span forms 1 and 3, pushing form-pair overlap to 6/7/6 in the
# common-item design -- an asymmetric anchor set that Stocking-Lord linking
# and MG-IRT would both be reading unequally. Taking either column alone
# discards half the item's data.
#
# Dropping it keeps every design's form structure exactly as specified and
# costs the weakest bike item (+0.363, against +0.65..+0.735 for the other
# six). This is an INTERIM decision: the design files should be regenerated
# from a 27-column pool, after which Bike_2 can be restored here.
EXCLUDED_ITEMS = ["Bike_2", "Bike_2_r"]

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
    df = read_dta(path)
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
