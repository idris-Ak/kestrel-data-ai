# Kestrel Motor Group: where customer experience needs attention

Across Kestrel's 24 dealerships, the strongest action is a group-wide Service improvement programme, starting at Parramatta and Dandenong. Service supplies **83% of negative ratings**; its scale and margin make it the clearest profit priority.

The original [brief](docs/BRIEF.md) is preserved verbatim. [Reproduction instructions](REPRO.md) distinguish rebuilding data from replaying saved AI results.

## What the business should know

Among **7,077 eligible rated responses** (7,006 individual responses plus 71 summary-only responses; selectively collected Noosa feedback excluded), 1,596 are negative:

| Department | Negative / rated | Negative rate, 95% interval |
|---|---:|---:|
| Service | 1,330 / 4,867 | **27.3% (26.1–28.6%)** |
| Parts | 113 / 700 | 16.1% (13.6–19.1%) |
| Sales | 153 / 1,510 | 10.1% (8.7–11.8%) |

**Reported drivers:** among **1,488 successfully classified comments on negative ratings**, communication leads (**33.3%, 95% interval 31.0–35.8%**), followed by timeliness (**31.2%, 28.9–33.6%**) and billing (**15.2%, 13.5–17.1%**). This covers **93.2% of all 1,596 negative responses**, including summary-only ratings in the denominator. Comments can carry several themes.

- **Service (n=1,238):** communication 34.7%, timeliness 32.2%, work quality 16.6%.
- **Sales (n=144):** sales pressure and handover each 27.1%; communication 22.9%.
- **Parts (n=106):** timeliness 47.2%, parts availability 43.4%, communication 31.1%.

Timeliness and communication lead at both Service hotspots; Dandenong also shows process friction. Sales hotspot comment samples are too small for site-level theme proportions, so the department themes guide investigation. [Theme tables and intervals](results/themes/).

**Location:** after allowing for department mix, Parramatta has 27% more negatives than expected at the group's department rates (95% interval: 9–46% more). Most dealerships do not differ clearly from expected group rates; a league table would exaggerate differences. Five department-level hotspots warrant investigation: Parramatta Service (36.3%, n=311), Dandenong Service (34.5%, n=319), Southport Sales (22.1%, n=68), Box Hill Sales (20.8%, n=77) and Liverpool Sales (17.5%, n=80). Treat these as investigation priorities.

**Time:** negatives increased from **19.9% in October 2025–March 2026 to 25.0% in April–September 2026**, a rise of **5.1 percentage points** (95% interval: 3.2–7.0). Holding dealer/department mix constant gives 5.2 points, so changing mix does not explain the rise. Parramatta Service, Dandenong Service and Liverpool Sales account for approximately half the increase; their changes survive multiple-comparison correction. Service rose most; Parts was approximately flat. Dandenong's recorded booking-system change on 5 May is a useful investigation lead, not evidence of causation.

Parts availability increased from **5.1% to 14.9%** of negative comments and process friction from **6.5% to 11.4%**, surviving multiple-comparison correction. These are reported issues, not established causes of the rating decline. Parramatta has no statistically clear theme-share change after correction; Dandenong's first-half base is only 27. Liverpool Sales has **one then 13 negative comments**, including eight pressure complaints in the second half: counts justify investigation, not precise theme-change estimates.

## Where to act, and roughly what it is worth

1. **Improve Service across the group**, beginning at Parramatta and Dandenong: test clearer updates and waiting-time commitments; investigate work quality, booking friction and billing explanations.
2. **Investigate Sales pressure and handover** at Southport, Box Hill and Liverpool, using the department evidence to structure local review.
3. **Standardise collection:** one template with dealer code, department, explicit rating direction and ISO dates; consistent invitation rules; and transactions plus invitations recorded as coverage denominators. Measure the same indicators monthly before and after changes.

A **one-percentage-point reduction in Service negatives** corresponds to approximately **A$185,000 annual revenue at risk and A$102,000 gross profit** under the base assumptions. A five-point reduction scales that to approximately A$0.93m revenue / A$0.51m gross profit. This illustrates a possible improvement's size; it is not a forecast of recoverable savings.

| Closing a dealership gap to its department median | Annual revenue at risk, base (P10–P90) | Indicative gross profit |
|---|---:|---:|
| Parramatta Service | A$59k (40–91k) | A$33k |
| Dandenong Service | A$48k (32–73k) | A$26k |
| Southport / Box Hill / Liverpool Sales | A$58k / 54k / 39k | A$5k / 4k / 3k |
| All dealer gaps combined | **A$419k (297–635k)** | **A$106k** |

The group-wide Service lever and dealer-gap scenarios overlap and must not be added. Sales' larger transaction values mask thinner margins. The model shrinks noisy rates, uses annual activity and spend, then applies explicit assumptions about representativeness, customer loss and repeat purchases. The weakest input is the extra probability of losing a customer after a negative experience (10/20/35%). These are scenarios, with benchmark margins and assumption ranges, rather than measured churn or causal benefits. [Methods and sources](analysis/VALUE.md), [assumptions](analysis/assumptions.md).

A fractional theme allocation assigns about **A$50k** of the Service one-point lever to communication and **A$43k** to timeliness. It partitions the existing scenario, assuming comment-theme shares represent avoidable negatives; it does not prove that fixing either theme delivers those amounts. [Value allocation](results/value/lever_by_theme.csv).

