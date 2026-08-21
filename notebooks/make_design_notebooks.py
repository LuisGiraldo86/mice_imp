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
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
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

# SMOKE = True gives a fast wiring check, NOT an inferential run. Flip to
# False for the real thing. CLAUDE.md: smoke-test before committing to full
# chains -- nothing in this pipeline has been executed end to end.
SMOKE = True

if SMOKE:
    NUM_CHAINS, NUM_WARMUP, NUM_SAMPLES = 2, 200, 200
else:
    NUM_CHAINS, NUM_WARMUP, NUM_SAMPLES = 4, 3000, 2000

# Chang's defaults. B-MI gets a gentler sampler: attaching PMFs turns masked
# cells from exact zeros into parameter-dependent curvature, which makes the
# geometry harder for NUTS.
STEP_SIZE, TARGET_ACCEPT = 0.002, 0.95
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


def main() -> None:
    for design, spec in DESIGNS.items():
        for itemset, ispec in ITEM_SETS.items():
            path = OUT / f"cm_{design.lower()}_{itemset}.ipynb"
            nb = build(design, spec, itemset, ispec)
            path.write_text(json.dumps(nb, indent=1) + "\n")
            print(f"wrote {path}  ({ispec['n_items']} items)")


if __name__ == "__main__":
    main()
