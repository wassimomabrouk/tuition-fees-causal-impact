# Design: Did tuition fees push German students across state borders?

This document fixes the causal logic **before** any code is written. Every modelling
choice downstream should trace back to something stated here. If the data forces a
change, the change is documented here, not hidden in a notebook.

---

## 0. Feasibility check (completed before anything else)

Treatment variation and outcome availability are verified first, since both can rule the
design out before any modelling choice matters.

### 0.1 Does the treatment have usable variation?

| requirement | status | evidence |
|---|---|---|
| staggered adoption | **yes** | 3 verified cohorts: WS 2006/07 (Niedersachsen, NRW), SS 2007 (Hamburg, Baden-Wuerttemberg, Bayern), WS 2007/08 (Hessen, Saarland) |
| never-treated units | **yes, 9 of 16 states** | Berlin, Brandenburg, Bremen, Mecklenburg-Vorpommern, Rheinland-Pfalz, Sachsen, Sachsen-Anhalt, Schleswig-Holstein, Thueringen never introduced general fees |
| treatment reversal | **yes** | all 7 states abolished fees, staggered WS 2008/09 to WS 2014/15 |
| sufficient pre-period | **yes** | outcome data begins WS 1998/99, giving 8 pre-treatment semesters |

The never-treated group is the decisive item: without units that are never exposed,
identification would rest only on differences in timing among adopters, which here span
just three semesters.

### 0.2 Does the outcome data exist at the required granularity and depth?

| data | table | unit x time | coverage | status |
|---|---|---|---|---|
| first-years by **university location** | GENESIS 21311-0014 | Bundesland x winter semester | WS 1998/99 onward (28 semesters) | **verified** |
| first-years by **home state** (state where the university-entrance qualification was earned) | GENESIS 21381-0011 | Bundesland x year | 2000-2023 | **verified** |
| HZB / Abitur cohort size (denominator) | GENESIS, Schulstatistik | Bundesland x year | not needed, see below | **resolved: not required** |
| first-years by **study state x home state** (full matrix) | Fachserie 11 R 4.1, detailed table 6 | Bundesland x Bundesland x winter semester | WS 2003/04 onward as machine-readable xls | **verified** |

*Table substitution, recorded during acquisition.* This section first specified
**21311-0015** for the study-location outcome. It proved unusable in practice: it is broken
out by 297 `Studienfach` categories with no aggregate option, so a full pull is truncated by
the GENESIS row limit. **21311-0014** carries the same measure at the grain this study needs
(Bundesland x winter semester, split only by nationality and sex, both of which are taken as
`Insgesamt`) and is the table the pipeline reads. Every reference below is to 21311-0014.

**The denominator problem, and how it was resolved (phase 2 feasibility check).** This
section originally recorded the HZB cohort size as load-bearing: the diversion outcome
(section 6.1) is the *difference* between two measures, so both must be in the same units,
and converting the rate in 21381-0011 back to a count appeared to require it.

Two findings during the phase 2 feasibility check removed the requirement.

First, the assumption behind it was wrong. The Studienanfaengerquote is **not** students per
school leaver. Destatis computes it by the *Quotensummenverfahren* from the student
statistics for the reporting year and the population statistics as at 31 December of the
previous year: an age-specific share is computed for each single year of age and the shares
are summed. The denominator is resident population by age, not the HZB cohort, so the
Schulstatistik table would not have converted it in any case.

Second, and better, a source was found that supplies **both margins as counts**, removing
the need to convert anything: Fachserie 11 Reihe 4.1, detailed table 6, *Studierende und
Studienanfaenger/-innen nach Land des Studienortes und Land des Erwerbs der
Hochschulzugangsberechtigung*. It is published per winter semester as a structured xls with
a `TAB-06` sheet, carrying a 16 x 16 matrix of first-years by study state and HZB state, with
`Ausland` and `ohne Angabe` as separate columns.

Verified against the existing panel: the Deutschland first-years total in table 6 for
WS 2006/07 is **294 946**, which equals the national sum of `first_years_location` in
`panel.parquet` for 2006 to the unit. The two sources are therefore the same measure, and no
reconciliation assumption is needed between the phase 1 and phase 2 outcomes.

**Known asymmetry.** The two outcomes do not match exactly:
21311-0014 is a semester-level **count**, 21381-0011 is an annual **rate**.

*Revised during implementation.* This section originally specified aggregating enrolments
to study-years (winter semester plus the following summer) so the two could be compared.
The table actually available at the required depth, 21311-0014, contains **winter semesters
only**, which removes the choice: the panel is one row per state per winter semester and no
aggregation happens. This is not a loss for phase 1, since the large majority of German
first-years enrol in winter, and it is more precise about timing than a study-year average
would have been. It does mean the alignment with the annual home-state rate in phase 2 has
to be handled at that point rather than assumed here.

### 0.3 Known confounder identified before estimation: the G8 school reform

States shortened Gymnasium from 13 to 12 years at different times, each producing a
**double Abitur cohort** in one year: a one-off surge in school leavers unrelated to fees.
These are large, state-specific, time-varying shocks landing inside the treatment window,
which is exactly the kind of confounder that breaks parallel trends (section 7).

The reform years are compiled in `data/treatment/g8_dates.csv` and verified against
primary sources before estimation. They are handled three ways:
excluded in a robustness specification, controlled for with a double-cohort indicator, and
partly neutralised by the triple difference, since a double cohort inflates *both* the
home-state and study-location measures while a fee should move only the latter.

---

## 0.4 Scope: minimum viable analysis first

This document specifies more analysis than a first pass should attempt: two outcomes plus
a derived third, three comparison groups, two absorbing experiments, heterogeneity splits,
and several sensitivity frameworks.

The work is therefore split. **Phase 1 is the minimum viable analysis**, and it is
complete and publishable on its own:

| phase 1 (build first) | why |
|---|---|
| outcome: **study-location first-years** (21311-0014) | single verified table; no denominator needed |
| window: **introduction only**, ending before the first abolition (WS 2008/09) | absorbing treatment, so Callaway-Sant'Anna is valid (section 2) |
| data quality + panel build + tests | the pipeline that everything else reuses |
| pre-trend diagnostic and **MDE per comparison group** (7.1, 5.2) | decides the primary specification before estimation |
| TWFE baseline, identification anatomy, Callaway-Sant'Anna, event study | the estimator ladder (section 8) |
| placebo dates, leave-one-state-out, east/west sensitivity | the checks most likely to change the conclusion |

