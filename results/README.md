# Aggregate results

These files contain counts, rates, model evaluation summaries and value scenarios. Customer text,
evidence spans and event IDs are excluded. Run IDs and artifact hashes identify inputs for reproduction.
Methods and commands are in [`analysis/`](../analysis/README.md).

| Folder | Start here | Detail |
|---|---|---|
| `metrics/` | `neg_rate_department.csv`, `movers.csv`, `change_h1_h2_summary.csv` | Ratings, dealer/department comparisons, time series, coverage and sensitivity checks |
| `themes/` | `theme_share_overall.csv`, `theme_share_department.csv`, `theme_change_h1_h2.csv` | Negative themes, uncertainty, coverage and fractional shares for value allocation |
| `value/` | `focus_list.csv`, `opportunity_department.csv`, `lever_by_theme.csv` | Annual revenue-at-risk scenarios, indicative gross profit and sensitivity |
| `ai/` | `classification_summary.json` | Full-run classification coverage, aggregate label counts, rating agreement and metered spend |

The primary rating base excludes selectively collected Noosa feedback and includes Toowoomba's 71
aggregate responses. Theme shares use classified comments on rating-negative responses; aggregate
responses have no text. `themes/coverage.csv` reconciles those denominators. Multi-label theme shares
can sum above 100%; fractional shares count each comment once for the value split.

Quoted rates require at least 30 observations. Small cells retain counts with shares suppressed;
dealer-specific value allocations require 20 negative comments and otherwise use department shares.
Wilson intervals describe sampling uncertainty within the responding/commenting population. They do
not cover selection bias or classification error.

Haiku 5.5 exceeded the recorded pilot targets against AI-generated references, which are not a human
gold standard. It over-tagged negative timeliness in that test (9 true positives and 4 false positives),
so timeliness estimates may lean high. Value allocations are prioritisation heuristics, not measured
causal savings. Do not add allocated theme values to their parent opportunity total.

`run_info.json` and `run_summary.json` pin input hashes and assumptions. Exact AI replay needs the
private saved labels and their classification summary; committed aggregates cannot reconstruct them.
