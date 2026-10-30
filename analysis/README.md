# Analysis

Standard-library scripts over the prepared database (opened read-only). Every script applies [`kestrel/analysis_policy.sql`](../kestrel/analysis_policy.sql) (decisions D1–D5 as TEMP views) and writes aggregate CSVs only to [`results/`](../results/): no comment text, evidence spans or event IDs. `tests/test_analysis.py` checks that.

Run from the repository root after `python -m kestrel prepare` and the stage-4 classification:

```bash
python3 -I analysis/metrics.py
python3 -I analysis/themes.py
python3 -I analysis/value_model.py --rates results/metrics/neg_rate_dealer_dept.csv --theme-shares results/themes/theme_shares.csv
```

| Script | Question | Method notes | Outputs |
|---|---|---|---|
| `metrics.py` | How negative, where, and what changed (ratings) | [METRICS.md](METRICS.md) | `results/metrics/` |
| `themes.py` | Which themes drive negative feedback, where, and how they shifted | below | `results/themes/` |
| `value_model.py` | Where to focus and roughly what it is worth | [VALUE.md](VALUE.md), [assumptions.md](assumptions.md) | `results/value/` |

## `themes.py`

- **Base:** classified comments on rating-negative, comparable responses, Noosa excluded. A theme's share is the proportion of those comments that carry it as a negative theme. Comments can carry several themes, so shares sum above 1. Sensitivity base: comments the model called negative or mixed, whatever the rating.
- Shares are quoted only when n ≥ 30, with Wilson 95% intervals. H1 vs H2 changes use Newcombe intervals, a pooled z-test and Benjamini–Hochberg q-values across all tested rows.
- `per100_h1/h2` estimate theme-negative responses per 100 rated responses (negative rate × share), so a theme's contribution to the rise in negatives can be read directly.
- `theme_shares.csv` feeds `value_model.py`: fractional shares (each negative comment counts once, split across its negative themes), by department and for dealer × department cells with at least 20 negative comments.
- Files: `coverage.csv`, `theme_share_overall.csv`, `theme_share_department.csv`, `theme_share_dealer.csv` (dealer and dealer × department, n ≥ 30), `theme_change_h1_h2.csv` (group, departments, the three movers), `theme_shares.csv`, `run_info.json` (input hashes).
- Caveat (D13): the stage-4 model, Haiku 5.5, over-tags negative timeliness (stage-3 test: 9/9 found plus 4 false positives), so timeliness shares lean high.
