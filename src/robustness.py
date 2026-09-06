"""
Robustness checks (DESIGN.md section 10). Mechanics only; the verdicts belong in
notebook 05.
"""
from __future__ import annotations
import pandas as pd

EAST = {"11", "12", "13", "14", "15", "16"}          # incl. Berlin (DESIGN.md 5.1)
CITY_STATES = {"02", "04", "11"}                      # Hamburg, Bremen, Berlin
WEST_NEVER_TREATED = {"01", "04", "07"}               # SH, Bremen, Rheinland-Pfalz


def leave_one_state_out(panel: pd.DataFrame, fit_fn, treated_codes) -> pd.DataFrame:
    """Re-estimate dropping each treated state in turn.

    With only 7 treated units, a single large state (Bayern, NRW) could drive
    the entire result, so this is a required check rather than an optional one.
    """
    rows = []
    for code in treated_codes:
        sub = panel[panel["state_code"] != code]
        rows.append({"dropped": code, **fit_fn(sub)})
    return pd.DataFrame(rows)


def by_comparison_group(panel: pd.DataFrame, fit_fn) -> pd.DataFrame:
    """Same estimate under the three candidate comparison groups (DESIGN.md 5.2)."""
    groups = {
        "west_never_treated": panel[(panel.ever_treated == 1) |
                                    (panel.state_code.isin(WEST_NEVER_TREATED))],
        "all_never_treated": panel,
        "excl_city_states": panel[~panel.state_code.isin(CITY_STATES)],
    }
    return pd.DataFrame([{"group": k, "n_states": v.state_code.nunique(), **fit_fn(v)}
                         for k, v in groups.items()])


def placebo_dates(panel: pd.DataFrame, fit_fn, shift_periods=(-4, -3, -2)) -> pd.DataFrame:
    """Assign fake treatment before the real reform; the effect should vanish."""
    rows = []
    for k in shift_periods:
        sub = panel.copy()
        # never-treated units have no event_time. Comparing against NA yields NA
        # under pandas nullable dtypes (and False under plain float), so the
        # missing values are made explicit before casting rather than relying on
        # whichever dtype the panel happens to carry.
        sub["treated"] = (sub["event_time"] >= k).fillna(False).astype(int)
        rows.append({"placebo_shift": k, **fit_fn(sub)})
    return pd.DataFrame(rows)


def placebo_based_inference(pre_period_estimates) -> dict:
    """Compare the spread of pre-period placebos against the analytic SE.

    Clustered standard errors with few clusters are known to understate
    uncertainty. The placebo spread is an assumption-light benchmark: if it
    substantially exceeds the analytic SE, the analytic interval is too narrow
    (DESIGN.md 8.5).
    """
    import numpy as np
    a = np.asarray(list(pre_period_estimates), dtype=float)
    return {"placebo_sd": a.std(ddof=1), "n_placebos": a.size}
