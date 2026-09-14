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
- **Scale:** 27 items (20 adapted `DA*` + 7 `Bike_*`). Bike_2 enters as
  `Bike_2_r_cor`, the corrected recoding shipped 2026-08-21; see fact 16.
- **Approaches (5) + reference:** CD (reference), FIML, MG-IRT, Stocking-Lord
  linking, B-IRT, B-MI.
- **Item sets (2):** every dataset is run twice — `full` (all 27 items) and
  `nobike` (the 20 adapted `DA*` items, bicycling block dropped). The bike
  block is unique to the German instrument, carries the strongest local
  dependence (open issue B), and is where the MCAR premise is most strained
  (open issue A); the `nobike` run shows whether any conclusion depends on
  it. It is a sensitivity analysis, not a fallback — report both. In the main
  and reduced-anchor files dropping the block leaves every anchor (all
  `DA*`) untouched, so form-pair overlap is identical in both runs. **Not in
  the alt-anchor files**: two of their anchors are `Bike_*`, so their
  `nobike` run also weakens linking (see "Data files"). The lists live in
  `wdfab_io.ITEM_SETS`.
- **Model:** graded response model (GRM) throughout.
- **Comparisons:** theta vs CD by MSE and Bland-Altman; slopes by OLS
  (target 1.0); intercepts by random-intercept (item) models. Stratified by
  gender, age group, CD theta quintile, self-rated health.

## Scope of the work in this repo (set 2026-08-21)

**This repo produces the Bayesian arms and hands over estimates. It does not
run the CD comparison.** Six runs — 3 designs x 2 item sets — each giving
`birt`, `bmi` and the `flat` control, exported as `item_parameters.csv` and
`theta.csv`. The coauthor synthesises: CD reference, the mirt/plink arms,
and every theta-vs-CD, slope, intercept and stratified comparison.

So the R arms and the CD calibration are **out of scope here**, and open
issue F (which CD source) is not ours to decide — but the answer still has
to travel with the handover, see "Handover" below, because the estimates are
only interpretable against a CD calibrated the same way.

What stays in scope and still blocks: open issue E (sparse categories -- it
is our sampler that diverges), the B-MI fallback rate (fact 3), and the ADVI
warm-start check (fact 17).

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
  export_estimates.py  # npz -> item_parameters.csv / theta.csv for coauthors
notebooks/
  make_design_notebooks.py   # GENERATOR — edit this, not the .ipynb files
  cm_{commonitem,standard,binterlaced}_{full,nobike}.ipynb  # 6 drivers
results/<design>/<itemset>/   # {birt,bmi,flat}.npz, noise_floor.json,
                              # summary.npz, item_parameters.csv, theta.csv
results_reduced_anchor/<design>/<itemset>/   # same, for the _small files
results_alt_anchor/<design>/<itemset>/       # same, for the _Aug2026_alt files
```

`export_estimates.py` is the coauthor-facing deliverable: `a` and `b1..b4`
per (arm, item), and an EAP theta + PSD per respondent keyed on `id_work`.
It reads the arm `.npz` and does no computation of its own beyond reshaping
— everything is already post-`standardize_marginal` and post-`cumsum`.

```
python -m mice_imp.export_estimates results/binterlaced/full \
    --source data_wdfab/WDFAB_ExperimentalData_CMBinterlaced_Jul2026.dta \
    --include-d
