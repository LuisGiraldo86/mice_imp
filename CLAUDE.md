# CLAUDE.md — WD-FAB-DE missing-data comparison

## What this project is

Head-to-head comparison of five IRT calibration approaches under planned
missingness, using the Community Mobility (CM) subscale of the WD-FAB-DE as
the test scale. CM was administered to everyone, so it has complete data
(CD); missingness is **simulated** on top of it.

- **Designs (3):** common item, standard, block interlaced (Joo et al. 2017).
  Respondents randomly assigned to forms A/B/C; within each form, non-anchor
  items randomly masked at ~2/3. Six anchor items selected by largest average
  reliability over theta in [-6, 6] from the CD graded response model.
  **The masked frames already exist** — see "Data files" below; do not
  regenerate them.
- **Scale:** 26 items (20 adapted `DA*` + 6 `Bike_*`). Bike_2 is excluded;
  see fact 15.
- **Approaches (5) + reference:** CD (reference), FIML, MG-IRT, Stocking-Lord
  linking, B-IRT, B-MI.
- **Model:** graded response model (GRM) throughout.
- **Comparisons:** theta vs CD by MSE and Bland-Altman; slopes by OLS
  (target 1.0); intercepts by random-intercept (item) models. Stratified by
  gender, age group, CD theta quintile, self-rated health.

Target: special issue in *Advances in Patient Reported Outcomes*.
Josh Chang (NIH/Mederrata, author of bayesianquilts) is a coauthor — ask him
directly when something about the library is ambiguous.

## Language split

- **R / `mirt` / `plink`:** CD, FIML, MG-IRT, Stocking-Lord.
- **Python / `bayesianquilts`:** B-IRT, B-MI.

Keeping the four frequentist arms in `mirt` is deliberate: it means B-IRT and
B-MI differ from FIML by the estimation engine and the imputation step only,
with nothing else confounded.

## Repository layout

```
data/            # CD export (git-ignored)
data_wdfab/      # the three masked design frames (git-ignored)
R/               # mirt/plink arms, anchor selection
mice_imp/
  wdfab_io.py        # .dta loading, item keys, 1..K -> 0..K-1 recode
  cm_preflight.py    # data contract checks — RUN FIRST
  cm_bayes_arms.py   # B-IRT / B-MI / flat-control arms
notebooks/
  make_design_notebooks.py   # GENERATOR — edit this, not the .ipynb files
  cm_{commonitem,standard,binterlaced}.ipynb   # generated drivers
results/<design>/    # {birt,bmi,flat}.npz, noise_floor.json, summary.npz
```

**The three design notebooks are generated.** They are thin drivers — set a
design, call into `mice_imp/`, plot — and they are byte-identical apart from
the design name and the design-specific header. Edit
`make_design_notebooks.py` and re-run it; hand-editing one `.ipynb` puts the
three out of sync silently, which is exactly the failure the generator
exists to prevent. Anything that should change for all three designs belongs
in `cm_bayes_arms.py`, not in the generator.

Each notebook opens with `SMOKE = True` (2 chains, 200/200). That is a
wiring check, not an inferential run.

`notebooks/wdfab.ipynb` is the earlier adaptation and is **superseded**: 20
items with no bike block, `.cat.codes` loading (fact 15), `MICEBayesianLOO`
rather than `PairwiseOrdinalStackingModel`, and a BCM section that fact 11
says to drop. Keep it for reference only.

`load_wdfab_single_pop.py` at the repo root is superseded by `wdfab_io.py`.
It lists only the 20 `DA*` items and derives codes via `.cat.codes`, which is
0-indexed relative to the categories present *in that file* — so on a masked
design where an item never shows its lowest category it produces a
differently-shifted scale per design. Do not use it.

## Data files

All Stata `.dta`, all N = 1363, all row-aligned (verified by exact agreement
on every unmasked cell).

| file | role |
|---|---|
| `data/Datenexport_test_mar2026.dta` | CD reference, N = 1363, 217 cols |
| `data/Datenexport_test_mar2026_2.dta` | **subset**, not an alternative — see below |
| `data_wdfab/WDFAB_ExperimentalData_CM{CommonItem,Standard,Binterlaced}_Jul2026.dta` | masked designs, 127 cols each |

