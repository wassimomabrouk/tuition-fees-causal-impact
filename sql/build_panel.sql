-- Build the state x winter-semester analysis panel.
--
-- Registered views:
--   raw_fy  = GENESIS 21311-0014 (Studienanfaenger: Bundeslaender, Semester,
--             Nationalitaet, Geschlecht), long format
--   fees    = data/treatment/fee_dates.csv
--   g8      = data/treatment/g8_dates.csv
--
-- Grain: one row per (state, winter semester).
--
-- Timing note: 21311-0014 contains WINTER semesters only ('YYYY-10P6M' = the
-- 6-month period starting in October of YYYY). Winter is when the large majority
-- of German first-years enrol, so this is the right period, and `year` below is
-- the calendar year in which the winter semester begins.
--
-- Treatment note: fees are in force in winter semester `year` when
--   year >= intro_year AND (abolish_year IS NULL OR year < abolish_year)
-- Verified against every state's dates: e.g. Bayern introduced in SS 2007, so its
-- first charged winter semester is WS 2007/08 (year 2007); Hessen abolished from
-- WS 2008/09, so its last charged winter semester is WS 2007/08 (year 2007).

WITH fy AS (
    SELECT
        "1_variable_attribute_code"                 AS state_code,
        "1_variable_attribute_label"                AS state_raw,
        CAST(SUBSTR("time", 1, 4) AS INTEGER)       AS year,
        TRY_CAST("value" AS BIGINT)                 AS first_years
    FROM raw_fy
    WHERE "2_variable_attribute_label" = 'Insgesamt'   -- Nationalitaet
      AND "3_variable_attribute_label" = 'Insgesamt'   -- Geschlecht
)
SELECT
    f.state          AS state,
    f.state_en       AS state_en,
    fy.state_code,
    fy.year,
    'WS ' || fy.year || '/' || RIGHT(CAST(fy.year + 1 AS VARCHAR), 2) AS term_label,
    fy.first_years   AS first_years_location,

    f.ever_treated,
    f.intro_year,
    f.abolish_year,

    CASE WHEN f.intro_year IS NOT NULL
              AND fy.year >= f.intro_year
              AND (f.abolish_year IS NULL OR fy.year < f.abolish_year)
         THEN 1 ELSE 0 END                          AS treated,

    CASE WHEN f.intro_year IS NOT NULL
         THEN fy.year - f.intro_year END            AS event_time,

    CASE WHEN f.abolish_year IS NOT NULL
         THEN fy.year - f.abolish_year END          AS event_time_abolition,

    -- cohort for Callaway-Sant'Anna: 0 marks never-treated
    COALESCE(f.intro_year, 0)                       AS cohort,

    CASE WHEN fy.state_code IN ('11','12','13','14','15','16') THEN 1 ELSE 0 END AS east,
    CASE WHEN fy.state_code IN ('02','04','11') THEN 1 ELSE 0 END                AS city_state,

    g.double_abitur_year,
    CASE WHEN g.double_abitur_year IS NOT NULL
              AND fy.year = g.double_abitur_year THEN 1 ELSE 0 END AS double_cohort_year
FROM fy
JOIN fees f ON fy.state_code = f.state_code
LEFT JOIN g8 g ON fy.state_code = g.state_code
ORDER BY fy.state_code, fy.year;
