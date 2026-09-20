"""
Extraction of the study-state x home-state first-year matrix (DESIGN.md 14.1, 14.8).

Source: Fachserie 11 Reihe 4.1, detailed table 6, sheet `TAB-06`, one xls per
winter semester. The sheet holds two stacked blocks with identical layout,
"Studierende insgesamt" and "Studienanfaenger/-innen insgesamt". Phase 2 uses
the second: fees change who enrols this year, and the stock of students is
mostly people who enrolled before the reform existed.

Mechanics only. The window, the outcome definitions and the reading of the
result belong in the notebooks.
"""
from __future__ import annotations

import re
from pathlib import Path

import numpy as np
import pandas as pd

SHEET = "TAB-06"

# Column order of the matrix as printed, which is alphabetical by German name.
STATES = ["Baden-Württemberg", "Bayern", "Berlin", "Brandenburg", "Bremen",
          "Hamburg", "Hessen", "Mecklenburg-Vorpommern", "Niedersachsen",
          "Nordrhein-Westfalen", "Rheinland-Pfalz", "Saarland", "Sachsen",
          "Sachsen-Anhalt", "Schleswig-Holstein", "Thüringen"]

# Destatis Bundesland codes, to join onto the phase 1 panel.
CODES = {"Schleswig-Holstein": "01", "Hamburg": "02", "Niedersachsen": "03",
         "Bremen": "04", "Nordrhein-Westfalen": "05", "Hessen": "06",
         "Rheinland-Pfalz": "07", "Baden-Württemberg": "08", "Bayern": "09",
         "Saarland": "10", "Berlin": "11", "Brandenburg": "12",
         "Mecklenburg-Vorpommern": "13", "Sachsen": "14",
         "Sachsen-Anhalt": "15", "Thüringen": "16"}


def winter_semester_year(path: str | Path) -> int:
    """Calendar year in which the volume's winter semester begins.

    Read from the sheet itself rather than the filename, which is an internal
    publication id (2110410077005) that encodes nothing usable.
    """
    head = pd.read_excel(path, sheet_name=SHEET, header=None, nrows=4)
    text = " ".join(str(v) for v in head.values.ravel() if str(v) != "nan")
    m = re.search(r"(\d{4})\s*/\s*(\d{2,4})", text)
    if not m:
        raise ValueError(f"no winter semester found in the header of {path}")
    return int(m.group(1))


def _block_start(df: pd.DataFrame) -> int:
    """Row index of the 'Studienanfaenger/-innen insgesamt' band.

    Located by its header text, not by a fixed offset: the number of sheets and
    the length of the preceding block differ between volumes (36 sheets in
    WS 2003/04, 50 in WS 2006/07) even though TAB-06 itself is identical.
    """
    for r in range(len(df)):
        line = " ".join(str(v) for v in df.iloc[r].tolist() if str(v) != "nan")
        if "Studienanf" in line and "insgesamt" in line:
            return r
    raise ValueError("first-year block header not found in TAB-06")


def read_matrix(path: str | Path) -> tuple[pd.DataFrame, pd.Series, pd.Series, int]:
    """Parse one volume.

    Returns (flows, total, abroad_unknown, year):
      flows  16 x 16, index = HZB state (origin), columns = study state
      total  `Insgesamt` per study state, i.e. the phase 1 outcome
      abroad_unknown  Ausland + ohne Angabe per study state, excluded from flows
      year   calendar year the winter semester begins
    """
    df = pd.read_excel(path, sheet_name=SHEET, header=None)
    rows: list[list[float]] = []
    for r in range(_block_start(df), len(df)):
        if str(df.iat[r, 2]).strip() != "i":        # keep the m+w total row only
            continue
        vals = pd.to_numeric(df.iloc[r, 3:22], errors="coerce")
        if vals.isna().all():
            continue
        rows.append(vals.tolist())
        if len(rows) == 17:                          # 16 states + Deutschland
            break
    if len(rows) != 17:
        raise ValueError(f"expected 17 data rows in {path}, found {len(rows)}")

    labels = STATES + ["Deutschland"]
    total = pd.Series([r[0] for r in rows], index=labels, dtype="float64")
    body = pd.DataFrame([r[1:17] for r in rows], index=labels, columns=STATES)
    extra = pd.DataFrame([r[17:19] for r in rows], index=labels,
                         columns=["Ausland", "ohne Angabe"]).fillna(0)

    flows = body.loc[STATES].T                       # transpose: origin x destination
    flows.index.name, flows.columns.name = "origin", "destination"
    return (flows, total, extra.sum(axis=1), winter_semester_year(path))


