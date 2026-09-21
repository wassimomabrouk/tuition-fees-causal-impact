"""
Guards for the phase 2 extraction (DESIGN.md 14.8).

The Fachserie volumes are hand-downloaded xls files whose internal layout is not
guaranteed to be stable across years, and the parser locates the first-year
block by searching for its header rather than by a fixed offset. These tests
check that the search still finds the right block in every volume, that each
volume is internally consistent, and that the result reconciles with the phase 1
panel, which is the strongest available check because the two come from
different publications of the same statistic.

Skipped when the volumes are not present, since raw data is gitignored.
Run: pytest -q
"""
from __future__ import annotations

import glob
import sys
from pathlib import Path

import pandas as pd
import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

RAW = ROOT / "data" / "raw" / "fachserie"
PANEL = ROOT / "data" / "processed" / "panel.parquet"
WINDOW = [2003, 2004, 2005, 2006, 2007]          # phase 2 (DESIGN.md 14.1)
WINDOW_P3 = list(range(2007, 2016))              # phase 3 (DESIGN.md 15.3)

# both .xls and .xlsx: Destatis switched format from WS 2013/14
pytestmark = pytest.mark.skipif(
    not any(RAW.glob("*.xls*")),
    reason="Fachserie volumes not present; see src/acquire.py")

from src import fachserie as fsx  # noqa: E402  (after the path insert)

VOLUMES = fsx.select_volumes(RAW, WINDOW[0], WINDOW[-1]) if any(RAW.glob("*.xls*")) else []


@pytest.fixture(scope="module")
def volumes():
    return [fsx.read_matrix(v) for v in VOLUMES]


@pytest.fixture(scope="module")
def panel():
    return fsx.build_panel(VOLUMES)


def test_window_is_complete_and_unique(volumes):
    """Five volumes, 2003 to 2007, no duplicates and no gaps."""
    years = sorted(v[3] for v in volumes)
    assert years == WINDOW, f"expected {WINDOW}, got {years}"


def test_every_volume_reconciles_internally(volumes):
    """Deutschland row equals the sum of the states; every column adds up."""
    bad = []
    for flows, total, extra, year in volumes:
        v = fsx.validate(flows, total, extra)
        if not (v["rows_reconcile"] and v["columns_reconcile"]):
            bad.append(f"{year}: rows={v['rows_reconcile']} cols={v['columns_reconcile']} "
                       f"worst residual {v['worst_column_residual']}")
    assert not bad, "; ".join(bad)


def test_matrix_is_sixteen_by_sixteen(volumes):
    for flows, _, _, year in volumes:
        assert flows.shape == (16, 16), f"{year}: matrix is {flows.shape}"
        assert list(flows.index) == fsx.STATES
        assert list(flows.columns) == fsx.STATES


def test_no_missing_cells(volumes):
    """A blank cell would silently become a zero flow and understate migration."""
    for flows, _, _, year in volumes:
        assert not flows.isna().any().any(), f"{year}: matrix has missing cells"


def test_most_first_years_stay_in_their_own_state(volumes):
    """Every state's largest destination is itself.

    Checks orientation and plausibility together. Note this holds ROW-wise
    (where a state's own school leavers go) but not column-wise: Bremen drew
    more first-years from Niedersachsen than from Bremen in 2004 and 2005,
    which is real and expected for a small city-state.
    """
    for flows, _, _, year in volumes:
        wrong = [s for s in fsx.STATES if flows.loc[s].idxmax() != s]
        assert not wrong, f"{year}: largest destination is not home for {wrong}"


def test_diagonal_share_is_stable(volumes):
    """Share of first-years studying in their own state, nationally.

    Observed at 67 to 71 percent across the window and drifting slowly. A break
    in this series would mean the matrix had been transposed, misaligned, or
    that the published definition changed.
    """
    shares = {}
    for flows, _, _, year in volumes:
        a = flows.to_numpy()
        shares[year] = 100 * a.diagonal().sum() / a.sum()
    lo, hi = min(shares.values()), max(shares.values())
    assert 60 <= lo and hi <= 80, f"diagonal share outside plausible range: {shares}"
    assert hi - lo < 10, f"diagonal share jumps between years: {shares}"


def test_panel_is_balanced(panel):
    assert len(panel) == 16 * len(WINDOW)
    assert panel["state_code"].nunique() == 16
    assert not panel.duplicated(["state_code", "year"]).any()


