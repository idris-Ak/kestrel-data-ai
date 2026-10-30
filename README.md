# Kestrel Motor Group: customer feedback

**Prioritise Service across the group, starting at Parramatta and Dandenong.** Service contributes **83% of negative ratings** and offers the strongest gross-profit opportunity. Improve communication, waiting-time commitments and work quality; investigate Sales pressure and handover at Southport, Box Hill and Liverpool.

## Findings

The data cover October 2025–September 2026. The primary comparison contains **7,077 rated responses**, including 71 summary-only responses and excluding Noosa's selective collection. Of these, **1,596 are negative**.

| Department | Negative / rated | Negative rate | Leading negative themes |
|---|---:|---:|---|
| Service | 1,330 / 4,867 | **27.3%** | Communication 34.7%; timeliness 32.2%; work quality 16.6% |
| Sales | 153 / 1,510 | 10.1% | Pressure 27.1%; handover 27.1%; communication 22.9% |
| Parts | 113 / 700 | 16.1% | Timeliness 47.2%; availability 43.4%; communication 31.1% |

Theme percentages use successfully classified negative comments: Service n=1,238, Sales n=144, Parts n=106. Across **1,488 comments**, communication leads (33.3%), followed by timeliness (31.2%) and billing (15.2%). This covers **93.2% of negative responses**; comments can carry several themes. [Theme evidence](results/themes/theme_share_department.csv).

**Dealership differences:** Parramatta has 27% more negatives than expected after department-mix adjustment (95% interval: 9–46% more). Most dealers do not differ clearly from expected rates. Parramatta and Dandenong Service, plus Southport, Box Hill and Liverpool Sales, warrant investigation. Sales site samples are too small for reliable theme proportions.

**Change:** negatives rose from **19.9% in the first six months to 25.0% in the last six**, **+5.1 percentage points** (95% interval: 3.2–7.0). Fixing dealer/department mix gives +5.2 points. Parramatta Service, Dandenong Service and Liverpool Sales explain approximately half the increase. Parts availability and process friction became more common among negative comments. These associations identify investigation priorities, not causes. [Trend evidence](results/metrics/change_h1_h2_summary.csv).

**Value:** a one-point reduction in Service negatives represents approximately **A$185k annual revenue at risk / A$102k gross profit** under the base assumptions. Closing all dealer gaps to department medians represents **A$419k revenue (P10–P90 A$297–635k) / A$106k gross profit**. These overlapping scenarios must not be added. Representativeness, customer loss and benchmark margins are assumptions; the figures are neither measured losses nor guaranteed savings. [Priority list](results/value/focus_list.csv).

## Approach and trust

Python, openpyxl and SQLite keep this small pipeline inspectable and portable. Explicit readers preserve source context and provenance: **52 files → 7,073 individual events**, with 180 proven copies linked and four test rows excluded. Online reviews and aggregate-only ratings remain separate. Validation reconciles counts, original hashes and revenue joins, and checks dates, ratings and privacy boundaries.

Assumptions include higher-is-better where no legend exists, explicit negative bands, Hunter→Newcastle and Bendigo department mappings. Alternative bands and excluded mappings test sensitivity. Findings describe voluntary respondents; collection bias and twelve-month seasonality remain limitations. Standardised templates and invitation tracking would improve future comparisons. [Methods, quality findings and assumptions](docs/METHODS.md).

**AI evaluation:** on 100 untouched test comments, Haiku scored **0.97 sentiment accuracy / 0.91 negative-theme F1**, versus a keyword baseline's 0.40/0.36 and Sonnet's 1.00/0.98. References came from two blind Opus instances and adjudication: **AI references, not human gold**, with shared-family bias. The budget choice was Haiku; broader exploration and additional Sonnet validation were limited by API cost.

**Timeliness leans high:** Haiku found nine reference complaints plus four false positives. Full classification accepted **5,342/5,349 comments**, retaining **seven failures (0.13%)**. The cumulative token-priced API ledger totals **US$3.49**; assistant subscriptions are outside that figure. Only redacted comments reach the model; saved evidence uses hashes/positions. Privacy review was automated/AI, with residual name risk.

## Reproduce

Use Python 3.12 and uv. Clone the repository and place the unchanged `feedback/`, `reference/` and `PS_Data_AI_Assignment.pdf` in its root. The original [brief](docs/BRIEF.md) is included. Exact AI replay also requires the author's private `labels.jsonl` and adjacent `summary.json`; committed results contain aggregates only. Set the path below to the supplied labels. Replay needs no API key; fresh model calls can vary.

```bash
uv sync --locked
uv run --locked python -m unittest discover -s tests
uv run --locked python -m kestrel prepare
uv run --locked python -I analysis/metrics.py
KESTREL_LABELS_PATH=/absolute/path/to/labels.jsonl
uv run --locked python -I analysis/themes.py --labels "$KESTREL_LABELS_PATH"
uv run --locked python -I analysis/value_model.py --rates results/metrics/neg_rate_dealer_dept.csv --theme-shares results/themes/theme_shares.csv
```

Without saved labels, set `ANTHROPIC_API_KEY` in your environment and run `uv run --locked python -m kestrel classify --run outputs/prepared/current` (paid API calls, **US$10 cumulative ledger cap**), then use the printed label path in the analysis commands above; fresh labels can vary.

## AI use

**Claude Code led development**, data foundation/preparation and substantial orchestration. **ChatGPT/Codex supported research, review and final integration/delegation.** Checks caught a revenue join dropping empty-feedback months, excessive name masking and a cache key missing department context. [Project approach](docs/PROJECT.md) explains the work; [methods](docs/METHODS.md) explain verification.