**Phase 2, added only once phase 1 produces an end-to-end result:** the HZB denominator
table, the derived net-migration outcome (6.1), the reversal window (2), the destination
mechanism (6.2), Honest DiD bounds, and the heterogeneity splits (8.4).

Consequence worth stating: **phase 1 needs only one GENESIS table**, 21311-0014, which is
already verified. The HZB denominator, marked required in 0.2, is required for the
*net-migration outcome*, not for phase 1, so its absence does not block starting.

## 1. Research question

Between 2006 and 2008, seven German states introduced general tuition fees of up to 500
euros per semester while nine did not. Did the fees change **where** students enrolled,
pushing them across state borders into fee-free states, and did they change **whether**
people enrolled at all?

This separates two effects that a single outcome cannot distinguish:

- **Deterrence:** fewer people study at all.
- **Diversion:** the same people study, but somewhere else.

Most of the public debate assumed deterrence. Diversion is the more plausible margin,
because moving one state over is far cheaper than abandoning a degree, and it is the
margin this design is built to measure.

**Descriptive evidence already points this way.** Contemporary reports noted that first-year numbers fell about 6.5% in Nordrhein-Westfalen
at WS 2006/07 even as the number of qualified school leavers there rose about 4.9%, and
fell about 5.2% in Hessen, while fee-free Bremen and Brandenburg saw double-digit increases
in the same period. Those are raw comparisons with no counterfactual: they cannot separate
fees from the many other things moving enrolment. Supplying that counterfactual is the
contribution here.

## 2. Why this is a natural experiment

Fees were set by state law, at different dates, and then repealed at different dates.
Nine states never charged them. That gives a treated group, a clean comparison group, and
variation in both directions.

**The diversion mechanism was anticipated by the Constitutional Court itself.** In striking
down the federal ban in January 2005, the Bundesverfassungsgericht explicitly reasoned
about the possibility that fees in some states but not others would produce
*Wanderungsbewegungen*, migration flows that would overload fee-free universities and
underfill fee-charging ones. The court considered this tolerable because states could
respond. So the question this project tests is not invented after the fact: it is the
mechanism the court named when it permitted the policy.

The reversal is an unusual asset: the same states are observed treated and then untreated
again. An effect that appears on introduction and unwinds on abolition is far more
credible than either half alone.

**But the reversal is also an econometric problem, and it constrains the estimator.**
Callaway and Sant'Anna assumes treatment is **absorbing**: once treated, always treated.
Seven states here un-treat themselves between 2008 and 2014, which violates that
assumption directly. Pooling the whole 1998-2019 window into a single staggered-DiD run
would therefore be invalid, no matter how modern the estimator.

The design responds by splitting the episode into **two separate absorbing experiments**:

1. **Introduction.** Treated = the 7 adopting states; window **ends before the first
   abolition** (WS 2008/09, Hessen), so no unit reverts inside the window.
2. **Abolition.** Treated = states removing fees, event time measured from the repeal
   date, estimated on its own window among the 7 fee states.

Each is absorbing within its own window, so the estimator's assumptions hold. Treating
these as two experiments rather than one long panel is a requirement, not a stylistic
choice, and it is stated here so it cannot be quietly forgotten at estimation time.

## 3. Estimand

The **Average Treatment effect on the Treated (ATT)**: the average change in first-year
enrolment in states that introduced fees, relative to what enrolment would have been in
those states had fees not been introduced.

Estimated separately for:

1. enrolments **at universities in the state** (captures deterrence + diversion), and
2. enrolments **by students from the state** (captures deterrence only).

The **difference between the two is the diversion effect**, which is the target of the
triple-difference in section 8.

## 4. Treatment definition

- **Unit:** Bundesland.
- **Introduction:** the first semester in which general fees were charged to new students.
- **Abolition:** the first semester in which they were no longer charged.
- Both are hand-coded from the legal record in `data/treatment/fee_dates.csv`.

All dates are verified and recorded with their legislative decision dates in
`data/treatment/fee_dates.csv`.

**Hamburg, previously disputed, is resolved: SS 2007.** Secondary sources variously gave
2006 and 2008. The law passed the Buergerschaft on 28 June 2006; introduction was
originally planned for SS 2006 but **actually took effect in SS 2007**. The "2008" in some
sources refers to a later change of *model*, not of introduction (see below).

### 4.1 Treatment is not uniform

Three departures from a clean binary treatment, each carried into the robustness plan.

- **Within-state heterogeneity.** In **Nordrhein-Westfalen** each university decided
  whether to charge and how much, up to 500 euros. **Bayern** ranged 300-500 euros at
  universities and 100-500 at Fachhochschulen. So state-level treatment is an average over
  institutions, which attenuates the estimate.
- **Changing intensity within a spell.** **Hamburg** switched from WS 2008/09 to a
  deferred-payment model of 375 euros payable only after graduation and above an income
  threshold. Economically that is a much weaker treatment than an upfront 500 euros, so
  Hamburg's later years should not be treated as identical to its earlier ones.
- **Dose varies across states.** Fee spells range from **2 semesters (Hessen)** to **16
  (Niedersachsen)**, and Saarland charged 300 euros for the first two semesters. Cohort
  effects are therefore expected to differ by construction, which is an argument for
  reporting ATT(g,t) rather than a single pooled number (section 8.4).

### 4.2 Treatment timing is politically determined, not random

Every adopting state was governed by CDU, CSU or FDP; no SPD-led government introduced
general fees, and several abolitions followed a change of government (NRW 2011,
Niedersachsen 2013, Baden-Wuerttemberg 2012). Kauder and Potrafke (2013) document this
ideological patterning directly.

Treatment timing is therefore not as-good-as-random. Parallel trends fails if governing
ideology also drives other things that move enrolment: higher-education spending, capacity
expansion, school policy. This is tested through the pre-trend diagnostics, and it is the
specific alternative explanation that Honest DiD bounds (section 10) are meant to
quantify.

## 5. Comparison group

The nine never-treated states, plus not-yet-treated states in the staggered framing.
Already-treated states are **not** used as controls for later-treated ones (section 8).

