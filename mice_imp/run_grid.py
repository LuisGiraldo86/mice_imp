#!/usr/bin/env python
"""
Run the whole Bayesian grid -- 3 designs x 2 item sets x 3 arms -- unattended.

This exists for the long unattended pass (the full chains are 4 x 3000/2000
and nothing here has been timed yet). Three properties matter for that:

  RESUMABLE   a (design, item set) whose three arm .npz files already exist
              is skipped, so an interrupted weekend picks up where it stopped
              rather than starting over. `--force` overrides.

  ISOLATED    one run raising does not take the other five with it. The
              traceback goes to that run's log and the grid continues.

  LOGGED      each run's stdout is captured to results/<design>/<itemset>/
              run.log, and the numbers that are only ever PRINTED by the
              fitting code -- above all the B-MI flat-fallback rate, which
              decides whether a null B-MI result means anything at all
              (CLAUDE.md fact 3) -- are parsed back out of it into
              results/grid_summary.csv.

The summary is rewritten after every run, so a crash on Sunday still leaves
Saturday's results readable.

Run order is deliberate: CommonItem, then Binterlaced, then Standard, and
`full` before `nobike` within each design. That is increasing order of
difficulty -- CommonItem carries the most linking information and Standard
the least, and Standard/nobike is the thinnest cell in the grid (7 items in
form 3, three of them anchors). Failures then surface where there is the
most signal to diagnose them with.

    python -m mice_imp.run_grid --smoke      # wiring check first
    python -m mice_imp.run_grid              # the real thing
"""
from __future__ import annotations

import argparse
import contextlib
import os
import re
import sys
import time
import traceback
from pathlib import Path

os.environ.setdefault("JAX_PLATFORMS", "cpu")
os.environ.setdefault("JAX_ENABLE_X64", "1")

import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402

REPO = Path(__file__).resolve().parent.parent
if str(REPO) not in sys.path:
    sys.path.insert(0, str(REPO))

from mice_imp.wdfab_io import ITEM_SETS, load_cm  # noqa: E402

DESIGNS = ["CommonItem", "Binterlaced", "Standard"]
ITEMSETS = ["full", "nobike"]
ARMS = ("birt", "bmi", "flat")

DATA_DIR = REPO / "data_wdfab"
RESULTS = REPO / "results"
CARDINALITY = 5


def data_path(design: str) -> Path:
    return DATA_DIR / f"WDFAB_ExperimentalData_CM{design}_Jul2026.dta"


def run_dir(design: str, itemset: str) -> Path:
    return RESULTS / design.lower() / itemset


def is_complete(design: str, itemset: str) -> bool:
    d = run_dir(design, itemset)
    return all((d / f"{arm}.npz").exists() for arm in ARMS)


class _Tee:
    """Write to a log file and echo to the real stdout.

    The fitting code reports the things that matter -- ADVI initialisation,
    R-hat, the fallback rate -- by printing them. Capturing without echoing
    would leave a weekend run looking hung.
    """

    def __init__(self, handle, mirror):
        self.handle, self.mirror = handle, mirror

    def write(self, text):
        self.handle.write(text)
        self.handle.flush()
        self.mirror.write(text)
        return len(text)

    def flush(self):
        self.handle.flush()
        self.mirror.flush()

    def isatty(self) -> bool:
        # bayesianquilts' training loop asks, to decide whether to draw a
        # progress bar. Say no: a log file full of carriage returns is worse
        # than plain lines, and a weekend run has no terminal watching it.
        return False

    def __getattr__(self, name):
        # Anything else a consumer expects of a stream (encoding, fileno,
        # writelines) comes from the real stdout rather than raising.
        return getattr(self.mirror, name)


def _parse_log(text: str) -> dict:
    """Recover from the log what the fitting code only prints."""
    out = {}
    m = re.search(r"flat fallback \d+ \(([\d.]+)%\)", text)
    if m:
        out["bmi_fallback_pct"] = float(m.group(1))
    m = re.search(r"unfilled \d+ \(([\d.]+)%\)", text)
    if m:
        out["bmi_unfilled_pct"] = float(m.group(1))
    out["advi_init_count"] = len(re.findall(r"Initializing from ADVI solution", text))
    return out