`_2` holds 642 of the same 1363 respondents with byte-identical values on the
CM items (verified NaN-aware: 0 differing cells). It is only 1.66% missing
with 586 complete cases, so it looks attractive as a CD source — but the
selection rule for those 642 is unknown. Find out before using it.

The `_small` variants are subsets — the full files are the ones to use.

All three design files share one 127-column schema and cover exactly the CD
respondent set (`id_work` sets identical). **None of them is complete**: in
every design each of the 26 CM items is masked in at least one form.

Form assignment is `grp_final` (1/2/3, n = 455/454/454). Masking is
**deterministic per form**: within a form every item is either fully masked
or administered, and the only within-form variation is the baseline item
nonresponse. So MG-IRT groups on `grp_final` coherently. Administered items
per form, after excluding Bike_2:

The three designs use the **same six anchors and the same 20 single-form
items** throughout. The 20 non-anchors sit in exactly 1 of 3 forms in every
design. The designs differ *only* in how the anchors are allocated:

| design | anchors per form | overlap 1&2 / 1&3 / 2&3 | items per form |
|---|---|---|---|
| CommonItem | all 6 in all 3 forms | 6 / 6 / 6 | 13 / 13 / 12 |
| Standard | all 6 in form 1; 3 each in forms 2, 3 | 3 / 3 / **0** | 13 / 10 / 10 |
| Binterlaced | 2 per form-pair, each anchor in a different pair | 2 / 2 / 2 | 11 / 11 / 11 |

Anchors are `DA054 DA058 DA060 DA064 DA066 DA067`. Under Standard, form 1 is
the reference form and forms 2 and 3 link only through it — they share
**zero** items with each other, by construction. Stocking-Lord must chain
2 -> 1 -> 3; it has no direct anchor for that pair.

## Environment

bayesianquilts is JAX-first (JAX 0.7.1+, TFP 0.25 for distributions, Flax
NNX, Optax, Orbax, BlackJAX for NUTS). The TF path is legacy — ignore it.

**Pin the commit.** The vendored `bayesianquilts/` is at **`7a29ec5`**, and
every API call in `cm_bayes_arms.py` was verified against it on 2026-08-13:
`GRModel.__init__` kwargs, `fit_marginal_advi` -> `(losses, params)`,
`fit_marginal_mcmc`, `standardize_marginal` -> `{'mu','sigma'}`,
`compute_eap_abilities`, `_compute_batch_pmfs` -> `(pmfs, weights)`,
`validate_imputation_model`, `PairwiseOrdinalStackingModel.{__init__,fit,
save_to_disk,load_from_disk}`, `PairwiseOnlyImputationModel(mice_model=)`.

**ADVI needs a shim at this commit — `mice_imp/compat.py`.**
`fit_marginal_advi` is batchless: it closes over `data` and builds
`loss_fn(params)`. But `bayesianquilts.util.training_loop` at `7a29ec5` is
the *batched* loop — it requires `data_iterator` and `steps_per_epoch` and
calls `value_and_grad_fn(batch, params)`. So ADVI raises
`TypeError: training_loop() missing 2 required positional arguments`.
`patch_batchless_training_loop()` injects an empty-batch iterator and widens
the loss signature. `fit_arm` calls it only when `run_advi=True`, and it
no-ops if a future version gives those parameters defaults.

Chang's `patch_all_training_loops_for_batchless_marginal_advi` fixes only
the loss signature, not the two missing arguments, so it does **not** solve
this on its own. His entropy patch is **not needed**: at `7a29ec5`
`fit_marginal_advi` already avoids the closed-form entropy with a Monte
Carlo estimate.

Chang's working script carries two monkey-patches
(`patch_all_training_loops_for_batchless_marginal_advi`,
`patch_tfp_transformed_distribution_entropy_for_advi`) that shim against a
specific state of the repo. Record the commit hash in `requirements.txt`.
Port the patches only if ADVI actually raises; do not carry them by default.

