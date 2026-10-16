#!/usr/bin/env python
"""
Generate one driver notebook per (masked design x item set).

Every dataset is run twice -- once on the full 27-item scale, once with the
bicycling block dropped -- so this writes SIX notebooks:

    cm_<design>_full.ipynb     27 items
    cm_<design>_nobike.ipynb   20 adapted DA items

They are identical except for a design name, an item set, and the facts in
the header. Keeping them GENERATED rather than hand-maintained is
deliberate: the grid is 3 designs x 2 item sets x 3 arms x replications, and
six hand-edited copies of the same 10 cells drift apart silently -- you fix
a sampler setting in one and forget the other five.

All real logic lives in `mice_imp/`. These notebooks only set a design and
an item set, call in, and plot. Anything you would want to change for all
six belongs in `mice_imp/cm_bayes_arms.py`; anything design-specific belongs
in DESIGNS below, anything item-set-specific in ITEM_SETS.

Usage:
    python notebooks/make_design_notebooks.py
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
if str(REPO) not in sys.path:
    sys.path.insert(0, str(REPO))

# Sampler sizes are quoted in the notebook prose, so read them from the runner
# rather than restating them -- a hardcoded "200/200" here goes stale the
# moment the profile changes, and the prose is what people size a run against.
from mice_imp.run_grid import PROFILES  # noqa: E402

SMOKE, FULL = PROFILES["smoke"], PROFILES["full"]
OUT = REPO / "notebooks"

# Design-specific facts, re-established 2026-08-21 against the corrected
# design files (see CLAUDE.md "Data files"). All three share the same six
# anchors and the same 21 single-form items; they differ only in anchor
# allocation. `per_form` is keyed by item set: dropping the bicycling block
# leaves the anchors untouched (all six are DA items), so form-pair overlap
# is identical for both runs and only the single-form items thin out.
DESIGNS = {
    "CommonItem": {
        "title": "Common-item design",
        "anchor_rule": "all six anchors administered in all three forms",
        "overlap": "6 / 6 / 6",
        "per_form": {"full": "13 / 13 / 13", "nobike": "11 / 11 / 10"},
        "anchor_forms": {
            "DA054": [1, 2, 3], "DA058": [1, 2, 3], "DA060": [1, 2, 3],
            "DA064": [1, 2, 3], "DA066": [1, 2, 3], "DA067": [1, 2, 3],
        },
        "note": (
            "This is the only design with a common anchor set across all "
            "three forms, so it is the one where Stocking-Lord linking and "
            "MG-IRT are on their strongest footing. Expect it to be the "
            "most favourable design for the frequentist arms -- which is "
            "the point of including it."
        ),
    },
    "Standard": {
        "title": "Standard design",
        "anchor_rule": "all six anchors in form 1; forms 2 and 3 carry three each",
        "overlap": "3 / 3 / 0",
        "per_form": {"full": "13 / 10 / 10", "nobike": "11 / 8 / 7"},
        "anchor_forms": {
            "DA054": [1, 3], "DA058": [1, 3], "DA060": [1, 2],
            "DA064": [1, 2], "DA066": [1, 2], "DA067": [1, 3],
        },
        "note": (
            "Forms 2 and 3 share **zero** items, by construction. Form 1 is "
            "the reference form and the other two link only through it, so "
            "Stocking-Lord must chain 2 -> 1 -> 3. Its error for that "
            "comparison compounds two linkings while the common-item "
            "design's does not. That is a result about the design, not "
            "about the method -- say so in the write-up. The Bayesian arms "
            "are not affected: they never link, they calibrate jointly."
        ),
    },
    "Binterlaced": {
        "title": "Block-interlaced design",
        "anchor_rule": "each anchor sits in a different pair of forms, two per pair",
        "overlap": "2 / 2 / 2",
        "per_form": {"full": "11 / 11 / 11", "nobike": "9 / 9 / 8"},
        "anchor_forms": {
            "DA054": [2, 3], "DA058": [1, 2], "DA060": [1, 3],
            "DA064": [1, 2], "DA066": [1, 3], "DA067": [2, 3],
        },
        "note": (
            "Overlap is balanced across all three form pairs, but thin -- "
            "two anchors per pair. Watch the anchor correlations: DA060 and "
            "DA066 correlate at 0.865 on CD and both link forms 1 and 3 "
            "here, so that pair is carrying less independent information "
            "than 'two anchors' suggests (CLAUDE.md open issue B)."
        ),
    },
}


# Item-set facts. `key` matches mice_imp.wdfab_io.ITEM_SETS, which is where
# the actual lists live -- do not restate the items here.
ITEM_SETS = {
    "full": {
        "title": "all 27 items",
        "n_items": 27,
        "n_single": 21,
        "import": "ITEM_KEYS as FIT_KEYS",
        "note": (
            "The full Community Mobility scale: 20 adapted `DA*` items plus "
            "the seven German bicycling items. `Bike_2` enters as "
            "`Bike_2_r_cor`, the recoding the collaborators corrected on "
            "2026-08-21 -- both raw columns are mis-scored and are excluded "
            "(CLAUDE.md fact 16)."
        ),
    },
    "nobike": {
        "title": "no bicycling items",
        "n_items": 20,
        "n_single": 14,
        "import": "DA_KEYS as FIT_KEYS",
        "note": (
            "The 20 adapted `DA*` items only. The bicycling block is unique "
            "to the German instrument, it carries the strongest local "
            "dependence on CD (`Bike_1`/`Bike_7` r = 0.931, "
            "`Bike_4`/`Bike_5` 0.921 -- open issue B), and its nonresponse "
            "is the one place where the MCAR premise is measurably strained "
            "(open issue A: bike block 12.7% missing against 6.8% for the DA "
            "block, standardised difference +0.19 in DA mean score between "
            "respondents who answered at least one bike item and those who "
            "answered none).\n\n"
            "This run is what shows whether any conclusion about the five "
            "calibration approaches depends on the bike block. It is a "
            "sensitivity analysis, not a fallback -- report both."
        ),
    },
}


def md(text: str) -> dict:
    return {"cell_type": "markdown", "metadata": {}, "id": "",
            "source": text.splitlines(keepends=True)}


def code(text: str) -> dict:
    return {"cell_type": "code", "execution_count": None, "metadata": {}, "id": "",
            "outputs": [], "source": text.rstrip().splitlines(keepends=True)}


def _assign_ids(cells: list[dict], slug: str) -> list[dict]:
    """Stable per-cell ids. nbformat 4.5+ requires them, and deriving them
    from position keeps regeneration diff-free rather than churning uuids."""
    for i, cell in enumerate(cells):
        cell["id"] = f"{slug}-{i:02d}"
    return cells


def build(design: str, spec: dict, itemset: str, ispec: dict) -> dict:
    anchor_tbl = "\n".join(
        f"| `{k}` | {', '.join(str(f) for f in v)} |"
        for k, v in spec["anchor_forms"].items()
    )

    cells = [
        md(f"""# B-IRT / B-MI — {spec['title']}, {ispec['title']} (`CM{design}`)

