"""
Estimators (DESIGN.md section 8). Mechanics only.

The estimator ladder is TWFE -> Callaway-Sant'Anna -> event study. Each function
returns tidy output; the *choice* of specification and the reading of results
belong in the notebooks, not here.

Reminder encoded from DESIGN.md section 2: Callaway-Sant'Anna assumes ABSORBING
treatment. The fee reversal violates that, so introduction and abolition must be
estimated as two separate windows, never pooled.
"""
from __future__ import annotations

import warnings

import numpy as np
import pandas as pd


# --------------------------------------------------------------------------
# two-way fixed effects
# --------------------------------------------------------------------------

def twfe(panel: pd.DataFrame, outcome: str, treat="treated", unit="state_id",
         time="year", cluster="state_id", extra=""):
    """Baseline and diagnostic only. Never the headline (DESIGN.md 8.1).

    `unit` defaults to the numeric state_id rather than state_code: the wild
    cluster bootstrap runs through numba and cannot take a string cluster.
    `extra` appends additional right-hand-side terms, e.g. " + double_cohort_year".
    """
    import pyfixest as pf
    return pf.feols(f"{outcome} ~ {treat}{extra} | {unit} + {time}",
                    data=panel, vcov={"CRV1": cluster})


def identification_anatomy(panel: pd.DataFrame, treat="treated",
                           time="year") -> pd.DataFrame:
    """Which periods actually contain both treated and untreated units?

    n_distinct == 1 means the period contributes no identifying variation: with
    unit and period fixed effects, the treatment indicator is only identified
    from within-period variation. Run this before trusting any pooled estimate.
    """
    return panel.groupby(time)[treat].agg(treated_share="mean", n_distinct="nunique")


# --------------------------------------------------------------------------
# Callaway-Sant'Anna
# --------------------------------------------------------------------------

def callaway_santanna(panel: pd.DataFrame, outcome: str,
                      cohort_col="treatment_year_cs", unit="state", time="year",
                      control_group="never_treated"):
    """Primary estimator. Requires an absorbing-treatment window.

    `cohort_col` must hold the first treated period and NaN (not 0) for
    never-treated units, which is what `differences` expects.
    """
    from differences import ATTgt
    cs = panel.set_index([unit, time]).copy()
    cs["cohort"] = cs[cohort_col]
    att = ATTgt(data=cs[[outcome, "cohort"]], cohort_column="cohort")
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        att.fit(formula=outcome, control_group=control_group, n_jobs=1,
                progress_bar=False)
    return att


def tidy_att(frame: pd.DataFrame) -> pd.DataFrame:
    """Flatten a `differences` aggregate() result to ATT / SE / lo / hi.

    The package returns a MultiIndex column layout that varies with the
    aggregation, so the columns are matched by suffix rather than by position.
    """
    out = frame.copy()
    out.columns = ["_".join(str(x) for x in c if str(x) != "").strip("_")
                   for c in out.columns]
    ren = {}
    for c in out.columns:
        if c.endswith("ATT"):
            ren[c] = "ATT"
        elif "std_error" in c:
            ren[c] = "SE"
        elif c.endswith("lower"):
            ren[c] = "lo"
        elif c.endswith("upper"):
            ren[c] = "hi"
    return out.rename(columns=ren)[["ATT", "SE", "lo", "hi"]]


def cs_overall(panel: pd.DataFrame, outcome: str, **kw) -> pd.DataFrame:
    """Overall ATT in one call. Convenience wrapper for the resampling loops."""
    return tidy_att(callaway_santanna(panel, outcome, **kw).aggregate("simple"))


def cs_overall_fast(panel: pd.DataFrame, outcome: str,
                    cohort_col="treatment_year_cs", unit="state_code",
                    time="year") -> float:
    """Closed form of the Callaway-Sant'Anna `simple` aggregation.

    Valid only in the case this study is in: never-treated controls, absorbing
    treatment, a balanced panel and no covariates. Each group-time effect is
    then just a 2x2 difference against the cohort's last pre-period,

        ATT(g,t) = [Ybar(g,t) - Ybar(g,g-1)] - [Ybar(never,t) - Ybar(never,g-1)]

    aggregated with weights proportional to cohort size.

    About 150 times faster than refitting through `differences`, which matters
    only for the resampling loops. It is **verified against `cs_overall` in the
    notebook before use**, and the analytic standard errors still come from the
    package: this returns a point estimate and nothing else.
    """
    y = panel.pivot(index=unit, columns=time, values=outcome)
    g = (panel.drop_duplicates(unit).set_index(unit)[cohort_col]).reindex(y.index)
    never = g.isna()
    if not never.any():
        return float("nan")
    num = den = 0.0
    for cohort in sorted(g.dropna().unique()):
        grp = g == cohort
        base = cohort - 1
        if base not in y.columns:
            continue
        for t in [c for c in y.columns if c >= cohort]:
            att = ((y.loc[grp, t] - y.loc[grp, base]).mean()
                   - (y.loc[never, t] - y.loc[never, base]).mean())
            w = int(grp.sum())
            num += w * att
            den += w
    return float(num / den) if den else float("nan")