## Non-obvious facts — do not rediscover these

### 1. Missing-data encoding is silent
`GRModel` masks a response wherever
`(y < 0) | (y >= response_cardinality) | isnan(y)`.
An out-of-range code does not raise — it disappears from the likelihood.
Responses must be 0-indexed integers with missing as `NaN`. If CD is
silently incomplete, every comparison is measured against a corrupted
reference.

### 2. Flat PMFs are equivalent to no imputation
The Rao-Blackwellised contribution of a masked cell is
`log sum_k q_k p(Y=k|phi)`. With `q_k = 1/K` this is `log(1/K)` — constant,
gradient zero — because GRM category probabilities sum to one. Verified
numerically.

Two consequences:
- The `flat` arm targets the **same posterior** as `birt`. Any difference
  between them is Monte Carlo noise, and gives the resolution at which a
  real B-MI effect could be detected. Report it.
- Chang's observation (2026-04-06) that flat probabilities "help slightly"
  over not imputing was run-to-run variation, not an effect.

### 3. Failed imputations silently degrade to B-IRT
`_compute_batch_pmfs` wraps each per-cell call in
`except (ValueError, KeyError, AttributeError): pmfs[...] = 1.0 / K`.
By (2), those cells then contribute nothing. With ~2/3 masking the
predictors the imputation model wants are often masked too, so this can fire
often. `attach_imputation_pmfs` in `cm_bayes_arms.py` counts fallbacks and
warns above 10%. **A null B-MI result is not interpretable until the
fallback rate is known to be low.**

### 4. Arms cannot be compared on log-likelihood
Skipped items leave PMFs at zero, floored to `1e-30`, contributing
`log(1e-30)` per cell — again constant, so inference is unaffected, but
arm-specific additive constants make ELPD/LOO comparisons meaningless.
Compare item parameters and thetas only. Do not add a fit-index comparison.

### 5. Parameter conventions differ from mirt
- bayesianquilts: `a_i * (theta - b_ik)`; mirt: `a_i * theta + d_ik`.
  So **`d_ik = -a_i * b_ik`**.
- Thresholds are stored as **increments** (`difficulties0` concatenated with
  `ddifficulties`); `cumsum` before use. Omitting the cumsum leaves the slope
  regression looking fine while the intercept regression is meaningless.
- Extract item parameters **after** `standardize_marginal`, or the metric
  will not match mirt's `theta ~ N(0,1)` identification.
`to_mirt_convention()` centralises all three — use it, don't reimplement.

### 6. B-IRT must run before B-MI
B-MI reuses B-IRT's ADVI warm-start (`run_advi=False`,
`init_advi_params=...`). This is structural, not stylistic. `run_all_arms`
raises if `birt` is excluded.

### 7. ADVI is a warm-start, never the inference
Chang found mean-field ADVI settling into a poor local optimum
(2026-03-30) and moved to NUTS on item parameters with abilities integrated
out on a quadrature grid. ADVI runs 100 iterations purely to initialise.
Sampled dimension is ~items x categories, not that plus N — so 27 items at
K=5 is comfortably tractable.

### 8. B-MI needs a gentler sampler
Chang's defaults: baseline `step_size=0.002, target_accept=0.95`; imputed
`step_size=0.0005, target_accept=0.98`. Attaching PMFs turns masked cells
from exact zeros into parameter-dependent curvature, which makes the
geometry harder. Warn above R-hat 1.05.

### 9. Imputation predictors are restricted to CM items
Chang fits the imputation model across all eight WD-FAB scales. Doing that
here would give B-MI information the mirt arms never see, and B-MI would win
for a reason unrelated to imputation. Fit
`PairwiseOrdinalStackingModel` on the CM items only, `n_top_features <=
len(item_keys) - 1`. A cross-scale version is legitimate **only** as an
explicitly labelled secondary arm.

### 10. Refit the imputation model per design
Missingness patterns differ across the three designs. Do not fit once and
reuse.

