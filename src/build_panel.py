"""
Build the state x winter-semester analysis panel from the raw GENESIS CSV.

Reads data/raw/, runs sql/build_panel.sql against it joined to the treatment
tables, and writes data/processed/panel.parquet (and .csv for inspection).

The full time range is written out. Choosing an estimation window is an analysis
decision and belongs in the notebooks, not here: the introduction window must end
before the first abolition so that treatment is absorbing (DESIGN.md section 2).

Run from the repo root:  python src/build_panel.py
"""
from __future__ import annotations

import glob
import sys
from pathlib import Path

import duckdb
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "data" / "raw"
OUT = ROOT / "data" / "processed"
SQL = ROOT / "sql" / "build_panel.sql"
TREAT = ROOT / "data" / "treatment"

FIRST_ABOLITION_YEAR = 2008   # Hessen, from WS 2008/09


def find_raw(patterns: tuple[str, ...]) -> str | None:
    for pat in patterns:
        hits = sorted(glob.glob(str(RAW / f"*{pat}*.csv")))
        if hits:
            return hits[0]
    return None


def read_de_csv(path: str) -> pd.DataFrame:
    """GENESIS flat CSVs are semicolon separated; encoding varies."""
    for enc in ("utf-8", "latin-1"):
        try:
            return pd.read_csv(path, sep=";", dtype=str, encoding=enc,
                               keep_default_na=False)
        except UnicodeDecodeError:
            continue
    raise RuntimeError(f"could not decode {path} as utf-8 or latin-1")


def main() -> int:
    raw_path = find_raw(("21311-0014", "first_years"))
    if raw_path is None:
        sys.exit(f"no first-years CSV found in {RAW}. See src/acquire.py.")
    print(f"raw: {Path(raw_path).name}")

    raw_fy = read_de_csv(raw_path)
    fees = pd.read_csv(TREAT / "fee_dates.csv", dtype={"state_code": str})
    g8 = pd.read_csv(TREAT / "g8_dates.csv", dtype={"state_code": str})
    for col in ("intro_year", "abolish_year"):
        fees[col] = pd.to_numeric(fees[col], errors="coerce").astype("Int64")
    g8["double_abitur_year"] = pd.to_numeric(g8["double_abitur_year"],
                                             errors="coerce").astype("Int64")

    con = duckdb.connect()
    con.register("raw_fy", raw_fy)
    con.register("fees", fees)
    con.register("g8", g8)
    panel = con.execute(SQL.read_text(encoding="utf-8")).df()

    OUT.mkdir(parents=True, exist_ok=True)
    panel.to_parquet(OUT / "panel.parquet", index=False)
    panel.to_csv(OUT / "panel.csv", index=False)

    # --- diagnostics: enough to spot a broken build immediately ---
    print(f"\npanel: {panel.shape[0]} rows x {panel.shape[1]} cols")
    print(f"states: {panel.state_code.nunique()}   "
          f"terms: {panel.year.min()}-{panel.year.max()} "
          f"({panel.year.nunique()} winter semesters)")
    print(f"balanced: {len(panel) == panel.state_code.nunique() * panel.year.nunique()}")
    print(f"missing first_years: {int(panel.first_years_location.isna().sum())}")

    print("\ntreated states per winter semester (introduction window):")
    win = panel[panel.year < FIRST_ABOLITION_YEAR]
    print(win.groupby("year")["treated"].agg(n_treated="sum",
                                             n_distinct="nunique").to_string())

    print("\nintroduction cohorts (winter-semester timing):")
    coh = (panel[panel.cohort > 0].groupby("cohort")["state"]
           .agg(lambda x: ", ".join(sorted(set(x)))))
    for c, states in coh.items():
        print(f"  {c}: {states}")
    print(f"  never treated ({panel[panel.cohort == 0].state.nunique()}): "
          f"{', '.join(sorted(panel[panel.cohort == 0].state.unique()))}")

    print("\nsample:")
    cols = ["state", "year", "term_label", "first_years_location",
            "treated", "event_time", "cohort"]
    print(panel.loc[panel.state_code == "05", cols].head(12).to_string(index=False))
    print(f"\nwrote {OUT/'panel.parquet'} and {OUT/'panel.csv'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
