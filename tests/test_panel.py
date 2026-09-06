"""
Pipeline guards.

These catch the failures that are silent rather than loud: a source download
that defaulted to a single period, a panel that lost states in a join, treatment
flags drifting out of sync with data/treatment/fee_dates.csv. Each would
otherwise surface only as a strange estimate much later.

Run: pytest -q
"""
import pandas as pd
import pytest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PANEL = ROOT / "data" / "processed" / "panel.parquet"
FEES = ROOT / "data" / "treatment" / "fee_dates.csv"

pytestmark = pytest.mark.skipif(not PANEL.exists(),
                                reason="panel not built yet; run src/build_panel.py")


@pytest.fixture(scope="module")
def panel():
    return pd.read_parquet(PANEL)


@pytest.fixture(scope="module")
def fees():
    return pd.read_csv(FEES, dtype={"state_code": str})


def test_sixteen_states(panel):
    assert panel["state_code"].nunique() == 16


def test_pre_period_depth(panel):
    """At least 4 pre-treatment periods before the first reform (WS 2006/07)."""
    pre = panel.loc[panel["year"] < 2006, "year"].nunique()
    assert pre >= 4, f"only {pre} pre-treatment periods; DiD needs a real pre-period"


def test_panel_is_balanced(panel):
    expected = panel["state_code"].nunique() * panel["year"].nunique()
    assert len(panel) == expected


def test_no_duplicate_state_periods(panel):
    assert not panel.duplicated(["state_code", "year"]).any()


def test_treatment_matches_source_table(panel, fees):
    in_panel = set(panel.loc[panel["ever_treated"] == 1, "state_code"])
    in_table = set(fees.loc[fees["ever_treated"] == 1, "state_code"])
    assert in_panel == in_table


def test_seven_treated_nine_control(fees):
    assert int(fees["ever_treated"].sum()) == 7
    assert int((1 - fees["ever_treated"]).sum()) == 9


def test_no_treatment_before_first_reform(panel):
    assert panel.loc[panel["year"] < 2006, "treated"].sum() == 0


def test_outcomes_non_negative(panel):
    for col in [c for c in panel.columns if "first_years" in c]:
        assert (panel[col].dropna() >= 0).all()