## A traceable foundation

**52 feedback files become 7,073 individual events**, linked to their physical source rows. Of 7,257 individual observations, 180 proven copies are linked and four identified test rows excluded. Eight copied online reviews remain separate, as do Toowoomba's 71 summary-only ratings. Business data retains all 864 dealership/month/department rows and **A$838,685,990** revenue. Aggregating feedback before joining revenue prevents multiplication.

Source-specific readers preserve spreadsheet context, native ratings, date precision and provenance. Material issues include Chermside's repeated quarter, Penrith's copied June tab (no genuine June), Essendon's cross-department copies, Geelong's reversed scale, Ringwood's scale change, Liverpool's US-format dates and six post-closure Shepparton dates. Uncertain records are flagged or excluded from affected calculations; original files stay unchanged. All **122 stored preparation checks** pass, including reconciliation, source hashes, reference amounts, integrity and the model-input boundary. [Data-quality detail](docs/STAGE_2_DATA_PREPARATION.md).

**Technology:** Python 3.12, a locked environment, pinned openpyxl, standard-library CSV/SQLite and explicit SQL policies. A local database makes joins and provenance inspectable without a server, at the cost of more reader code and limited concurrent writing.

**Working assumptions:** unspecified scales mean higher is better (explicit reversed legends take precedence); negatives are 1–2 of five, 1–4 of ten, or “bad”; Hunter maps to Newcastle; Bendigo's S/SV/P codes map to Sales/Service/Parts. These remain documented assumptions, supported by source/context diagnostics and tested through alternative bands or excluded mappings. Department ordering and the main deterioration survive nine sensitivity scenarios. Noosa is excluded from comparisons because collection is selective; Shepparton contributes only valid open periods. [Metric definitions and sensitivity results](analysis/METRICS.md).

## How the AI analysis was checked

Local redaction produces **5,349 eligible comments**; 1,724 individual events contain no text. Rules-3 releases the 547 comments previously withheld by name signals. Automated identifier scans and 77 stratified AI-reviewed examples found no residual known identifiers. This is **AI review, not human privacy certification**, and unknown names can still escape detection. Only allowlisted redacted text and department context reach the classifier; ratings and the raw database stay local.

One comment is classified per request into multiple themes and sentiment. Evidence is validated against its input; persisted labels retain hashes and positions instead of comment quotations. Cached results are keyed to the full request context. The business analysis queries saved labels and ratings; it does not ask a chatbot to invent totals.

The pilot reserved 100 untouched test comments. Two blind Opus 5.5 annotator instances, followed by adjudication, supplied **AI reference labels, not a human gold standard**. Agreement was high (sentiment kappa 1.00; pooled theme kappa 0.996), but shared-model agreement can share errors.

| Method | Sentiment accuracy | Negative-theme F1 |
|---|---:|---:|
| Keyword baseline | 0.40 | 0.36 |
| **Haiku 5.5** | **0.97 (0.92–0.99)** | **0.91 (0.84–0.97)** |
| Sonnet 5.5 | 1.00 | 0.98 |

The frozen selection rule preferred Sonnet. The user chose **Haiku for the US$10 budget**: it meets the pre-agreed targets (accuracy ≥0.85, F1 ≥0.75, failures ≤2%). It had one rejected test output. **Timeliness is over-tagged:** nine reference complaints were found plus four false positives. Its reported shares therefore lean high; this sample does not establish a correction factor for every site. Rare themes have insufficient test support, and same-family reference labels can flatter both models. [Full evaluation](docs/STAGE_3_CHECKPOINT.md).

Full classification produced **5,342 successful results from 5,349 comments**, with seven failures (0.13%) retained as failures. Sentiment agrees with ratings in **4,265/4,285 clear positive/negative pairs (99.5%)**; that conditional check is not accuracy over every comment. The cumulative token-priced API ledger for pilot and full classification totals **US$3.49**, within the US$10 cap. Coding/annotation assistant sessions and subscriptions are not metered in that ledger. A clean-clone reproduction passed **160 tests** and reproduced all **36 aggregate CSVs** byte for byte. [Verification details](REPRO.md).

## Limits and AI usage

These findings describe **respondents**, whose ratings cover roughly 1–10% of transactions, with uneven collection. Comment themes describe available comments, not every negative experience. Twelve months cannot separate seasonality; association cannot establish causes. Intervals express sampling uncertainty, not all collection, mapping, privacy or model error.

**ChatGPT/Codex** supported discovery, research, the initial design and stages 1–2; **Claude Code** orchestrated the pilot, privacy changes, analysis workstreams and first report draft. **ChatGPT/Codex then took over orchestration and delegated final classification, analysis and reporting.** Checks included source reconciliation, blinded AI comparison, rating-band agreement, sensitivity analysis, tests and reproduction. Review caught a revenue join dropping empty-feedback months, over-broad name redaction, and a cache key missing changed department context; these were corrected. Budget and model choices stayed with the user.

**TODO(user):** confirm exact tools used in the earliest discovery/stages 1–2; add 2–3 representative prompts/interactions, a rejected AI suggestion, and what you personally reviewed or kept outside delegation.

Detailed journey: [PROJECT.md](PROJECT.md). Reproducible methods and aggregate tables: [analysis](analysis/README.md), [results](results/).
