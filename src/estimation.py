"""
Estimators (DESIGN.md section 8). Mechanics only.

The estimator ladder is TWFE -> Callaway-Sant'Anna -> event study -> net-migration
DiD. Each function returns tidy output; the *choice* of specification and the
reading of results belong in notebook 04, not here.

Reminder encoded from DESIGN.md section 2: Callaway-Sant'Anna assumes ABSORBING
treatment. The fee reversal violates that, so introduction and abolition must be
estimated as two separate windows, never pooled.
"""
from __future__ import annotations
import pandas as pd


def twfe(panel: pd.DataFrame, outcome: str, treat="treated",
         unit="state_code", time="year", cluster="state_code"):
    """Baseline and diagnostic only. Never the headline (DESIGN.md 8.1)."""
    import pyfixest as pf
    return pf.feols(f"{outcome} ~ {treat} | {unit} + {time}",
                    data=panel, vcov={"CRV1": cluster})


def identification_anatomy(panel: pd.DataFrame, treat="treated", time="year") -> pd.DataFrame:
    """Which periods actually contain both treated and untreated units?

    n_distinct == 1 means the period contributes no identifying variation: with
    unit and period fixed effects, the treatment indicator is only identified
    from within-period variation. Run this before trusting any pooled estimate.
    """
    return panel.groupby(time)[treat].agg(treated_share="mean", n_distinct="nunique")


def callaway_santanna(panel: pd.DataFrame, outcome: str, cohort_col="cohort",
                      unit="state", time="year", control_group="never_treated"):
    """Primary estimator. Requires an absorbing-treatment window."""
    from differences import ATTgt
    d = panel.set_index([unit, time]).copy()
    att = ATTgt(data=d[[outcome, cohort_col]], cohort_column=cohort_col)
    att.fit(formula=outcome, control_group=control_group, n_jobs=1, progress_bar=False)
    return att


def minimum_detectable_effect(panel: pd.DataFrame, outcome: str, n_treated: int,
                              n_control: int, alpha=0.05, power=0.80) -> dict:
    """MDE from pre-period residual variance (DESIGN.md 7.1).

    Computed before estimation and separately for each candidate comparison
    group (DESIGN.md 5.2): the western-only group has 3 controls, the pooled
    group has 9, so their detectable effects differ substantially.
    """
    import numpy as np
    from scipy import stats
    pre = panel.loc[panel["treated"] == 0, outcome]
    sd = pre.std(ddof=1)
    z_a = stats.norm.ppf(1 - alpha / 2)
    z_b = stats.norm.ppf(power)
    mde = (z_a + z_b) * sd * np.sqrt(1 / n_treated + 1 / n_control)
    return {"outcome": outcome, "pre_sd": sd, "n_treated": n_treated,
            "n_control": n_control, "mde_abs": mde,
            "mde_pct_of_mean": 100 * mde / pre.mean() if pre.mean() else float("nan")}
