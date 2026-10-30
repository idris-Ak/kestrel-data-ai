# Stage 3 — AI pilot plan

**30 October 2026 · Resumed 15:00 · Tooling built; awaiting human labels and API key**

Current status is in the [checkpoint](STAGE_3_CHECKPOINT.md). The sections after "Decisions on resume" are the original plan and research, kept for rationale; where they differ, the decisions below apply.

## Decisions on resume (user, 30 October)

| Question | Decision |
|---|---|
| Processing boundary | Redacted, automated-pass comments only (the 4,802-record export) may go to external models, including the coding assistant reading samples to draft themes. Raw data, the 547 withheld comments and ratings stay local. |
| Models | Test several rather than pick one: Claude Haiku 5.5 (user's lead candidate), GPT-6 Luna (if an OpenAI key is supplied), Claude Sonnet 5.5 and Opus 5.5 as higher-capability references, and a keyword baseline. Public research found no head-to-head on this task type, only general benchmarks and one small classification test where Haiku and Luna tied. |
| Human labels | About 120 by the user: 20 calibration + 100 untouched test (instead of 60 + 200). Overall-accuracy intervals are about ±7–10 points; rare themes will have too little support for firm claims, and the scorecard shows support per theme. |
| Budget | US$10 pilot cap, enforced by a local ledger that reserves each call's worst case before sending it. |

**Selection rule, fixed before any test call:** among model configurations with at most 2% failures, choose the cheapest per comment whose negative-theme micro-F1 and overall-sentiment accuracy are each within 0.05 of the best. Proposed acceptance targets: overall accuracy ≥ 0.85, negative-theme micro-F1 ≥ 0.75. The rule is written into `frozen_config.json` before the test split can be run.

**Goal:** determine whether a comment-analysis method is accurate, inspectable and economical enough for stage 4. Deliver reference examples, measured results and a recommendation. Research supports the methods below; it does not establish a winning model or guarantee accuracy on Kestrel's data.

## Upstream review and input contract

The user confirmed stages 1 and 2 complete. Reviewed their reports, schemas and databases, and obtained clarification from the stage-two session. The handoff supplies the technical inputs needed for this plan. Privacy review and human reference labels remain work to perform; the recommendations below replace the earlier requests for unfamiliar reviewer/provider choices.

The [local intake evidence](../outputs/ai_pilot/intake_review.json) records **18 passing read-only checks**: all 56 original hashes and four published artifacts match; generating-code provenance is reconciled; SQLite integrity/relationships pass; all 4,802 exported records align with the database; and all 732 stage-one event IDs survive. The 118 stored preparation checks also passed. This review did not rerun the full automated test suite or certify privacy.

**Version note:** the published run records code fingerprint `68055342…`; later commit `4773197` has fingerprint `835d4acb…`. Reversing its single output-directory symlink guard change in memory reproduces the generating fingerprint exactly. Export/processing logic is unchanged and all four artifact hashes were rechecked. Keep the original run's generation identity; do not relabel it as produced by the later code.

| Required input | Reviewed value | Remaining condition |
|---|---|---|
| Snapshot and schema | Run `ec6f5be3…b3b3f`; input snapshot `6a48c384…772c1fc`; schema 2, parser 2.0.0. Full IDs/hashes are in the intake evidence. | Freeze the immutable run directory, rather than the mutable `current` link. |
| Stable identifier, text and provenance | JSONL `event_id` → `feedback_events.event_id`; `text` → `redacted_text`; provenance through `event_source_history`. | Model input remains the allowlisted JSONL, never the raw database. |
| Eligibility and population | `population='individual' AND model_eligible=1`: **4,802 candidates**. Primary text: **5,349**; withheld: **547**; another **1,724** events have no text. | Screening status is not external-inference approval; report both screening and later classification coverage. |
| Leakage identities | Resolved event ID, `duplicate_candidate_group` and nonblank redacted-text hashes. Current candidates form 4,802 singleton connected groups; no exact repeated redacted hashes. | Use transitive connected groups, not concatenated keys. Near-duplicates/repeated customers are not comprehensively resolved. |
| Redaction and readiness | `rules-2`; agent review of 67 examples. Stage-two session confirms no independent human privacy review or external-inference approval was recorded. | Review a privacy sample and record the chosen processing boundary before external calls. |
| Sampling dimensions and lengths | 50 candidate source files; 23 confirmed dealer codes plus 204 unresolved-dealer candidates; departments and 12 usable months. Text lengths: median 99, p95 206, maximum 490 characters. | Keep unresolved identities separate. Language eligibility is unassessed; channel is missing for 4,691/4,802 candidates. |
| Business workload | Required question families are known: negative themes, department/site variation, period changes and priorities/value scenarios. | Freeze exact pilot requests and counting rules with the guide; native rating bands remain unresolved and are not reference sentiment labels. |

**Changes driven by these outputs:**

- Use the 4,802 screened candidates for the initial pilot; do not quietly include the 547 withheld comments, eight external reviews or aggregate-only ratings. Coverage is 89.8% of primary text and uneven: Ipswich 60%, Essendon 63%. Results cannot automatically represent all feedback.
- Keep the 304 candidates without a valid default business join available for text interpretation. Apply their mapping/time restrictions only to affected comparisons. Do not confirm Hunter/Newcastle or Bendigo departments by assumption.
- Use confirmed department/source/month dimensions for diagnostics, with explicit unknown buckets. Candidate department counts are Service 3,328; Sales 935; Parts 445; unresolved 94. Assess language before making language-support claims; channel cannot support broad stratification at current completeness.

Text eligibility differs from eligibility for rating/time comparisons. The presence of a comment alone does not establish privacy readiness. Enforce input and permission boundaries outside the model. [OWASP guidance](https://cheatsheetseries.owasp.org/cheatsheets/LLM_Prompt_Injection_Prevention_Cheat_Sheet.html).

## Recommended starting choices

These are project-specific proposals, not measured outcomes or spending approval. Use a small Python classifier over the existing JSONL/SQLite handoff: one comment per independent request, multiple theme/sentiment labels and exact supporting quotes. Preserve the text and link derived labels back to it. The later business questions use SQL counts plus checked evidence.

### Human comparison examples

I prepare a local review sheet and plain-language guide. Proposed primary reviewer: the user, or a person comfortable interpreting customer feedback; specialist machine-learning knowledge is unnecessary. Start with **20 calibration examples**, then use measured review time to confirm the remaining workload. Check redaction, meaning loss and language at the same time. A sample review does not certify the entire export anonymous.

Proposed allocation: **60 development comments, including those first 20; 200 untouched random test comments; and up to 40 separate challenge cases**. Draw/reserve the random test first, from all 4,802 candidates, before selecting development examples across departments, sources, months and unresolved groups. Keep derived challenge variants with their parent split and identify synthetic cases. Freeze the actual seed and manifest before use.

Humans label themes, sentiment and evidence **before seeing model predictions or ratings**. A second person should independently label 50 randomly selected test comments where available; retain original labels, record agreement and adjudicate differences without model suggestions. If unavailable, report a single-reviewer reference and its limitation; a second AI is not independent human validation. Showing AI suggestions can bias human labels and inflate evaluation scores. [Annotation experiment](https://aclanthology.org/2025.findings-acl.1323/).

The 200-case test is a practical first pilot, not a research-prescribed minimum: a simple overall binary proportion has roughly **±6.8 percentage points** worst-case 95% sampling error at this population size. Theme/subgroup estimates can be much less precise. Report Wilson intervals for binary measures and explicit support; obtain additional untouched examples or narrow claims for rare themes. This uncertainty excludes reviewer mistakes and withheld-data bias. [NIST sampling guidance](https://itl.nist.gov/div898/handbook/prc/section2/prc241.htm).

### Provider and cost

**Recommend OpenAI's commercial API: `gpt-6-luna` first, with `gpt-6.1-sol` as a higher-capability challenger on the same development examples.** Both document structured outputs. One provider limits integration and account setup; the small model fits a focused extraction task. Choose the least costly configuration that meets the frozen quality criteria. This is not evidence that OpenAI outperforms the alternatives on these comments. [Luna capabilities](https://developers.openai.com/api/docs/models/gpt-6-luna), [Sol capabilities](https://developers.openai.com/api/docs/models/gpt-6.1-sol).

Prices checked **30 October 2026**; USD per million standard, uncached text tokens:

| Candidate | Input / output | Role |
|---|---|---|
| GPT-6 Luna | $0.10 / $0.50 | First candidate. [OpenAI pricing](https://developers.openai.com/api/docs/pricing) |
| GPT-6.1 Sol | $2 / $10 | Quality challenger, not the reference answer. [OpenAI pricing](https://developers.openai.com/api/docs/pricing) |
| Claude Haiku 5.5 | $0.10 / $0.50 for prompts ≤100k | Comparable low-cost alternative if needed; no initial multi-provider build. [Anthropic specifications/pricing](https://platform.claude.com/docs/en/models/haiku-5-5/overview) |
| Gemini 3.5 Flash-Lite | $0.30 / $2.50 | Alternative; use standard paid processing if chosen. [Google pricing](https://ai.google.dev/gemini-api/docs/pricing) |

Use the Responses API with `store=false`, no tools, no shared conversations and no training-data opt-in. Standard abuse-monitoring retention can still include content for up to 30 days, with documented exceptions: this is **not zero retention**. Record actual account access and accepted processing terms before inference. Anthropic also excludes commercial inputs/outputs from training by default; Google's free and contributor tiers have different data-use terms from standard paid processing. [OpenAI data controls](https://developers.openai.com/api/docs/guides/your-data), [Anthropic data use](https://privacy.claude.com/en/articles/7996868-is-my-data-used-for-model-training), [Google tiers](https://ai.google.dev/gemini-api/docs/pricing).

**Proposed pilot inference cap: US$10.** At most two prompt variants × two models × 60 development comments, followed by 200 test + 40 challenge + 10 repeat calls for the selected configuration gives 490 calls before retries. Illustrative assumptions of 1,000–2,000 input tokens (including instructions/schema) and 200–1,000 total billed output tokens per call give an upper scenario around **US$6.32 including 20% extra retry usage**, even if Sol is selected. These are assumptions, not token measurements or a quote. Reasoning tokens count as billed output. Reserve maximum request cost, including in-flight calls, and stop before the cap. [Output billing and limits](https://developers.openai.com/api/docs/guides/reasoning).

Under those same assumptions, one pass over all 4,802 candidates is approximately **US$0.96–4.03 with Luna**, or **US$19.21–80.67 with Sol**; the upper ends include 20% retry usage. Excludes human time, taxes, currency conversion, credit purchases, optional caching/storage and future price changes. Measure actual usage before setting the stage-four cap. Begin with independent synchronous requests; batch discounts are optional later, not necessary to make this pilot affordable.

## Values that still require evidence

| Record | Value | Complete when |
|---|---|---|
| Privacy review outcome, language policy, actual reviewers |  | Guided human review is complete; record availability rather than inventing approval. |
| Final vocabulary, guide, seed/split manifest and semantic acceptance criteria |  | Development/reference work supports definitions and intended use; freeze criteria before model trials. Rare labels cannot pass through absent test support. |
| Provider account, processing-boundary acceptance and trial spending authorisation |  | Actual access and the concrete US$10 proposal are confirmed; no inference is authorised by this document. |
| Selected model/settings, prompt and schema; measured full-run cost/cap |  | Development selects a configuration; freeze before testing. Set stage-four budget from measured usage. |

Technical gates are fixed: every accepted output must have a valid unique input ID, allowed labels and exact source evidence. Reject failures, retain their status and include them in coverage/error reporting. Semantic quality targets are project acceptance choices, not universal thresholds supplied by the literature.

## Sequence, rationale and checkpoints

The technical intake portion of step 1 is complete; its privacy checkpoint and later steps remain pending. At each checkpoint, present the output, check results and unresolved issues for confirmation before continuing.

1. **Accept and freeze the inputs.** Use the reviewed contract above; record the immutable run path, artifact hash, eligibility and redaction versions in the pilot manifest. Complete privacy/language review without modifying the upstream snapshot. Pin exact model-facing text so every candidate receives comparable inputs and evidence quotes can be traced. **Checkpoint:** approved input contract and privacy readiness. This applies the data-derivation principle in [W3C PROV](https://www.w3.org/TR/prov-overview/).

2. **Define the interpretation task and human guide.** Use development comments to define multiple themes and sentiment per theme, supporting quotes, and an uncertain/other route. Human reviewers label without seeing model predictions or numeric ratings; document minimal context they need. Independently review a subset where feasible, clarify inconsistent definitions and retain genuine ambiguity. **Checkpoint:** guide, development reference examples and reviewer arrangement. [Aspect-based sentiment research](https://aclanthology.org/S14-2004/), [annotation disagreement procedure](https://aclanthology.org/2021.humeval-1.15/), [limits of a single reference answer](https://aclanthology.org/2021.bppf-1.3/).

3. **Freeze the evaluation protocol.** Set acceptance criteria and spending limits. Sample from the 4,802 candidates, not every event. Create development examples, an untouched representative test sample and separate challenge cases; keep connected groups and derived variants in one split. Record inclusion probabilities if sampling strata unequally. Human-label the test independently and keep it out of prompt/category tuning. Select sample sizes from desired precision, category support and reviewer capacity. Assess privacy-withheld selection effects locally; they remain outside inference tests. **Checkpoint:** reproducible split manifest, reference labels and scoring policy. [Test leakage and grouped evaluation](https://scikit-learn.org/stable/modules/cross_validation.html), [CheckList behavioural tests](https://aclanthology.org/2020.acl-main.442/), [sampling uncertainty](https://itl.nist.gov/div898/handbook/prc/section2/prc241.htm).

4. **Build the smallest testable runner.** Accept only the frozen inputs; return structured identifiers, themes, sentiment, supporting text and review status. Give the classifier no action tools. Validate IDs, labels, missing/duplicate outputs and exact evidence against redacted inputs. Bound retries, record failures, and cache by input plus model/settings, prompt, guide, schema and redaction versions. **Checkpoint:** fixtures demonstrate correct alignment, rejection and resumability. Schema-valid JSON does not establish semantic truth. [Structured-output limitations](https://ai.google.dev/gemini-api/docs/structured-output), [OWASP boundaries](https://cheatsheetseries.owasp.org/cheatsheets/LLM_Prompt_Injection_Prevention_Cheat_Sheet.html).

5. **Compare methods on development data.** Compare a simple rules baseline with a bounded shortlist of structured-output model configurations on the same task. Start with isolated comments; test shared-comment prompts only as an optimisation, including shuffled order and malicious instructions inside comments. An API batch of independent requests is a different option. Measure quality, variability, retries, actual tokens, cost and runtime; separate fresh-call and cache-replay results. **Checkpoint:** development scorecard and one selected configuration. Batch size affects performance, and shared prompts can permit interference; published results are not predictions for our model. [Batch-prompting research](https://arxiv.org/abs/2301.08721), [batch interference research](https://arxiv.org/abs/2503.15551), [independent API batch example](https://platform.claude.com/docs/en/build-with-claude/batch-processing).

6. **Evaluate the frozen choice.** Run the selected configuration on untouched test data and held-back challenge cases. Report per-theme precision, recall, F1 and support; joint theme/sentiment correctness; evidence validity; failures, abstentions and coverage. Missing required aspects count as misses, rather than disappearing from scoring. Inspect mixed opinions, negation, sarcasm and reported serious concerns; report challenge results separately. Check differences across available source groups and show insufficient support. If failures drive tuning, the exposed test becomes regression material; obtain fresh untouched examples for a new generalisation claim. **Checkpoint:** independent results and error analysis against the predeclared criteria. [Metric definitions](https://scikit-learn.org/stable/modules/generated/sklearn.metrics.classification_report.html), [behavioural testing](https://aclanthology.org/2020.acl-main.442/), [test-set reuse risk](https://scikit-learn.org/stable/modules/cross_validation.html).

7. **Measure the operational case.** Project full-run inference cost from eligible population × representative cost per attempted comment, including retries and weighting strata where needed; show variation, trial costs and human review effort separately. Recheck the selected provider's prices and processing/data-handling terms. Compare saved classifications with on-demand analysis that also caches, using the agreed question workload and equivalent quality requirements. Leave savings blank if that comparison is unavailable. **Checkpoint:** measured cost/runtime evidence, limitations and proposed stage-four budget. This is a project-specific experiment, not a promised saving; [batch documentation](https://platform.claude.com/docs/en/build-with-claude/batch-processing) describes capabilities and limits rather than Kestrel's total cost.

8. **Decide and hand off.** Produce a short scorecard: proceed, revise or stop, with intended scope, known errors and reference/run versions. Record whether the data, quality and budget conditions passed. Do not claim independent validation without human reference review. **Checkpoint:** user confirmation before stage 4. Concise reporting of intended use, evaluation and limitations follows [Model Cards](https://arxiv.org/abs/1810.03993).

## Revisit rule

The reviewed snapshot now replaces the former upstream placeholders. Fill remaining pilot choices before trials. If schema, event resolution, eligibility or redaction changes, assess affected samples, references and caches; rerun affected checks under a new manifest. Weak evidence means more review or narrower claims, not an automatic pass. No model calls or full-corpus classification have been made.
