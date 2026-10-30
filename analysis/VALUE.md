# Where to focus first, and roughly what it is worth

Value workstream, 30 Oct 2026. All figures are **annual revenue at risk** (one year of lost customer spend) in AUD, not profit. Ranges: the *base* case, with *P10–P90* from 4,000 Monte Carlo draws over the assumptions. Aggregates only; no customer text. Outputs: [`results/value/`](../results/value/); assumptions and sources: [assumptions.md](assumptions.md).

## Findings (for the Head of Customer Experience)

- **Service is the priority, and it is a group-wide problem, not a few bad dealers.** Service has the highest negative rate (27.3% of 4,867 rated responses, vs Sales 10.1% and Parts 16.1%) and 198k jobs a year. Real dealer-to-dealer spread is small (about 2.8 points SD after removing noise). So the lever is a group-wide Service fix: **each 1-point cut in Service negatives across the group ≈ A$185k revenue (≈ A$100k gross profit) a year**. A 5-point cut (27% → 22%) ≈ A$0.9m revenue (≈ A$0.5m GP), more than closing every dealer gap below.
- **Two Service outliers to start with: Parramatta (NSW01) and Dandenong (VIC01).** Both are clearly above the group median (36.3% and 34.5% negative; lower 95% bounds 31.2% and 29.5%, above the 27.1% target). Closing to median is worth **A$59k (A$40–91k)** and **A$48k (A$32–73k)** a year. They are the largest gross-profit items on the list (≈ A$33k and A$26k).
- **Three Sales outliers: Southport (QLD04), Box Hill (VIC05) and Liverpool (NSW04).** Negative rates are 22.1%, 20.8% and 17.5% vs a 10.2% median, all clearly above it. They are worth **A$58k (A$41–89k)**, **A$54k (A$38–82k)** and **A$39k (A$28–59k)** in revenue. Thin new-vehicle margins make that only about A$3–5k gross profit each. Their value grows if lost buyers also take their servicing with them, which is not counted here.
- **Total for closing dealer gaps:** to the group median ≈ **A$0.42m/yr (P10–P90 A$0.30–0.64m; ≈ A$0.11m GP)**; to the best quartile ≈ **A$0.89m (A$0.63–1.34m; ≈ A$0.19m GP)**. That is about 0.05–0.1% of A$839m group revenue. These are worthwhile but modest sums: the business case rests on Service scale and gross profit, not on headline revenue.
- **Parts: no dealer-specific action.** Parts dealer differences fit chance (estimated true spread 0), so there is no gap to value. A group-wide 1-point cut is worth about A$34k revenue.

### Ranked focus list (closing to the group median, base; full list in `focus_list.csv`)

| # | Dealer × department | Negative rate (n) | Confidence above median | Revenue at risk, base (P10–P90) | Stretch (best quartile) | Gross profit, base |
|---|---|---|---|---|---|---|
| 1 | Parramatta Service | 36.3% (311) | clear | A$59k (40–91k) | A$69k | A$33k |
| 2 | Southport Sales | 22.1% (68) | clear | A$58k (41–89k) | A$85k | A$5k |
| 3 | Box Hill Sales | 20.8% (77) | clear | A$54k (38–82k) | A$81k | A$4k |
| 4 | Dandenong Service | 34.5% (319) | clear | A$48k (32–73k) | A$58k | A$26k |
| 5 | Liverpool Sales | 17.5% (80) | clear | A$39k (28–59k) | A$66k | A$3k |
| 6 | Penrith Sales | 13.9% (115) | likely | A$37k (26–56k) | A$83k | A$3k |
| 7 | Chermside Sales | 12.8% (109) | likely | A$26k (19–40k) | A$72k | A$2k |
| 8 | Chatswood Sales | 15.2% (66) | likely | A$24k (17–36k) | A$50k | A$2k |

The other 22 cells with value are each under A$14k. Note that Noosa (QLD05, selective collection) and Shepparton (closed) are not ranked.

### By department (`opportunity_department.csv`)

| Department | To median, base (P10–P90) | To best quartile, base | GP to median / best quartile | Per 1-pt group-wide cut (revenue / GP) |
|---|---|---|---|---|
| Service | A$154k (104–236k) | A$255k | A$85k / A$140k | A$185k / A$102k |
| Sales | A$265k (188–401k) | A$632k | A$21k / A$51k | A$184k / A$15k |
| Parts | A$0 (no real dealer differences) | A$0 | 0 / 0 | A$34k / A$8k |
| **All** | **A$419k (297–635k)** | **A$886k** | **A$106k / A$191k** | A$404k / A$125k |