### 5.1 The comparison group is partially collinear with east/west

This needs stating plainly because it is close to a confound rather than a nuisance:

- **every treated state is western** (Hamburg, Niedersachsen, NRW, Hessen,
  Baden-Wuerttemberg, Bayern, Saarland);
- **six of the nine never-treated states are eastern** (Berlin, Brandenburg,
  Mecklenburg-Vorpommern, Sachsen, Sachsen-Anhalt, Thueringen), leaving only
  **three western never-treated states**: Schleswig-Holstein, Bremen, Rheinland-Pfalz.

So treatment status is largely collinear with east/west, and any east-west differential
trend in the 2000s maps almost directly onto the treatment indicator. That trend is not
small. The post-1990 birth collapse cut eastern school-leaver cohorts sharply in exactly
this window, and eastern universities had different capacity, migration and labour-market
trajectories throughout.

### 5.2 Comparison-group choice is a specification decision, tested not assumed

Three candidate comparison groups:

| group | units | argument | cost |
|---|---|---|---|
| **western never-treated** | 3 | most comparable trajectories; avoids the east-west confound | very few units, low power |
| **all never-treated** | 9 | maximum power | imports the east-west differential trend |
| **not-yet-treated** | varies | uses the staggered timing | all western, but short comparison windows |

The **minimum detectable effect is computed separately for each** (section 7.1), and the
primary specification is chosen on that evidence. If the western-only comparison is too
underpowered to serve as primary, the pooled version is used and the east-west caveat is
reported in the headline. Whichever is chosen, the other two are reported alongside it,
and a result that survives in only one grouping is described as fragile.

**Eastern states are not simply dropped.** They are informative controls and discarding six
of nine units has a real cost. The question is not whether to keep them but whether the
answer depends on keeping them.

## 6. Outcomes

- **Study-location margin:** first-year students per state per winter semester, by
  **university location** (GENESIS 21311-0014). Responds to *both* participation and
  location choice. Modelled in **logs**, since state sizes differ roughly 20-fold.

  *Normalisation by Abitur cohort was considered and rejected for this outcome.* Dividing
  study-location enrolments by the state's own school-leaver cohort mixes two different
  populations, because students enrolled in a state did not all attend school there. The
  resulting ratio measures inflow per local school leaver rather than enrolment propensity,
  and moves with the migration this study is trying to isolate. Cohort normalisation is
  appropriate for the participation margin below, not here.
- **Participation margin:** first-year rate by **home state**, the state where the
  university-entrance qualification was earned (GENESIS 21381-0011). Responds to whether
  people from that state enrol *anywhere*.

**Naming discipline.** The second outcome is deliberately **not** called "deterrence".
Deterrence is a behavioural mechanism; what is measured is a participation rate. Someone
who defers a year, studies abroad, or switches to an apprenticeship all move this number
without any single mechanism being identified. The write-up says participation margin
throughout.

Counts are normalised (per Abitur cohort or per capita) so that state size and cohort
swings do not drive results.

### 6.1 The derived diversion outcome, and why it is not a triple difference

The comparison of the two outcomes is **not** a triple difference, despite superficially
resembling one.

A DDD requires two **disjoint** groups within each state-period, one exposed to treatment
and one not. These two outcomes are not disjoint: a student from Nordrhein-Westfalen who
studies in Nordrhein-Westfalen is counted in **both** measures. There is no untreated
comparison group inside the state, so the third difference does not exist.

What the two measures actually support is a **derived outcome**:

```
net_inflow(s,t) = first_years_studying_in(s,t) - first_years_from(s,t)
```

which is net student migration into state s. A fee should reduce it. Running DiD on this
derived outcome is legitimate, but it carries **its own identifying assumption**: *absent
fees, net migration into treated and comparison states would have followed parallel
trends*. That is a different and in some ways stronger
assumption than parallel trends in enrolment levels, because migration flows are volatile
and respond to capacity, admission restrictions (Numerus clausus) and university openings.
It is tested with the same pre-trend machinery.

**Units.** Both terms must be counts, which is why the HZB denominator table is required
(section 0.2).

### 6.2 Mechanism: where do diverted students go? (conditional on data)

The two outcomes above establish **whether** diversion happened. They cannot say **where**
students went. Answering that turns the project from "I estimated a DiD" into "I traced the
behavioural mechanism", which is the stronger result.

Doing it requires a **home-state x study-state migration matrix**, which section 0.2
records as **not found** in GENESIS. If such a table is located, the following become
possible and are worth doing:

- flows from fee states into **bordering** fee-free states, versus distant ones;
- whether the receiving state charging fees itself dampens the flow;
- whether flows reverse after abolition.

If the matrix cannot be found, the write-up states that the destination question could not
be answered with public aggregate data and the analysis stops at net diversion.

## 7. Identifying assumption

**Parallel trends:** absent fees, treated and comparison states would have followed the
same enrolment trajectory. Untestable directly; assessed by:

- pre-treatment event-study leads (should be flat, near zero);
- placebo treatment dates;
- explicit handling of the G8 double cohorts (section 0.3).

**A pre-trend test is a diagnostic, not a proof.** Parallel trends is an assumption about
an unobserved counterfactual and cannot be verified by data. Failing to reject flat leads
is weak evidence, and it is weakest exactly when it looks most reassuring: with few units
and noisy series the test has low power, so "no significant pre-trend" may simply mean "no
ability to detect one". With 16 state-level series that concern is concrete rather than
theoretical.

The pre-trend check is therefore treated as an **identification diagnostic**: it can
falsify the design but never confirm it. Confidence comes from the combination of that
diagnostic, the power analysis (section 7.1), placebo-based inference, and Honest DiD
bounds, not from any single test.

**Gate rule.** If pre-trends are clearly non-parallel, the design is adapted and the
adaptation is documented, rather than reporting a number that cannot be defended.

### 7.1 Power and minimum detectable effect, computed before estimation

With **7 treated and 9 comparison states**, power is a first-order concern. Before any
treatment effect is estimated, the **minimum detectable effect** is computed from the pre-period variance of the outcome, the number of units and periods,
and state-level clustering.

**The MDE is computed separately for each candidate comparison group** in section 5.2,
because the western-only group has three units and the pooled group has nine. That
calculation, not a prior preference, decides which grouping serves as the primary
specification.

