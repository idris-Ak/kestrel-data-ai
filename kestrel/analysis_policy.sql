-- Shared analysis policy. Creates TEMP views only; the prepared database stays read-only and neutral.
-- Decisions (outputs/workstreams/DECISIONS.md, summarised in the stage-2 doc):
--   D1 rating direction (higher is better unless a legend says otherwise) and
--   D2 rating bands (5-pt 1-2 / 10-pt 1-4 / 3-label bad = negative; strict and broad sensitivities)
--      are analysis-time assumptions applied here, never written to the database.
--   D3 Hunter Motors -> NSW05 and D4 Bendigo S/SV/P -> Sales/Service/Parts are applied by
--      `prepare` (dealer_status='assumed_mapping', department_status='assumed_code'); this file
--      only exposes them as dealer_assumed / department_assumed for sensitivity checks.
--   D5 population and comparability rules (period, Noosa selective collection, H1/H2, quarters).
-- Usage: sqlite3 -readonly outputs/prepared/current/prepared.sqlite  then  .read kestrel/analysis_policy.sql
--    or: python3 -I: con=sqlite3.connect('file:<db>?mode=ro',uri=True); con.executescript(open('kestrel/analysis_policy.sql').read())

DROP VIEW IF EXISTS temp.analysis_events;
CREATE TEMP VIEW analysis_events AS
WITH base AS (
  SELECT e.*,
    e.dealer_code AS dealer_final,
    CASE WHEN e.dealer_status = 'assumed_mapping' THEN 1 ELSE 0 END AS dealer_assumed,
    e.department AS department_final,
    CASE WHEN e.department_status = 'assumed_code' THEN 1 ELSE 0 END AS department_assumed,
    CASE WHEN e.rating_direction = 'unspecified' THEN 'high_is_good_assumed' ELSE e.rating_direction END AS direction_final,
    CASE WHEN e.rating_valid = 0 THEN NULL
         WHEN e.rating_direction = 'unspecified' THEN e.rating_value
         ELSE e.rating_oriented END AS rating_final
  FROM feedback_events e
  WHERE e.population = 'individual'
)
SELECT b.*,
  d.dealership_name, d.state, d.region, d.status AS dealer_status_ref,
  CASE WHEN b.rating_final IS NULL THEN NULL
       WHEN b.rating_scale_max = 10 THEN CASE WHEN b.rating_final <= 4 THEN 'negative' WHEN b.rating_final <= 6 THEN 'neutral' ELSE 'positive' END
       WHEN b.rating_scale_max = 3  THEN CASE b.rating_final WHEN 1 THEN 'negative' WHEN 2 THEN 'neutral' ELSE 'positive' END
       ELSE CASE WHEN b.rating_final <= 2 THEN 'negative' WHEN b.rating_final = 3 THEN 'neutral' ELSE 'positive' END
  END AS rating_band,
  CASE WHEN b.rating_final IS NULL THEN NULL
       WHEN b.rating_scale_max = 10 THEN b.rating_final <= 2
       WHEN b.rating_scale_max = 3  THEN b.rating_final = 1
       ELSE b.rating_final = 1 END AS negative_strict,
  CASE WHEN b.rating_final IS NULL THEN NULL
       WHEN b.rating_scale_max = 10 THEN b.rating_final <= 6
       WHEN b.rating_scale_max = 3  THEN b.rating_final <= 2
       ELSE b.rating_final <= 3 END AS negative_broad,
  CASE WHEN b.time_eligible = 1 AND b.feedback_month BETWEEN '2025-10' AND '2026-09'
        AND b.dealer_final IS NOT NULL AND b.department_final IS NOT NULL THEN 1 ELSE 0 END AS compare_eligible,
  CASE WHEN b.dealer_final = 'QLD05' THEN 1 ELSE 0 END AS selective_collection,
  CASE WHEN b.feedback_month BETWEEN '2025-10' AND '2026-03' THEN 'H1'
       WHEN b.feedback_month BETWEEN '2026-04' AND '2026-09' THEN 'H2' END AS half,
  CASE WHEN b.feedback_month BETWEEN '2025-10' AND '2025-12' THEN '2025Q4'
       WHEN b.feedback_month BETWEEN '2026-01' AND '2026-03' THEN '2026Q1'
       WHEN b.feedback_month BETWEEN '2026-04' AND '2026-06' THEN '2026Q2'
       WHEN b.feedback_month BETWEEN '2026-07' AND '2026-09' THEN '2026Q3' END AS quarter
FROM base b LEFT JOIN dealerships d ON d.dealer_code = b.dealer_final;

-- Toowoomba Q4 2025 aggregate buckets (5-point, higher is better assumed): weighted rows.
DROP VIEW IF EXISTS temp.analysis_aggregates;
CREATE TEMP VIEW analysis_aggregates AS
SELECT a.dealer_code AS dealer_final, a.department AS department_final, a.month AS feedback_month,
  a.rating_bucket AS rating_final, a.response_count,
  CASE WHEN a.rating_bucket <= 2 THEN 'negative' WHEN a.rating_bucket = 3 THEN 'neutral' ELSE 'positive' END AS rating_band,
  '2025Q4' AS quarter, 'H1' AS half
FROM rating_aggregates a;

-- Default comparison set: rated, comparable, not selectively collected, plus aggregate buckets.
DROP VIEW IF EXISTS temp.rated_responses;
CREATE TEMP VIEW rated_responses AS
SELECT dealer_final, department_final, feedback_month, quarter, half, rating_band, 1 AS weight, 'individual' AS source_kind,
       dealer_assumed, department_assumed, selective_collection
FROM analysis_events WHERE compare_eligible = 1 AND rating_band IS NOT NULL
UNION ALL
SELECT dealer_final, department_final, feedback_month, quarter, half, rating_band, response_count, 'aggregate', 0, 0, 0
FROM analysis_aggregates;