**Decision for the orchestrator:** the ranking depends on whether we rank by revenue (the brief's wording) or by gross profit. By revenue, the Sales and Service outliers interleave. By gross profit, Service leads clearly. We recommend leading with revenue as asked, saying plainly that Service is the profit priority, and presenting the group-wide Service lever alongside the dealer list.

## Method

1. **Activity:** 12-month activity per dealer × department from `business_monthly`. The business data passed every check (`business_checks.csv`): complete 864-row grid, revenue reconciles to A$838,685,990, no per-unit outliers or month jumps. The only zeros are Shepparton's 18 post-closure rows. Revenue per unit is very stable (Service A$394–436/job), so revenue per unit is taken from the data.
2. **Negative rates:** computed with `kestrel/analysis_policy.sql` (bottom-2-box, Wilson CI) and written to `neg_rate_dealer_dept.csv`. This matches the metrics session's file in all 72 cells (`rates_comparison.csv`). The model accepts that file with `--rates` and stops if its cell set or counts differ from the database/policy result. `run_summary.json` records content hashes for supplied rates and theme-share files. This enforces input provenance; it does not change the value assumptions.
3. **Avoid chasing noise:** rank only cells with n ≥ 30. Shrink each rate toward its department mean (empirical-Bayes beta-binomial), so small or noisy cells count for less. Label each cell *clear* (lower 95% bound above target) or *likely* (shrunk rate above target). Targets are the median and best quartile of shrunk rates among ranked cells.
4. **Value chain:** avoidable negatives = activity × (shrunk rate − target) × representativeness (A1). Customers lost = avoidable × P(loss) (A2). Revenue at risk = lost × annual value per customer: Service = revenue/job × visits/yr (A3); Sales = revenue/vehicle ÷ purchase cycle (A4); Parts = revenue/transaction × purchases/yr (A5).
5. **Uncertainty**, in three separate views:
   - Low/base/high corners, with every assumption at its end: total A$33k / A$419k / A$2.25m. These are extreme bounds, because the ends multiply.
   - Monte Carlo P10–P90 over assumptions, using triangular distributions.
   - Rank stability from statistical noise only: `p_top3` and `p_top10` from 4,000 draws of each cell's posterior rate.
6. **One-at-a-time sensitivity** (`sensitivity.csv`, total to median, base A$419k): P(loss) −50% / +75%; representativeness −33% / +33%; gap measure −68% (lower bound) / +75% (raw rates); best-quartile target +112%; 3-year horizon +200%; strict bands −40%; broad bands +72%; dropping the Hunter → Newcastle events (D3) −8%; n ≥ 50 −1%; including Noosa +7%.

## Caveats

- **Respondents are not all customers.** Only 1–10% of transactions leave a rating. The representativeness factor scales the size of the result but not the ranking, *unless* response bias differs by dealer. Collection practices do differ (see Noosa).
- **P(loss) is the weakest link.** Public evidence is mostly stated intent (J.D. Power, PwC), which overstates behaviour. We use one value for every department, because no department-specific evidence was found.
- **Revenue is not profit.** The gross-profit view uses benchmark margins (Deloitte AU top-30% dealers; NADA), not Kestrel's own.
- **Internal benchmarks understate a systemic problem.** If all dealers are poor at something, closing to the median finds little. That is why the per-point Service lever is shown separately.
- **Rank order at the top is uncertain.** Even the leading cells have only about a 50% chance of being in the top 3 under noise alone (`p_top3`). Treat the top five as a set, not as an exact order. Service cells ranked 10th and below have under a 2% chance of entering the top 3.

## What would change the ranking

- **Revenue vs gross profit:** moves the Service outliers above all Sales cells.
- **Value per customer:** with 2 service visits/yr, Dandenong Service moves into the top 3; with a 5-year purchase cycle, Sales leads.
- **Rating band definition:** strict bands (1 only) push Sales up (Southport, Penrith, Box Hill top 3); broad bands (1–3) push Service up (Parramatta, Dandenong, Liverpool Sales).
- **Best-quartile target:** brings Penrith Sales into the top 3.
- **Not affected:** the representativeness factor, P(loss) and the horizon scale every cell equally, so they never change the order.
- **Stage-4 themes:** they do not change the dealer ranking; they identify issues to investigate. See below.

## Splitting each opportunity by theme

`opportunity_theme_ready.csv` holds each ranked cell's value. [`themes.py`](themes.py) writes `results/themes/theme_shares.csv` (fractional: each negative comment counts once, split across its negative themes). Pass `--theme-shares shares.csv` (columns `department,theme,share[,dealer_code,n_negative_text]`, template in `theme_shares_template.csv`) to write `opportunity_by_theme.csv` and `lever_by_theme.csv` (the group-wide per-point lever split by department theme shares):
- Dealer-level shares are used where there are at least 20 negative comments; otherwise department shares.
- Multi-label shares that sum above 1 are normalised to 1, and any shortfall becomes `unassigned`.
- Tested with synthetic shares, including department fallback and unassigned value. The complete theme/value rerun reproduces all 20 generated files byte for byte.
- Assumption: a theme's share of negative comments equals its share of avoidable negatives. Comment coverage differs by dealer (negatives with no text; before rules-3 also withheld text at Ipswich and Essendon), so prefer department-level shares where coverage is thin.
- On the completed labels, Service's one-point lever is allocated A$49,934 revenue / A$27,463 GP to communication, A$42,610 / A$23,435 to timeliness, and A$23,400 / A$12,870 to work quality. These partition the existing Service total; they are prioritisation heuristics, not measured causal savings. Timeliness may lean high because Haiku over-tagged it in evaluation.

## Files and rerun

`value_model.py` (stdlib, read-only DB, under 1 s):

```bash
python3 -I analysis/value_model.py --rates results/metrics/neg_rate_dealer_dept.csv --theme-shares results/themes/theme_shares.csv
```

| File | What it holds |
|---|---|
| `focus_list.csv` | Ranked cells |
| `opportunity_dealer_dept.csv` | All 72 cells: rates, shrinkage, targets, low/base/high and Monte Carlo for both targets, GP, rank stability, exclusion reasons |
| `opportunity_department.csv` | Department totals and per-point levers |
| `sensitivity.csv` | One-at-a-time sensitivity |
| `business_profile.csv`, `business_checks.csv` | Business data profile and checks |
| `neg_rate_dealer_dept.csv`, `rates_comparison.csv` | Rates and comparison with the metrics file |
| `run_summary.json` | Input hashes, parameters, totals |
| `assumptions.md` | Every assumption with its range and source |