Bayesian arms for one masked design of the WD-FAB-DE Community Mobility
missing-data comparison, on **{ispec['n_items']} items**.
**Generated by `notebooks/make_design_notebooks.py` — edit the generator,
not this file.** All logic lives in `mice_imp/`; this notebook sets a design
and an item set, calls in, and plots.

## This item set

{ispec['note']}

Each design is run on both item sets, into separate output directories.
Dropping the bicycling block leaves the six anchors untouched — all of them
are `DA*` items — so form-pair overlap is the same in both runs and only the
single-form items thin out.

## This design

{spec['anchor_rule'].capitalize()}.

| | |
|---|---|
| form-pair overlap (1&2 / 1&3 / 2&3) | {spec['overlap']} |
| items administered per form | {spec['per_form'][itemset]} |
| respondents per form | 455 / 454 / 454 |

| anchor | administered in forms |
|---|---|
{anchor_tbl}

The other {ispec['n_single']} items sit in exactly one form each,
identically across all three designs.

{spec['note']}

## The three arms

| arm | imputation | what it is |
|---|---|---|
| `birt` | none | masked cells contribute exactly 0 to the log-likelihood |
| `bmi` | `PairwiseOrdinalStackingModel` PMFs | masked cells contribute `log sum_k q_k p_k(phi)` — analytic Rao-Blackwellisation, **not** Rubin-style MI |
| `flat` | uniform `1/K` | noise-floor control |

`flat` targets **exactly the same posterior** as `birt`: with `q_k = 1/K` the
masked-cell contribution is `log(1/K)`, a constant with zero gradient. Any
`flat`-vs-`birt` difference is Monte Carlo noise, and it tells you the
resolution at which a real B-MI effect could be detected. A *systematic*
difference means the plumbing is wrong.