Two things follow, and both are reported in the write-up regardless of the result:

1. **What this design can and cannot see.** If the MDE is, say, 5% of baseline enrolment,
   then any true effect smaller than that was never detectable, and a null result carries
   no information about effects below it.
2. **How to read a null.** A null with a large MDE is uninformative; a null with a small
   MDE is a substantive finding. Stating which one applies is the difference between an
   honest inconclusive result and a misleading one.



## 8. Estimation strategy

The estimators are **not interchangeable**. They form a hierarchy, and each step exists to
fix a specific failure of the step above. The write-up presents them in this order and says
what each one buys.

```
  TWFE                 baseline and diagnostic only, reported then critiqued
    |
  Callaway-Sant'Anna   primary estimate: cohort-by-period ATT against clean controls
    |
  Event study          dynamics, anticipation, and the formal pre-trend test
    |
  Net-migration DiD    the derived diversion outcome (section 6.1)
    |
  Robustness           placebos, leave-one-out, Honest DiD bounds, reversal analysis
```

### 8.1 Why not vanilla TWFE

TWFE is reported as a **baseline and a teaching device**, never as the headline. Under
staggered adoption with heterogeneous effects it is biased, because it implicitly uses
**already-treated** units as controls for later-treated ones. Those "forbidden comparisons"
can carry negative weights and, in extreme cases, flip the sign of the estimate. With a
reversal in the panel the problem compounds: post-abolition observations enter as
"treated" in a simple specification even though the policy is gone.

### 8.2 Threats specific to staggered DiD, and the response to each

| threat | why it bites here | response |
|---|---|---|
| **staggered timing** | 4 distinct introduction dates | cohort-by-period ATT(g,t) rather than a single pooled coefficient |
| **effect heterogeneity** | fee levels, exemptions and university autonomy differed by state | CS aggregates cohort effects with correct weights; heterogeneity inspected directly (8.4) |
| **already-treated contamination** | the core TWFE bias | CS restricts comparisons to never-treated and not-yet-treated units |
| **anticipation** | fees were announced well before taking effect | event-study leads; CS re-run with an anticipation window of 1 period as a robustness check |
| **treatment reversal** | breaks the absorbing-treatment assumption | two separate absorbing experiments; see section 2 |
| **differential state trends** | east/west and urban/rural trajectories differ | pre-trend testing, the triple difference, and Honest DiD bounds (10) |
| **spillovers (SUTVA)** | diversion means controls are affected by treatment elsewhere | the object of study, addressed by the triple difference (8.3) |

### 8.3 The net-migration specification

Fees should change **where** students enrol more than **whether** they enrol. The derived
outcome of section 6.1, net inflow, isolates that margin.

**What it does and does not buy.** Differencing the two measures removes shocks that move
them **proportionally**, and to that extent it helps with demographic swings and cohort
size. It does **not** automatically neutralise the G8 double cohorts. A double cohort
inflates the home-state measure and the study-location measure by different amounts,
because not all extra school leavers stay in state and neighbouring states compete for the
same places; it also spills across borders, which is the very margin under study.

The net-migration result is therefore treated as **supporting evidence consistent with or
against diversion**, not as a specification that has solved confounding. The G8 years are
still excluded in a robustness run (section 10) and still controlled for directly.

### 8.4 Heterogeneity (exploratory, and labelled as such)

CS returns ATT(g,t) for free, so cohort-level and period-level effects are plotted rather
than collapsed to one number. Splits worth inspecting: by adoption cohort, by fee duration
(Hessen charged for one year, Niedersachsen for eight), by city-state versus area-state,
and by whether a state borders a fee-free state.

**Limit.** There are 16 units and 7 treated ones, so these splits are **descriptive and
exploratory** rather than powered subgroup analysis, and no causal-forest or ML-based CATE
method is appropriate at this sample size.

### 8.5 Inference

Standard errors clustered at the state level. **In addition, placebo-based inference:** the
spread of pre-period placebo estimates is compared against the analytic standard error.
Clustered errors on short panels with few clusters are known to understate uncertainty, so
the placebo spread provides an assumption-light benchmark alongside the analytic one.

## 9. Data quality and validation

Run before estimation, documented in notebook 01.

- **Reconciliation.** State counts must sum to published national totals per semester.
- **Winter/summer asymmetry.** Most programmes start in winter, so summer semesters are
  systematically smaller. Aggregate to study-years rather than comparing raw semesters.
- **Definitional break.** The Hochschulstatistikgesetz was amended in 2016, changing how
  students at multi-site institutions are counted. Check for a level shift and, if
  present, keep the estimation window before it.
- **Double cohorts.** Flag and inspect each state's G8 year (section 0.3).
- **Missing or suppressed cells** logged, never silently dropped.

## 10. Robustness plan

- **Event-study pre-trends**, the core diagnostic.
- **Placebo treatment dates**, assigning a fake reform 2-3 years early.
- **Leave-one-state-out.** Re-estimate dropping each treated state in turn. With only 7
  treated units, a single state (Bayern and Nordrhein-Westfalen are the large ones) could
  drive the entire result. Cheap to run and immediately interpretable, so it is a required
  check rather than an optional one.
- **Honest DiD (Rambachan and Roth, 2023).** Rather than asserting parallel trends, bound
  the estimate under specified violations of it: how large would a differential trend have
  to be before the conclusion changes? This is the correct sensitivity tool for a DiD,
  because the assumption at risk is parallel trends, not unconfoundedness. (Selection-on-
  observables tools such as E-values or Cinelli-Hazlett answer a different question and do
  not apply here.)
- **Dropping city-states** (Berlin, Hamburg, Bremen), where cross-border commuting is
  extreme and the diversion margin is mechanically different.
- **East versus west** (section 5.2). Re-estimate against western never-treated states
  only, against all never-treated states, and with an east indicator interacted with time.
  Treated as **exploratory heterogeneity and sensitivity**, never as the headline: the aim
  is to learn how much the answer depends on including six eastern controls whose
  demographic trajectories differ sharply from the treated states.
- **Excluding double-cohort years** (section 0.3).
- **Alternative coding of the disputed Hamburg date** (section 4).
- **Reversal analysis**, run as its own absorbing experiment (section 2), and reported as a correlated second shock rather than independent replication.
- **Placebo-based inference** against the analytic standard errors (section 8.5).

