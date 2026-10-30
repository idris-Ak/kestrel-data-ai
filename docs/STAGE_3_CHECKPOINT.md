# Stage 3 — AI pilot checkpoint

**30 October 2026, 15:10 Melbourne time · Tooling built and tested · Waiting on: your 20 calibration labels and an API key**

## Where it stands

Stages 1–2 are complete and committed (`4773197`). Stage 3 planning and the input audit were done earlier, in ChatGPT; this session built the pilot tooling on that plan. The [plan](STAGE_3_AI_PILOT.md) records your decisions: redacted text may leave the machine, several models get compared, about 120 human labels, and a US$10 cap. No paid model calls have been made.

**Built and tested (120/120 tests pass, 21 new):**

| Piece | What it does |
|---|---|
| Frozen splits | `pilot-sample` verifies the export hash (`4f1db5d6…`), then draws **100 test** comments by simple random sampling *first*, then **20 calibration** (Service 12, Sales 4, Parts 2, unresolved 2), then **80 design**. Seed `20261030`. The manifest stores IDs and hashes only and refuses to be redrawn. |
| Theme list | [`ai_pilot_taxonomy.json`](../kestrel/ai_pilot_taxonomy.json): 11 themes plus overall sentiment, drafted from the 80 design comments only. Test and calibration text has not been read. |
| Labelling page | `pilot-sheet` writes a self-contained offline page (no network, comment + department only, no ratings or predictions). It autosaves in your browser and exports JSON. `pilot-import` validates the export against the frozen split before accepting it. |
| Classifier | [`classifier.py`](../kestrel/classifier.py): one comment per request, no tools, the comment wrapped as data. Each output must use allowed labels and quote its evidence verbatim from the comment, or it is retried once and then recorded as a failure. Adapters for Claude (Anthropic SDK) and OpenAI (Responses API, `store=False`). Results are cached per prompt/model fingerprint, so reruns resume without repaying. |
| Spending stop | Every call reserves its worst-case cost against the US$10 ledger before it is sent. |
| Scoring | `pilot-score` scores overall accuracy (Wilson 95% CI), negative-theme and theme+sentiment micro-F1 (bootstrap CI), per-theme precision/recall/support, failures, cost and latency. Failures count as misses. It makes no model calls. |
| Test guard | The test split cannot be run until `pilot-freeze` records the configurations and selection rule. A config whose prompt or settings changed after freezing is refused. |

The design-set keyword baseline works but is weak, as expected; it is the floor the models must beat.

## Calibration results (30 October, 15:40)

The user chose not to hand-label. The 20 calibration labels came from a separate Claude session working blind: it read only the guide and those 20 comments, with no ratings or model output. These are **AI reference labels, not human ones**. Because the labelling session ran on the same model as Opus 5.5, Opus's agreement with them is likely inflated.

| Config | Overall accuracy | Negative-theme F1 | Cost per 1,000 comments |
|---|---:|---:|---:|
| Keyword baseline | 0.25 | 0.00 | US$0 |
| Haiku 5.5 (effort low) | 1.00 | 0.97 | US$0.24 |
| Sonnet 5.5 (effort low) | 1.00 | 0.96 | US$4.75 |
| Opus 5.5 (effort low) | 1.00 | 1.00 | US$9.51 |

What changed during calibration:
- **Guide revision (themes-2).** Before it, all three models added "explanation" on top of billing and call-back complaints. Four boundary rules were added; the label space did not change.
- **Validator change.** It now merges a theme quoted twice with the same sentiment, which caused Haiku's two failures, and still rejects opposite sentiments. Raw outputs of failed calls are kept locally for analysis.

These scores are optimistic: the guide was tuned on the same 20 comments, and 20 cannot separate the models (intervals overlap). The test split decides. Spend so far: **US$0.56** of US$10.

## What you need to do

1. **Label the 20 calibration comments** (about 10–15 minutes). Open this page in your browser and press *Export labels* when done:
   `outputs/ai_pilot/labelling/calibration.html`
2. **Import the file it downloads:**
   ```bash
   uv run --locked python -m kestrel pilot-import --file ~/Downloads/kestrel_labels_calibration.json
   ```
3. **Set an API key in your shell** before asking me to run models. `ANTHROPIC_API_KEY` covers Haiku, Sonnet and Opus; add `OPENAI_API_KEY` to include GPT-6 Luna.

## What happens next

1. Run all configurations on the 20 calibration comments (about US$0.20–0.50) and compare them against your labels. Look for definition problems; adjust the theme list or prompt once if needed. A theme change regenerates the test page before you start it.
2. Confirm the acceptance targets with you, then `pilot-freeze` the comparison.
3. You label the 100 test comments (about 45–60 minutes); import them.
4. Run the frozen configurations on the test split once; `pilot-score` applies the rule and writes `outputs/ai_pilot/scorecard_test.md`.
5. Report the selection, errors, cost per 1,000 comments and the projected full-run cost, then ask for go-ahead on stage 4 (classifying all 4,802).

## Known limits

- One human reviewer; no second-person agreement check unless someone else labels the 50-comment subset.
- 100 test comments cannot validate rare themes or per-dealership accuracy; the scorecard shows support so thin results are visible.
- Results apply to the 4,802 screened comments. The 547 withheld comments (40% of Ipswich's, 37% of Essendon's) are not classified.
- The theme list came from 80 comments; "Other opinion" flags from your labelling show what it misses.

**Frozen input:** `outputs/prepared/runs/ec6f5be3bf88fff169456310a93d249704fab9b3553b9611833d522b7f6b3b3f/`. Pilot outputs (`outputs/ai_pilot/`) are ignored by Git because they hold redacted comment text.
