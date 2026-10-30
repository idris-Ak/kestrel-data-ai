# Kestrel: project record

**Step 01 — Discovery and solution proposal · 28–30 October 2026**

Discovery is documented and stages one and two are complete, as confirmed by the user. Stage-three pilot tooling is built; human labels and model runs are next. Consolidated on 30 October from earlier reviews and discussion. Success criteria were drafted before implementation; AI classification has not run.

## 1. Problem space

**Problem.** Head office receives inconsistent feedback files from 24 dealerships and cannot reliably compare customer experience across sites, departments and time.

**Goal.** Help the Head of Customer Experience understand negative-feedback themes, differences and trends, prioritise improvements, and assess approximate value.

**Scope.** Consolidated data, applied quality rules, evaluated AI comment analysis, business recommendations, reproducible code and a concise report/AI usage record. The [assignment brief](README.md) supplies the requirements. An assistant is optional.

**Draft success criteria, established before solution implementation:**

| Outcome | How it will be checked |
|---|---|
| Trustworthy data | Reconcile source observations; explain exclusions, corrections and unresolved cases. |
| Useful AI interpretation | Measure theme/sentiment errors against independent human-reviewed examples, including difficult cases. |
| Defensible answers | Answer every required question with counts, denominators, evidence and limitations. |
| Reproducibility | Rebuild results from unchanged inputs, versioned rules and saved AI outputs. |

**Candidate measures.** Negative-rating rate under a native-scale policy; negative-theme responses / successfully classified eligible text responses, with classification coverage; comparable-period change; and value scenarios. Rating mappings and AI acceptance thresholds remain open.

## 2. Validation

**Journey completed before implementation:**

1. Reviewed the problem and business questions in the brief.
2. Clarified the goal, deliverables and proposed success measures.
3. Inspected 52 feedback files and two reference tables, including spreadsheet context.
4. Researched preparation, privacy, AI analysis, querying and evaluation; compared implementation approaches.
5. Drafted and challenged the proposal, recording assumptions and required checks.

**Evidence.** Found copied records, rating reversals, date/layout changes, personal information and collection bias. Audited 29 decisions and passed 19 bounded source checks and synthetic counter examples. Original hashes remained unchanged; AI accuracy remains unmeasured.

**AI usage.** AI assisted research, design and verification scripts. Review corrected a revenue-join example and qualified batching/savings suggestions. No production classification, external customer-data upload or independent human labelling has occurred.

**Open questions.** Stage two preserves candidate aliases, uncertain dates and weak duplicates with explicit eligibility. Human privacy review remains a checkpoint before inference. Model, batching, actual cost and label quality need a pilot. Revenue does not establish profit, churn or causal benefit.

## 3. Ready to make it — proposed solution

**Context:** heterogeneous files, short comments and quantitative business questions. **Status:** the data pilot and full preparation are implemented; AI components remain proposed.

| Component | Approach and reason |
|---|---|
| Data foundation | Source-specific readers, common tables and source references preserve meaning while enabling queries. |
| Quality and privacy | Explicit rules, issue records and redacted text expose uncertainty and prepare model inputs. |
| Comment interpretation | Pilot multi-theme sentiment extraction with evidence; preserve comments and reuse labels if evaluation supports it. |
| Analysis and delivery | Tested SQL feeds the business report; an optional assistant uses the same calculations and evidence. |

**Trade-off.** Saved labels add preparation effort; compare with analysis performed when requested that also caches results. Savings are unmeasured. The pilot uses Python 3.12, pinned openpyxl and standard-library CSV/SQLite, with a uv dependency lock.

## Build plan — proposed

Stages one and two are complete. Stage three's pilot tooling is built and tested; it waits on human labels and an API key. Stages four to seven remain pending. Complete one stage, show its output, checks and open issues, then obtain user confirmation before starting the next. Evaluation accompanies each stage.