```

### Handover

The CSVs are the deliverable, so they must be readable without this repo.
Every row carries `design`, `itemset`, `arm` and `max_rhat`; thetas are keyed
on `id_work`. Send these five facts with them or the synthesis will be wrong
in ways that look fine:

1. **`Bike_2` must be `Bike_2_r_cor` on their side too.** The CD export does
   not carry the corrected column (fact 16). If their CD calibration uses raw
   `Bike_2` or `Bike_2_r`, that item's parameters are comparing two different
   codings, and B-MI's imputation PMFs are over permuted categories.
2. **Each run is standardised independently** (`standardize_marginal`, theta
   ~ N(0,1) within its own run). Thetas are not on a common metric across
   designs, item sets, or against their CD fit until they put them there.
   Any slope-against-CD analysis has to handle this explicitly.
3. **`flat` is a noise floor, not a method.** It targets the same posterior
   as `birt` by construction (fact 2). It must not appear as a third arm in
   any results table; it is the resolution limit for the B-MI effect.
4. **Parameter conventions** — `a_i(theta - b_ik)`, thresholds already
   `cumsum`-ed, `d_ik = -a_i*b_ik` supplied alongside, and the exported `d`
   will not reproduce as `-a*b` from the exported columns (fact 5, and the
   note below).
5. **The B-MI fallback rate for that run**, from the fit log. A null B-MI
   result is uninterpretable without it (fact 3).

`--source` is what attaches `id_work` and `grp_final`; without it the key is
a bare row index. Both CSVs carry `max_rhat` per arm so a non-converged arm
cannot be picked up silently, and the exporter warns on stderr above 1.05.
Note the exported `d` will not reproduce as `-a * b` from the exported
columns: each is a posterior mean of its own quantity, and the mean of a
product is not the product of the means (~0.02 apart here). Do not
"fix" it.

**The six design notebooks are generated** — 3 designs x 2 item sets. They
are thin drivers (set a design and an item set, call into `mice_imp/`, plot)
and are byte-identical apart from the design name, the item set, and their
headers. Edit `make_design_notebooks.py` and re-run it; hand-editing one
`.ipynb` puts the six out of sync silently, which is exactly the failure the
generator exists to prevent. Anything that should change for all six belongs
in `cm_bayes_arms.py`, not in the generator.

Each notebook binds its item set once, as `FIT_KEYS`, and uses that
everywhere — `load_cm` always reads all 27 items and `FIT_KEYS` selects. The
two runs of a dataset write to separate directories and must not share an
imputation model: the predictor pool differs.

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
| `data/Datenexport_test_mar2026_2.dta` | **not used** — see below |
| `data_wdfab/WDFAB_ExperimentalData_CM{CommonItem,Standard,Binterlaced}_Jul2026.dta` | masked designs, 128 cols each |
| `data_wdfab/WDFAB_ExperimentalData_CM{CommonItem,Standard,Binterlaced}_Jul2026_small.dta` | reduced-anchor sensitivity designs, 128 cols each |
| `data_wdfab/WDFAB_ExperimentalData_CM{CommonItem,Standard,Binterlaced}_Aug2026_alt.dta` | alt-anchor sensitivity designs, 128 cols each |

`_2` is **out of scope (2026-08-21)**. It is a 642-row subset of the main
export with byte-identical values, selected on having answered the CM items
by a rule nobody has been able to state, and its respondents score 0.28 SD
lower on community mobility than the rest. It is not a cleaner CD source and
it is not an alternative dataset. Do not reopen it.

The `_small` variants (`..._Jul2026_small.dta`, one per design) are the
**reduced-anchor sensitivity analysis** — confirmed as intended 2026-09-14.
They are **not** subsets or a smaller sample: same 1363 rows and 128 columns,
same form sizes, but only three anchors (`DA054` / `DA058` / `DA066`)
multi-form. Overlap 1&2 / 1&3 / 2&3 is CommonItem 3/3/3, Binterlaced 1/1/1,
Standard 1/2/0. They vary **linking strength**, and two of the three anchors
are the correlated pair `DA054`/`DA058` (open issue B). Run them with
`python -m mice_imp.run_grid --variant reduced_anchor` (or
`notebooks/run_all_sensitivity.ipynb`); results go to
`results_reduced_anchor/` and every exported row carries
`variant = reduced_anchor`. Preflight 2b fails on them too, slightly worse
than on the main files (10–11 items with a category < 20).

The `_Aug2026_alt` variants (arrived 2026-09-14) are the **alt-anchor
sensitivity analysis**: same respondents, row order, `grp_final`, anchor
count, form-pair overlap and items per form as the main files, and they agree
with them cell for cell wherever both observe a response — but a **different
six anchors**, `DA052 DA058 DA066 DA073 Bike_3 Bike_7` (four of main's
replaced). They vary **anchor choice**. Because two anchors are bike items,
`nobike` overlap drops to CommonItem 4/4/4, Binterlaced **2/2/0** (forms 2
and 3 unlinked), Standard 3/1/0; both item sets are still run (decided
2026-09-14), but that `full`-vs-`nobike` contrast confounds item set with
linking and must be reported as such. `Bike_7` is in the strongest dependent
pair on the scale (issue B). Run with `--variant alt_anchor` or
`notebooks/run_all_alt_anchor.ipynb`; results go to `results_alt_anchor/`.
Preflight 2b fails as on main (9–10 items).

All three design files share one 128-column schema and cover exactly the CD
respondent set (`id_work` sets identical). **None of them is complete**: in
every design each of the 26 CM items is masked in at least one form.

Form assignment is `grp_final` (1/2/3, n = 455/454/454). Masking is
**deterministic per form**: within a form every item is either fully masked
or administered, and the only within-form variation is the baseline item
nonresponse. So MG-IRT groups on `grp_final` coherently. Administered items
per form:

The three designs use the **same six anchors and the same 21 single-form
items** (7 per form) throughout. The 21 non-anchors sit in exactly 1 of 3
forms in every design. The designs differ *only* in how the anchors are allocated:

Items per form is given for both item sets, `full` / `nobike`. Overlap is
the same in both, since every anchor is a `DA*` item.

| design | anchors per form | overlap 1&2 / 1&3 / 2&3 | items per form (full) | (nobike) |
|---|---|---|---|---|
| CommonItem | all 6 in all 3 forms | 6 / 6 / 6 | 13 / 13 / 13 | 11 / 11 / 10 |
| Standard | all 6 in form 1; 3 each in forms 2, 3 | 3 / 3 / **0** | 13 / 10 / 10 | 11 / 8 / 7 |
| Binterlaced | 2 per form-pair, each anchor in a different pair | 2 / 2 / 2 | 11 / 11 / 11 | 9 / 9 / 8 |

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

### 16. Bike_2 is in, as `Bike_2_r_cor`, and both raw columns are wrong
Resolved 2026-08-21; the item list is now 27. The raw columns are still in
the files, so this stays a live trap.

The item shipped as `Bike_2` and `Bike_2_r == 6 - Bike_2`, and **both are
mis-scored**. Verified on the 393 form-3 rows of every design file, the
correction is a deterministic permutation of `Bike_2`:

    1 -> 4    2 -> 3    3 -> 2    4 -> 1    5 -> 5

Categories 1..4 are reversed; category 5 stays put, because it is not the
top of that continuum. **The coauthor confirmed on 2026-08-21 that this is
the intended recoding**, with the wording of category 5 still to be
double-checked on their side. Mean score on the other 26 items by raw `Bike_2`
category is 2.21 / 1.98 / 1.71 / 1.57 for 1..4 — decreasing — and **3.29**
for category 5. So the flat `6 - x` reversal that produced `Bike_2_r` sent
those 303 respondents to the bottom of the scale.

That is why neither original column worked: item-rest correlation +0.363
for `Bike_2`, -0.363 for `Bike_2_r`. `Bike_2_r_cor` is monotone in the
rest-score across all five categories (1.45 / 1.68 / 1.97 / 2.17 / 3.29)
and correlates +0.614, in line with the other six bicycling items
(+0.65..+0.735).

Column roles in the current design files:

| column | role |
|---|---|
| `Bike_2_r_cor` | the item — design-masked, form 3, 393 responses, in all three designs |
| `Bike_2` | old coding, masked to form 3 |
| `Bike_2_r` | old coding, **unmasked** (all 1191, every form) — same trap as fact 14 |

Both raw columns are in `wdfab_io.EXCLUDED_ITEMS`. Using `Bike_2_r` would
take the wrong coding *and* drop the design masking.

**The CD export does not carry `Bike_2_r_cor`** — the correction shipped in
the design files only. `wdfab_io.derive_bike2_correction` applies
`BIKE2_RECODE` to any frame that lacks the column, and raises if a file
supplies a column that disagrees with the table. Ask the collaborators for a
corrected CD export; until then CD's copy is derived here.

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
simulation variance. With 27 items the MCMC is cheap enough to replicate;
plan for it in the directory layout from the start. Note the delivered
design files are one realisation each — replicating means regenerating
masks, which needs the generating script from the collaborators.

**E. DEFERRED (2026-08-21) — not being raised with the coauthor yet; the
analysis below stands for when it is. REOPENED (2026-08-13) — categories are
present but several are nearly empty.** All 27 items do show exactly 5 distinct categories, so the scalar
`response_cardinality=5` is formally correct. That was the shallow reading.
On **CD**, category 3 holds 10 responses for `DA068`, 13 for `DA053`, 15 for
`DA061`; seven items have a category under 40. Under a design that gives an
item to one form those counts drop to ~2.

A GRM estimates two thresholds around every interior category. With a
handful of respondents in it, both are close to unidentified, the posterior
develops a flat ridge, and NUTS diverges — which surfaces as an R-hat
failure far from its cause. Measured with `birt`, 2 chains, 500 warmup:

| frame | non-divergent ratio | adapted step size |
|---|---|---|
| CD (8.2% missing) | 0.200 / 0.140 | 2.93e-2 / 2.85e-2 |
| Binterlaced (62% missing) | 0.160 / 0.025 | 2.83e-3 / 9.75e-3 |

**CD diverges as badly as the masked designs**, so this is not a
missing-data problem and no per-design sampler tuning will fix it. Masking
adds adaptation instability on top (note the two masked chains disagree on
step size by 3.4x while the CD chains agree).

**In the design frames it is worse.** Measured 2026-08-21 on the delivered
files, identically across all three designs: `DA061` and `DA068` each have
**2** responses in one category, `DA053` has 5, and 8–9 items (full) or 5–6
(nobike) fall below 20. These are the frames we actually fit, so these are
the numbers that matter:

| design | items with a category < 20 (full / nobike) | worst |
|---|---|---|
| CommonItem | 8 / 5 | `DA061` and `DA068`, 2 responses |
| Standard | 9 / 6 | same |
| Binterlaced | 9 / 6 | same |

`cm_preflight.py` check 2b now FAILs below 20 responses in any category and
WARNs below 40. Options, none free: collapse the sparse category (but
`response_cardinality` is a scalar, so it affects every item, and the mirt
arms must do the same or the comparison stops being like-for-like); tighten
the threshold prior and argue prior sensitivity; or document those item
parameters as not interpretable. **Decide before any full run.**

**F. OUT OF SCOPE HERE (2026-08-21) — the CD reference is the coauthor's.**
This repo no longer fits CD; see "Scope of the work in this repo". The
analysis below stands and should be sent to them, because whichever source
they pick changes what our estimates are compared against. Measured on the
27-item scale, and note the design masking is a **strict overlay** on CD --
all 105 administered (design, form, item) cells have exactly CD's observed
respondents, so ~7.9% baseline nonresponse sits inside every arm's data and
no arm ever sees complete responses:

| CD source | N | CM missing | complete cases | selection vs rest |
|---|---|---|---|---|
| main, all rows | 1363 | 8.33% | 798 (58.5%) | — |
| main, complete cases | 798 | 0% | 798 | -0.119 SD |

Recommend the full 1363, with a complete-case sensitivity check on item
parameters only. (`_2` was the third candidate and is out of scope -- see
"Data files".)

The tension is real either way and belongs in the write-up: calibrating on
all 1363 makes the CD reference itself a missing-data method, while
restricting to the complete cases costs 41% of the sample and selects on
completeness. There is no third option.

**G. Confirm the Standard design's chained linking is intended.** Forms 2
and 3 share zero items by construction (see "Data files"), so Stocking-Lord
must chain 2 -> 1 -> 3. That is a coherent reading of the standard design,
but it means SL's error for the 2-3 comparison compounds two linkings while
CommonItem's does not — which is a result about the design, not about the
method, and needs saying in the write-up.

## How to work here

1. `cm_preflight.py` must pass before any fitting. **Run it on each design
   file** — those are the frames we fit, and since the CD calibration moved
   to the coauthor (see "Scope"), CD is no longer part of this pipeline.
   Preflight detects `grp_final`, prints the form layout, and notes that
   checks 3–7 then describe the design rather than the data contract. That
   is the right reading here: checks 1, 2 and 2b are the contract, and 2b
   is the one that gates the runs.

   ```
   for d in CommonItem Standard Binterlaced; do
     python -m mice_imp.cm_preflight \
       data_wdfab/WDFAB_ExperimentalData_CM${d}_Jul2026.dta
   done
   ```

2. Smoke-test `cm_bayes_arms.py` with `--num-warmup 200 --num-samples 200`
   before committing to full chains. Signatures are verified against
   `7a29ec5` (see Environment), but nothing has been *executed* end to end.

   ```
   python -m mice_imp.cm_bayes_arms \
       data_wdfab/WDFAB_ExperimentalData_CMCommonItem_Jul2026.dta \
       --items full --output-dir results/commonitem/full \
       --num-warmup 200 --num-samples 200
   ```

   `--items {full,nobike}` picks the item set; run each dataset both ways,
   into separate `--output-dir`s.
3. Keep logic in scripts with argparse and `.npz` checkpoints. The grid is
   3 designs x 2 item sets x 3 arms x replications; individual arms fail and need
   selective re-runs, which is painful from a notebook. The per-design
   notebooks exist for reading results interactively — they call into
   `mice_imp/` and hold no logic of their own. Do not move logic into them.
4. Never silently "fix" a failing check by relaxing it. Every check here
   corresponds to a failure that is silent downstream, not loud.
