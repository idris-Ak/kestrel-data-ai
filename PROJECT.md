# Kestrel: project record

**28–30 October 2026.** The submission report is [README.md](README.md); requirements remain in the verbatim [assignment brief](docs/BRIEF.md). [REPRO.md](REPRO.md) records verification and the boundary between public aggregates and private inputs.

## Discovery and design, before implementation

1. **Understand the problem:** inconsistent feedback files prevented head office from comparing experience across 24 dealerships.
2. **Define the goal and success:** reconcile the files without losing context; state what can be trusted; measure AI error; answer the business questions with denominators, uncertainty and value assumptions; make the work reproducible.
3. **Inspect and research:** reviewed 52 feedback files and two references, including spreadsheet notes, layouts and source provenance; investigated preparation, privacy, AI interpretation and evaluation methods.
4. **Challenge the proposal:** audited 29 design decisions and tested difficult cases. Review corrected a revenue join and qualified unsupported batching/savings claims.
5. **Choose a bounded design:** explicit readers → traceable SQLite data → quality/privacy checks → evaluated comment classification → aggregate analysis → concise report. A conversational assistant was optional and omitted to keep delivery focused.

The original proposal preferred independent human-reviewed reference examples. The user later chose blind AI reference labels instead; the report discloses that change and its limits. No human annotation or privacy certification is claimed.

## Build checkpoints

Counts below describe their recorded checkpoint, not today's total test suite.

| Stage | Delivered and checked |
|---|---|
| [1. Data foundation pilot](docs/STAGE_1_PILOT.md) | Eight feedback files plus both references; 844 observations → 732 events; 112 version links; 71 aggregate responses separate. **40 checks and 43 tests** passed. |
| [2. Full preparation](docs/STAGE_2_DATA_PREPARATION.md) | All files reconciled: 7,257 observations → 7,073 events, 180 copy links and four test exclusions. Original checkpoint: **118 checks / 99 tests**, 4,802 model candidates and 547 withheld. Later mapping and rules-3 changes: **122 checks**, all 5,349 primary comments eligible. |
| [3. AI pilot](docs/STAGE_3_CHECKPOINT.md) | Frozen development/calibration/test split; 100 blind test examples with two Opus annotator instances and adjudication. Haiku accuracy **0.97**, negative-theme F1 **0.91**; keyword baseline 0.40/0.36. Frozen rule selected Sonnet; user chose Haiku within the US$10 cap (D13). AI references are not human gold. |
| 4. Full classification | **5,342/5,349** successful classifications; seven failures (**0.13%**) accounted for. Cumulative token-priced API ledger **US$3.49**, within the US$10 cap. Conditional rating agreement **4,265/4,285** clear positive/negative pairs. Evidence is validated but stored as hashes/positions; changed request contexts invalidate cached labels. |
| [5. Business analysis](analysis/README.md) | Rating comparisons, fixed-mix trends, negative themes, uncertainty and nine rating-policy sensitivities. Revenue joins reconcile to **A$838,685,990**; value scenarios disclose representativeness, churn and margin assumptions. |
| 6. Optional assistant | Omitted. Saved labels and explicit metric queries answer the required questions directly. |
| [7. Final delivery](README.md) | Original brief moved verbatim; report plus aggregate-only `results/` and analysis code. Clean remote clone of snapshot `630bf81` passed **160 tests**, pilot **40/40** and preparation **122/122** checks. All **36 CSVs** reproduced byte for byte; four JSONs matched numerically apart from expected run-ID/database-hash metadata. All 56 original hashes and the saved classification hashes matched. No API calls were needed. |

## Decisions carried into delivery

- Preserve native values and provenance. Known copies link to one event; uncertain duplicates remain visible.
- Apply higher-is-better and negative bands as explicit analysis policies, with sensitivity checks. Retain explicit reversed legends.
- Map Hunter → Newcastle and Bendigo codes → departments as flagged assumptions; exclude selective Noosa collection from primary comparisons.
- Redact locally; send only allowlisted comments and department context to the external classifier. Numeric ratings stay local.
- Use Haiku as the user's documented budget deviation, with its timeliness over-tagging caveat.
- Report annual revenue-at-risk scenarios alongside indicative gross profit; prioritise group-wide Service and avoid claiming realised savings.
- Reuse saved labels only for matching content and request context. Private labels are hash-pinned; committed results contain aggregates only.

## AI usage and handover

ChatGPT/Codex assisted discovery, initial design and stages 1–2. Claude Code then orchestrated stage 3, privacy/mapping integration, analytical workstreams and the draft report. ChatGPT/Codex resumed orchestration with delegated classification, analysis and reporting workstreams for completion. The final report preserves owner-supplied `TODO(user)` details rather than inventing personal contributions.

Checks caught over-broad surname masking, partial-name leakage, a revenue join dropping months without feedback, and a cache key omitting department changes. Automated tests, source controls and independent calculations verify specific properties; they do not convert AI review into human review or prove the business assumptions.

Documentation follows the problem/goal/checkpoint structure of the [Atlassian Project Poster](https://www.atlassian.com/team-playbook/plays/project-poster), [GOV.UK discovery guidance](https://www.gov.uk/service-manual/agile-delivery/how-the-discovery-phase-works) and [Nygard's decision-record principles](https://cognitect.com/blog/2011/11/15/documenting-architecture-decisions). Earlier discovery files remain in a local archive; the committed fixtures preserve hashes and controls needed for reproduction.
