# Stage 5: what the ratings say about negative feedback

Ratings only (themes come later, in stage 4). "Negative" means the bottom two boxes on a 5-point scale (1–4 on Ringwood's 10-point scale, "bad" on Tamworth's labels), using [`kestrel/analysis_policy.sql`](../kestrel/analysis_policy.sql). Outputs: [`results/metrics/`](../results/metrics/). Rerun on the rules-3 run (`5b074a08…`): every rating table is byte-identical; only text coverage changed (no comments withheld). Primary set: **7,077 rated responses** (7,006 individual plus 71 Toowoomba aggregate responses), Oct 2025 – Sep 2026, with Noosa excluded. Rates are shown with Wilson 95% intervals, and a rate is quoted only when n ≥ 30.

## Findings for the Head of Customer Experience

**1. Service is the main source of negative feedback.** 27.3% of Service responses are negative (26.1–28.6%), against 16.1% for Parts (13.6–19.1%) and 10.1% for Sales (8.7–11.8%). Service accounts for **83% of all negative responses**. The order Service > Parts > Sales holds in every sensitivity check. Group rate: 22.6%.

**2. Dealerships differ less than the raw league table suggests, with one clear exception.** After adjusting for each dealer's department mix:
- **Parramatta (NSW01) is the only dealer clearly worse than the group.** It has 27% more negatives than its department mix predicts (O/E 1.27, CI 1.09–1.46). It ranks worst in every scenario.
- Wollongong (O/E 0.74) and Springwood (0.78) are clearly better than the group. Tamworth (0.69) is borderline, and it uses a different 3-label scale.
- The 20 dealers in between cannot be told apart, and their order changes under the strict band (Spearman ρ = 0.58). **Don't publish a full dealer league table.**
- The raw table flatters or penalises some dealers through department mix alone. For example, Rockhampton ranks 2nd worst raw but 8th after adjustment, because 83% of its responses are from Service.

**3. Worst and best dealer × department cells (full year; the H2 rate is the current picture):**

| Worst cells | n | Full year | Apr–Sep 2026 |
|---|---|---|---|
| Parramatta Service | 311 | 36.3% (31.2–41.8) | **49.1%** |
| Dandenong Service | 319 | 34.5% (29.5–39.9) | **46.6%** |
| Chatswood Service | 180 | 31.1% (24.8–38.2) | 33.7% |
| Southport Sales | 68 | 22.1% (13.9–33.3), vs 10.1% for Sales overall | |
| Box Hill Sales | 77 | 20.8% (13.2–31.1) | |

- Statistically above their department's rate: Parramatta and Dandenong Service, plus Southport, Box Hill and Liverpool Sales (17.5%).
- Best cells: Essendon Sales 1.3%, Ringwood Sales 3.6%, Wollongong Service 20.4%, Tamworth Service 16.7%.
- Parts cells are mostly n = 30–49, too small to rank with confidence.

**4. States and regions barely differ.** After department adjustment, NSW, QLD and VIC are all within ±4% of the group, and every interval includes 1. NSW Metro is the highest region (O/E 1.10, CI 1.01–1.21), and that is mostly Parramatta and Liverpool. NSW Regional is the lowest (0.84). QLD Regional looks bad on raw numbers (23.5%), but that comes from department mix: it collects almost no Sales feedback (24 responses in a year).

**5. Things got worse over the year, and it is a real change, not a mix shift.**
- **Group:** 19.9% negative in H1 (Oct–Mar) → 25.0% in H2 (Apr–Sep), **+5.1pp (CI +3.2 to +7.0)**. Holding the dealer × department mix fixed gives +5.2pp, so the mix component is about 0. The step appears in April 2026: every H1 month is 17.5–22.3% and every H2 month is 22.7–27.1%.
- **By department:** Service +6.1pp, Sales +4.8pp, Parts flat (−0.3pp).
- **Three cells account for about half the rise.** They pass Benjamini–Hochberg (q < 0.05) and Bonferroni across the 35 cells tested:
  - **Parramatta Service** 23.0% → 49.1% (+26pp). It rises from April and peaks at 63–64% in Jul–Aug. Mean rating fell **4.13 → 3.07** between Oct–Dec 2025 and Jun–Sep 2026 (verified).
  - **Dandenong Service** 20.0% → 46.6% (+27pp). It rises from April–May and peaks at 61% in June.
  - **Liverpool Sales** 2.4% → 34.2% (+32pp). It had no negatives Oct–Feb and climbed from March. The cell is small (n = 42 / 38).
- At dealer level (department-adjusted), Parramatta, Dandenong and Liverpool are robust movers, and Bendigo is suggestive (+17pp, q = 0.06).
- **The rest of the group also drifted up slightly:** +2.7pp (CI +0.7 to +4.8) without the three cells. This part is fragile: it loses significance once all the data-assumption exclusions are combined (+1.9pp, CI −0.4 to +4.1).
- **Not a collection artefact:** responses per 1,000 jobs or vehicles in the three cells barely changed between halves (H2/H1 ratio 0.88–1.20).
- **No dealer improved significantly.** Geelong −7.6pp is not significant.

