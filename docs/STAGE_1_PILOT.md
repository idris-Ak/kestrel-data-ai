# Stage 1 — Data foundation pilot

**Implemented and verified; later stages require their own review.**

**What:** import eight selected feedback files and both reference tables into a local, traceable SQLite dataset.

**How:** Python 3.12, pinned openpyxl, explicit source layouts/date/rating rules, preserved raw values, source links and tested SQL. Original files remain unchanged.

**Why:** prove difficult formats can be combined without losing context, double-counting responses or silently changing meaning.

- 844 individual source observations resolve to 732 events; 112 version links remain traceable.
- Six aggregate rows represent 71 responses separately from individual events.
- 24 dealerships and 288 dealership-month records become 864 department-month records.
- Revenue reconciles to AUD 838,685,990 without join multiplication.
- 40 reconciliation checks and 43 tests pass; repeat builds preserve logical records and query results.
- All 56 supplied files match the discovery hashes in `tests/fixtures/original_input_hashes.json`.
- Unspecified rating directions and Noosa's collection bias remain visible.
- No AI classifications or final business recommendations are part of this stage.

## Reproduce locally

Install uv and Python 3.12. Place the original assignment pack's `feedback/`, `reference/` and `PS_Data_AI_Assignment.pdf` beside the unchanged supplied `README.md`. Inputs are deliberately excluded from Git. Integration tests require the complete original pack.

```bash
uv sync --locked
uv run --locked python -m kestrel pilot
uv run --locked python -m unittest discover -s tests -p 'test_pilot.py' -v
```

Outputs: `outputs/pilot/pilot.sqlite` and `outputs/pilot/summary.md`. The generated report includes reconciliation checks and example queries. The database contains raw customer information; keep it local. The discovery ZIP is also local; the versioned hash fixture provides the pilot's independent input check without uploading the archive.

## Commit workflow

- Commit one coherent change with a short explanation of its purpose.
- Run the relevant tests and inspect staged changes before committing.
- Update the project checkpoint when a stage is ready for review.
- Tag reviewed stage snapshots; keep unreviewed work separate.
- Keep source data, exports, databases and credentials out of Git.

The initial stage-one commit is a scoped snapshot prepared from the current working folder. It records the available implementation now; it does not reconstruct or backdate the earlier development history.