def cs_overall_nyt_fast(panel: pd.DataFrame, outcome: str, cohort_col="abol",
                        unit="state_code", time="year") -> float:
    """Closed form of Callaway-Sant'Anna with NOT-YET-TREATED controls.

    For a sample with no never-treated units, which is the phase 3 primary
    specification (DESIGN.md 15.2). `differences` then uses the last cohort as
    the comparison group and keeps only periods before the last cohort's date;
    this reproduces that exactly. Each group-time effect is a 2x2 difference
    against units not yet treated at t, excluding the group itself.

    Used only inside resampling loops, and verified against the package in the
    notebook before use.
    """
    y = panel.pivot(index=unit, columns=time, values=outcome)
    g = (panel.drop_duplicates(unit).set_index(unit)[cohort_col]).reindex(y.index)
    last = g.max()
    years = [t for t in y.columns if t < last]
    num = den = 0.0
    for cohort in sorted(g.dropna().unique()):
        if cohort == last:
            continue
        grp = g == cohort
        base = cohort - 1
        if base not in y.columns:
            continue
        for t in [t for t in years if t >= cohort]:
            ctrl = (g > t) & ~grp
            if not ctrl.any():
                continue
            att = ((y.loc[grp, t] - y.loc[grp, base]).mean()
                   - (y.loc[ctrl, t] - y.loc[ctrl, base]).mean())
            w = int(grp.sum())
            num += w * att
            den += w
    return float(num / den) if den else float("nan")


def cs_event_study(panel: pd.DataFrame, outcome: str, **kw) -> pd.DataFrame:
    """Relative-period ATTs, with the relative period as a column named `rel`."""
    ev = tidy_att(callaway_santanna(panel, outcome, **kw).aggregate("event"))
    ev = ev.reset_index()
    ev = ev.rename(columns={ev.columns[0]: "rel"})
    ev["rel"] = ev["rel"].astype(int)
    return ev


# --------------------------------------------------------------------------
# power
# --------------------------------------------------------------------------

def residual_sd(panel: pd.DataFrame, outcome: str, unit="state_code",
                time="year") -> float:
    """SD of the outcome after absorbing unit and period effects.

    The raw cross-state spread is dominated by state size, which differs
    twentyfold, so the residual is the noise the design actually works against.
    """
    import statsmodels.formula.api as smf
    m = smf.ols(f"{outcome} ~ C({unit}) + C({time})", data=panel).fit()
    return float(np.std(m.resid, ddof=1))


def minimum_detectable_effect(panel: pd.DataFrame, outcome: str, n_post: int,
                              label: str = "", alpha=0.05, power=0.80) -> dict:
    """MDE for a DiD contrast on a LOGGED outcome (DESIGN.md 7.1).

    `panel` should be the pre-treatment sample, since the residual SD is meant
    to describe variation in the absence of treatment. Computed before
    estimation and separately for each candidate comparison group
    (DESIGN.md 5.2): the western-only group has 3 controls and the pooled group
    has 9, so their detectable effects differ substantially.

    The outcome is in logs, so MDE_% converts the log-point effect rather than
    dividing by a mean, which would be meaningless for a logged variable.
    """
    from scipy import stats
    sd = residual_sd(panel, outcome)
    n_t = int(panel.loc[panel["ever_treated"] == 1, "state_code"].nunique())
    n_c = int(panel.loc[panel["ever_treated"] == 0, "state_code"].nunique())
    n_pre = int(panel["year"].nunique())
    se = sd * np.sqrt((1 / n_t + 1 / n_c) * (1 / n_pre + 1 / n_post))
    z = stats.norm.ppf(1 - alpha / 2) + stats.norm.ppf(power)
    return {"comparison group": label, "treated": n_t, "controls": n_c,
            "pre_periods": n_pre, "post_periods": n_post,
            "resid_sd_log": sd, "MDE_log": z * se,
            "MDE_%": 100 * (np.exp(z * se) - 1)}