def _read_rhats(d: Path) -> dict:
    out = {}
    for arm in ARMS:
        p = d / f"{arm}.npz"
        if p.exists():
            with np.load(p, allow_pickle=True) as z:
                out[f"{arm}_max_rhat"] = float(z["max_rhat"])
    return out


def _read_noise_floor(d: Path) -> dict:
    p = d / "noise_floor.json"
    if not p.exists():
        return {}
    import json
    with open(p) as fh:
        return json.load(fh)


def run_one(design: str, itemset: str, smoke: bool, force: bool,
            seed: int, export: bool) -> dict:
    from mice_imp.cm_bayes_arms import run_all_arms

    out_dir = run_dir(design, itemset)
    row = {"design": design.lower(), "itemset": itemset,
           "n_items": len(ITEM_SETS[itemset]),
           "started": time.strftime("%Y-%m-%d %H:%M:%S")}

    if is_complete(design, itemset) and not force:
        row.update(status="skipped (already complete)", minutes=0.0)
        row.update(_read_rhats(out_dir))
        row.update(_read_noise_floor(out_dir))
        return row

    out_dir.mkdir(parents=True, exist_ok=True)
    log_path = out_dir / "run.log"
    chains, warmup, samples = (2, 200, 200) if smoke else (4, 3000, 2000)

    print(f"\n{'=' * 72}\n{design} / {itemset}  "
          f"({len(ITEM_SETS[itemset])} items, {chains} chains, "
          f"{warmup}/{samples})\n  log: {log_path}\n{'=' * 72}", flush=True)

    t0 = time.time()
    with open(log_path, "w") as fh:
        tee = _Tee(fh, sys.__stdout__)
        try:
            with contextlib.redirect_stdout(tee), contextlib.redirect_stderr(tee):
                df = load_cm(data_path(design), cardinality=CARDINALITY)
                run_all_arms(
                    df=df[ITEM_SETS[itemset]],
                    item_keys=ITEM_SETS[itemset],
                    cardinality=CARDINALITY,
                    output_dir=out_dir,
                    imputation_model_path=out_dir / "imputation_model",
                    arms=ARMS,
                    seed=seed,
                    num_chains=chains,
                    num_warmup=warmup,
                    num_samples=samples,
                )
                if export:
                    from mice_imp.export_estimates import export as export_csv
                    export_csv(out_dir, design=design.lower(), itemset=itemset,
                               source=data_path(design), include_d=True)
            row["status"] = "ok"
        except Exception as exc:                       # noqa: BLE001
            traceback.print_exc(file=fh)
            row["status"] = f"FAILED: {type(exc).__name__}: {exc}"[:200]
            print(f"  FAILED -- see {log_path}", file=sys.__stdout__, flush=True)

    row["minutes"] = round((time.time() - t0) / 60, 1)
    row.update(_parse_log(log_path.read_text()))
    row.update(_read_rhats(out_dir))
    row.update(_read_noise_floor(out_dir))
    return row


# Set by main() when --summary is given. Six processes running one cell each
# would otherwise all write results/grid_summary.csv and clobber one another.
SUMMARY_PATH: Path | None = None


def write_summary(rows: list[dict]) -> Path:
    RESULTS.mkdir(parents=True, exist_ok=True)
    path = SUMMARY_PATH or (RESULTS / "grid_summary.csv")
    path.parent.mkdir(parents=True, exist_ok=True)
    pd.DataFrame(rows).to_csv(path, index=False)
    return path


