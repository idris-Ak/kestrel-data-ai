# Handoff notes: final delivery (Claude → ChatGPT)

Branch `Fix/final-delivery-054752`, based on `main` (2649f99). The gitignored pack (`feedback/`, `reference/`, `PS_Data_AI_Assignment.pdf`) and `outputs/` live only in the main folder. Copy the pack in to run the tests; never commit it.

## Done (Part 1)
- **D7:** brief moved word for word to `docs/BRIEF.md` (hash `ace3eee6…` unchanged); `kestrel/pilot.py` `protected_hashes` and `tests/fixtures/original_input_hashes.json` updated. **There is no `README.md` yet**: the report becomes it (see below).
- **`analysis/`:** `metrics.py`, `value_model.py` (repo-relative defaults, read `kestrel/analysis_policy.sql`), new `themes.py`, method notes `METRICS.md`, `VALUE.md`, `assumptions.md`, `README.md` (run order).
- **`results/metrics`, `results/value`:** aggregate-only outputs on run `5b074a08` (rules-3). Rating tables are byte-identical to the earlier workstream run; only text coverage changed (94% of negatives classifiable, none withheld).
- **`themes.py`:** tested on synthetic labels only. It writes theme shares among negative comments (overall, department, dealer and dealer × department, n ≥ 30, Wilson CI), H1 vs H2 changes (group, departments, Parramatta Service, Dandenong Service, Liverpool Sales) and fractional `theme_shares.csv` for `value_model.py --theme-shares`, which writes `opportunity_by_theme.csv` and `lever_by_theme.csv`. It never writes comment text, evidence or event IDs.
- **Docs:** dead links and stale statuses fixed in `PROJECT.md`, `docs/STAGE_1_PILOT.md` and `docs/STAGE_3_AI_PILOT.md`; stale "awaits user confirmation" line removed from `kestrel/__main__.py`.
- **Tests:** `tests/test_analysis.py` added (theme maths; committed results contain no customer text or identifiers). Full suite: **146/146 pass** (`uv run --locked python -m unittest discover -s tests`).

## Left (Part 2)
1. Finish stage 4 (branch `feat/stage-4-classification`; labels at `outputs/classified/<run_id>/labels.jsonl`), merge it to `main`, then merge `main` into this branch.
2. Run, from the repo root, with `--db` pointing to the main folder's `outputs/prepared/current/prepared.sqlite` if needed:
   - `python3 -I analysis/themes.py --labels <labels.jsonl>`
   - `python3 -I analysis/value_model.py --rates results/metrics/neg_rate_dealer_dept.csv --theme-shares results/themes/theme_shares.csv`
3. Turn `outputs/workstreams/report/REPORT_DRAFT.md` (main folder) into `README.md`: about 1,500 words in the main body. Fill every `TODO(results)`: drivers from `results/themes/`, and the AI evaluation from `docs/STAGE_3_CHECKPOINT.md`, including the D13 Haiku deviation and the timeliness over-tagging caveat. Link `analysis/` where the draft says `TODO(integration)`. Keep the `TODO(user)` lines in the AI-usage record visibly marked, and add that the project moved from Claude to ChatGPT for the final phase.
4. Liverpool Sales has fewer than 30 negative comments per half, so its theme shares are suppressed: describe it by counts.
5. Report the actual stage-4 cost (US$2.55 had been spent at 2,267/5,349, above the ≈US$1.30 estimate).
6. Update the header of `docs/STAGE_3_CHECKPOINT.md` ("Next: stage-4 budget decision"), which was left alone to avoid a conflict with the stage-4 branch, and add the stage-4 result to `PROJECT.md`.
7. Verify from a clean clone (tests pass; the analysis reruns), then open a PR to `main`. Don't merge without the user's OK.

Rules: no customer text, `outputs/`, `.env` or the supplied pack in commits. Never read comments in the stage-3 test/calibration splits.