## 11. Decision frame: from estimate to recommendation

The project closes by converting the estimate into something a decision-maker can act on.

- **Translate into students.** Convert the ATT into an approximate number of first-years
  gained or lost per state per year, carrying the confidence interval so the answer is a
  range, not false precision.
- **Separate the two margins.** If the effect is diversion rather than deterrence, then a
  fee does not reduce participation, it exports students and tuition revenue to
  neighbours. That is a materially different policy conclusion, and it is the one the
  public debate mostly missed.
- **Report inconclusive results as such.** If the effect cannot be distinguished from zero
  under assumption-light inference, that is the finding, and section 7.1 says whether the
  design could have detected a plausible effect at all.

## 12. Threats to validity

- **Spillovers (SUTVA).** Diversion means control states are affected by treatment
  elsewhere, which biases a naive DiD on the study-location outcome toward overstating the
  effect. This is not a nuisance here, it is the object of study, and the net-migration
  outcome (section 6.2) is the response.
- **Eastern controls were not passive.** Eastern universities actively recruited western
  students during this period, offering free tuition and available places into shrinking
  local cohorts. That is a **treatment-induced response in the control group**, a second
  SUTVA violation distinct from ordinary spillover: the controls changed their behaviour
  because of treatment elsewhere. It biases the study-location estimate away from zero and
  is a further reason the comparison-group choice (section 5.2) is reported explicitly.
- **The net-migration outcome has its own assumption.** Parallel trends in migration flows
  is not implied by parallel trends in enrolment levels, and flows are volatile and
  sensitive to capacity and admission restrictions. Stated and tested separately.
- **Low power.** With 7 treated units the minimum detectable effect may exceed plausible
  true effects; quantified in section 7.1.
- **G8 double cohorts.** See section 0.3.
- **Outcome asymmetry.** Semester counts versus annual rates; see section 0.2.
- **Fee variation and non-uniform treatment.** See section 4.1: within-state institutional
  choice in NRW and Bayern, Hamburg's mid-spell switch to deferred payment, and fee spells
  ranging from 2 to 16 semesters. All attenuate a pooled estimate.
- **Politically determined treatment timing.** See section 4.2. This is the most serious
  threat to parallel trends in this design.
- **Anticipation.** Fees were announced well before they took effect, so some response may
  precede the formal date. Tested with event-study leads.
- **Disputed Hamburg coding.** See section 4.

## 13. Data sources

- **Enrolment by university location:** Destatis GENESIS 21311-0014.
- **First-year rate by home state:** Destatis GENESIS 21381-0011.
- **Treatment dates:** hand-coded from the legal record, `data/treatment/fee_dates.csv`.

## 14. Phase 2: deterrence or diversion

*Written after phase 1 shipped and after the feasibility check in 0.2, and before any phase 2
code. Phase 1 established that first-year enrolment in the fee states fell by roughly 5 to 7
percent at the university location. That outcome counts students where they enrol, so a
student who abandoned higher education and a student who crossed a state border are
indistinguishable in it. Phase 2 separates them.*

### 14.1 Data and window

Primary source: **Fachserie 11 Reihe 4.1, detailed table 6**, sheet `TAB-06`, one xls per
winter semester. The sheet holds two stacked blocks with identical layout, *Studierende
insgesamt* and *Studienanfaenger/-innen insgesamt*; phase 2 uses the second. Rows are the
study state (three per state, m / w / i) and columns are the state where the HZB was earned,
plus `Insgesamt`, `Ausland` and `ohne Angabe`.

**Window: WS 2003/04 to WS 2007/08. Three pre-periods, two post.**

Shorter than phase 1's ten periods, for a reason that is worth recording rather than hiding.
The Fachserie became a free download from WS 2003/04; earlier volumes exist in the
Statistische Bibliothek only as scans whose OCR is unusable for numeric tables (sampled
output includes `Statistisch€s Bundesamt` and `bild6nde Künste`). Digit-level OCR errors are
silent, so extracting a 16 x 16 matrix from them would produce numbers that cannot be
validated. The window is therefore set by data quality, not by convenience.

The end of the window is the same absorbing-treatment boundary as phase 1 (section 2):
Hessen abolishes from WS 2008/09.

**Consequence, stated in advance: three pre-periods is thin.** The joint pre-trend test that
carried check 1 in phase 1 will have far less power here. This is the main cost of the matrix
route and it is not compensated by anything else in the design.

**Secondary outcome, retained for exactly that reason:** GENESIS 21381-0011, the
Studienanfaengerquote by state of HZB acquisition, 2000 to 2023. It is a weaker measure (a
constructed rate whose denominator is a population extrapolation, least accurate far from a
census, which is precisely this window) but it reaches back three years further and can test
pre-trends where the primary cannot. The two outcomes fail in different directions, which is
the point of carrying both.

### 14.2 Timing alignment

A *Studienjahr* is the summer semester plus the following winter semester (definition in
force since WS 1996/97, so stable across this window). Table 6 is per winter semester, so
phase 2 inherits phase 1's winter-semester grain and the annual-versus-semester problem
recorded in 0.2 does not arise for the primary outcome.

It does arise for the secondary outcome, which is annual. Mapping is exact rather than
approximate, because no reform falls mid-semester:

| Studienjahr | halves | states charging |
|---|---|---|
| 2006 | SS 2006, **WS 2006/07** | NRW, Niedersachsen: second half only |
| 2007 | **SS 2007**, **WS 2007/08** | NRW, NI both halves; HH, BW, BY both halves; Hessen, Saarland second half only |

Treatment within a Studienjahr is therefore exactly none, half or all of it, and is encoded
as that fraction rather than rounded.

### 14.3 Outcomes

From the first-years block of table 6, for state `s` in winter semester `t`:

- `study_location[s,t]` = row total. Reproduces the phase 1 outcome and is used as a
  reconciliation check, not as a new result.
- `origin[s,t]` = column total over study states. First-years **from** state `s`, wherever
  they enrolled. This is the participation margin, **as a count**.
- `net_inflow[s,t]` = `study_location - origin`. The diversion outcome.
- `flow[o,d,t]` = matrix interior. First-years with HZB from `o` studying in `d`, used for
  the destination analysis in 14.6.