### 11. Disable IPW; drop BCM
Chang's IPW corrects applicant/normative oversampling in the US calibration
data — no analogue here, and he told the PI to disable it. Note the argparse
trap in his script: `--use-ipw` has `action="store_true"` *and*
`default=True`. The BCM block (`IrtMixedImputationModel`) is CAT-scoring
machinery for his manuscript, not ours.

### 12. Do not use `advanced_column_merge`
It reconciles the US instrument's skip-pattern item pairs, and its
`re.sub(r"[a-zA-Z]+$", "", col)` would rewrite `DA062_r` -> `DA062_` and
`Bike_2_r` -> `Bike_2_`, breaking every lookup.

### 13. Item order is canonical and positional
Posterior arrays are positional and get aligned against mirt output. Never
re-sort `ITEM_KEYS`. The mixed `DA###` / `Bike_#` naming means alphabetical
sorting would silently reorder.

### 14. Polarity is settled once, upstream
Reverse-scored items carry `_r`. The GRM and the imputation model must be
fit from the **same frame** — the imputation model returns PMFs over
category indices, so any re-reversal in between permutes them silently.

For `DA062` / `DA063` / `DA069` the `_r` column is the right one: in the
design files the un-suffixed column is the *unmasked source* (observed in
every form, ~1225–1266 rows) while `_r` carries the design masking. Using
the raw column would drop the masking and flip polarity at once.

### 15. Raw codes are 1..K and the files are labelled `.dta`
Two silent failures, both closed by `wdfab_io.py`:
- `pd.read_stata` defaults to `convert_categoricals=True` and returns the
  German label *strings*. Read with `convert_categoricals=False`.
- Responses are stored **1..5**. With `response_cardinality=5` every `5`
  satisfies `y >= K` and is dropped by fact 1 — so the top category of every
  item disappears and CD is built on truncated data. `recode_items` verifies
  the range and shifts explicitly, raising rather than silently shifting
  something unexpected.

### 16. Bike_2 is excluded — one item, two columns, split across forms
`Bike_2_r == 6 - Bike_2` exactly in CD (r = -1.000). `Bike_2` is the
correctly oriented column (+0.363 vs the rest of the scale), `Bike_2_r` is
flipped (-0.363). But the design files treated the two columns as **two
separate items in the masking pool**: `Bike_2` went to form 1 (397 observed)
and `Bike_2_r` to form 3 (393), disjointly, in all three designs.

So no use of this item is both complete and faithful to the design. Merging
recovers all 790 responses but makes the item span forms 1 and 3, pushing
common-item overlap to 6/7/6 — an asymmetric anchor set. Either column alone
discards half the data. It is dropped (`wdfab_io.EXCLUDED_ITEMS`), leaving
26 items and costing the weakest bike item (+0.363 against +0.65..+0.735 for
the other six).

**This is interim.** The design files should be regenerated from a
27-column pool; then restore Bike_2.

### 17. ADVI's result must be assigned to `model.params` by hand
`fit_marginal_advi` stores its output in `self.marginal_params`. But
`fit_marginal_mcmc` warm-starts by scanning **`self.params`** for keys
starting with a var name and ending in `loc`; if `self.params` is None it
silently initialises every chain from the **prior** instead. So after
running ADVI you must do `model.params = advi_params` — `fit_arm` does.

This bit us: the `birt` arm ran ADVI and discarded it, while `bmi` and
`flat` were initialised from those same params. The `flat`-vs-`birt` gap
then measured initialisation *plus* Monte Carlo noise, which would have
quietly destroyed the noise floor's meaning (fact 2). Confirm
`Initializing from ADVI solution` appears in every arm's MCMC output.

### 18. `standardize_marginal` mutates in place, and that is load-bearing
`fit_marginal_mcmc` returns the same dict object it stores as
`self.mcmc_samples`, and `standardize_marginal` rescales that dict by key
assignment. So calling `to_mirt_convention(mcmc_samples)` on the returned
handle *after* standardising does see standardised draws — but only because
of that aliasing. Do not copy the dict in between.

## Open issues — resolve before full runs

