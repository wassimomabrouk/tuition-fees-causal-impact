"""
Source tables from Destatis GENESIS-Online (https://genesis.destatis.de).

Reproducible record of WHICH tables to pull and HOW to slice them. Verified in
DESIGN.md section 0.2 before the design was written.

Phase 1 (the analysis in notebooks 01-05) needs table 1 below and nothing else.
Tables 2 and 3 are phase 2 and are listed so the requirement is on the record,
not because anything currently reads them.

-------------------------------------------------------------------------------
1. FIRST-YEARS BY UNIVERSITY LOCATION  (primary outcome, PHASE 1)
   Table   21311-0014  "Studienanfaenger: Bundeslaender, Semester, Nationalitaet,
                        Geschlecht"
   Verified coverage: WS 1998/99 onward (28 winter semesters), all 16 Bundeslaender.
   Select: all semesters; all 16 Bundeslaender;
           Nationalitaet = Insgesamt; Geschlecht = Insgesamt.
   Grain:  one row per Bundesland per WINTER semester. The `time` field is an
           ISO 8601 duration, 'YYYY-10P6M', the six months from October of YYYY.
           There are no summer semesters in this table, so `year` in the panel is
           the calendar year in which the winter semester begins.

   WHY NOT 21311-0015. The design originally specified 21311-0015, which carries
   the same measure but is additionally broken out by 297 Studienfach categories
   with no aggregate option. A full pull is truncated by the GENESIS row limit and
   the table cannot be collapsed to a usable total through the web UI. 21311-0014
   is the same measure at the grain this study needs. The substitution is recorded
   in DESIGN.md 0.2.

2. FIRST-YEAR RATE BY HOME STATE  (secondary outcome, PHASE 2)
   Table   21381-0011  "Studienanfaengerquote (Hochschulzugangsberechtigung):
                        Bundeslaender, Jahre, Geschlecht"
   Verified coverage: 2000-2023, annual.
   NOTE:   "Bundeslaender" here means the state where the university-entrance
           qualification was earned, not the state of study. This is the measure
           that separates deterrence from diversion.
   ALIGNMENT PROBLEM, unresolved: this is an ANNUAL RATE while table 1 is a
           WINTER-SEMESTER COUNT. Reconciling them needs the denominator in
           table 3 and a stated assumption about how a winter intake maps to an
           academic year. Do not assume the two are directly comparable.

3. ABITUR / HZB COHORT SIZE  (denominator, PHASE 2)  [TO VERIFY]
   Needed to convert the rate in table 2 back to a count, and to handle the G8
   double cohorts (DESIGN.md 0.3). Table not yet identified. Verify before use.
   Phase 1 does not depend on it.
-------------------------------------------------------------------------------

Download (web UI): search the table code, log in (download is disabled when logged
out), "Anpassen" to set the time range and collapse unused dimensions, then
"Werteabruf" -> Download -> CSV (flat). Save into data/raw/ (gitignored).

Expected raw file for phase 1:
  21311-0014_first_years_by_location.csv

src/build_panel.py locates it by pattern, matching either the table code or
"first_years" in the filename, so a different but descriptive name still works.
"""

TABLES = {
    "by_location":   {"table": "21311-0014", "grain": "Bundesland x winter semester",
                      "coverage": "WS 1998/99 onward", "phase": 1, "status": "verified"},
    "by_home_state": {"table": "21381-0011", "grain": "Bundesland x year",
                      "coverage": "2000-2023", "phase": 2, "status": "verified"},
    "abitur_cohort": {"table": "<to identify>", "grain": "Bundesland x year",
                      "coverage": "?", "phase": 2, "status": "TO VERIFY"},
}

if __name__ == "__main__":
    print("GENESIS tables (save CSVs into data/raw/):\n")
    for name, t in TABLES.items():
        print(f"  [phase {t['phase']}] {name:15s} {t['table']:14s} "
              f"{t['grain']:30s} {t['coverage']:20s} {t['status']}")
    print("\nPhase 1 (notebooks 01-05) needs only 21311-0014.")
