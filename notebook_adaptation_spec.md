# Notebook adaptation spec: single-population WDFAB GRM fitting

## Purpose

Adapt the reference script (multi-scale, two-population WDFAB GRM fitting
pipeline with IPW reweighting) into a Jupyter notebook for a **single
population, single scale** dataset. Keep the Baseline vs. Pairwise-imputation
comparison — that is the one piece of the original design being preserved
in full.

This document specifies what each notebook cell/section should do. It is a
guide for building the notebook, not a diff — write the implementation
fresh, following the reference script's functions where noted, and the
decisions below where they diverge from it.

---

## Decisions already made (do not re-derive these)

1. **One population.** No `group_ids`, no IPW, no `compute_ipw_weights`,
   no `effective_sample_size`. These should not appear anywhere in the
   notebook.
2. **One scale, flat item list of 20 items** (not a multi-scale loop over
   `item_to_scale.yaml`). No `item_to_scale_path`, no
   `group_keys_by_labels`, no per-scale directory structure — everything
   fits once.
3. **Source data is a Stata `.dta` file**, not two CSVs. Load with
   `pd.read_stata(..., convert_categoricals=True, convert_dates=True,
   preserve_dtypes=True)`.
4. **Ordinal codes come from `.cat.codes`**, not from a manual `- 1` shift
   on raw integer codes. Pandas' `.cat.codes` already gives 0-indexed
   categories with `-1` for missing; map that `-1` to `NaN`.
5. **No `advanced_column_merge`.** The item list has no split-duplicate
   columns needing `max()`-merging. Load `df[item_keys]` directly.
6. **`_r`-suffixed items (`DA062_r`, `DA063_r`, `DA069_r`) are already
   reverse-coded in the source data.** No reversal transform is needed.
   Treat them identically to all other items throughout.
7. **Keep the Baseline vs. Pairwise-imputation comparison.** Both variants
   still get fit, exactly as in the reference script's
   `fit_irt_mcmc_variant`, called twice per the original pattern (Pairwise
   reuses Baseline's ADVI warm-start params rather than running its own
   ADVI — preserve this optimization).
8. **Drop all multi-scale aggregation**: no `abilities_combined.npz`, no
   `ability_corr_heatmap` across scales, no `scale_summary.csv` across
   scales. A single scale's outputs are the final outputs.

## Reference item list

```python
ITEM_KEYS = [
    "DA051", "DA053", "DA054", "DA055", "DA058", "DA060", "DA061",
    "DA062_r", "DA063_r", "DA064", "DA066", "DA067", "DA052", "DA068",
    "DA069_r", "DA070", "DA071", "DA072", "DA073", "DA074",
]
```

## Reference data path

```
/home/luis/CGE/mice_imp/data_wdfab/WDFAB_ExperimentalData_CMCommonItem_Jul2026.dta
```

---

## Notebook structure

### Section 0 — Setup and compatibility patches

Port verbatim from the reference script, unchanged:
- `patch_all_training_loops_for_batchless_marginal_advi`
- `patch_tfp_transformed_distribution_entropy_for_advi`
- The `os.environ["JAX_PLATFORMS"]` / `JAX_ENABLE_X64` settings and imports

Run the two patch functions once, near the top, same as the reference
script's module-level calls.

Flag to the user in a markdown cell: these patches work around
version-specific bugs in `bayesianquilts`/`tensorflow_probability`. If a
different library version is in use, check whether they're still needed
before assuming they are.

### Section 1 — Load and validate data

Implement a loader function equivalent to the `load_wdfab_single_pop.py`
script already written (attached separately / described above):
- `pd.read_stata` with the three conversion flags
- Per-item: assert categorical dtype (fail loudly if not — do not
  silently coerce), extract `.cat.codes`, map `-1` to `NaN`
- Return a responses DataFrame indexed like the source, over exactly
  `ITEM_KEYS`

Follow with a diagnostic cell: for each item, print or display its
observed category counts (`value_counts(dropna=False)`), and check the
number of distinct non-missing codes per item. This is a manual check the
user needs to eyeball — the GRM's `response_cardinality` argument assumes
every item shares the same ordinal range (0..K-1 for the same K across all
20 items). Do not silently proceed if any item's code range doesn't match
the rest; surface it clearly and let the user decide how to handle it.

Also report:
- Total number of respondents
- Missingness rate per item (proportion NaN)
- Overall missingness rate across the response matrix

### Section 2 — Build the data dict

