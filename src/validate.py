"""
Data-quality gate (DESIGN.md section 9). Run after acquire, before build_panel.

Design rule: mechanics live here, interpretation lives in the notebooks. These
functions return structured results; notebook 01 reads them and draws conclusions.
"""
from __future__ import annotations
import pandas as pd


def check_balanced(panel: pd.DataFrame, unit="state_code", time="year") -> dict:
    """Every unit observed in every period, exactly once."""
    n_u, n_t = panel[unit].nunique(), panel[time].nunique()
    dupes = int(panel.duplicated([unit, time]).sum())
    return {"units": n_u, "periods": n_t, "expected_rows": n_u * n_t,
            "actual_rows": len(panel), "balanced": len(panel) == n_u * n_t,
            "duplicate_unit_periods": dupes}


def check_missing(panel: pd.DataFrame) -> pd.Series:
    return panel.isna().sum()


def check_treatment_consistency(panel: pd.DataFrame, fee_dates: pd.DataFrame) -> dict:
    """Treatment flags in the panel must match data/treatment/fee_dates.csv."""
    treated_panel = set(panel.loc[panel["ever_treated"] == 1, "state_code"].unique())
    treated_table = set(fee_dates.loc[fee_dates["ever_treated"] == 1, "state_code"].unique())
    return {"match": treated_panel == treated_table,
            "in_panel_only": sorted(treated_panel - treated_table),
            "in_table_only": sorted(treated_table - treated_panel)}


def check_national_totals(panel: pd.DataFrame, published: pd.DataFrame | None = None) -> pd.DataFrame:
    """Sum states to national totals per period for reconciliation against Destatis."""
    return panel.groupby("year", as_index=False).agg(
        first_years_location=("first_years_location", "sum"))


def check_structural_breaks(panel: pd.DataFrame, col: str) -> pd.DataFrame:
    """Period-on-period national change, to surface definitional breaks
    (e.g. the 2016 Hochschulstatistikgesetz amendment, DESIGN.md 9)."""
    nat = panel.groupby("year", as_index=False)[col].sum()
    nat["pct_change"] = nat[col].pct_change() * 100
    return nat
