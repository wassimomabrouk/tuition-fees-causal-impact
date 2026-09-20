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

2. FIRST-YEARS BY STUDY STATE x HOME STATE  (primary PHASE 2 source)
   Source  Fachserie 11 Reihe 4.1, "Studierende an Hochschulen", detailed
           table 6: "Studierende und Studienanfaenger/-innen nach Land des
           Studienortes und Land des Erwerbs der Hochschulzugangsberechtigung".
   Where   Statistische Bibliothek (www.statistischebibliothek.de), one volume
           per winter semester. Download the **xls**, not the PDF.
   Sheet   `TAB-06`. Two stacked blocks with identical layout: "Studierende
           insgesamt" then "Studienanfaenger/-innen insgesamt". Phase 2 uses the
           SECOND block. Rows are the study state (3 per state: m / w / i),
           columns are the state where the HZB was earned, plus Insgesamt,
           Ausland and ohne Angabe.
   Window  WS 2003/04 to WS 2007/08 (five volumes; DESIGN.md 14.1).
   Verified: WS 2003/04 and WS 2006/07 both parse with one parser. Sheet count
           differs between volumes (36 vs 50) but TAB-06 is identical in shape
           (138 x 23). Deutschland first-years in WS 2006/07 = 294 946, equal to
           the national sum of first_years_location in the phase 1 panel.

   WHY NOT EARLIER VOLUMES. The Fachserie became a free download from WS
   2003/04. Earlier issues exist in the Statistische Bibliothek only as scans
   whose OCR is unusable for numeric tables. Digit errors in OCR are silent, so
   a 16 x 16 matrix extracted from them could not be validated.

3. FIRST-YEAR RATE BY HOME STATE  (secondary outcome, PHASE 2)
   Table   21381-0011  "Studienanfaengerquote (Hochschulzugangsberechtigung):
                        Bundeslaender, Jahre, Geschlecht"
   Verified coverage: 2000-2023, annual, in percent.
   NOTE:   "Bundeslaender" here means the state where the university-entrance
           qualification was earned, not the state of study.
   Carried because it reaches back to 2000 and can test pre-trends where the
   five-volume primary window cannot. It is the weaker measure: a constructed
   rate whose denominator is a population extrapolation (see below).
   ALIGNMENT: annual, on the Studienjahr (summer plus the following winter),
           while source 1 and source 2 are winter semesters. The mapping is
           exact rather than approximate because no reform falls mid-semester;
           DESIGN.md 14.2 gives the table.

   DENOMINATOR, resolved: no Abitur cohort table is needed. The
   Studienanfaengerquote is computed by the Quotensummenverfahren from the
   student statistics for the reporting year and the population statistics as at
   31 December of the previous year, summing age-specific shares. The
   denominator is resident population by age, NOT the HZB cohort. The entry that
   previously stood here as "[TO VERIFY] and REQUIRED" is therefore closed as
   not required (DESIGN.md 0.2).
-------------------------------------------------------------------------------

Download (web UI): search the table code, log in (download is disabled when logged
out), "Anpassen" to set the time range and collapse unused dimensions, then
"Werteabruf" -> Download -> CSV (flat). Save into data/raw/ (gitignored).

Expected raw file for phase 1:
  21311-0014_first_years_by_location.csv

src/build_panel.py locates it by pattern, matching either the table code or
"first_years" in the filename, so a different but descriptive name still works.

Expected raw files for phase 2 (save into data/raw/fachserie/):
  fs11_4_1_WS2003_04.xls ... fs11_4_1_WS2007_08.xls
"""

TABLES = {
    "by_location":   {"table": "21311-0014", "grain": "Bundesland x winter semester",
                      "coverage": "WS 1998/99 onward", "phase": 1, "status": "verified"},
    "origin_matrix": {"table": "FS 11 R 4.1, TAB-06",
                      "grain": "study state x HZB state x winter semester",
                      "coverage": "WS 2003/04 onward (xls)", "phase": 2,
                      "status": "verified"},
    "by_home_state": {"table": "21381-0011", "grain": "Bundesland x year",
                      "coverage": "2000-2023", "phase": 2, "status": "verified"},
}

if __name__ == "__main__":
    print("GENESIS tables (save CSVs into data/raw/):\n")
    for name, t in TABLES.items():
        print(f"  [phase {t['phase']}] {name:14s} {t['table']:20s} "
              f"{t['grain']:44s} {t['coverage']:24s} {t['status']}")
    print("\nPhase 1 (notebooks 01-05) needs only 21311-0014.")
    print("Phase 2 primary source is the Fachserie xls, not a GENESIS table.")