**6. Coverage caveats for the theme analysis (stage 4).**
- Negative responses are much more likely to carry a comment: **94% of negatives have text vs 70% of non-negatives**, and 85% vs 64% are model-eligible. Themes will therefore over-represent negatives, which suits a drivers analysis. Negatives are 28% of model-eligible comments but 22% of responses.
- *Superseded by rules-3 (D10):* coverage was weakest at Ipswich (55%) and Essendon (67%) because of privacy withholding. With every comment released, 94% of negatives are model-eligible (all of those with text).
- Response volume differs by collection practice, not by satisfaction. Sales gets about 100 responses per 1,000 vehicles, Service about 25 per 1,000 jobs and Parts about 12 per 1,000 transactions. Toowoomba, Rockhampton and Townsville collect Sales feedback at 1/3 to 1/5 of the norm, and Noosa at about 1/4 in every department. So compare rates, never complaint counts.

### Robust vs fragile (`sensitivity.csv`, 9 scenarios × 12 headlines)

| Headline | Holds? |
|---|---|
| Service > Parts > Sales | All scenarios |
| Group rise H1→H2, raw and mix-adjusted | All scenarios (+3.8 to +5.5pp) |
| Service rose; Sales rose | All scenarios |
| Parramatta worst dealer, clearly above group | All scenarios |
| Parramatta Service, Dandenong Service, Liverpool Sales movers | All scenarios (p < 0.05 each) |
| Worst-5 / best-5 cells stable | All scenarios |
| No state difference | All scenarios |
| Full dealer ranking | **Fragile**: ρ = 0.58 under the strict band |
| Rise outside the three movers | **Fragile**: fails with all exclusions combined |
| Sales rise without Liverpool Sales | **Fragile**: +3.2pp, CI −0.2 to +6.6 |

The exclusion scenarios remove Hunter (Newcastle assumed), Toowoomba aggregates, Ringwood 10-point rows and Bendigo departments, separately and together. Noosa is added back in its own scenario. Removing Bendigo's assumed departments removes all of Bendigo.

## Technical notes

- **Run:** `python3 -I analysis/metrics.py [--db PATH] [--policy PATH] [--out DIR] [--expect-individual N] [--expect-aggregate N]`.
  - Standard library only; opens the DB read-only; output is deterministic (verified byte-identical on rerun).
  - `run_info.json` records the DB sha256, run_id and a file index.
- **Reconciliation** (`reconciliation.csv`, raises on failure):
  - 7,055 rated individual + 71 aggregate = 7,126 comparison set = 7,077 primary + 49 Noosa.
  - 7,073 individual events = 7,055 rated + 10 with no valid rating + 8 not comparable (time-ineligible or outside the window). All match `analysis_policy.sql`.
  - Every table's n sums back to its base.
- **Noosa:** excluded from all group, department and region figures as well as rankings, because its selective collection biases them (1 negative in 49). It is still listed in the dealer and dealer × department files.
- **Department adjustment** is indirect standardisation: expected negatives = Σ n_dept × group department rate. The O/E interval is the Wilson interval scaled by n/E (approximate).
- **Mix-adjusted change:** each cell's H1 and H2 rates are weighted by its pooled H1+H2 share, using cells present in both halves (99.4% of responses; Shepparton has H1 only). The variance uses (x+1)/(n+2) rates. `contribution_to_group_change` = weight × cell change, so the contributions sum to the adjusted group change.
- **Tests:**
  - Difference intervals: Newcombe hybrid score.
  - Two-proportion test: pooled z.
  - Monthly trend: Cochran–Armitage.
  - Cells are tested only when n ≥ 30 in both halves (35 cells, about 1.75 false positives expected at p < 0.05). Movers are tiered by BH q; `movers.csv` also includes one nominal-only cell (Bendigo Service).
- **Files:**
  - Rates: `neg_rate_department.csv`, `neg_rate_dealer.csv`, `neg_rate_dealer_dept.csv` (the fixed columns for the value workstream: it includes Noosa and n < 30 cells, so filter n ≥ 30 and drop QLD05), `neg_rate_dealer_dept_detail.csv`, `neg_rate_region_state.csv`.
  - Series: `series_{month,quarter}_{department,dealer}.csv`.
  - Change: `change_h1_h2_dealer_dept.csv`, `change_h1_h2_summary.csv` (including rows without the robust movers), `movers.csv`.
  - Robustness and coverage: `sensitivity.csv`, `text_coverage_{dealer,band,dealer_dept}.csv`, `response_coverage_dealer_dept.csv`.

### Limitations

- Results depend on D1, that higher is better where no legend says otherwise. It is lexicon-tested but still an assumption, especially for Toowoomba's aggregate buckets.
- Scales differ by dealer (Tamworth 3-label; Ringwood switched to 10-point in Feb 2026), so cross-dealer comparisons for those two are approximate. Results survive excluding Ringwood's 10-point rows.
- Feedback is self-selected and collection practices differ, so rates describe the people who responded, not all customers.
- H1/H2 is a single cut. The monthly series confirm the April step, but there are only 12 months, so seasonality cannot be separated out.
- Liverpool Sales and the Parts cells are small. Read Liverpool Sales as a signal to investigate, not a measured size.
- No customer text is used or written: all outputs are aggregates.
