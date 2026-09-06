#!/usr/bin/env python
"""
Single entry point for the pipeline.

    python run_all.py

Raw data is NOT downloaded automatically: Destatis GENESIS requires an
interactive login, so src/acquire.py documents exactly which tables to pull and
how to slice them. Everything after that is reproducible from this script.
"""
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
RAW = ROOT / "data" / "raw"

STEPS = [
    ("build panel", [sys.executable, str(ROOT / "src" / "build_panel.py")]),
    ("run tests",   [sys.executable, "-m", "pytest", "-q", str(ROOT / "tests")]),
]


def main() -> int:
    csvs = list(RAW.glob("*.csv"))
    if not csvs:
        print("No CSVs in data/raw/.")
        print("Run:  python src/acquire.py   for the exact GENESIS tables to download.")
        return 1
    print(f"found {len(csvs)} raw file(s)\n")

    for name, cmd in STEPS:
        print(f"=== {name} ===")
        r = subprocess.run(cmd)
        if r.returncode != 0:
            print(f"FAILED at: {name}")
            return r.returncode
        print()

    print("Pipeline complete. Run notebooks/01-05 in order for the analysis.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