def validate(flows: pd.DataFrame, total: pd.Series, extra: pd.Series,
             tol: float = 1.0) -> dict:
    """Internal consistency of one volume (DESIGN.md 14.8).

    Returns structured results; the notebook decides what to do about them.
    """
    state_sum = float(total[STATES].sum())
    germany = float(total["Deutschland"])
    per_state = flows.sum(axis=0) + extra[STATES]    # inflow + unattributable
    resid = (per_state - total[STATES]).abs()
    return {"germany_row": germany, "sum_of_states": state_sum,
            "rows_reconcile": abs(germany - state_sum) <= tol,
            "columns_reconcile": bool((resid <= tol).all()),
            "worst_column_residual": float(resid.max()),
            "unattributed_share_pct": 100 * float(extra[STATES].sum()) / state_sum}


def build_panel(paths) -> pd.DataFrame:
    """Long panel of the phase 2 outcomes, one row per state per winter semester.

    `net_inflow` is a difference of counts and can be negative, so it is not
    logged (DESIGN.md 14.3). It is left in levels here; scaling belongs in the
    notebook.

    Columns: study_location (all first-years enrolled in the state, matching the
    phase 1 outcome), unattributed (Ausland + ohne Angabe), german_location
    (study_location net of those), origin (first-years with a German HZB from
    the state, wherever they enrolled), stayers (the diagonal), attraction
    (PRIMARY outcome, log of german_location over origin), retention (second
    outcome, stayers over origin), net_inflow and net_inflow_incl_foreign
    (retained as robustness variants in levels), outflow and inflow.
    """
    out = []
    for p in paths:
        flows, total, extra, year = read_matrix(p)
        out.append(pd.DataFrame({
            "state": STATES,
            "state_code": [CODES[s] for s in STATES],
            "year": year,
            "study_location": total[STATES].to_numpy(),
            "origin": flows.sum(axis=1).to_numpy(),
            "stayers": np.diag(flows.to_numpy()),
            "unattributed": extra[STATES].to_numpy(),
        }))
    panel = pd.concat(out, ignore_index=True)

    # German-HZB first-years studying in the state. `study_location` is left
    # unmodified so it still reconciles against the phase 1 outcome exactly.
    panel["german_location"] = panel["study_location"] - panel["unattributed"]

    # Primary outcome (DESIGN.md 14.3): both sides count German-HZB holders only.
    panel["net_inflow"] = panel["german_location"] - panel["origin"]

    # Robustness variant, foreign and unknown origin left in the destination
    # term. Reported alongside, never as the headline.
    panel["net_inflow_incl_foreign"] = panel["study_location"] - panel["origin"]

    panel["outflow"] = panel["origin"] - panel["stayers"]
    panel["inflow"] = panel["german_location"] - panel["stayers"]

    # Scale-free outcomes (DESIGN.md 14.3). `attraction` is the primary: log of
    # the ratio of German-HZB first-years hosted to produced, so it is in log
    # points and comparable with the phase 1 coefficient. `retention` is the
    # share of a state's own school leavers who stay.
    panel["attraction"] = np.log(panel["german_location"] / panel["origin"])
    panel["retention"] = panel["stayers"] / panel["origin"]

    return panel.sort_values(["state_code", "year"]).reset_index(drop=True)


def flows_long(paths) -> pd.DataFrame:
    """Origin-destination pairs over time, for the destination analysis (14.6)."""
    out = []
    for p in paths:
        flows, _, _, year = read_matrix(p)
        f = flows.stack().rename("first_years").reset_index()
        f["year"] = year
        out.append(f)
    return pd.concat(out, ignore_index=True)
