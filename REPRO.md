# Reproducing the submission

**Verification:** TODO(internal): insert the orchestrator's clean-clone results after final integration. The commands below are the intended reproduction path; a new live model run can vary from the saved one.

## Inputs and environment

Clone this private repository with authorised access, then run commands from its root:

```bash
git clone https://github.com/idris-Ak/kestrel-data-ai.git
cd kestrel-data-ai
uv sync --locked
```

Python 3.12 is pinned in `.python-version`; `uv.lock` pins dependencies. Supply the original assignment pack unchanged:

- `feedback/` (52 files);
- `reference/dealerships.csv` and `reference/monthly_revenue.csv`;
- `PS_Data_AI_Assignment.pdf`.

The original brief is already committed verbatim as `docs/BRIEF.md`. The 56 input hashes are checked against `tests/fixtures/original_input_hashes.json`. Inputs, `.env`, generated databases, model inputs and caches are deliberately excluded from Git. Do not add extra files under the supplied data directories.

## Rebuild data and ratings without a model

```bash
uv run --locked python -m unittest discover -s tests -v
uv run --locked python -m kestrel pilot
uv run --locked python -m kestrel prepare
uv run --locked python -I analysis/metrics.py
```

Tests use synthetic/mock model calls; no API key is required. Integration tests require the original pack. Expected foundation counts:

| Build | Expected result |
|---|---|
| Pilot | 844 observations, 732 events, 112 version links; 71 aggregate responses separate; **40/40 checks** |
| Preparation | 7,257 observations, 7,073 events, 180 copy links, four test exclusions; **122/122 checks** |
| Model input | **5,349** redacted comments; zero withheld under rules-3; 1,724 individual events have no text |
| Primary rating analysis | **7,077** eligible ratings (7,006 individual + 71 aggregate), Noosa excluded; **1,596** negative |
| Business reconciliation | 864 department/month rows; **A$838,685,990** revenue |
| Saved classification | **5,342** successful labels and **seven** failed records out of 5,349; cumulative token-priced API ledger **US$3.49** |

`outputs/prepared/current/` points to a complete immutable run containing `prepared.sqlite`, `model_input.jsonl`, `manifest.json`, `quality_report.json` and `summary.md`. Its directory ID includes code/runtime identity, so a rebuild can have a different ID after the brief-path migration or on another runtime. Content hashes establish whether its analytical input matches the saved classification input; never rename a run to imply a different provenance.

## Replay the exact AI aggregates

Exact replay requires the **private saved stage-4 `labels.jsonl` and `summary.json`**, supplied separately by the author. They are deliberately absent from the repository: the committed `results/` contains aggregates only. Keep labels beside their hash-pinning summary under `outputs/classified/5b074a08a2745a111dc5fc931d3183f263c62fc76b39c948e0822457a30b7bad/`.

```bash
kestrel_labels_dir=outputs/classified/5b074a08a2745a111dc5fc931d3183f263c62fc76b39c948e0822457a30b7bad
uv run --locked python -I analysis/themes.py --labels "$kestrel_labels_dir/labels.jsonl" --summary "$kestrel_labels_dir/summary.json"
uv run --locked python -I analysis/value_model.py --rates results/metrics/neg_rate_dealer_dept.csv --theme-shares results/themes/theme_shares.csv
```

The delivered label SHA-256 is `8e65c0fd26ade15c2cbcfe7ea3a9657b6f19a5613063f3c989593e5b7e3c119a`; model-input SHA-256 is `0ccb01b3caba0d7117c783200662b49d14264e6512c6e26995253573c948fef0`. The theme analysis checks the prepared database and model-input hashes against their manifest, the database/run identity, and the saved labels against their summary hash. Matching model-input content permits a changed prepared-run directory ID after migration or a runtime change. The value model reads rating rates and fractional theme shares; no comment text or API is needed.

Rating CSVs and unallocated value scenarios reproduce offline from the supplied pack. Theme CSVs and value allocations by theme reproduce exactly only with the saved private labels. Aggregate metadata may change when a new run has different code/runtime provenance; compare numerical CSV results and the pinned input hashes, not directory names. The analytical scripts write aggregate CSV/JSON only, without comment text, evidence or event IDs.

## Optional new model execution

The delivered run already answers the brief. To execute a new classification instead of replaying its labels:

```bash
uv run --locked python -m kestrel classify --run outputs/prepared/current --configs haiku-5.5
```

New requests require `ANTHROPIC_API_KEY` in the environment or ignored `.env`; never commit a key. Only redacted, automated-pass text and department context go to the model. A local ledger enforces the **US$10 cumulative cap** and matching cached requests are reused without provider calls. Evidence is checked in memory and persisted as references, not quotations. Run the theme/value commands with the new labels and report its actual spend and model variability. Repeating the pilot is a separate evaluation exercise; frozen calibration/test comments should not be inspected while reproducing the final aggregates.

## Where to inspect the evidence

- [Analysis commands and theme definitions](analysis/README.md)
- [Rating metrics and sensitivity methods](analysis/METRICS.md)
- [Value calculations](analysis/VALUE.md) and [assumptions/sources](analysis/assumptions.md)
- [Committed aggregate results](results/)
- [Data preparation record](docs/STAGE_2_DATA_PREPARATION.md) and [AI pilot evaluation](docs/STAGE_3_CHECKPOINT.md)

The raw database and model-input export contain customer information and remain private. Hashes identify artefacts; they do not anonymise a retained database or certify that every unknown name was removed.
