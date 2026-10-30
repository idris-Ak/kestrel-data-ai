# Stage 3 — AI pilot checkpoint

**30 October 2026 · Pilot complete · Selected: Claude Sonnet 5.5 (meets acceptance targets) · Next: stage-4 budget decision**

## Result

On 100 untouched test comments, Sonnet 5.5 was selected by the rule fixed before testing: the cheapest model within 0.05 of the best on both headline measures. Haiku 5.5 also clears the acceptance targets, at about a twentieth of the cost, but trails by 0.07 on negative-theme F1.

| Config | Overall accuracy | Negative-theme F1 | Theme+sentiment F1 | Failed outputs | Cost per 1,000 comments |
|---|---:|---:|---:|---:|---:|
| Keyword baseline | 0.40 (0.31–0.50) | 0.36 (0.24–0.48) | 0.35 | 0 | US$0 |
| Haiku 5.5, effort low | 0.97 (0.92–0.99) | 0.91 (0.84–0.97) | 0.93 | 1 | US$0.24 |
| **Sonnet 5.5, effort low** | **1.00 (0.96–1.00)** | **0.98 (0.94–1.00)** | **0.98** | 0 | **US$4.80** |
| Opus 5.5, effort low (self-evaluation, not selectable) | 1.00 (0.96–1.00) | 0.97 (0.94–1.00) | 0.98 | 0 | US$9.62 |

Acceptance targets, confirmed by the user before testing: accuracy ≥ 0.85, negative-theme F1 ≥ 0.75, ≤ 2% failed outputs. Brackets show 95% intervals (Wilson for accuracy, comment-level bootstrap for F1).

**Where the models miss:**
- Haiku over-tags waiting-time complaints: 13 predicted against 9 in the reference (F1 0.82). It mislabelled 2 comments as neutral, and 1 output was rejected because its quote wasn't in the comment.
- Sonnet's only misses are on themes with support 0–1, such as sales-pressure praise and vehicle handover.

**Pilot spend:** US$2.03 of the US$10 cap.

## How we know it worked, and the limits

- **The reference labels are AI-generated, not human.** The user chose not to hand-label. Two independent blind Claude Opus 5.5 annotators labelled the test set from the written guide only, never seeing ratings or model outputs. They agreed almost perfectly: overall-sentiment kappa 1.00, pooled theme kappa 0.996, 99/100 comments identical. The one disagreement was adjudicated by the stage-3 session, which saw only that comment and the two annotations.

  Two instances of the same model agreeing shows consistency, not correctness. Opus is therefore excluded from selection, and Sonnet (same model family) may also be flattered.
- **A model-free check backs the labels.** Ratings were never shown to any model. Wherever the customer's rating band was clearly positive (4–5) or negative (1–2) and the model said positive or negative, they agreed:
  - Sonnet: 87/87 (95% CI 0.96–1.00).
  - Haiku: 85/85.

  Comments rated 3 mostly come out mixed or negative. This also supports treating unlabelled scales as higher-is-better.
- **Calibration optimism.** The guide was revised once on the 20 calibration comments (themes-2). Test scores fell from calibration by 0.03–0.06 for Haiku and Opus, and not at all for Sonnet.
- **Scope.** 100 test comments support the headline measures but not rare themes: sales pressure, vehicle handover and price have support of 1–7. Results cover the 4,802 screened comments; the 547 withheld ones are outside this test.

## Decision needed: stage-4 budget

Classifying every comment from the next prepared run means about 5,350 comments: the 4,802 screened, plus the 547 that redaction rules-3 would release.

| Option | Estimated cost | Basis |
|---|---:|---|
| Sonnet 5.5 (selected by the rule) | about US$26 | test-run usage, US$0.0048 per comment |
| Haiku 5.5 (meets targets; 0.07 lower negative-theme F1) | about US$1.30 | test-run usage, US$0.00024 per comment |

The pilot's US$10 cap doesn't cover the Sonnet run. The rule picks Sonnet; spending above the cap is the user's call.

**Decision (user, 30 October): Haiku 5.5 for the full run.** This is a deliberate, documented deviation from the predeclared rule, for budget reasons. Rationale:
- Haiku meets every acceptance target.
- Its gap to Sonnet is mostly one measured error: on the test it found all 9 waiting-time complaints and added 4 false ones. Its other themes are close to Sonnet's.
- The business questions compare themes, sites, departments and periods, where a consistent over-count matters less than in absolute shares.
- It agreed with customers' rating bands in all 85 clear-cut test cases.

The report states the waiting-time over-count wherever that theme's share is quoted. A Sonnet re-check of Haiku's waiting-time tags (about US$4–5) was offered and declined to keep the work lean.

## How it was built (reproducible)

- **Frozen splits.** `pilot-sample` checks the export hash `4f1db5d6…`, then draws 100 test comments first, then 20 calibration and 80 design (seed `20261030`). The manifest holds IDs and hashes only.
- **Theme list.** [`ai_pilot_taxonomy.json`](../kestrel/ai_pilot_taxonomy.json), themes-2: 11 themes and overall sentiment, drafted from the design comments only.
- **Classifier.** [`classifier.py`](../kestrel/classifier.py): one comment per request, no tools, the comment wrapped as data, structured JSON output.
  - Labels must come from the allowed set and evidence must be quoted verbatim. Otherwise the call is retried once, then counted as a failure.
  - Results are cached by prompt and model fingerprint, and a US$10 ledger reserves each call's worst case before it is sent.
- **Test protocol.**
  - `pilot-freeze` recorded the configurations and selection rule before any test call. It was re-frozen once, before any test call, to mark Opus as not selectable; the superseded file is kept.
  - `pilot-agree` / `pilot-adjudicate` build the reference labels.
  - `pilot-score` scores saved results without making calls.
  - `rating_agreement` runs the model-free check.
- **Tests.** 125 automated tests pass (26 for the pilot).

Commands: `uv run --locked python -m kestrel pilot-sample | pilot-sheet | pilot-import | pilot-freeze | pilot-run | pilot-agree | pilot-adjudicate | pilot-score` (see `--help`).

**Frozen input:** `outputs/prepared/runs/ec6f5be3bf88fff169456310a93d249704fab9b3553b9611833d522b7f6b3b3f/`. Pilot outputs live in `outputs/ai_pilot/`, ignored by Git because they hold redacted comment text: scorecards, labels, caches and the spend ledger.

## Stage 4 handoff (30 October)

State at handoff:
- Rebuilt run `5b074a08a2745a111dc5fc931d3183f263c62fc76b39c948e0822457a30b7bad`: D3/D4 mappings plus redaction rules-3, 122/122 checks pass. It holds 5,349 model-eligible comments: the 4,802 from the frozen run, byte-identical, plus the 547 that rules-3 released.
- Haiku 5.5 classification was in progress, with 2,267/5,349 labels cached. Results are cached by comment hash, so rerunning resumes and never re-bills finished comments. Spend: US$2.55 of the US$10 cap; the remainder should cost about US$0.75.

To finish stage 4:
```bash
uv run --locked python -m kestrel classify --run outputs/prepared/runs/5b074a08a2745a111dc5fc931d3183f263c62fc76b39c948e0822457a30b7bad --configs haiku-5.5
```
This verifies the export against the run manifest. It writes `outputs/classified/<run_id>/labels.jsonl` (one row per comment: overall sentiment, themes with verbatim evidence, status) and `summary.json` (counts, cost, and the rating-band check against customers' own ratings). Failed outputs stay recorded as failures. Report coverage, the rating-band agreement, and the waiting-time over-count caveat.
