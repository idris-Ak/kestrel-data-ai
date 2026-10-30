# Methods and limitations

## Data foundation

Python 3.12, pinned openpyxl and SQLite provide an inspectable local pipeline without a server.
Source-specific readers consolidate 52 feedback files while preserving native fields, worksheet notes,
physical row locations, date precision and source hashes. Formulas are not evaluated. Original inputs
remain unchanged; all 56 supplied-file hashes are checked. The prepared database separates source
observations, resolved feedback events, rating aggregates, dealership references and monthly business
activity. Independent rating, text, date and join eligibility prevent one unusable field discarding
the rest of a record.

There are 7,257 individual observations and 7,073 resolved events: 180 proven copies are linked and
four identified test rows excluded. Eight copied online reviews and Toowoomba's 71 summary-only
responses remain separate. Copy evidence resolves Chermside versions, Penrith's copied tab, Essendon
cross-department copies and Springwood repeats. Ambiguous collisions remain distinct. Readers handle
Geelong's reversed scale, Ringwood's scale change and Liverpool's US-format dates explicitly. Six
post-closure Shepparton dates and uncertain months cannot enter affected period comparisons; partial
dates never receive invented days.

All 122 preparation checks pass: layouts and inventories, source/event reconciliation, copy evidence,
native scale/date rules, reference joins, business amounts, SQLite integrity, unchanged inputs and
the serialized model-input boundary. All 864 dealership/month/department business rows and
A$838,685,990 revenue reconcile. Feedback is aggregated before joining business activity, preventing
join multiplication. Failed publication preserves the previous complete prepared snapshot.

Local redaction replaces located names and identifiers. All 5,349 text-bearing events pass automated
checks; another 1,724 have no text. Identifier scans and 77 stratified AI-reviewed examples found no
remaining known identifiers. This is not human privacy certification: unknown names can escape.
Only allowlisted redacted text and department context reach the classifier; raw tables and ratings
stay local. Databases, exports, labels and credentials remain private; committed results are aggregates.

## Measurement and uncertainty

Native values remain intact. [`analysis_policy.sql`](../kestrel/analysis_policy.sql) supplies temporary
analysis views. Where direction is unspecified, higher means better; Geelong's explicit reverse legend
takes precedence. Source-level text/rating diagnostics support this assumption but do not prove it;
Toowoomba's text-free buckets require an assumption. Negative means 1–2 on five points, 1–4 on ten,
or “bad” on three labels. Strict and broad alternatives test dependence on these thresholds.

Hunter Motors maps to Newcastle from the reference gap, regional alias and brand match; Bendigo's
S/SV/P codes map to Sales/Service/Parts from source context. Raw aliases and assumption flags remain.
The primary comparison covers October 2025–September 2026, resolved dealership/department and usable
periods. Noosa's selective collection is excluded from comparisons but reported separately. Shepparton
contributes only valid open periods. Toowoomba's 71 responses enter rates as weighted buckets, never
as invented comments. The primary base is 7,077 ratings, including 7,006 individual responses.

Rates require n≥30; n=30–49 is flagged low precision. Wilson 95% intervals describe sampling
uncertainty among respondents. Half-year differences use Newcombe intervals and pooled proportion
tests, with Benjamini–Hochberg correction; monthly trends use Cochran–Armitage tests. Dealer comparisons
adjust for department mix through observed/expected negatives. Half-year comparisons hold pooled
dealership/department weights fixed. Nine sensitivity scenarios vary bands and uncertain-source
inclusions. Response/activity ratios measure coverage, not invitation response rates, and cannot
eliminate selection bias. Twelve months cannot separate seasonality from other changes.

## AI interpretation and evaluation

The task assigns overall sentiment plus any supported themes from an 11-theme vocabulary. Each
request contains one comment as data, with no action tools. Structured outputs must use allowed labels
and evidence occurring in the input after case/whitespace normalization. Bounded retries retain failures
in coverage. Persisted evidence contains hashes and positions instead of quotations. Cache identity
includes the full request context and configuration. Content hashes bind saved labels to the prepared
export; identical inputs can be replayed after code/runtime changes without another API call.

The evaluation separates 80 design, 20 calibration and 100 untouched test comments from the initially
screened population. Two blind Opus 5.5 annotator instances, followed by adjudication, supplied references
without ratings or candidate predictions. Sentiment kappa was 1.00, pooled theme kappa 0.996 and 99/100
annotations matched. These are AI references, not human gold labels; shared-family errors can inflate
agreement. Newly released comments and rare themes have weaker direct evaluation support.