Run order matters: `bmi` reuses `birt`'s ADVI warm-start."""),

        md("## Setup"),

        code(f'''import os
import sys
from pathlib import Path

REPO = Path("{REPO}")
sys.path.insert(0, str(REPO))

os.environ.setdefault("JAX_PLATFORMS", "cpu")
os.environ.setdefault("JAX_ENABLE_X64", "1")

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from mice_imp.wdfab_io import {ispec['import']}, FORM_KEY, load_cm, describe
from mice_imp.cm_bayes_arms import (
    fit_arm, fit_imputation_model, PairwiseOnlyImputationModel, _report_noise_floor,
)

DESIGN = "{design}"
ITEMSET = "{itemset}"   # see mice_imp.wdfab_io.ITEM_SETS
DATA_PATH = REPO / "data_wdfab" / f"WDFAB_ExperimentalData_CM{{DESIGN}}_Jul2026.dta"

# One directory per (design, item set). The two runs share a dataset but not
# a scale, so they must not share arm .npz files or an imputation model.
OUTPUT_DIR = REPO / "results" / DESIGN.lower() / ITEMSET
IMPUTER_PATH = OUTPUT_DIR / "imputation_model"

CARDINALITY = 5
SEED = 42

# SMOKE = True is a fast wiring check, NOT an inferential run. False (the
# default since 2026-08-21) is the real thing: 4 chains, 3000 warmup, 2000
# samples. The pipeline HAS now been run end to end at smoke settings -- all
# three arms, 0% B-MI fallback, ADVI reaching every arm, and a flat-vs-birt
# noise floor of 0.003 in theta RMSE.
SMOKE = False

if SMOKE:
    NUM_CHAINS, NUM_WARMUP, NUM_SAMPLES = 2, 200, 200
else:
    NUM_CHAINS, NUM_WARMUP, NUM_SAMPLES = 4, 3000, 2000

# Measured, not inherited: mice_imp/sweep_sampler.py compared 2e-3/0.95,
# 5e-4/0.98 and 1e-4/0.98 on B-IRT with everything else fixed, and 5e-4/0.98
# came out best on both divergences and R-hat. That is also what B-MI used
# already, so all three arms now share a sampler -- which keeps the
# flat-vs-birt noise floor a like-for-like comparison.
STEP_SIZE, TARGET_ACCEPT = 0.0005, 0.98
BMI_STEP_SIZE, BMI_TARGET_ACCEPT = 0.0005, 0.98

OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
print(f"design={{DESIGN}}  items={{ITEMSET}} ({{len(FIT_KEYS)}})  "
      f"smoke={{SMOKE}}  chains={{NUM_CHAINS}} "
      f"warmup={{NUM_WARMUP}} samples={{NUM_SAMPLES}}")
print(f"out: {{OUTPUT_DIR}}")'''),

        md("""## Load

`load_cm` reads the `.dta` with `convert_categoricals=False` (the default
returns the German label *strings*) and shifts the raw 1..5 codes onto 0..4,
raising on anything out of range. That shift is not cosmetic: `GRModel` masks
a cell wherever `(y < 0) | (y >= response_cardinality) | isnan(y)`, so a
stored `5` with `response_cardinality=5` would vanish from the likelihood
without an error.

`load_cm` always reads the full 27-item scale; `FIT_KEYS` selects the
{ispec['n_items']} items this run calibrates. `describe` is called on
`FIT_KEYS`, so the form layout it prints is the layout *for this item set*.

`Bike_2` enters as `Bike_2_r_cor`, the recoding the collaborators corrected
on 2026-08-21 — both raw columns (`Bike_2`, `Bike_2_r`) are mis-scored and
are excluded. The CD export does not carry the corrected column; `load_cm`
derives it. See CLAUDE.md fact 16."""),

        code('''df = load_cm(DATA_PATH, cardinality=CARDINALITY)
describe(df, FIT_KEYS)

fitting_frame = df[FIT_KEYS]
print(f"\\nfitting frame: {fitting_frame.shape[0]} x {fitting_frame.shape[1]}")'''),

        md("""## Arm 1 — B-IRT

No imputation model. Runs the ADVI warm-start (100 iterations) that the
other two arms reuse.

ADVI is a warm-start, never the inference. Chang found mean-field ADVI
settling into a poor local optimum and moved to NUTS on item parameters with
abilities integrated out on a quadrature grid — which is also why this is
tractable: the sampler explores ~items x categories dimensions, not that
plus N."""),

        code('''birt = fit_arm(
    "birt", fitting_frame, FIT_KEYS, CARDINALITY, OUTPUT_DIR,
    imputation_model=None, run_advi=True,
    num_chains=NUM_CHAINS, num_warmup=NUM_WARMUP, num_samples=NUM_SAMPLES,
    step_size=STEP_SIZE, target_accept_prob=TARGET_ACCEPT, seed=SEED,
)'''),

        md("""## Arm 2 — B-MI

The imputation model is fit on the **CM items only**. Chang fits his across
all eight WD-FAB scales; doing that here would give B-MI information the
FIML / MG-IRT / Stocking-Lord arms never see, and B-MI would win for a
reason unrelated to imputation. A cross-scale version is legitimate only as
an explicitly labelled secondary arm.

Refit per design — missingness patterns differ, so do not fit once and reuse
across the three notebooks.

**Watch the fallback rate.** `_compute_batch_pmfs` wraps each per-cell call
in `except (ValueError, KeyError, AttributeError): pmfs[...] = 1.0 / K`, and
a flat PMF is mathematically equivalent to no imputation. So every fallback
silently downgrades that cell to B-IRT. With most items masked in two of the
three forms, the predictors the imputation model wants are often masked too,
and the no-bike run has fewer predictors left to fall back on.
`attach_imputation_pmfs` prints the rate and warns above 10%. **A null B-MI
result is not interpretable until you know this number is low.**"""),

        code('''imputer = fit_imputation_model(
    fitting_frame, FIT_KEYS, seed=SEED, save_path=IMPUTER_PATH,
)'''),

        code('''bmi = fit_arm(
    "bmi", fitting_frame, FIT_KEYS, CARDINALITY, OUTPUT_DIR,
    imputation_model=PairwiseOnlyImputationModel(mice_model=imputer),
    init_advi_params=birt["advi_params"], run_advi=False,
    num_chains=NUM_CHAINS, num_warmup=NUM_WARMUP, num_samples=NUM_SAMPLES,
    step_size=BMI_STEP_SIZE, target_accept_prob=BMI_TARGET_ACCEPT, seed=SEED + 1,
)'''),

        md("""## Arm 3 — flat control

Same posterior as `birt` by construction. This is the noise floor."""),

        code('''flat = fit_arm(
    "flat", fitting_frame, FIT_KEYS, CARDINALITY, OUTPUT_DIR,
    imputation_model=None,
    init_advi_params=birt["advi_params"], run_advi=False,
    num_chains=NUM_CHAINS, num_warmup=NUM_WARMUP, num_samples=NUM_SAMPLES,
    step_size=STEP_SIZE, target_accept_prob=TARGET_ACCEPT, seed=SEED + 2,
)'''),

        md("""## Noise floor

If B-MI differs from B-IRT by less than about twice the `flat`-vs-`birt`
distance, there is no detectable effect at these sampler settings — report
that as a resolution limit, not as a null result."""),

        code('''results = {"birt": birt, "bmi": bmi, "flat": flat}
_report_noise_floor(results, OUTPUT_DIR)

print("\\nmax R-hat by arm:")
for name, res in results.items():
    flag = "  <-- ABOVE 1.05" if res["max_rhat"] > 1.05 else ""
    print(f"  {name:6s} {res['max_rhat']:.4f}{flag}")'''),

        md("## Comparison plots"),

        code('''def _tufte(ax):
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    ax.tick_params(direction="out", length=3, width=0.5)


fig, axes = plt.subplots(1, 2, figsize=(11, 5))
for ax, other in zip(axes, ["flat", "bmi"]):
    x, y = birt["eap"], results[other]["eap"]
    r = float(np.corrcoef(x, y)[0, 1])
    rmse = float(np.sqrt(np.mean((x - y) ** 2)))
    ax.scatter(x, y, s=8, alpha=0.35)
    lo, hi = min(x.min(), y.min()), max(x.max(), y.max())
    ax.plot([lo, hi], [lo, hi], color="gray", lw=0.8, ls="--")
    ax.set_xlabel("B-IRT theta")
    ax.set_ylabel(f"{other} theta")
    ax.set_title(f"{other} vs birt   r={r:.4f}  RMSE={rmse:.4f}")
    _tufte(ax)
fig.suptitle(f"{DESIGN} / {ITEMSET}: theta agreement "
             f"(left panel is the noise floor)")
fig.tight_layout()'''),

        code('''# Discriminations, with the flat/birt gap as the reference for "no difference".
fig, ax = plt.subplots(figsize=(7, max(4, len(FIT_KEYS) * 0.28)))
y = np.arange(len(FIT_KEYS))
for off, (name, res) in zip([-0.25, 0.0, 0.25], results.items()):
    ip = res["item_params"]
    ax.errorbar(ip["a_mean"], y + off, xerr=ip["a_sd"], fmt="o", ms=3,
                lw=0.8, capsize=0, label=name)
ax.set_yticks(y)
ax.set_yticklabels(FIT_KEYS, fontsize=7)
ax.invert_yaxis()
ax.set_xlabel("discrimination (mirt convention, post-standardisation)")
ax.legend(frameon=False, fontsize=8)
ax.set_title(f"{DESIGN} / {ITEMSET}: item discriminations by arm")
_tufte(ax)
fig.tight_layout()'''),

        md("""## Outputs

`fit_arm` already wrote `{birt,bmi,flat}.npz` and `_report_noise_floor`
wrote `noise_floor.json`, both under `OUTPUT_DIR`. The cell below adds a
single combined file for the cross-design comparison.

Item parameters are stored in mirt's convention (`d_ik = -a_i * b_ik`), with
thresholds already `cumsum`-ed from the stored increments and extracted
*after* `standardize_marginal`. Do not redo any of those three steps
downstream — `to_mirt_convention` centralises them."""),

        code('''np.savez(
    OUTPUT_DIR / "summary.npz",
    design=np.asarray(DESIGN),
    itemset=np.asarray(ITEMSET),
    item_keys=np.asarray(FIT_KEYS),
    form=df[FORM_KEY].to_numpy() if FORM_KEY in df.columns else np.asarray([]),
    smoke=np.asarray(SMOKE),
    **{f"{n}_{k}": np.asarray(res[k])
       for n, res in results.items() for k in ("eap", "psd", "max_rhat")},
    **{f"{n}_a_mean": res["item_params"]["a_mean"] for n, res in results.items()},
    **{f"{n}_d_mean": res["item_params"]["d_mean"] for n, res in results.items()},
)
print(f"wrote {OUTPUT_DIR / 'summary.npz'}")'''),

        md("""### CSV for coauthors

`item_parameters.csv` — one row per (arm, item): `a`, `b1..b4` and their
posterior SDs. `theta.csv` — one row per respondent, keyed on `id_work`,
with an EAP theta and its PSD per arm.

`b` is the location parameterisation `a_i(theta - b_ik)`, which is what
"a and b1..b4" normally means; `--include-d` / `include_d=True` adds mirt's
intercepts alongside. Both files carry `max_rhat` per arm, so a
non-converged arm cannot be picked up silently."""),

        code('''from mice_imp.export_estimates import export

export(OUTPUT_DIR, design=DESIGN.lower(), itemset=ITEMSET,
       source=DATA_PATH, include_d=True)'''),
    ]

    return {
        "cells": _assign_ids(cells, f"{design.lower()}-{itemset}"),
        "metadata": {
            "kernelspec": {"display_name": "Python 3", "language": "python",
                           "name": "python3"},
            "language_info": {"name": "python"},
        },
        "nbformat": 4,
        "nbformat_minor": 5,
    }