**A. RESOLVED (2026-08-13) — bike missingness is elevated, not structural.**
Bike block 12.7% missing vs DA block 6.8% (1.9x, under the 3x threshold).
DA mean score for respondents answering at least one bike item vs none:
1.103 vs 0.928, standardised difference **+0.19**, under the 0.2 warn line.
Non-cyclists do sit slightly lower on community mobility, in the predicted
direction, but weakly. The MCAR premise holds. Report the magnitude; do not
claim the effect is absent.

**B. Local dependence — STILL OPEN, and worse than expected.** 44 pairs
above |r| = 0.75 on CD; at 0.85 the top offenders are `Bike_1`/`Bike_7`
0.931, `Bike_4`/`Bike_5` 0.921, `DA061`/`DA066` 0.906, `DA053`/`DA066`
0.900, `DA073`/`DA074` 0.888. Two things follow:
- Local dependence is **not confined to the bike block** — several DA-DA
  pairs are the strongest offenders.
- The six fixed anchors are themselves correlated (`DA060`/`DA066` 0.865,
  `DA066`/`DA067` 0.845, `DA054`/`DA058` 0.840). Correlated anchors carry
  less joint information than their individual reliabilities imply, which
  weakens the common-item linking condition specifically.

**C. RESOLVED (2026-08-13) — masking exists and is per-form.** See "Data
files". No masking layer to write.

**D. Replication.** A single masking realisation gives no handle on
simulation variance. With 26 items the MCMC is cheap enough to replicate;
plan for it in the directory layout from the start. Note the delivered
design files are one realisation each — replicating means regenerating
masks, which needs the generating script from the collaborators.

**E. RESOLVED (2026-08-13).** All 26 items show exactly 5 categories, so the
scalar `response_cardinality=5` is correct.

**F. CD is not complete.** No file in the repo has complete CM data — the
design files are all masked, and `_2` is a subset of the main export, not an
unmasked alternative. Three options, none free:

| CD source | N | CM missing | complete cases |
|---|---|---|---|
| main export, all rows | 1363 | 8.2% | 809 (59.4%) |
| main export, complete cases only | 809 | 0% | 809 |
| `_2` subset | 642 | 1.7% | 586 |

Calibrating on all 1363 with FIML makes the CD reference itself a
missing-data method, muddying what it is a reference *for*. Restricting to
809 costs 41% of the sample and selects on completeness. `_2` is cleanest
per-row but is 47% of the sample under an unknown selection rule.
**Decide and document before any fitting.**

**G. Confirm the Standard design's chained linking is intended.** Forms 2
and 3 share zero items by construction (see "Data files"), so Stocking-Lord
must chain 2 -> 1 -> 3. That is a coherent reading of the standard design,
but it means SL's error for the 2-3 comparison compounds two linkings while
CommonItem's does not — which is a result about the design, not about the
method, and needs saying in the write-up.

## How to work here

1. `cm_preflight.py` must pass before any fitting. Run it on the CD export —
   on a masked design file it detects `grp_final`, prints the form layout,
   and says so, because checks 3–7 then describe the design rather than the
   data contract.

   ```
   python -m mice_imp.cm_preflight data/Datenexport_test_mar2026.dta
   ```

2. Smoke-test `cm_bayes_arms.py` with `--num-warmup 200 --num-samples 200`
   before committing to full chains. Signatures are verified against
   `7a29ec5` (see Environment), but nothing has been *executed* end to end.

   ```
   python -m mice_imp.cm_bayes_arms \
       data_wdfab/WDFAB_ExperimentalData_CMCommonItem_Jul2026.dta \
       --output-dir results/commonitem --num-warmup 200 --num-samples 200
   ```
3. Keep logic in scripts with argparse and `.npz` checkpoints. The grid is
   3 designs x 3 arms x replications; individual arms fail and need
   selective re-runs, which is painful from a notebook. The per-design
   notebooks exist for reading results interactively — they call into
   `mice_imp/` and hold no logic of their own. Do not move logic into them.
4. Never silently "fix" a failing check by relaxing it. Every check here
   corresponds to a failure that is silent downstream, not loud.
