# Stage 2 — Complete data preparation

**30 October 2026 · Implemented; user review pending before stage 3**

The generated local report, `outputs/prepared/current/summary.md`, is the current checkpoint; generated outputs are excluded from Git. Stage 1 is preserved. This stage prepares data and model-input candidates; it makes no theme/sentiment classifications.

## What was built, and why

| Step | Implementation and reason |
|---|---|
| Register | Explicit profiles cover 52 feedback files, 82 worksheet/CSV surfaces and both references. Every populated row is a registered header, context or observation, so unexpected content stops the build. |
| Read | Strict CSV dialects/encodings and source-specific Excel layouts preserve native fields, physical row locations, contextual notes and source hashes. Formulas are never evaluated. |
| Normalise | Schema 2 adds independent rating, text, date and join eligibility. Native scales stay separate; partial dates never acquire invented days. |
| Resolve | Exact matching links 112 Chermside, 43 Penrith, 13 Essendon and 12 Springwood copies. Four identified Southport tests remain as excluded observations. Essendon actions and ambiguous collisions are retained. |
| Protect | Local rules use structured identifiers and text patterns. Only allowlisted, redacted comments that pass automated checks enter a separate JSONL file; unresolved cases are withheld. |
| Publish | Reconcile observations and references, validate the serialized export, then install a complete run and atomically switch `current`. A failed build leaves the previous successful run available. |

## Result and remaining decisions

- **7,257 individual observations → 7,073 individual events**, 180 copy links and four test exclusions. Eight copied reviews and 71 aggregate responses remain separate.
- **4,802 / 5,349 primary text comments (89.8%)** pass automated privacy checks; **547** are withheld. Another 1,724 individual events have no text. These are different denominators.
- Hunter's proposed Newcastle mapping (**303 events**) and Bendigo department codes (**144**) remain candidates, excluded from affected default joins. Six Shepparton dates remain unchanged but unusable for periods. Eight Ipswich entries support month precision; two `Aug?` entries remain uncertain.
- Three ambiguous duplicate groups retain seven events. Native rating directions remain unspecified where no supplied meaning establishes them. Noosa's selective-collection note remains visible.
- Business context preserves **864 department/month scopes and AUD 838,685,990**. Missing eligible feedback stays NULL. Empty responses contribute no analytical counts.

**Evidence:** 118 stored run checks and 99 automated tests pass, including the 42 original pilot regressions and a subsequent pilot path-safety check. Hash-only and count-only fixtures freeze controls from discovery without requiring its archive. Tests compare every file count, each business amount/activity and all 56 original hashes with those independent controls. They also exercise malformed layouts, native scales/dates, copy evidence, privacy leakage and failed publication. Repeat builds produced identical artifacts in the same recorded runtime; all 732 pilot event identifiers survive.

An agent spot-reviewed **67 examples across 50 source files**, including contact redaction, partial names, long comments and withheld cases. Hashes/statuses are preserved in [review fixtures](../tests/fixtures/privacy_review.json). This caught overly broad surname replacement and partial-name leakage, which were corrected and regression-tested. This is targeted agent review, not independent human privacy certification. Conservative triggers also withhold harmless wording, so later analysis must report coverage by source and comment style.

## Run and handoff

```bash
uv run --locked python -m kestrel prepare
uv run --locked python -m unittest discover -s tests -v
```

Integration tests require the unchanged original assignment pack, as described in [stage-one reproduction](STAGE_1_PILOT.md). They do not require the discovery archive or pre-existing generated outputs.

Outputs are under `outputs/prepared/current/`: `prepared.sqlite`, `model_input.jsonl`, `quality_report.json`, `summary.md` and `manifest.json`. Source hashes, input snapshot, schema/parser/redaction/runtime versions and artifact hashes identify the run. Published snapshots live under `outputs/prepared/runs/`; `current` selects one complete snapshot. The pilot command and its outputs are preserved; no new dependency was added.

The database contains raw personal information and remains private. Model JSONL contains only `event_id`, redacted `text`, `department`, `text_sha256`, `redaction_version`, `input_snapshot` and `privacy_status`. The status `automated_pass` is not external-inference approval. No inference API calls are part of this stage.

For the next stage, use event IDs to join locally to provenance and sampling dimensions. Keep copies in one event; group ambiguous candidates and identical text hashes before evaluation splits. Do not give the classifier the raw database or numeric ratings. Source comments remain untrusted content.

**Checkpoint:** review the mapping candidates, counting/eligibility rules, exclusions and privacy coverage before accepting this snapshot and beginning the Stage 3 AI pilot. Its dependent settings remain unfilled until acceptance.
