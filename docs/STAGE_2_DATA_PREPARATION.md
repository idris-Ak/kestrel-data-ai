# Stage 2 — Complete data preparation

**30 October 2026 · Implemented and accepted; updated the same day with mapping decisions D3/D4 and redaction rules-3 (D10)**

The generated local report, `outputs/prepared/current/summary.md`, is the current checkpoint; generated outputs are excluded from Git. Stage 1 is preserved. This stage prepares data and model-input candidates; it makes no theme/sentiment classifications.

## What was built, and why

| Step | Implementation and reason |
|---|---|
| Register | Explicit profiles cover 52 feedback files, 82 worksheet/CSV surfaces and both references. Every populated row is a registered header, context or observation, so unexpected content stops the build. |
| Read | Strict CSV dialects/encodings and source-specific Excel layouts preserve native fields, physical row locations, contextual notes and source hashes. Formulas are never evaluated. |
| Normalise | Schema 2 adds independent rating, text, date and join eligibility. Native scales stay separate; partial dates never acquire invented days. |
| Resolve | Exact matching links 112 Chermside, 43 Penrith, 13 Essendon and 12 Springwood copies. Four identified Southport tests remain as excluded observations. Essendon actions and ambiguous collisions are retained. |
| Protect | Local rules use structured identifiers and text patterns (`rules-3`). Residual names that can be located become `[NAME]`; contact, identifier or name signals that remain withhold the comment. Only allowlisted, redacted comments that pass automated checks enter a separate JSONL file. |
| Publish | Reconcile observations and references, validate the serialized export, then install a complete run and atomically switch `current`. A failed build leaves the previous successful run available. |

## Result and remaining decisions

- **7,257 individual observations → 7,073 individual events**, 180 copy links and four test exclusions. Eight copied reviews and 71 aggregate responses remain separate.
- **5,349 / 5,349 primary text comments (100%)** pass automated privacy checks under `rules-3`; none are withheld. Under `rules-2` 4,802 passed (89.8%) and 547 were withheld, skewed towards Ipswich (40% withheld) and Essendon (37%). Another 1,724 individual events have no text. These are different denominators.
- **Assumed mappings, flagged rather than hidden.** The Hunter Motors file (**303 events**) maps to `NSW05` Kestrel Newcastle with `dealer_status='assumed_mapping'` (D3). The 144 Bendigo codes `S`/`SV`/`P` map to Sales/Service/Parts with `department_status='assumed_code'` (D4). Aliases and raw codes are kept, each event carries an `ASSUMED_*` quality finding, and all 447 are now business-join eligible. Business-join eligible individual events: **7,063** (was 6,616).
- Six Shepparton dates remain unchanged but unusable for periods. Eight Ipswich entries support month precision; two `Aug?` entries remain uncertain.
- Three ambiguous duplicate groups retain seven events. Native rating directions remain unspecified where no supplied meaning establishes them. Noosa's selective-collection note remains visible.
- Business context preserves **864 department/month scopes and AUD 838,685,990**. Missing eligible feedback stays NULL. Empty responses contribute no analytical counts.

**Evidence:** 122 stored run checks and 116 automated tests pass (43 pilot, 57 preparation, 16 synthetic `rules-3` redaction tests). Hash-only and count-only fixtures freeze controls from discovery without requiring its archive. Tests compare every file count, each business amount/activity and all 56 original hashes with those independent controls. They also exercise malformed layouts, native scales/dates, copy evidence, privacy leakage and failed publication. Repeat builds produced identical artifacts in the same recorded runtime; all 732 pilot event identifiers survive.

An agent spot-reviewed **67 examples across 50 source files**, including contact redaction, partial names, long comments and previously withheld cases. Hashes/statuses are preserved in [review fixtures](../tests/fixtures/privacy_review.json), now recomputed for `rules-3`. This caught overly broad surname replacement and partial-name leakage, which were corrected and regression-tested. This is targeted agent review, not independent human privacy certification.

## Decisions applied in this run

| Decision | Evidence | Sensitivity |
|---|---|---|
| D3 Hunter Motors → `NSW05` | Workbook title "Kestrel Hunter Motors"; Newcastle is the only reference dealership with no other file; the file spans all 12 months in Newcastle's Hunter region; comments mention exactly the brands Altura, Kodiak and Voltra, and only NSW05 sells that combination (brand mentions match reference brands for every dealer, with zero mismatches). | Exclude `dealer_status='assumed_mapping'`. |
| D4 Bendigo `S`/`SV`/`P` → Sales/Service/Parts | Comment keywords align with each code (SV: 18 service words, 0 sales); the Service share (67%) matches the group pattern. | Exclude `department_status='assumed_code'`. |
| D10 redaction `rules-3` | `rules-2` was reproduced exactly first. All 547 withholdings were name signals, none were contact or identifier residuals. Known-identifier check: 0 hits across 5,349 released texts. A stratified review of 77 items was clean (AI review, not human). The 4,802 `rules-2` passes are byte-identical, so stage-3 labels on them stay valid; 486 newly released texts are unchanged and 61 gain one `[NAME]`. | Report text coverage by dealer. |

Rating direction (D1) and rating bands (D2) stay analysis-time assumptions. The database keeps `rating_direction='unspecified'` and adds no bands. [`kestrel/analysis_policy.sql`](../kestrel/analysis_policy.sql) applies them as TEMP views, exposes `dealer_assumed`/`department_assumed` for the D3/D4 sensitivity checks, and adds the population rules (D5).

**Residual privacy limits:** unknown single first names without a person cue ("Sarah was great") are not detected by either rule set. The ordinary-word lexicon is hand-curated and English-only. Short given names (under 3 letters) are never redacted. Treat 100% as "no automated signal left", not as an anonymity guarantee.

## Run and handoff

```bash
uv run --locked python -m kestrel prepare
uv run --locked python -m unittest discover -s tests -v
```

Integration tests require the unchanged original assignment pack, as described in [stage-one reproduction](STAGE_1_PILOT.md). They do not require the discovery archive or pre-existing generated outputs.

Outputs are under `outputs/prepared/current/`: `prepared.sqlite`, `model_input.jsonl`, `quality_report.json`, `summary.md` and `manifest.json`. Source hashes, input snapshot, schema/parser/redaction/runtime versions and artifact hashes identify the run. Published snapshots live under `outputs/prepared/runs/`; `current` selects one complete snapshot. The pilot command and its outputs are preserved; no new dependency was added.

The database contains raw personal information and remains private. Model JSONL contains only `event_id`, redacted `text`, `department`, `text_sha256`, `redaction_version`, `input_snapshot` and `privacy_status`. The status `automated_pass` is not external-inference approval. No inference API calls are part of this stage.

For the next stage, use event IDs to join locally to provenance and sampling dimensions. Keep copies in one event; group ambiguous candidates and identical text hashes before evaluation splits. Do not give the classifier the raw database or numeric ratings. Source comments remain untrusted content.

**Run lineage:** the stage-3 AI pilot froze its input from the earlier `rules-2` run. This run supersedes it for later stages: stage 4 only needs to classify the 547 events whose `privacy_status` changed from `withheld` to `automated_pass`.