def test_derived_outcomes_are_consistent(panel):
    """Identities behind the outcome definitions (DESIGN.md 14.3).

    The primary outcome counts German-HZB holders on both sides; the robustness
    variant leaves Ausland and ohne Angabe in the destination term.
    """
    assert (panel["german_location"] ==
            panel["study_location"] - panel["unattributed"]).all()
    assert (panel["net_inflow"] == panel["german_location"] - panel["origin"]).all()
    assert (panel["net_inflow_incl_foreign"] ==
            panel["study_location"] - panel["origin"]).all()
    assert (panel["outflow"] == panel["origin"] - panel["stayers"]).all()
    assert (panel["inflow"] == panel["german_location"] - panel["stayers"]).all()
    assert (panel[["origin", "study_location", "german_location", "stayers",
                   "inflow", "outflow"]] >= 0).all().all()
    assert (panel["stayers"] <= panel["origin"]).all()
    assert (panel["stayers"] <= panel["german_location"]).all()


def test_scale_free_outcomes(panel):
    """The primary and second outcomes (DESIGN.md 14.3).

    `attraction` is a log ratio of two strictly positive counts and `retention`
    is a share, so both have hard bounds a parsing error would violate.
    """
    import numpy as np
    assert np.allclose(panel["attraction"],
                       np.log(panel["german_location"] / panel["origin"]))
    assert np.allclose(panel["retention"], panel["stayers"] / panel["origin"])
    assert panel["attraction"].notna().all() and np.isfinite(panel["attraction"]).all()
    assert panel["retention"].between(0, 1).all(), "retention outside [0, 1]"
    assert panel["attraction"].abs().max() < 2, "implausible attraction ratio"
    # every state hosts and produces first-years, so neither term can be zero
    assert (panel[["german_location", "origin"]] > 0).all().all()


def test_unattributed_share_is_stable(panel):
    """Ausland and ohne Angabe are excluded from `origin` (DESIGN.md 14.3).

    The share is large, about one first-year in seven, so a jump between years
    would change what `net_inflow` means and must not pass unnoticed.
    """
    share = 100 * panel.groupby("year")["unattributed"].sum() / \
        panel.groupby("year")["study_location"].sum()
    assert share.between(5, 25).all(), f"implausible share by year:\n{share}"
    assert share.max() - share.min() < 5, f"share moves too much between years:\n{share}"


@pytest.mark.skipif(not PANEL.exists(), reason="phase 1 panel not built")
def test_study_location_matches_the_phase_one_panel(panel):
    """Same statistic, two publications: they must agree exactly.

    GENESIS 21311-0014 and Fachserie 11 R 4.1 table 6 both report first-years by
    university location. If they ever disagree, one of them is not the measure
    this study thinks it is (DESIGN.md 0.2).
    """
    p1 = pd.read_parquet(PANEL)
    p1 = p1[p1.year.isin(WINDOW)][["state_code", "year", "first_years_location"]]
    merged = panel.merge(p1, on=["state_code", "year"], how="inner")
    assert len(merged) == 16 * len(WINDOW), "phase 1 panel does not cover the window"
    diff = (merged["study_location"] - merged["first_years_location"]).abs()
    worst = merged.loc[diff.idxmax()]
    assert (diff <= 1).all(), (
        f"sources disagree, worst case {worst['state']} {int(worst['year'])}: "
        f"Fachserie {worst['study_location']:.0f} vs GENESIS "
        f"{worst['first_years_location']:.0f}")


def test_flows_long_is_complete():
    lf = fsx.flows_long(VOLUMES)
    assert len(lf) == 16 * 16 * len(WINDOW)
    assert set(lf.columns) == {"origin", "destination", "first_years", "year"}
    assert lf["first_years"].notna().all()


# ---------------------------------------------------------------------------
# phase 3 window (DESIGN.md 15)
# ---------------------------------------------------------------------------

def _p3():
    try:
        return fsx.select_volumes(RAW, WINDOW_P3[0], WINDOW_P3[-1])
    except FileNotFoundError:
        return []


@pytest.mark.skipif(not _p3(), reason="phase 3 volumes not present")
def test_phase3_window_is_complete():
    years = [fsx.winter_semester_year(v) for v in _p3()]
    assert years == WINDOW_P3, f"expected {WINDOW_P3}, got {years}"


@pytest.mark.skipif(not _p3(), reason="phase 3 volumes not present")
def test_phase3_volumes_reconcile():
    """Every phase 3 volume, including the .xlsx ones, must reconcile exactly."""
    bad = []
    for v in _p3():
        flows, total, extra, year = fsx.read_matrix(v)
        r = fsx.validate(flows, total, extra)
        if not (r["rows_reconcile"] and r["columns_reconcile"]):
            bad.append(year)
    assert not bad, f"volumes failing reconciliation: {bad}"


def test_volume_selection_ignores_other_windows():
    """Phase 2 must see exactly its five volumes even with phase 3 files present.

    Guards the failure this was written for: a folder holding volumes for two
    experiments, where globbing one extension silently changes the window.
    """
    if not any(RAW.glob("*.xls*")):
        pytest.skip("no volumes")
    years = [fsx.winter_semester_year(v) for v in VOLUMES]
    assert years == WINDOW