| Method | Sentiment accuracy | Negative-theme F1 |
|---|---:|---:|
| Keyword baseline | 0.40 | 0.36 |
| Haiku 5.5 | 0.97 (0.92–0.99) | 0.91 (0.84–0.97) |
| Sonnet 5.5 | 1.00 | 0.98 |

Intervals use Wilson for accuracy and comment-level bootstrap for F1. Haiku passed the agreed targets
(accuracy≥0.85, F1≥0.75, failures≤2%), with one rejected test output. Although the predeclared selection
rule preferred Sonnet, Haiku was chosen within the US$10 cap. Budget limited broader model validation
and an additional Sonnet audit. Haiku found nine reference timeliness complaints and added four false
positives, so reported timeliness shares may lean high; no universal correction factor is justified.

Full classification accepted 5,342/5,349 results, with seven failures (0.13%). Sentiment matched ratings
in 4,265/4,285 clear positive/negative pairs; this conditional corroboration is not full-run accuracy.
Classification/evaluation API spend totals US$3.49, excluding coding/annotation assistant sessions and subscriptions.
Exploratory Q&A calls are additional metered usage under the same US$10 cumulative ledger cap.
Theme shares use 1,488 classified comments on negative ratings, covering 93.2% of all 1,596 negatives.
Multi-label shares can exceed 100%; small cells retain counts with proportions suppressed.

## Value scenarios

Annual revenue at risk = activity × positive gap above a target negative rate × representativeness
× incremental probability of customer loss × annual customer value. Empirical-Bayes beta-binomial
shrinkage reduces noisy dealer gaps. Targets are department median and best quartile among eligible
open cells; Noosa is excluded. Annual customer value uses revenue/unit times Service visits or Parts
purchases; Sales divides revenue/vehicle by the replacement cycle.

| Assumption | Low / base / high | Evidence and qualification |
|---|---|---|
| Customer/respondent negative-rate ratio | 0.50 / 0.75 / 1.00 | Judgement; voluntary-review bias documented by [Hu et al.](https://aisel.aisnet.org/misq/vol41/iss2/8) |
| Extra probability of customer loss | 0.10 / 0.20 / 0.35 | Judgement discounted from [J.D. Power](https://www.dev.jdpower.com/?p=3218) stated intent; intent differs from behavior ([Mittal & Kamakura](https://doi.org/10.1509/jmkr.38.1.131.18832)) |
| Service visits/customer/year | 1 / 1.5 / 2 | [NRMA servicing guidance](https://www.mynrma.com.au/open-road/advice-and-how-to/car-maintenance/car-servicing-guide), [ABS vehicle use](https://www.abs.gov.au/statistics/industry/tourism-and-transport/survey-motor-vehicle-use-australia/12-months-ended-30-june-2018); repairs allowance is judgement |
| Years between vehicle purchases | 7 / 6 / 5 | Weak editorial anchor: [WhichCar](https://www.whichcar.com.au/advice/when-should-i-replace-my-car) |
| Parts purchases/customer/year | 1 / 2 / 4 | Judgement; no supporting public estimate |
| Gross margin: Sales / Service / Parts | 4/8/11%; 45/55/63%; 20/23/25% | Indicative scenarios informed by [Deloitte benchmarks](https://www.deloitte.com/content/dam/assets-zone1/au/en/docs/industries/2025-dealership-benchmarks.pdf); not Kestrel margins |

The horizon is one year, with three years in sensitivity. Four thousand seeded Monte Carlo draws use
triangular assumptions to show P10–P90 ranges; statistical rank stability is separate. Extreme multiplied
corners are not probability intervals. Gross profit applies benchmark margins to revenue scenarios.
Repeat customers cannot be deduplicated; Sales omits servicing, finance and referrals. No observed
churn or causal return is measured.

Fractional theme allocation counts each negative comment once, split across its negative themes;
theme-less comments stay unassigned. Dealer shares require 20 negative comments, otherwise department
shares apply. This heuristic partitions existing value and cannot demonstrate savings. Dealer-gap and
group-wide improvement scenarios overlap and must not be added. Reproduction commands are in
[`README.md`](../README.md); verification is recorded in [`PROJECT.md`](PROJECT.md).

Aggregate evidence: [ratings, coverage and sensitivity](../results/metrics/), [themes](../results/themes/),
[value scenarios](../results/value/) and [classification coverage/provenance](../results/ai/classification_summary.json).