# The two batch drivers. Both run the same six cells through the same
# `mice_imp/run_grid.py`; they differ only in which anchor variant of the
# design files they point it at, and therefore where the results land.
#
# `_small` is a misleading filename and the header below says so out loud:
# those files are the same 1363 respondents with THREE anchors instead of six,
# not a smaller sample. `_alt` keeps six anchors but changes which items they
# are -- two of them bike items, which changes what `nobike` means for it.
# See VARIANTS in mice_imp/run_grid.py.
RUNNERS = {
    "run_all": {
        "slug": "rungrid",
        "variant": "main",
        "results": "results",
        "flags": '"--force"',
        "title": "Run the whole grid — 3 designs x 2 item sets",
        "lede": (
            "Runs all six calibrations back to back, `birt` -> `bmi` -> "
            "`flat` in each."
        ),
        "preamble": "",
        "force_note": """If you smoke-tested first, the smoke `.npz` files are sitting in the output
directories and will cause every run to be skipped as already complete —
hence `--force` here.""",
    },
    "run_all_sensitivity": {
        "slug": "rungridsens",
        "variant": "reduced_anchor",
        "results": "results_reduced_anchor",
        "flags": '"--variant", "reduced_anchor"',
        "title": "Sensitivity grid — three anchors instead of six",
        "lede": (
            "The same six calibrations, `birt` -> `bmi` -> `flat` in each, on "
            "the `_small` design files."
        ),
        "preamble": """## What this varies — read this before quoting any number from it

The `_small` files are **not a smaller sample.** Same 1363 respondents, same
128 columns, same form sizes 455 / 454 / 454. What changes is the anchor set:
**three anchors (`DA054`, `DA058`, `DA066`) where the main delivery carries
six.** Verified against the delivered files on 2026-08-28.

| design | overlap 1&2 / 1&3 / 2&3 — main | reduced anchor |
|---|---|---|
| CommonItem | 6 / 6 / 6 | **3 / 3 / 3** |
| Binterlaced | 2 / 2 / 2 | **1 / 1 / 1** |
| Standard | 3 / 3 / 0 | **1 / 2 / 0** |

So this is a sensitivity analysis on **linking strength**, not on sample size,
and it should be described that way in the write-up — "small" is the
collaborators' filename, not what is being varied. It is also a direct probe of
**open issue B**: two of the three surviving anchors are the correlated pair
`DA054` / `DA058` (r = 0.840), and `DA066` correlates 0.88 with `DA053` and
0.876 with `DA060`. Three anchors that are not independent carry less joint
information than three anchors would suggest, and Binterlaced drops to a
**single** shared item per form pair.

All three anchors are `DA*` items, so `nobike` leaves the anchor set untouched
in this variant exactly as it does in the main one, and the two item sets stay
comparable.

### Preflight check 2b FAILs here — decide before trusting the output

Run on 2026-08-28, all three files fail category sparsity: **10–11 items have a
category with fewer than 20 responses** (`DA061`, `DA068`, `DA053`, `Bike_1`,
`DA069_r`, `Bike_6`, `Bike_7`, `DA067`, `DA073`, `DA060`, and `DA066` in
Standard and Binterlaced), against 8–9 items in the main files. Thinner
anchoring spreads the same responses across fewer shared items, so open issue E
is *worse* here, not better. Expect divergent transitions and R-hat failures
that look like a sampler problem and are not one. This is the standing issue-E
decision (collapse the category, tighten the threshold prior, or document those
parameters as not interpretable) — it is not resolved by running this grid.

""",
        "force_note": """No `--force` here: `results_reduced_anchor/` starts empty, so nothing is
skipped. Add it only after a smoke run has put `.npz` files there.""",
    },
    "run_all_alt_anchor": {
        # Own cell-id namespace: _keep_outputs matches on id, and the ids of the
        # two existing notebooks must not move or their stored output is lost.
        "slug": "rungridalt",
        "variant": "alt_anchor",
        "results": "results_alt_anchor",
        "flags": '"--variant", "alt_anchor"',
        "title": "Sensitivity grid — a different six anchors",
        "lede": (
            "The same six calibrations, `birt` -> `bmi` -> `flat` in each, on "
            "the `_Aug2026_alt` design files."
        ),
        "preamble": """## What this varies — read this before quoting any number from it

The `_alt` files keep the main delivery's design structure exactly — same 1363
respondents in the same order, same form assignment, same anchor count, same
form-pair overlap and items per form — and change **which items are the
anchors**:

| | anchors |
|---|---|
| main | `DA054` `DA058` `DA060` `DA064` `DA066` `DA067` |
| alt | `DA052` `DA058` `DA066` `DA073` `Bike_3` `Bike_7` |

Four of the six are replaced, and the single-form items are reshuffled across
forms to make room. Observed responses agree with the main files cell for cell
wherever both carry one, so this is a different mask over the same data.
Verified against the delivered files on 2026-09-14. It is a sensitivity
analysis on **anchor choice**, as `reduced_anchor` is on anchor count.

Issue B bites the new set directly: `Bike_7` is a member of the strongest
dependent pair on the scale (`Bike_1` / `Bike_7`, r = 0.931), and `DA073`
correlates 0.888 with `DA074`.

### `nobike` is not like the other `nobike` runs

Two of the six anchors are bicycling items. Dropping the bike block therefore
removes a third of the linking as well as the block itself — unlike `main` and
`reduced_anchor`, whose anchors are all `DA*`:

| design | overlap 1&2 / 1&3 / 2&3 — alt `full` | alt `nobike` |
|---|---|---|
| CommonItem | 6 / 6 / 6 | **4 / 4 / 4** |
| Binterlaced | 2 / 2 / 2 | **2 / 2 / 0** |
| Standard | 3 / 3 / 0 | **3 / 1 / 0** |

Binterlaced `nobike` ends up with forms 2 and 3 sharing **no item**, as
Standard has by design. Both item sets are run (decided 2026-09-14), but in
this variant the `full`-vs-`nobike` contrast confounds dropping the bike block
with weakening the linking. Say so wherever it is reported.

### Preflight check 2b FAILs here too

Run on 2026-09-14: **9–10 items have a category with fewer than 20 responses**
(`DA061`, `DA053`, `DA068`, `Bike_1`, `Bike_6`, `DA069_r`, `DA074`, `DA067`,
`DA060`, and `DA066` in Standard and Binterlaced) — about the same as the main
files. This is the standing, deferred issue E; running this grid does not
resolve it.

""",
        "force_note": """No `--force` here: `results_alt_anchor/` starts empty, so nothing is
skipped. Add it only after a smoke run has put `.npz` files there.""",
    },
}