`Ausland` and `ohne Angabe` cannot be attributed to a German state, so they are absent from
`origin` by construction. The question is whether they should also be removed from
`study_location` before taking the difference.

**Decided: remove them from both sides.**

    net_inflow[s,t] = (study_location[s,t] - unattributed[s,t]) - origin[s,t]

so that both terms count only first-years holding a German HZB.

The alternative, leaving `study_location` intact, would preserve exact comparability with the
phase 1 outcome. It is rejected, on evidence collected before any estimation:

- the unattributed share is **13 to 14 percent nationally**, far too large to treat as
  rounding
- it varies more than threefold across states, from 25.5 percent in Berlin to 7.2 percent in
  Schleswig-Holstein, so the contamination would be concentrated in particular states rather
  than spread evenly
- it moves **within** the window and differently by state (Hamburg swings 11.6 to 16.7 and
  back to 12.3; Schleswig-Holstein falls steadily from 10.2 to 7.2), so state fixed effects
  would not absorb it
- the fee-state and never-treated group means cross over in **2006**, the first treated
  winter semester. The movement is small but it is differential movement in the contaminating
  component, aligned with the treatment date, and under the alternative it would enter the
  estimate indistinguishably from a fee effect

Berlin, the most contaminated state at 25.5 percent, is a control; Schleswig-Holstein, the
least at 7.2 percent, is one of the three western never-treated states carrying the
co-primary comparison. The alternative would therefore have made the cleanest comparison in
the study the most contaminated one.

Substantively the same argument holds: a 500 euro semester fee is a real constraint on a
German school leaver choosing between two German states, and close to irrelevant to someone
choosing between Germany and another country. Mixing the two populations gives a coefficient
that answers no single question.

The comparability that the alternative buys is worth less than it appears, since `net_inflow`
is modelled in levels rather than logs (below) and is not directly comparable with phase 1's
coefficient in any case.

**Carried as a robustness check**, not discarded: the specification with `study_location` left
intact is re-run in notebook 07 and reported alongside. The per-state share table is reported
as a figure, since it is the justification for the choice.

`study_location` itself is kept unmodified in the panel, so the reconciliation against the
phase 1 outcome (14.8) still holds exactly.

#### Scaling of the diversion outcome, revised after the power check

`net_inflow` can be negative and is a difference of counts, so it cannot be logged. This
section originally specified reporting it per 1 000 of the state's origin cohort.

**That scaling was found to be underpowered and is demoted to a robustness variant.** The
revision was made on **pre-treatment variance only**, using the 2003 to 2005 residual after
absorbing state and year effects, and no treatment-period information entered the decision.

The diagnosis: dividing by `origin` puts a small, volatile denominator under a difference.
Bremen's origin cohort is roughly 2 600 against a university sector serving a wider region,
so its ratio sits near +640 per 1 000 and moves sharply year to year; Sachsen-Anhalt is the
other large contributor, and there the denominator is inflated by the 2007 G8 double cohort
already recorded in 0.3. Those two states carry residual standard deviations around 84, about
double any other. Note also that 97 percent of the raw variance in this outcome is *between*
states rather than within, so it is absorbed by state fixed effects and the cross-state
dispersion overstates what the estimator actually faces.

Two scale-free outcomes from the same table are substantially better powered:

| outcome | pre-period residual SD | MDE |
|---|---|---|
| `net_inflow` per 1 000 origin (original) | 34.0 | 43.8 per 1 000 |
| **`log(german_location / origin)`** (primary) | 0.032 | **4.2 percent** |
| **`stayers / origin`** (second outcome) | 0.013 | **1.7 points on a base of 0.611** |

**Primary: `attraction = log(german_location / origin)`.** The log of the ratio of German-HZB
first-years a state hosts to those it produces. Positive means a net importer. It is
scale-free, symmetric in the two margins, well defined because both terms are strictly
positive, and it is in log points, which restores direct comparability with the phase 1
coefficient that the levels scaling had given up.

**Second outcome: `retention = stayers / origin`.** The share of a state's own school leavers
who enrol in that state. This is the most direct test of diversion available: if fees push
students across a border, the fraction staying home is the first thing that should move. It
is also the least noisy series in the table.

`net_inflow` in levels and per 1 000 is **retained and reported** alongside both, so the
change of scaling is visible in the output rather than hidden.

The MDE for the primary outcome, 4.2 percent, sits below the 6.3 percent phase 1 estimated on
the location margin, so the design can detect an effect of the size phase 1 implies if one is
there. The MDE is recomputed in notebook 07 and is the pre-committed threshold.

### 14.4 Identifying assumption for the derived outcome

Section 6.1 already states this and it is restated here because it is the assumption most
likely to fail. A DiD on `net_inflow` requires parallel trends **in the difference**, which is
neither implied by nor implies parallel trends in either component. Two states whose
enrolment and whose origin cohorts each trend differently can still have a stable gap, and
two states with parallel components can have a diverging gap.

It is therefore tested on its own terms: the pre-period event study is run on `net_inflow`
directly, not inferred from the components passing.

### 14.5 What counts as which answer, fixed before estimation

| `origin` (participation) | `attraction` = log(location/origin) | `retention` | reading |
|---|---|---|---|
| falls | flat | flat | **deterrence**: fee states' school leavers became less likely to enrol anywhere |
| flat | falls | falls | **diversion**: the same people enrolled across a border |
| falls | falls | falls | **both**, with the split given by how much of the location fall `origin` accounts for |
| flat | flat | flat | phase 1's result does not replicate in this window; report that |

`attraction` and `retention` should move together under diversion and are reported together
for that reason: `retention` isolates the state's own school leavers leaving, `attraction`
combines that with any change in students arriving from elsewhere. A fall in `attraction`
with flat `retention` would mean the state stopped attracting outsiders rather than losing
its own, which is a different mechanism and is reported as such.

The fourth row is a real possibility and is listed deliberately: phase 1's effect is
identified off a ten-period window and phase 2 has five, so a failure to replicate is
informative about the shorter window rather than evidence against phase 1.

### 14.6 Destination analysis

