"""
Trimmed data loader: single-population WDFAB data from a Stata .dta file.

Compared to the reference script's load_wdfab_data(), this drops:
  - two-file concatenation (app vs. con) -> group_ids
  - IPW-related plumbing (nothing to reweight with one population)
  - advanced_column_merge (assumes no split-duplicate item columns;
    confirm this holds for your item list before relying on it)
  - item_to_scale.yaml / multi-scale grouping (you have one flat item list)

Kept, because it's still doing real work:
  - explicit missing-value handling via .cat.codes
  - a clean separation between "responses" and everything else
"""

from pathlib import Path

import numpy as np
import pandas as pd

ITEM_KEYS = [
    "DA051", "DA053", "DA054", "DA055", "DA058", "DA060", "DA061",
    "DA062_r", "DA063_r", "DA064", "DA066", "DA067", "DA052", "DA068",
    "DA069_r", "DA070", "DA071", "DA072", "DA073", "DA074",
]


def load_wdfab_single_population(dta_path, item_keys=ITEM_KEYS):
    """
    Load a single-population WDFAB dataset from a Stata .dta file and
    return an ordinal response matrix ready for GRM fitting.

    Uses convert_categoricals=True, then derives integer ordinal codes
    from the categorical labels via .cat.codes. Pandas' .cat.codes
    convention already matches what the reference script hand-rolled:
    valid categories -> 0-indexed integers, missing -> -1 (here mapped
    to NaN instead, since the GRM expects NaN for missing).

    IMPORTANT: .cat.codes is 0-indexed *relative to the categories your
    data actually contains*. If some item never has, say, its lowest
    response category observed in this sample, that item's codes will
    not align with its true 0..(K-1) response range. Check
    df[item].cat.categories per item before trusting this blindly,
    especially for any item you suspect has sparse/rare categories.
    """
    dta_path = Path(dta_path).expanduser()

    df = pd.read_stata(
        dta_path,
        convert_categoricals=True,
        convert_dates=True,
        preserve_dtypes=True,
    )

    missing_items = [k for k in item_keys if k not in df.columns]
    if missing_items:
        raise KeyError(f"Items not found in .dta columns: {missing_items}")

    responses = {}
    for item in item_keys:
        col = df[item]

        if not isinstance(col.dtype, pd.CategoricalDtype):
            # Not every column may come back as categorical (e.g. if a
            # value label set wasn't attached in Stata). Fail loudly
            # rather than silently mis-coding an item.
            raise TypeError(
                f"Column '{item}' is not categorical after "
                f"convert_categoricals=True (dtype={col.dtype}). "
                "Check the .dta value label mapping for this item."
            )

        codes = col.cat.codes.astype(np.float64)
        codes = codes.replace(-1, np.nan)  # pandas' missing sentinel -> NaN
        responses[item] = codes

    responses = pd.DataFrame(responses, index=df.index)

    return {
        "responses": responses,
        "item_keys": item_keys,
        "num_people": len(responses),
    }


if __name__ == "__main__":
    loaded = load_wdfab_single_population(
        "/home/luis/CGE/mice_imp/data_wdfab/WDFAB_ExperimentalData_CMCommonItem_Jul2026.dta"
    )
    responses = loaded["responses"]

    print(f"num_people: {loaded['num_people']}")
    print(f"num_items: {len(loaded['item_keys'])}")
    print("\nPer-item response category counts (sanity check):")
    for item in loaded["item_keys"]:
        vc = responses[item].value_counts(dropna=False).sort_index()
        print(f"  {item}: {dict(vc)}")