def build_runner(spec: dict) -> dict:
    """A batch driver: all six runs of one anchor variant, back to back.

    Holds no logic of its own -- everything is in `mice_imp/run_grid.py`, so
    that an unattended run does not depend on a live kernel. `spec` is one
    entry of RUNNERS above.
    """
    variant, results, flags = spec["variant"], spec["results"], spec["flags"]
    nohup_flags = "" if variant == "main" else f" --variant {variant}"
    flags_prose = ("`--force` as needed" if variant == "main"
                   else f'`--variant {variant}`')
    cells = [
        md(f"""# {spec["title"]}

{spec["lede"]}
**Generated by `notebooks/make_design_notebooks.py` — edit the generator,
not this file.** All logic is in `mice_imp/run_grid.py`.

{spec["preamble"]}Order is CommonItem, Binterlaced, Standard, and `full` before `nobike`:
increasing difficulty, so a failure lands where there is the most signal to
diagnose it. `standard/nobike` is the thinnest cell in the grid and runs last.

The runner is **resumable** — a run whose three arm `.npz` files already
exist is skipped, so an interrupted weekend continues rather than restarting
— **isolated**, in that one run raising does not stop the other five, and
**logged**, with each run's output captured to
`{results}/<design>/<itemset>/run.log` and `{results}/grid_summary.csv`
rewritten after every run.

Everything this notebook writes goes under **`{results}/`**, and every
exported CSV row carries `variant = "{variant}"`, so these estimates cannot be
pooled with the other grid's by accident.

## For a weekend run, prefer the terminal

A notebook kernel is the wrong container for something that has to survive
until Monday: a closed laptop, a suspended session or a dropped connection
takes the kernel and the run with it. From a terminal instead:

```
nohup python -m mice_imp.run_grid{nohup_flags} > {results}/grid.out 2>&1 &
tail -f {results}/grid.out
```

Same script, same resumability. Use the cells below to watch progress, or to
run a single cell of the grid interactively."""),

        md(f"""## Smoke first

Run the wiring check before committing a weekend to a full pass — it is
{SMOKE["chains"]} chains of {SMOKE["warmup"]}/{SMOKE["samples"]} with a
{SMOKE["advi"]}-epoch ADVI warm-start, against {FULL["chains"]} x
{FULL["warmup"]}/{FULL["samples"]} for the real thing. It writes to the same
directories, so a real run afterwards needs `--force` (or delete the smoke
`.npz` files).

It is sized to answer *does the plumbing work*, not *what is the answer*: at
{SMOKE["warmup"]} warmup draws the R-hats and the noise floor mean nothing.
Read only the three checks below off it. The floor on how fast it can go is
the B-MI imputation fit, which does not shrink with chain length; a re-run in
a directory that already has `imputation_model/` reuses it.

Override any of it with `--num-chains`, `--num-warmup`, `--num-samples`,
`--advi-iterations`.

Three things to read off it, each of which silently invalidates a run:

- `Initializing from ADVI solution` must appear for **all three** arms. If it
  appears for some and not others, the `flat`-vs-`birt` gap is measuring
  initialisation rather than Monte Carlo noise, and the noise floor is
  meaningless (CLAUDE.md fact 17).
- the **B-MI flat-fallback rate** must be low. Every fallback downgrades that
  cell to B-IRT, so a high rate means B-MI is not really running (fact 3).
- `flat` and `birt` must land on top of each other. They target the same
  posterior by construction; a systematic gap means the plumbing is wrong
  (fact 2)."""),

        code(f'''import subprocess, sys
from pathlib import Path

REPO = Path("{REPO}")

def run_grid(*flags):
    """Run mice_imp.run_grid as a subprocess, streaming its output."""
    cmd = [sys.executable, "-m", "mice_imp.run_grid", *flags]
    print(" ".join(cmd), flush=True)
    proc = subprocess.Popen(cmd, cwd=REPO, stdout=subprocess.PIPE,
                            stderr=subprocess.STDOUT, text=True, bufsize=1)
    for line in proc.stdout:
        print(line, end="")
    return proc.wait()


# Wiring check only -- uncomment to run it. It writes .npz files, so the
# full pass below would then need --force.
# run_grid("--smoke", {flags})'''),

        md(f"""## The full grid

4 chains, 3000 warmup, 2000 samples, six times over. Only start this once
the smoke output above looks right.

{spec["force_note"]}"""),

        code(f'''run_grid({flags})'''),

        md(f"""## Progress

Safe to run while the grid is still going: `{results}/grid_summary.csv` is
rewritten after every run, and each run's `run.log` is flushed as it goes."""),

        code(f'''import pandas as pd

summary = pd.read_csv(REPO / "{results}" / "grid_summary.csv")
cols = [c for c in ["design", "variant", "itemset", "n_items", "status", "minutes",
                    "birt_max_rhat", "bmi_max_rhat", "flat_max_rhat",
                    "bmi_fallback_pct", "advi_init_count",
                    "theta_rmse_flat_vs_birt", "theta_rmse_bmi_vs_birt"]
        if c in summary.columns]
summary[cols]'''),

        md(f"""## Re-run one cell

`--only` takes `design/itemset`, e.g. after fixing whatever made a single
run fail. Keep {flags_prose} on it — without that the re-run reads the
other variant's data and writes over the other variant's results:

```
run_grid("--only", "standard/nobike", {flags}, "--force")
```"""),

        code(f'''# run_grid("--only", "standard/nobike", {flags}, "--force")'''),
    ]
    return {
        "cells": _assign_ids(
            cells, spec["slug"]),
        "metadata": {
            "kernelspec": {"display_name": "Python 3", "language": "python",
                           "name": "python3"},
            "language_info": {"name": "python"},
        },
        "nbformat": 4,
        "nbformat_minor": 5,
    }