Conditional on diversion appearing, the matrix interior answers where students went. The
pre-committed hypothesis is that flows from a fee state rise disproportionately into
**bordering fee-free states**, because the cost of crossing is lowest there. Testing it needs
an adjacency matrix for the sixteen states, which is hand-coded and sourced like
`fee_dates.csv`, and it is descriptive evidence on the mechanism rather than a second causal
estimate.

### 14.7 Power, before estimation

The minimum detectable effect is computed for `net_inflow` on this window, with its three
pre-periods and two post-periods, using `src/estimation.py` and reported before any treatment
effect is estimated, exactly as notebook 03 did for phase 1. If the MDE exceeds the effect
size phase 1 would imply, that is recorded as a design limit up front and a null is reported
as uninformative rather than as evidence of no diversion.

### 14.8 Extraction

Five workbooks, one parser. The first-years block is located by searching for its header row
rather than by a fixed row index, since the number of sheets differs between volumes (36 in
WS 2003/04, 50 in WS 2006/07) even though `TAB-06` itself is identical in shape.

Validation, run per volume and enforced in `tests/`: the Deutschland row must equal the sum
of the sixteen state rows; `study_location` must equal `first_years_location` in the existing
panel for the overlapping years; and the matrix interior plus `Ausland` plus `ohne Angabe`
must equal the `Insgesamt` column.


## 15. Phase 3: does the effect reverse when the policy does?

*Written after phase 2 shipped and before any phase 3 code. Phase 2 decomposed phase 1's fall
into roughly -2.9% participation and -3.6% redistribution, but neither half cleared its own
detection threshold, and with three pre-periods a pre-trend three times the size of the
effect could pass the pre-trend test unrejected (notebook 07). Phase 3 attacks both problems
with a second experiment on the same source.*

### 15.1 The test this experiment adds

If fees reduced enrolment, removing them should raise it again. The prediction is a **sign
flip**: the abolition coefficient should be positive where the introduction coefficient was
negative. A pre-existing trend does not reverse when a policy reverses; a causal effect should.
This is the one test neither earlier window can run, and it is the reason for phase 3.

**Reversal need not be symmetric**, and that is stated now so an asymmetric result is not
over-read later. Several mechanisms could make the abolition effect smaller than the
introduction effect without the introduction effect being spurious: students who moved
state may have settled; universities may have adjusted capacity or admissions while fees were
in force; information about the change may have spread more slowly than the change itself.
A sign flip of any size is evidence for the introduction effect. **No flip is evidence
against it only if the abolition design has the power to see one**, which 15.6 checks.

### 15.2 Comparison group: the fee states themselves

Section 2 committed the abolition experiment to be estimated **among the seven fee states**.
That commitment is kept, and it turns out to be the strongest feature of this design.

Callaway-Sant'Anna is run with **not-yet-treated** controls: each state that abolishes in a
given year is compared against fee states that are **still charging** that year. The
counterfactual for an abolishing state is then exactly the right one, a state that kept its
fees, rather than a state that never had any.

It also **removes the east-west confound** that phases 1 and 2 could only narrow. Every
treated state and every control in this specification is western, and every one of them was
under a CDU/CSU-era fee regime. The political-selection problem recorded in the README is not
fully solved, since states chose their abolition dates too, but the comparison is now between
states that all made the same first decision.

**The cost is severe and is stated in advance.** The design has at most seven units, and the
pool of not-yet-treated controls shrinks as states abolish:

| cohort | abolishing | not-yet-treated controls available |
|---|---|---|
| 2008 | Hessen | 6 |
| 2010 | Saarland | 5 |
| 2011 | Nordrhein-Westfalen | 4 |
| 2012 | Hamburg, Baden-Wuerttemberg | 2 |
| 2013 | Bayern | 1 |
| 2014 | Niedersachsen | **none** |

Niedersachsen, abolishing last, has no not-yet-treated comparison at all and drops out of the
primary specification. Bayern is compared against a single state.

**Secondary specification: never-treated controls**, the nine states that never charged, as
in phases 1 and 2. More power and continuity with the earlier phases, at the cost of
reintroducing the east-west confound and of a weaker counterfactual: a never-fee state
represents a fee state that kept its fees only if the introduction effect was a one-off level
shift. Both are reported; the not-yet-treated specification is primary.

### 15.3 Window

**WS 2007/08 to WS 2015/16**, nine winter semesters.

The start is set so that every treated state is **inside its fee regime** in the first period.
For the abolition experiment the "before" state is fees in force, and in WS 2006/07 only
Nordrhein-Westfalen and Niedersachsen were charging; the other five had not begun. Starting in
2006 would put pre-introduction years into the abolition pre-period, mixing two regimes.

Callaway-Sant'Anna uses year g-1 as each cohort's base, which is always a fee year from 2007
onward, so the estimator is correct regardless. The window start matters for the **leads**,
which are a pre-trend test only if every lead is a fee-regime year.

The end is set by the next double cohort: Schleswig-Holstein, a never-treated state, has its
G8 double cohort in 2016. Stopping at WS 2015/16 keeps it out.

Leads available by cohort: Hessen 1, Saarland 3, Nordrhein-Westfalen 4, Hamburg and
Baden-Wuerttemberg 5, Bayern 6, Niedersachsen 7. **Hessen charged for a single winter
semester** and has effectively no pre-period inside its fee regime; its abolition estimate
rests on one base year.

### 15.4 Data

Fachserie 11 Reihe 4.1, detailed table 6, **WS 2008/09 to WS 2015/16**: eight further volumes,
added to WS 2007/08 already held. Same sheet, same parser, same validation rules as 14.8. The
phase 2 extraction guards in `tests/test_fachserie.py` extend to the new window without
modification, except the window constant.

### 15.5 Confounds inside the window

**G8 double cohorts**, from the verified `g8_dates.csv`. This is the principal threat, and it
is worse here than in either earlier window because the double cohorts fall in the same years
and the same states as the abolitions:

| state | abolition | double cohort | gap |
|---|---|---|---|
| Hessen | 2008 | none (phased 2012-2014) | n/a |
| Saarland | 2010 | 2009 | -1 |
| Nordrhein-Westfalen | 2011 | 2013 | +2 |
| Hamburg | 2012 | 2010 | -2 |
| **Baden-Wuerttemberg** | **2012** | **2012** | **0** |
| Bayern | 2013 | 2011 | -2 |
| Niedersachsen | 2014 | 2011 | -3 |