def print_summary(rows: list[dict]) -> None:
    df = pd.DataFrame(rows)
    cols = [c for c in ["design", "itemset", "n_items", "started", "status", "minutes",
                        "birt_max_rhat", "bmi_max_rhat", "flat_max_rhat",
                        "bmi_fallback_pct", "advi_init_count",
                        "theta_rmse_flat_vs_birt", "theta_rmse_bmi_vs_birt"]
            if c in df.columns]
    print("\n" + "=" * 72 + "\nGRID SUMMARY\n" + "=" * 72)
    print(df[cols].to_string(index=False))

    for _, r in df.iterrows():
        if r.get("status") == "running":
            print(f"  {r['design']}/{r['itemset']}: still marked 'running' -- "
                  "the process was killed before this run finished")

    # The three things that silently invalidate a run. Say them out loud.
    for _, r in df.iterrows():
        tag = f"{r['design']}/{r['itemset']}"
        for arm in ARMS:
            k = f"{arm}_max_rhat"
            if k in r and pd.notna(r[k]) and r[k] > 1.05:
                print(f"  {tag}: {arm} R-hat {r[k]:.3f} > 1.05 -- not trustworthy")
        if r.get("advi_init_count", 0) not in (0, 3):
            print(f"  {tag}: 'Initializing from ADVI solution' appeared "
                  f"{int(r['advi_init_count'])}x, expected 3 (CLAUDE.md fact 17) "
                  "-- the noise floor is measuring initialisation, not MC noise")
        if pd.notna(r.get("bmi_fallback_pct", np.nan)) and r["bmi_fallback_pct"] > 10:
            print(f"  {tag}: B-MI fell back to flat PMFs on "
                  f"{r['bmi_fallback_pct']:.1f}% of masked cells -- a null B-MI "
                  "result here is not interpretable (fact 3)")


def main() -> None:
    ap = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--smoke", action="store_true",
                    help="2 chains, 200/200 -- a wiring check, NOT inference")
    ap.add_argument("--force", action="store_true",
                    help="re-run cells that already have all three arm .npz")
    ap.add_argument("--only", default=None,
                    help="comma-separated design/itemset, e.g. "
                         "'commonitem/full,standard/nobike'")
    ap.add_argument("--seed", type=int, default=42)
    ap.add_argument("--summary", type=Path, default=None,
                    help="where to write the summary CSV. Give each concurrent "
                         "process its own path -- they all default to "
                         "results/grid_summary.csv and would overwrite "
                         "each other.")
    ap.add_argument("--no-export", action="store_true",
                    help="skip the CSV export after each run")
    args = ap.parse_args()

    global SUMMARY_PATH
    SUMMARY_PATH = args.summary

    grid = [(d, i) for d in DESIGNS for i in ITEMSETS]
    if args.only:
        want = {s.strip().lower() for s in args.only.split(",") if s.strip()}
        grid = [(d, i) for d, i in grid if f"{d.lower()}/{i}" in want]
        if not grid:
            raise SystemExit(f"--only matched nothing; grid is "
                             f"{[f'{d.lower()}/{i}' for d in DESIGNS for i in ITEMSETS]}")

    missing = [str(data_path(d)) for d, _ in dict.fromkeys(grid) if not data_path(d).exists()]
    if missing:
        raise SystemExit("missing design files:\n  " + "\n  ".join(missing))

    print(f"grid: {len(grid)} run(s), smoke={args.smoke}, force={args.force}")
    rows = []
    t0 = time.time()
    for design, itemset in grid:
        # Publish the row as 'running' FIRST. Writing only on completion left a
        # killed run represented by whatever the file said before it started --
        # a stale failure that reads exactly like a current one.
        rows.append({"design": design.lower(), "itemset": itemset,
                     "n_items": len(ITEM_SETS[itemset]),
                     "started": time.strftime("%Y-%m-%d %H:%M:%S"),
                     "status": "running", "minutes": None})
        write_summary(rows)
        rows[-1] = run_one(design, itemset, args.smoke, args.force,
                           args.seed, not args.no_export)
        path = write_summary(rows)          # rewritten after every run
        print(f"  -> {rows[-1]['status']}  ({rows[-1]['minutes']} min)  "
              f"summary: {path}", flush=True)

    print_summary(rows)
    print(f"\ntotal {(time.time() - t0) / 60:.1f} min")
    if any(r["status"].startswith("FAILED") for r in rows):
        raise SystemExit(1)


if __name__ == "__main__":
    main()