# The complete-data diagnostic. `WDFAB_ExperimentalData_Full.dta` (arrived
# 2026-10-08) is the design files' 128-column schema with NO design masking:
# the CD frame, with `Bike_2_r_cor` already carried. Verified on arrival
# against all nine design files: zero disagreements on cells both observe, and
# every administered (design, form, item) cell has exactly this file's
# respondents -- the masks are a strict overlay on it.
#
# It is a DIAGNOSTIC, not a seventh cell of the grid and not the CD reference
# arm (that is the coauthor's -- CLAUDE.md "Scope"). It asks one question the
# masked runs cannot: what does our B-IRT sampler do when nothing is masked?
#
# Both item sets, like the grid. The nobike run is the reference for the
# nobike design runs -- the cells where B-MI converges -- and drops the bike
# block whose local dependence inflates the full run's bike slopes.
# `title`, `import` and `note` are the only item-set-specific text; for `full`
# they render the notebook byte-identically to its first version, so its
# stored output survives regeneration.
_CD_COMMON = {"file": "WDFAB_ExperimentalData_Full.dta", "results": "results_cd"}
CD_DIAGNOSTICS = {
    "full": {
        **_CD_COMMON, "slug": "cdfull", "itemset": "full",
        "title": "all 27 items", "import": "ITEM_KEYS as FIT_KEYS", "note": "",
    },
    "nobike": {
        **_CD_COMMON, "slug": "cdnobike", "itemset": "nobike",
        "title": "the 20 DA items", "import": "DA_KEYS as FIT_KEYS",
        "note": """## This item set

The 20 adapted `DA*` items only, bicycling block dropped. On the full run the
design B-IRT fits agree with this frame on the DA discriminations (median
ratio 0.96 to 1.02) but put the bike slopes about 35% lower, most likely
because the seven locally dependent bike items are only ever answered
together here. Without the bike block that effect is gone, so this run shows
how the designs compare when it is out of the picture. It is also the
reference for the `nobike` design runs, which are the cells where B-MI
converges.

""",
    },
}