Baden-Wuerttemberg abolished fees and had its double cohort in the same year. **It is excluded
from the primary specification** and reported in a leave-one-out, since its abolition effect
cannot be separated from a doubling of its school leavers.

Under the not-yet-treated design the controls are the other fee states, so their double
cohorts enter the comparison directly. The outcomes are partly protected: a double cohort
inflates a state's own school leavers, raising `origin`, and most of them stay, raising
`german_location` too, so in `attraction` the shock enters numerator and denominator together
and largely cancels. `retention` behaves similarly. `log(origin)` is **not** protected and is
expected to spike in double-cohort years. A double-cohort indicator is included as a
covariate and the estimates are reported with and without it.

**The end of conscription** in July 2011 released a cohort of young men into higher education
nationally. It is common to all states, so year fixed effects absorb its level; any
differential effect by state would need the male share of first-years, which table 6 reports
separately (the `m` rows) and which is used as a check if the 2011 estimates look anomalous.

### 15.6 Power, before estimation

Computed in the first phase 3 notebook on the **pre-abolition fee-regime years only**, using
`src/estimation.py`, before any abolition effect is estimated.

The threshold that matters is not the phase 1 effect size but **the smallest reversal worth
detecting**. Phase 2 put participation at -2.9% and attraction at -3.6%. If the abolition MDE
on either outcome exceeds the corresponding phase 2 estimate, the design cannot see a full
reversal, and a null result is reported as uninformative rather than as evidence that the
introduction effect was spurious. Given six effective units under not-yet-treated controls,
**that outcome is plausible and is flagged now** rather than discovered after estimation.

Randomisation inference over six or seven units has a small permutation space, so exact
enumeration replaces random draws, and the smallest achievable p-value is reported alongside
the result.

### 15.7 What counts as which answer, fixed before estimation

| `origin` after abolition | `attraction` after abolition | reading |
|---|---|---|
| rises | rises | **both mechanisms reverse**, corroborating the phase 2 split |
| flat | rises | **redistribution reverses**, participation does not |
| rises | flat | **participation reverses**, redistribution does not |
| flat | flat | **no reversal detected**; read against 15.6 before interpreting |
| falls | any | inconsistent with a fee effect; investigate before reporting |

"Rises" means a positive estimate that clears its own MDE and whose interval excludes zero,
the same double condition used throughout phase 2.

### 15.8 Outcome: phase 3 is underpowered, and estimation is not pursued as a test

*Added after the power calculation in notebook 10. Everything above this subsection was
committed as `b0c3575` before any phase 3 code was written, and none of it has been changed.*

**The design cannot detect the reversal it was built to find.** Computed by exact enumeration
of all 720 assignments of the six abolition dates for the primary specification, and 2 000
permutations for the secondary:

| specification | outcome | MDE | reversal to detect | ratio |
|---|---|---|---|---|
| primary, not-yet-treated | attraction | +16.5% | 3.6% | about 4x |
| primary, not-yet-treated | participation | +22.5% | 2.9% | about 7x |
| secondary, never-treated | attraction | +17.7% | 3.6% | about 4x |
| secondary, never-treated | participation | +35.8% | 2.9% | about 10x |

The permutation spread is computed on realised data and is therefore conservative, but
halving it would still leave the MDE above the target on every outcome.

**The cause is the period, not the specification.** With identical outcomes and identical
state and year fixed effects, the residual standard deviation across 2007 to 2015 is 2.2
times phase 2's on attraction and 4.5 times on participation. The abolitions coincided with
the Hochschulpakt expansion (national first-years rose 51 percent between WS 2006/07 and
WS 2011/12), the end of conscription in 2011, rising internationalisation (the unattributable
share rose from 13 to 17 percent), and G8 double cohorts in most states. Double-cohort
state-years are noisier than the rest, but the rest of the window is noisier than phase 2
too, so excluding them would not recover the lost precision.

**A second consequence of the primary design**, predicted in 15.2 and confirmed: with no
never-treated units, the estimator makes the last abolisher (Niedersachsen, 2014) the
comparison group for every other cohort and drops every period from 2014 onward. The
effective primary window is WS 2007/08 to WS 2013/14.

**Disclosure.** The point estimates were printed once, during a check that the estimator
executed, before this power calculation was run. The specification had already been
committed and has not been altered. The estimates are reported in notebook 10 alongside their
MDEs and labelled uninformative, without inference.

**What this does and does not mean.** Under 15.7, the reading is "no reversal detected", and
under 15.1 that is **not** evidence that the introduction effect was spurious, because the
design could not have seen a reversal of the size phase 2 implies. Phase 2's decomposition
stands as a point estimate, neither strengthened nor weakened by phase 3.

**Why the design is not modified to rescue it.** A shorter window, a different comparison
group or the exclusion of double-cohort years might each reduce the noise. Each would be a
specification choice made after the estimates had been seen, and there would be no way to
show it was not chosen to produce a significant result. The committed specification is
the only one that can be defended, and it says the answer is uninformative.

**What would make the test possible.** Not more years: the primary specification has no
controls left after 2014, and later years bring the Schleswig-Holstein double cohort (2016),
the G9 reversals (the Niedersachsen missing cohort around 2020) and COVID. The binding
constraint is units. Enrolment at the level of individual universities or districts would
turn sixteen states into hundreds of units and is the natural extension if the question is
pursued.

## References

- Callaway, B. and Sant'Anna, P. (2021). *Difference-in-Differences with Multiple Time Periods.* Journal of Econometrics.
- Rambachan, A. and Roth, J. (2023). *A More Credible Approach to Parallel Trends.* Review of Economic Studies.
- Goodman-Bacon, A. (2021). *Difference-in-Differences with Variation in Treatment Timing.* Journal of Econometrics.
- Bundesverfassungsgericht, decision of 26 January 2005, on the federal ban on general tuition fees.
- Huebner, M. (2012). *Do tuition fees affect enrollment behavior? Evidence from a German policy experiment.* Economics of Education Review.
- Kauder, B. and Potrafke, N. (2013). *Government Ideology and Tuition Fee Policy: Evidence from the German States.* CESifo Working Paper 4205.
- Bruckmeier, K. and Wigger, B. (2014). *The effects of tuition fees on transition from high school to university in Germany.* Economics of Education Review.
