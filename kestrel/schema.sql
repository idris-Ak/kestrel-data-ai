PRAGMA foreign_keys = ON;
PRAGMA user_version = 1;

CREATE TABLE run_metadata (key TEXT PRIMARY KEY, value TEXT NOT NULL);
CREATE TABLE source_files (
    source_id TEXT PRIMARY KEY, path TEXT NOT NULL UNIQUE, sha256 TEXT NOT NULL,
    kind TEXT NOT NULL, profile_json TEXT NOT NULL, metadata_json TEXT NOT NULL
);
CREATE TABLE dealerships (
    dealer_code TEXT PRIMARY KEY, dealership_name TEXT NOT NULL, suburb TEXT,
    state TEXT NOT NULL, region TEXT NOT NULL, brands TEXT, status TEXT NOT NULL,
    closed_date TEXT, source_id TEXT NOT NULL REFERENCES source_files,
    source_row INTEGER NOT NULL, raw_fields_json TEXT NOT NULL
);
CREATE TABLE source_observations (
    observation_id TEXT PRIMARY KEY, source_id TEXT NOT NULL REFERENCES source_files,
    sheet TEXT NOT NULL, source_row INTEGER NOT NULL, source_end_row INTEGER NOT NULL,
    layout_version TEXT NOT NULL, kind TEXT NOT NULL CHECK(kind IN ('feedback','rating_aggregate')),
    raw_fields_json TEXT NOT NULL, event_id TEXT REFERENCES feedback_events,
    disposition TEXT NOT NULL CHECK(disposition IN ('pending','retained','duplicate','aggregate')),
    resolution_rule TEXT,
    UNIQUE(source_id,sheet,source_row)
);
CREATE TABLE feedback_events (
    event_id TEXT PRIMARY KEY,
    canonical_observation_id TEXT NOT NULL UNIQUE REFERENCES source_observations(observation_id),
    dealer_code TEXT NOT NULL REFERENCES dealerships, department_raw TEXT, department TEXT,
    department_subtype TEXT,
    feedback_date_raw TEXT, feedback_date TEXT, date_precision TEXT NOT NULL,
    time_eligible INTEGER NOT NULL CHECK(time_eligible IN (0,1)),
    rating_raw TEXT, rating_value INTEGER, rating_scale_max INTEGER NOT NULL,
    rating_direction TEXT NOT NULL CHECK(rating_direction IN ('low_is_good','high_is_good','unspecified')),
    rating_oriented INTEGER, rating_valid INTEGER NOT NULL CHECK(rating_valid IN (0,1)),
    comment_raw TEXT, has_text INTEGER NOT NULL CHECK(has_text IN (0,1)),
    native_reference TEXT, reference_namespace TEXT,
    CHECK(rating_value IS NULL OR rating_value BETWEEN 1 AND rating_scale_max),
    CHECK(rating_oriented IS NULL OR rating_oriented BETWEEN 1 AND rating_scale_max),
    CHECK(department IS NULL OR department IN ('Sales','Service','Parts'))
);
CREATE TABLE rating_aggregates (
    observation_id TEXT NOT NULL REFERENCES source_observations,
    dealer_code TEXT NOT NULL REFERENCES dealerships, month TEXT NOT NULL,
    department TEXT NOT NULL CHECK(department IN ('Sales','Service','Parts')),
    rating_bucket INTEGER NOT NULL CHECK(rating_bucket BETWEEN 1 AND 5),
    response_count INTEGER NOT NULL CHECK(response_count >= 0),
    rating_direction TEXT NOT NULL DEFAULT 'unspecified',
    PRIMARY KEY(observation_id,rating_bucket)
);
CREATE TABLE business_monthly (
    dealer_code TEXT NOT NULL REFERENCES dealerships, month TEXT NOT NULL,
    department TEXT NOT NULL CHECK(department IN ('Sales','Service','Parts')),
    activity_count INTEGER NOT NULL CHECK(activity_count >= 0),
    revenue_cents INTEGER NOT NULL CHECK(revenue_cents >= 0),
    source_id TEXT NOT NULL REFERENCES source_files, source_row INTEGER NOT NULL,
    raw_fields_json TEXT NOT NULL,
    PRIMARY KEY(dealer_code,month,department)
);
CREATE TABLE quality_issues (
    issue_id TEXT PRIMARY KEY, source_id TEXT NOT NULL REFERENCES source_files,
    observation_id TEXT REFERENCES source_observations,
    sheet TEXT, source_row INTEGER, severity TEXT NOT NULL,
    rule_id TEXT NOT NULL, message TEXT NOT NULL, disposition TEXT NOT NULL
);
CREATE INDEX observations_event ON source_observations(event_id);
CREATE INDEX events_scope ON feedback_events(dealer_code,department,feedback_date);

CREATE VIEW event_counts AS
SELECT dealer_code,department,substr(feedback_date,1,7) AS month,
       COUNT(*) AS event_count, SUM(rating_valid) AS valid_rating_count,
       SUM(has_text) AS text_response_count
FROM feedback_events
WHERE time_eligible=1 AND department IS NOT NULL
GROUP BY dealer_code,department,substr(feedback_date,1,7);

CREATE VIEW native_rating_distribution AS
SELECT dealer_code,department,rating_scale_max,rating_direction,rating_value,
       rating_oriented,COUNT(*) AS response_count
FROM feedback_events WHERE rating_valid=1
GROUP BY dealer_code,department,rating_scale_max,rating_direction,rating_value,rating_oriented;

CREATE VIEW business_context AS
WITH a AS (
    SELECT dealer_code,month,department,SUM(response_count) AS aggregate_response_count
    FROM rating_aggregates GROUP BY dealer_code,month,department
)
SELECT b.*, e.event_count, e.valid_rating_count, e.text_response_count,
       a.aggregate_response_count,
       CASE WHEN e.event_count IS NOT NULL AND a.aggregate_response_count IS NOT NULL
                 THEN 'individual_and_aggregate_loaded'
            WHEN e.event_count IS NOT NULL THEN 'individual_feedback_loaded'
            WHEN a.aggregate_response_count IS NOT NULL THEN 'aggregate_only'
            ELSE 'no_eligible_pilot_feedback' END AS pilot_feedback_status
FROM business_monthly b
LEFT JOIN event_counts e USING(dealer_code,month,department)
LEFT JOIN a USING(dealer_code,month,department);