def build_cd_diagnostic(spec: dict) -> dict:
    cells = [
        md(f"""# B-IRT on the complete data — diagnostic, {spec['title']}

`birt` only, fit on `data_wdfab/{spec['file']}`.
**Generated by `notebooks/make_design_notebooks.py` — edit the generator,
not this file.** All fitting logic lives in `mice_imp/`; this notebook sets
the frame, calls in, and plots.

## What the file is

The same 1363 respondents, 128 columns, row order and `grp_final` as the
design files, with **no design masking**: 8.33% of the 27 CM cells are
missing, all of it baseline nonresponse, and every item is observed in every
form. Verified on arrival (2026-10-08) against all nine design files (main,
`_small`, `_alt`): zero disagreements on cells both observe, and every
administered (design, form, item) cell has exactly this file's respondents.
The masked designs are cut from it.

It carries `Bike_2_r_cor` for all 1191 bike respondents, matching the
recode table `1->4 2->3 3->2 4->1 5->5` exactly, so `load_cm` reads it
rather than deriving it (CLAUDE.md fact 16).

{spec['note']}## Why it is a diagnostic, not an arm

This is **not** the CD reference — that calibration belongs to the coauthor
(CLAUDE.md "Scope"), and nothing here is handed over as one. It is also not a
seventh cell of the grid. It answers questions the masked runs cannot:

1. **Is the sampler's trouble caused by masking or by the data?** On a frame
   with nothing masked, divergences and R-hat failures can only come from the
   data. Preflight check 2b FAILs here too: `DA068` has 10 responses in one
   category, `DA053` 13, `DA061` 15 (open issue E). Issue E's earlier
   500-warmup probe found CD diverging as badly as Binterlaced; this is the
   full-length version of that probe.
2. **How far does each design's B-IRT land from the unmasked B-IRT?** The
   same engine, sampler and priors on the same people, with and without the
   mask. That isolates what the design costs our arm.

Read (2) with handover fact 2 in mind: every run is standardised on its own
(`standardize_marginal`, theta ~ N(0,1) within the run). All runs here
standardise over the same 1363 respondents, so the metrics are close, but
they are **not linked** — a uniform shift or stretch between a design and
this fit is identification, not error.

Outputs go to `{spec['results']}/{spec['itemset']}/`, never `results/`, and
the exported CSVs carry `design = "cd"` and `variant = "complete_data"`."""),

        md("## Setup"),

        code(f'''import os
import sys
from pathlib import Path

REPO = Path("{REPO}")
sys.path.insert(0, str(REPO))

os.environ.setdefault("JAX_PLATFORMS", "cpu")
os.environ.setdefault("JAX_ENABLE_X64", "1")

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from mice_imp.wdfab_io import {spec['import']}, FORM_KEY, load_cm, describe
from mice_imp.cm_bayes_arms import fit_arm
from mice_imp.export_estimates import _load_arm

ITEMSET = "{spec['itemset']}"
DATA_PATH = REPO / "data_wdfab" / "{spec['file']}"
OUTPUT_DIR = REPO / "{spec['results']}" / ITEMSET

CARDINALITY = 5
SEED = 42

# A finished birt.npz in OUTPUT_DIR is loaded rather than refit. The full
# fit takes hours; set REFIT = True to run it again anyway.
REFIT = False

# SMOKE = True is a wiring check, not an inferential run. It writes to
# OUTPUT_DIR like the real fit does, so set REFIT = True for the real one
# afterwards.
SMOKE = False

if SMOKE:
    NUM_CHAINS, NUM_WARMUP, NUM_SAMPLES = 2, 200, 200
else:
    NUM_CHAINS, NUM_WARMUP, NUM_SAMPLES = {FULL["chains"]}, {FULL["warmup"]}, {FULL["samples"]}

# The grid's sampler, so the comparison with the design runs below differs
# by the mask and nothing else.
STEP_SIZE, TARGET_ACCEPT = 0.0005, 0.98

OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
print(f"items={{ITEMSET}} ({{len(FIT_KEYS)}})  smoke={{SMOKE}}  chains={{NUM_CHAINS}} "
      f"warmup={{NUM_WARMUP}} samples={{NUM_SAMPLES}}")
print(f"out: {{OUTPUT_DIR}}")'''),

        md("""## Load

`load_cm` reads with `convert_categoricals=False`, shifts 1..5 onto 0..4 and
raises on anything out of range (CLAUDE.md facts 1 and 15).

The check below confirms this is the unmasked frame: under any design some
item has **no** responses in some form. Here none may."""),

        code('''df = load_cm(DATA_PATH, cardinality=CARDINALITY)
describe(df, FIT_KEYS)

fitting_frame = df[FIT_KEYS]
observed_per_form = fitting_frame.notna().groupby(df[FORM_KEY]).sum()
unadministered = (observed_per_form == 0).sum().sum()
assert unadministered == 0, (
    f"{unadministered} (form, item) cells have no responses -- this is a "
    "masked design file, not the complete-data frame")
print(f"\\nfitting frame: {fitting_frame.shape[0]} x {fitting_frame.shape[1]}, "
      f"{fitting_frame.isna().to_numpy().mean():.2%} missing, every item in every form")'''),

        md("""## Category sparsity

The suspected cause of divergence (open issue E). Items with a category below
20 responses are what preflight 2b fails on; they are marked in every plot
below, so a misfit that sits on them can be read as a sparsity effect."""),

        code('''counts = pd.DataFrame(
    {k: fitting_frame[k].value_counts().reindex(range(CARDINALITY), fill_value=0)
     for k in FIT_KEYS}).T
counts.columns = [f"cat{c}" for c in range(CARDINALITY)]
counts["min"] = counts.min(axis=1)
SPARSE = counts.index[counts["min"] < 20].tolist()
print(f"items with a category < 20: {SPARSE}")
counts.sort_values("min").head(8)'''),

        md("""## B-IRT

No imputation model, ADVI warm-start then NUTS — the same `fit_arm` call the
grid makes for `birt`. Check that `Initializing from ADVI solution` appears
in the output (CLAUDE.md fact 17), and note the **mean non-divergent ratio**:
that is the number question 1 is about, and it is only printed, not saved."""),

        code('''npz = OUTPUT_DIR / "birt.npz"
if npz.exists() and not REFIT:
    print(f"loading existing fit: {npz}")
else:
    fit_arm(
        "birt", fitting_frame, FIT_KEYS, CARDINALITY, OUTPUT_DIR,
        imputation_model=None, run_advi=True,
        num_chains=NUM_CHAINS, num_warmup=NUM_WARMUP, num_samples=NUM_SAMPLES,
        step_size=STEP_SIZE, target_accept_prob=TARGET_ACCEPT, seed=SEED,
    )

cd = _load_arm(npz)
assert cd["item_keys"] == list(FIT_KEYS), "item order differs from ITEM_KEYS"
flag = "  <-- ABOVE 1.05, do not read the comparisons below" if cd["max_rhat"] > 1.05 else ""
print(f"max R-hat {cd['max_rhat']:.4f}{flag}")'''),

        md("""## Per-parameter R-hat

Where the non-convergence sits, if there is any. If it concentrates on the
thresholds of the sparse items, that is issue E showing up as a sampler
failure; if it is spread across the scale, it is something else."""),

        code('''from mice_imp.cm_bayes_arms import rhat

# The sampled parameters, as stored: the first threshold and then the
# threshold INCREMENTS (fact 5), so `dthr2..` are gaps, not thresholds.
z = np.load(npz, allow_pickle=True)
per_item = lambda name: rhat(z[name]).reshape(len(FIT_KEYS), -1)

rhats = pd.DataFrame(
    np.column_stack([per_item("discriminations"), per_item("difficulties0"),
                     per_item("ddifficulties")]),
    index=FIT_KEYS,
    columns=["a", "thr1"] + [f"dthr{k}" for k in range(2, CARDINALITY)],
)
rhats["worst"] = rhats.max(axis=1)
rhats["sparse"] = rhats.index.isin(SPARSE)
num = rhats.columns[:-1]
rhats.sort_values("worst", ascending=False).style.format(
    "{:.3f}", subset=num).background_gradient(
    vmin=1.0, vmax=1.1, cmap="Reds", subset=num)'''),

        md(f"""## Against the masked designs

Each main-design `birt/{spec['itemset']}` run against this fit. Same engine, sampler,
priors and respondents; the only difference is the design mask. Remember the
runs are standardised separately — read the scatter around the diagonal, not
a small uniform offset from it.

Runs that have not been fitted are skipped."""),

        code('''def _tufte(ax):
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    ax.tick_params(direction="out", length=3, width=0.5)


designs = {}
for name in ("commonitem", "standard", "binterlaced"):
    p = REPO / "results" / name / ITEMSET / "birt.npz"
    if p.exists():
        designs[name] = _load_arm(p)
        assert designs[name]["item_keys"] == cd["item_keys"]
    else:
        print(f"  skipping {name}: no {p.relative_to(REPO)}")

sparse_mask = np.isin(FIT_KEYS, SPARSE)
rows = []
for name, res in designs.items():
    rows.append({
        "design": name,
        "max_rhat": res["max_rhat"],
        "a_rmse": float(np.sqrt(np.mean((res["a_mean"] - cd["a_mean"]) ** 2))),
        "b_rmse": float(np.sqrt(np.mean((res["b_mean"] - cd["b_mean"]) ** 2))),
        "b_rmse_sparse": float(np.sqrt(np.mean(
            (res["b_mean"][sparse_mask] - cd["b_mean"][sparse_mask]) ** 2))),
        "b_rmse_rest": float(np.sqrt(np.mean(
            (res["b_mean"][~sparse_mask] - cd["b_mean"][~sparse_mask]) ** 2))),
        "theta_r": float(np.corrcoef(res["eap"], cd["eap"])[0, 1]),
        "theta_rmse": float(np.sqrt(np.mean((res["eap"] - cd["eap"]) ** 2))),
    })
pd.DataFrame(rows).set_index("design").round(4)'''),

        code('''n = max(len(designs), 1)
fig, axes = plt.subplots(2, n, figsize=(4.2 * n, 8.4), squeeze=False)
for j, (name, res) in enumerate(designs.items()):
    ax = axes[0, j]
    ax.scatter(cd["a_mean"][~sparse_mask], res["a_mean"][~sparse_mask], s=14, label="other")
    ax.scatter(cd["a_mean"][sparse_mask], res["a_mean"][sparse_mask], s=22,
               color="C3", label="category < 20")
    lo = min(cd["a_mean"].min(), res["a_mean"].min()); hi = max(cd["a_mean"].max(), res["a_mean"].max())
    ax.plot([lo, hi], [lo, hi], color="gray", lw=0.8, ls="--")
    ax.set_xlabel("complete-data a"); ax.set_ylabel(f"{name} a")
    ax.set_title(f"{name}: discriminations")
    _tufte(ax)

    ax = axes[1, j]
    ax.scatter(cd["b_mean"][~sparse_mask].ravel(), res["b_mean"][~sparse_mask].ravel(), s=10)
    ax.scatter(cd["b_mean"][sparse_mask].ravel(), res["b_mean"][sparse_mask].ravel(), s=18, color="C3")
    lo = min(cd["b_mean"].min(), res["b_mean"].min()); hi = max(cd["b_mean"].max(), res["b_mean"].max())
    ax.plot([lo, hi], [lo, hi], color="gray", lw=0.8, ls="--")
    ax.set_xlabel("complete-data b"); ax.set_ylabel(f"{name} b")
    ax.set_title(f"{name}: thresholds b1..b4")
    _tufte(ax)
if designs:
    axes[0, 0].legend(frameon=False, fontsize=8)
fig.suptitle(f"B-IRT, masked design vs complete data ({ITEMSET}); red = sparse-category items")
fig.tight_layout()'''),

        code('''fig, axes = plt.subplots(1, n, figsize=(4.2 * n, 4.2), squeeze=False)
for ax, (name, res) in zip(axes[0], designs.items()):
    ax.scatter(cd["eap"], res["eap"], s=6, alpha=0.35)
    lo = min(cd["eap"].min(), res["eap"].min()); hi = max(cd["eap"].max(), res["eap"].max())
    ax.plot([lo, hi], [lo, hi], color="gray", lw=0.8, ls="--")
    r = float(np.corrcoef(cd["eap"], res["eap"])[0, 1])
    ax.set_xlabel("complete-data theta"); ax.set_ylabel(f"{name} theta")
    ax.set_title(f"{name}   r={r:.3f}")
    _tufte(ax)
fig.suptitle(f"B-IRT EAP theta, masked design vs complete data ({ITEMSET})")
fig.tight_layout()'''),

        md("""## Export

The same CSV layout as the grid, so it can be read alongside it. Labelled
`design = "cd"` and `variant = "complete_data"` so it cannot be mistaken for a
design run or pooled with one. It is a diagnostic: if it is sent on, say so,
and say that it is not the CD reference."""),

        code('''from mice_imp.export_estimates import export

export(OUTPUT_DIR, design="cd", itemset=ITEMSET, source=DATA_PATH,
       arms=("birt",), include_d=True, variant="complete_data")'''),
    ]
    return {
        "cells": _assign_ids(cells, spec["slug"]),
        "metadata": {
            "kernelspec": {"display_name": "Python 3", "language": "python",
                           "name": "python3"},
            "language_info": {"name": "python"},
        },
        "nbformat": 4,
        "nbformat_minor": 5,
    }


