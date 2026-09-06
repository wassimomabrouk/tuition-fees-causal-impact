# Notebooks (run in order)

Design rule: **mechanics live in `src/`, interpretation lives here.** The modules
fit models and run checks; these notebooks choose the specification, read the
diagnostics, and state the caveats.

1. `01_data_validation.ipynb` - reconciliation, structural breaks, missing cells,
   treatment-table consistency (DESIGN.md section 9).
2. `02_eda.ipynb` - cohort trends, levels by state, east/west trajectories,
   double-cohort years.
3. `03_pretrends_power.ipynb` - the identification diagnostic and the minimum
   detectable effect per comparison group (DESIGN.md 7.1 and 5.2). Locks the
   specification before any treatment effect is estimated.
4. `04_estimation.ipynb` - TWFE baseline and identification anatomy, then
   Callaway-Sant'Anna, event study, and the net-migration outcome.
5. `05_robustness.ipynb` - placebos, leave-one-state-out, comparison-group
   sensitivity, east/west, G8 exclusion, reversal analysis, placebo-based
   inference.
