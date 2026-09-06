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
| HZB / Abitur cohort size (denominator) | GENESIS, Schulstatistik | Bundesland x year | not yet checked | **to verify, and REQUIRED** |
| full home-state x study-state migration matrix | unknown | | | **not found** |

*Table substitution, recorded during acquisition.* This section first specified
**21311-0015** for the study-location outcome. It proved unusable in practice: it is broken
out by 297 `Studienfach` categories with no aggregate option, so a full pull is truncated by
the GENESIS row limit. **21311-0014** carries the same measure at the grain this study needs
(Bundesland x winter semester, split only by nationality and sex, both of which are taken as
`Insgesamt`) and is the table the pipeline reads. Every reference below is to 21311-0014.

**The denominator table is load-bearing, not optional.** The diversion outcome (section
6.1) is the *difference* between two measures, so both must be in the same units. Table
21311-0014 is a count; 21381-0011 is a rate over the age cohort. Converting the rate back
to a count requires the HZB cohort size. **If that table cannot be found, the derived
net-migration outcome cannot be constructed** and the project falls back to comparing the
two measures in normalised form only. This must be settled before the panel is built.

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

## References

- Callaway, B. and Sant'Anna, P. (2021). *Difference-in-Differences with Multiple Time Periods.* Journal of Econometrics.
- Rambachan, A. and Roth, J. (2023). *A More Credible Approach to Parallel Trends.* Review of Economic Studies.
- Goodman-Bacon, A. (2021). *Difference-in-Differences with Variation in Treatment Timing.* Journal of Econometrics.
- Bundesverfassungsgericht, decision of 26 January 2005, on the federal ban on general tuition fees.
- Huebner, M. (2012). *Do tuition fees affect enrollment behavior? Evidence from a German policy experiment.* Economics of Education Review.
- Kauder, B. and Potrafke, N. (2013). *Government Ideology and Tuition Fee Policy: Evidence from the German States.* CESifo Working Paper 4205.
- Bruckmeier, K. and Wigger, B. (2014). *The effects of tuition fees on transition from high school to university in Germany.* Economics of Education Review.
