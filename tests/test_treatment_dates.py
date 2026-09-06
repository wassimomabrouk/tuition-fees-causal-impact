"""
Guards for the hand-coded treatment table (data/treatment/fee_dates.csv).

This file is the one input to the study that was typed by a human rather than
downloaded, so it is the one input with no upstream validation. These tests
check it against itself: the derived columns must agree with the semester
fields, and the semester fields must agree with the panel's winter-semester
cohort coding.

Convention, applied throughout the file: `abolish_semester` is the first
semester WITHOUT fees, so the number of semesters charged is the difference
between the two semester indices.
"""
from __future__ import annotations
from pathlib import Path

import pandas as pd
import pytest

ROOT = Path(__file__).resolve().parents[1]
FEES = ROOT / "data" / "treatment" / "fee_dates.csv"


def semester_index(sem: str) -> int:
    """Order index over semesters. WS 2006/07 -> 4012, SS 2007 -> 4013.

    Winter semester y/y+1 is indexed 2*y, the following summer semester 2*y+1,
    so consecutive semesters differ by exactly 1.
    """
    sem = str(sem).strip()
    if sem.startswith("WS"):
        return 2 * int(sem.split()[1].split("/")[0])
    if sem.startswith("SS"):
        return 2 * int(sem.split()[1]) - 1
    raise ValueError(f"unparseable semester: {sem!r}")


@pytest.fixture(scope="module")
def fees() -> pd.DataFrame:
    return pd.read_csv(FEES, dtype={"state_code": str})


def test_sixteen_states_with_unique_codes(fees):
    assert len(fees) == 16
    assert fees["state_code"].nunique() == 16
    assert set(fees["state_code"]) == {f"{i:02d}" for i in range(1, 17)}


def test_seven_treated_nine_never_treated(fees):
    assert (fees.ever_treated == 1).sum() == 7
    assert (fees.ever_treated == 0).sum() == 9


def test_never_treated_rows_carry_no_dates(fees):
    never = fees[fees.ever_treated == 0]
    for col in ("intro_semester", "intro_year", "abolish_semester", "abolish_year"):
        assert never[col].isna().all(), f"never-treated state has a value in {col}"
    assert (never["semesters_charged"] == 0).all()


def test_treated_rows_are_complete(fees):
    treated = fees[fees.ever_treated == 1]
    for col in ("decision_date", "intro_semester", "intro_year",
                "abolish_semester", "abolish_year"):
        assert treated[col].notna().all(), f"treated state missing {col}"


def test_semesters_charged_matches_the_semester_fields(fees):
    """The derived count must equal the difference of the semester indices.

    Caught a transcription error in Nordrhein-Westfalen: fees ran WS 2006/07
    through SS 2011, which is 10 semesters, recorded as 11.
    """
    treated = fees[fees.ever_treated == 1]
    bad = []
    for _, r in treated.iterrows():
        expected = semester_index(r.abolish_semester) - semester_index(r.intro_semester)
        if expected != r.semesters_charged:
            bad.append(f"{r.state_en}: stated {r.semesters_charged}, recomputed {expected}")
    assert not bad, "semesters_charged disagrees with the semester fields: " + "; ".join(bad)


def test_intro_year_is_the_first_affected_winter_semester(fees):
    """The panel is winter semesters, so a summer introduction takes effect
    at the following winter intake. Both map to the same intro_year."""
    treated = fees[fees.ever_treated == 1]
    for _, r in treated.iterrows():
        sem = str(r.intro_semester)
        year = int(sem.split()[1].split("/")[0]) if sem.startswith("WS") else int(sem.split()[1])
        assert r.intro_year == year, (
            f"{r.state_en}: intro_semester {sem} implies intro_year {year}, "
            f"file says {r.intro_year}")


def test_abolition_comes_after_introduction(fees):
    treated = fees[fees.ever_treated == 1]
    for _, r in treated.iterrows():
        assert semester_index(r.abolish_semester) > semester_index(r.intro_semester), \
            f"{r.state_en}: abolition is not after introduction"


def test_decision_precedes_introduction(fees):
    """A fee cannot be charged before it is legislated. Also a weak check on
    anticipation: the gap between decision and introduction is the window in
    which students could have responded early."""
    treated = fees[fees.ever_treated == 1].copy()
    treated["decision"] = pd.to_datetime(treated["decision_date"])
    for _, r in treated.iterrows():
        intro_year = int(r.intro_year)
        assert r.decision.year <= intro_year, (
            f"{r.state_en}: decided {r.decision.date()} but introduced in {intro_year}")


def test_treatment_is_absorbing_within_the_estimation_window(fees):
    """DESIGN.md 2: Callaway-Sant'Anna requires absorbing treatment. The
    1998-2007 window is valid only if no state abolished fees by 2007."""
    treated = fees[fees.ever_treated == 1]
    assert (treated["abolish_year"] > 2007).all(), (
        "a state abolished fees inside the estimation window, so treatment is "
        "not absorbing and Callaway-Sant'Anna is invalid on this window")


def test_estimation_window_contains_two_cohorts(fees):
    """Sanity check on the identifying variation the study actually uses."""
    treated = fees[fees.ever_treated == 1]
    cohorts = sorted(treated.loc[treated.intro_year <= 2007, "intro_year"].unique())
    assert cohorts == [2006, 2007], f"unexpected cohorts: {cohorts}"
    counts = treated.intro_year.value_counts().to_dict()
    assert counts[2006] == 2 and counts[2007] == 5