def _keep_outputs(nb: dict, path: Path) -> dict:
    """Carry stored outputs across a regeneration, where the source is unchanged.

    `run_all.ipynb` holds the output of a completed grid -- for the main
    variant that is a 99-hour run, and the only record of its ADVI-init counts,
    fallback rates and per-arm R-hats outside the logs. Regenerating wrote a
    fresh notebook with empty outputs and silently destroyed it. So: for every
    cell whose id AND source both match the notebook already on disk, keep that
    cell's outputs and execution count. Cells whose source changed come back
    empty, which is right -- their old output no longer describes them.
    """
    if not path.exists():
        return nb
    try:
        old = json.loads(path.read_text())
    except (json.JSONDecodeError, OSError):
        return nb
    stored = {
        c.get("id"): c
        for c in old.get("cells", [])
        if c.get("cell_type") == "code" and c.get("outputs")
    }
    kept = 0
    for cell in nb["cells"]:
        prev = stored.get(cell.get("id"))
        if prev is not None and prev.get("source") == cell["source"]:
            cell["outputs"] = prev["outputs"]
            cell["execution_count"] = prev.get("execution_count")
            kept += 1
    if kept:
        print(f"  kept stored output of {kept} unchanged cell(s) in {path.name}")
    return nb


def main() -> None:
    for design, spec in DESIGNS.items():
        for itemset, ispec in ITEM_SETS.items():
            path = OUT / f"cm_{design.lower()}_{itemset}.ipynb"
            nb = build(design, spec, itemset, ispec)
            path.write_text(json.dumps(nb, indent=1) + "\n")
            print(f"wrote {path}  ({ispec['n_items']} items)")

    for name, spec in RUNNERS.items():
        path = OUT / f"{name}.ipynb"
        nb = _keep_outputs(build_runner(spec), path)
        path.write_text(json.dumps(nb, indent=1) + "\n")
        print(f"wrote {path}  (batch driver, variant={spec['variant']})")

    for itemset, spec in CD_DIAGNOSTICS.items():
        path = OUT / f"cm_cd_{itemset}.ipynb"
        nb = _keep_outputs(build_cd_diagnostic(spec), path)
        path.write_text(json.dumps(nb, indent=1) + "\n")
        print(f"wrote {path}  (complete-data diagnostic, {itemset})")


if __name__ == "__main__":
    main()