| Stage | Deliverable | Checkpoint before progressing |
|---|---|---|
| 1. Data foundation pilot | Project setup, working schema and a queryable sample covering ordinary and difficult source formats. | Confirm structure, initial counting rules, source links and sample reconciliation. |
| [2. Complete data preparation](docs/STAGE_2_DATA_PREPARATION.md) | All supplied files ingested; cleaned tables, quality findings and redacted analytical text. | Reconcile all observations; review uncertain mappings, exclusions, rating/date handling and privacy checks. |
| [3. AI pilot](docs/STAGE_3_AI_PILOT.md) | Human-reviewed reference examples, trial classifications and measured error, cost and runtime. | Set acceptance criteria before testing; confirm the approach, model, batching and full-run budget from the evidence. |
| 4. Full comment analysis | Versioned theme/sentiment labels, supporting text, cached results and unresolved cases. | Account for every eligible comment; inspect coverage, errors and supporting evidence. |
| 5. Business analysis | Tested metric queries, answers to the business questions, priorities and value scenarios. | Verify calculations, comparisons, evidence and sensitivity to assumptions. |
| 6. Assistant, if included | A question interface over the same metrics and redacted evidence. | Test known answers, paraphrases, ambiguous requests and unsupported questions; confirm whether to include it. |
| 7. Final delivery | Reproducible solution, concise report and AI usage record. | Rerun from original files and saved annotations; confirm the submission meets the brief. |

Stage 6 can be skipped. Refine later stages as evidence emerges.

## Build stage 1 checkpoint — 30 October 2026

**Status:** complete; stage-two implementation authorised by the user.

- Eight feedback files plus both references produce 844 individual source observations, 732 resolved events and 112 retained version links. Six aggregate rows separately represent 71 responses.
- All 40 reconciliation checks and 43 automated tests pass. Repeat builds preserve logical database contents and query results. All 56 supplied files, including the brief, match their earlier hashes.
- Open policies: seven source/layout findings lack an explicit rating direction; Noosa's selective-collection note remains visible. No negative-rating bands are inferred.
- Generated data remains local and ignored by source control. The pilot database contains raw text; stage two supplies separate redacted candidates, while AI processing remains later work.

Review the [reconciliation report and query examples](outputs/pilot/summary.md), [schema](kestrel/schema.sql) and [database](outputs/pilot/pilot.sqlite).

From this project directory:

```bash
uv run --locked python -m kestrel pilot
uv run --locked python -m unittest discover -s tests -v
```

## Build stage 2 checkpoint — 30 October 2026

**Status:** complete, as confirmed by the user. Human privacy review and inference readiness remain stage-three checkpoints.

- All 52 feedback files and both references reconcile: 7,257 individual observations → 7,073 events, with 180 copy links and four test exclusions. Eight copied reviews and 71 aggregate responses remain separate.
- All 118 stored preparation checks and 99 automated tests pass. All 56 originals and the pilot outputs remain unchanged; failed publication preserves the previous run.
- There are 4,802 redacted model-input candidates and 547 withheld primary comments. Targeted agent privacy review covers 67 examples; automated-pass status is not independent privacy approval.
- Mapping candidates, native rating uncertainty, approximate dates, ambiguous duplicates and collection bias remain visible. No inference API calls or AI classifications have been run.

Review the [concise implementation and handoff](docs/STAGE_2_DATA_PREPARATION.md). The generated local report is `outputs/prepared/current/summary.md`; outputs are excluded from Git. Rebuild with `uv run --locked python -m kestrel prepare`.

## Build stage 3 checkpoint — 30 October 2026

**Status:** pilot tooling built and tested; waiting on human calibration labels and an API key. No paid model calls yet.

Planning and an 18-check input audit were done first (in ChatGPT). On resume the user approved:
- sending redacted text to external models;
- a multi-model comparison;
- about 120 human labels;
- a US$10 cap.

Built so far:
- frozen sample splits (100 test drawn first, 20 calibration, 80 design);
- an 11-theme list drafted from the design comments only;
- an offline labelling page;
- a validated, cached, budget-capped classifier for Claude and OpenAI models, plus a keyword baseline;
- scoring with confidence intervals and a selection rule fixed before testing.

120 automated tests pass.

The [checkpoint](docs/STAGE_3_CHECKPOINT.md) has the next steps; the [plan](docs/STAGE_3_AI_PILOT.md) has the decisions, rationale and sources.

**Documentation basis.** Structure: [Atlassian Project Poster](https://www.atlassian.com/team-playbook/plays/project-poster). Discovery: [GOV.UK guidance](https://www.gov.uk/service-manual/agile-delivery/how-the-discovery-phase-works). Decision status and rationale: [Nygard's ADR principles](https://cognitect.com/blog/2011/11/15/documenting-architecture-decisions). Update evidence and status as work progresses.

Earlier discovery material remains in the local archive, excluded from Git. See [stage-one reproduction and commit workflow](docs/STAGE_1_PILOT.md).