Equivalent to reference's `make_data_dict`, but simplified: no
`group_ids` parameter, no `sample_weights` key. Structure:

```python
def make_data_dict(dataframe):
    data = {col: dataframe[col].to_numpy().astype(np.float64) for col in dataframe.columns}
    data["person"] = np.arange(len(dataframe), dtype=np.float64)
    return data
```

### Section 3 — Fit the shared pairwise imputation model

Port `PairwiseOrdinalStackingModel` fitting logic from the reference
script's `main()` (the block that fits it once, before the per-scale
loop, and saves/loads it via `save_pairwise_model` / `load_pairwise_model`
so it isn't refit unnecessarily). Since there's only one scale here, this
still only needs to be fit once — keep that "fit once, reuse" structure
even though the multi-scale loop that motivated it is gone, since it's
still the shared imputation backbone for the Pairwise IRT variant.

Use all 20 items (no `n_top_features` scale-specific subsetting is needed
here, though the reference script's default of "up to `n_top_features`
top features" can stay as a configurable parameter — with only 20 items
this will likely just use all of them anyway; make the notebook explicit
about what it resolves to).

### Section 4 — Fit Baseline and Pairwise IRT models

Port `fit_irt_mcmc_variant` from the reference script largely as-is
(ADVI warm-start → MCMC → R-hat check → standardize → EAP). Call it
twice, following the reference script's `fit_one_scale_worker` pattern:

1. **Baseline**: `imputation_model=None`, `run_advi=True`,
   `init_advi_params=None`
2. **Pairwise**: `imputation_model=PairwiseOnlyImputationModel(mice_model=pairwise_model)`,
   `run_advi=False`, `init_advi_params=<Baseline's advi_params>`

Preserve the R-hat gate as a visible warning (not a silent pass) — the
reference script only prints a warning above 1.05 but still proceeds; keep
that behavior, but make sure the notebook cell output makes the warning
impossible to miss (e.g., don't bury it in scrolled-past log lines).

Since there's no `group_ids` any more, drop the reference's
`imputation_model.validate_imputation_model()` group-related checks only
if they were group-specific — otherwise keep validation as-is; it isn't
IPW-related.

### Section 5 — Build the BCM (mixed imputation) artifact

Port `save_bcm_model_artifact` and the `IrtMixedImputationModel`
construction from `fit_one_scale_worker`, conditioned on whichever of
Baseline/Pairwise the user chooses via a `bcm_source` variable (default
`"pairwise"`, matching the reference script's CLI default). Keep this as
an explicit notebook variable near the top of the section rather than a
CLI arg, since there's no argparse in a notebook context.

### Section 6 — Diagnostics and comparison plots

Port, in one cell each:
- `plot_advi_losses` (Baseline vs. Pairwise ADVI loss curves)
- `plot_forest` for `discriminations` and for `difficulties0`
  (or whichever difficulty/threshold parameters the fitted `GRModel`
  exposes — check attribute names against the installed library version)
- `plot_ability_histogram` (Baseline vs. Pairwise EAP ability
  distributions)

Drop `plot_ability_corr_heatmap` — that was for correlating abilities
*across scales*, which doesn't apply with one scale.

Add one more comparison cell not in the reference script, since it's
useful precisely because there's no multi-scale summary to fall back on:
a scatter plot of Baseline EAP vs. Pairwise EAP (one point per person),
with a diagonal reference line, so it's visually obvious whether the two
imputation strategies produce materially different ability estimates for
this scale. Report the Pearson correlation and RMSE between the two EAP
vectors alongside the plot.

### Section 7 — Save outputs

Port the single-scale portion of `save_npz` calls from
`fit_one_scale_worker` (the `scale_summary.npz` block), dropping anything
`group_ids`/`sample_weights`-related. Keep:
- item keys, EAP and PSD for both variants, R-hat for both variants,
  model paths, ADVI/MCMC settings used

Drop the reference script's separate multi-scale `abilities_combined.npz`
and `scale_summary.csv` — with one scale there is nothing to combine.

---

## Things to flag to the user in markdown cells, not just silently handle

- The category-alignment check in Section 1 (already noted above) —
  make this a clearly labeled markdown warning cell if any item fails it,
  not just a printed table to skim.
- The R-hat gate in Section 4 — same treatment.
- Confirm, in a markdown cell near Section 1, that `_r` items are already
  reverse-coded in the source `.dta` (this was confirmed by the user
  directly, not derived — state it as a documented assumption so it's
  auditable later, not just baked in silently).
