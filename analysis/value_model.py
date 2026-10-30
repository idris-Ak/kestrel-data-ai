#!/usr/bin/env python3
"""Kestrel value model: where should Kestrel focus first, and roughly what is it worth?

Standard library only; opens the prepared database read-only and applies kestrel/analysis_policy.sql.

    python3 -I analysis/value_model.py [--db outputs/prepared/current/prepared.sqlite] \
        [--policy kestrel/analysis_policy.sql] [--out results/value] \
        [--rates results/metrics/neg_rate_dealer_dept.csv] \
        [--theme-shares results/themes/theme_shares.csv] [--draws 4000] [--seed 20261030] [--min-n 30]

Chain per dealer x department cell (all assumptions documented in assumptions.md):
    avoidable negatives = annual activity x max(0, negative rate - target) x representativeness
    customers lost      = avoidable negatives x P(negative experience loses the customer's business)
    revenue at risk     = customers lost x one year of that customer's spend   (revenue, not profit)
"""
import argparse
import csv
import hashlib
import json
import math
import random
import sqlite3
import statistics
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
DEPARTMENTS = ('Sales', 'Service', 'Parts')
SELECTIVE_COLLECTION = {'QLD05'}          # DECISIONS D5: Noosa reported, not ranked
LOW_PRECISION_N = 50                       # D5: n 30-49 flagged low precision
THEME_MIN_N = 20                           # dealer-specific theme shares need >= 20 negative comments
RATES_COLUMNS = ('dealer_code', 'department', 'n', 'negative', 'rate', 'ci_low', 'ci_high')

# (low, base, high). Low/high are the ends that make the result smaller/larger.
ASSUMPTIONS = {
    'representativeness': (0.50, 0.75, 1.00),     # customer negative rate / respondent negative rate
    'p_loss': (0.10, 0.20, 0.35),                 # incremental P(lose next year's business | negative)
    'service_visits_per_year': (1.0, 1.5, 2.0),
    'sales_cycle_years': (7.0, 6.0, 5.0),         # years between vehicle purchases
    'parts_purchases_per_year': (1.0, 2.0, 4.0),
}
GAP_MEASURES = ('ci_low', 'shrunk', 'observed')   # low / base / high
HORIZON_YEARS = 1                                  # headline counts one year of lost spend
HORIZON_ALT = 3                                    # sensitivity: lost customers would have stayed 3 years
GROSS_MARGIN = {'Sales': (0.04, 0.08, 0.11), 'Service': (0.45, 0.55, 0.63), 'Parts': (0.20, 0.23, 0.25)}


def scenario_params(level):
    i = {'low': 0, 'base': 1, 'high': 2}[level]
    p = {k: v[i] for k, v in ASSUMPTIONS.items()}
    p['gap_measure'] = GAP_MEASURES[i]
    p['horizon_years'] = HORIZON_YEARS
    return p


def wilson(k, n, z=1.96):
    if n <= 0:
        return None, None
    p = k / n
    d = 1 + z * z / n
    c = (p + z * z / (2 * n)) / d
    h = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / d
    return max(0.0, c - h), min(1.0, c + h)


def connect(db, policy):
    con = sqlite3.connect(f'file:{Path(db).resolve()}?mode=ro', uri=True)
    con.executescript(Path(policy).read_text())
    return con


# ---------------------------------------------------------------- business data

def load_business(con):
    dealers = {r[0]: {'name': r[1], 'state': r[2], 'status': r[3], 'closed_date': r[4]}
               for r in con.execute('SELECT dealer_code, dealership_name, state, status, closed_date FROM dealerships')}
    monthly = con.execute('SELECT dealer_code, month, department, activity_count, revenue_cents FROM business_monthly').fetchall()
    cells = {}
    for d, m, dep, a, r in monthly:
        c = cells.setdefault((d, dep), {'activity': 0, 'revenue': 0.0, 'months_active': 0, 'months': 0})
        c['activity'] += a
        c['revenue'] += r / 100
        c['months'] += 1
        c['months_active'] += a > 0
    return dealers, monthly, cells


def business_checks(dealers, monthly, cells):
    checks = []
    def add(check, result, detail):
        checks.append({'check': check, 'result': result, 'detail': detail})
    grid = {(d, dep, m) for d, m, dep, _, _ in monthly}
    months = sorted({m for _, m, _, _, _ in monthly})
    add('grid complete', 'pass' if len(grid) == len(dealers) * 3 * len(months) == len(monthly) else 'fail',
        f'{len(monthly)} rows = {len(dealers)} dealers x 3 departments x {len(months)} months ({months[0]}..{months[-1]})')
    total = sum(r for *_, r in monthly) / 100
    add('total revenue (AUD)', 'info', f'{total:,.0f}')
    zero = [(d, m, dep) for d, m, dep, a, r in monthly if a == 0 or r == 0]
    unexplained = [z for z in zero if not (dealers[z[0]]['closed_date'] and z[1] > dealers[z[0]]['closed_date'][:7])]
    add('zero activity/revenue rows', 'pass' if not unexplained else 'fail',
        f'{len(zero)} rows, all after a recorded closure (Shepparton VIC09 closed 2026-03-31)' if not unexplained
        else f'unexplained: {unexplained[:10]}')
    mismatched = [(d, m, dep) for d, m, dep, a, r in monthly if (a == 0) != (r == 0)]
    add('activity and revenue zero together', 'pass' if not mismatched else 'fail', f'{len(mismatched)} mismatches')
    for dep in DEPARTMENTS:
        pu = [(r / 100 / a, d, m) for d, m, dp, a, r in monthly if dp == dep and a > 0]
        vals = [v for v, *_ in pu]
        med = statistics.median(vals)
        mad = statistics.median(abs(v - med) for v in vals) * 1.4826
        out = [(d, m, round(v)) for v, d, m in pu if mad and abs(v - med) > 5 * mad]
        add(f'{dep} revenue per unit outliers (|robust z| > 5)', 'pass' if not out else 'review',
            f'median A${med:,.0f}, range A${min(vals):,.0f}-A${max(vals):,.0f}, {len(out)} outliers {out[:5]}')
    jumps = []
    for (d, dep), _ in cells.items():
        acts = [a for dd, m, dp, a, r in monthly if dd == d and dp == dep and a > 0]
        med = statistics.median(acts)
        jumps += [(d, dep, a) for a in acts if a > 1.6 * med or a < 0.5 * med]
    add('month-to-month activity jumps (>1.6x or <0.5x dealer median)', 'pass' if not jumps else 'review',
        f'{len(jumps)} found {jumps[:5]}')
    return checks


# ---------------------------------------------------------------- negative rates

def compute_rates(con, definition='primary', exclude_assumed_dealer=False):
    """(dealer, department) -> (n, negative), using policy.sql views. Primary equals rated_responses."""
    neg = {'primary': "rating_band = 'negative'", 'strict': 'negative_strict = 1', 'broad': 'negative_broad = 1'}[definition]
    agg_neg = {'primary': 'rating_final <= 2', 'strict': 'rating_final = 1', 'broad': 'rating_final <= 3'}[definition]
    extra = 'AND dealer_assumed = 0' if exclude_assumed_dealer else ''
    rows = con.execute(f"""
        SELECT dealer_final, department_final, SUM(w), SUM(neg) FROM (
          SELECT dealer_final, department_final, 1 AS w, CASE WHEN {neg} THEN 1 ELSE 0 END AS neg
            FROM analysis_events WHERE compare_eligible = 1 AND rating_band IS NOT NULL {extra}
          UNION ALL
          SELECT dealer_final, department_final, response_count, CASE WHEN {agg_neg} THEN response_count ELSE 0 END
            FROM analysis_aggregates)
        GROUP BY 1, 2""").fetchall()
    rates = {(d, dep): (n, k) for d, dep, n, k in rows}
    if definition == 'primary' and not exclude_assumed_dealer:
        check = {(d, dep): (n, k) for d, dep, n, k in con.execute(
            "SELECT dealer_final, department_final, SUM(weight), SUM(CASE WHEN rating_band='negative' THEN weight ELSE 0 END)"
            " FROM rated_responses GROUP BY 1, 2")}
        assert check == rates, 'primary rates differ from policy.sql rated_responses'
    return rates


def read_rates_csv(path):
    with open(path, newline='') as f:
        reader = csv.DictReader(f)
        missing = set(RATES_COLUMNS) - set(reader.fieldnames or [])
        if missing:
            raise SystemExit(f'{path}: missing columns {sorted(missing)}')
        rates = {}
        for row in reader:
            n, k = float(row['n']), float(row['negative'])
            if not 0 <= k <= n:
                raise SystemExit(f'{path}: bad counts in {row}')
            rates[(row['dealer_code'], row['department'])] = (n, k)
    return rates


def write_rates_csv(path, rates):
    rows = []
    for (d, dep), (n, k) in sorted(rates.items(), key=lambda x: (x[0][0], x[0][1])):
        lo, hi = wilson(k, n)
        rows.append({'dealer_code': d, 'department': dep, 'n': fmt_count(n), 'negative': fmt_count(k),
                     'rate': round(k / n, 4), 'ci_low': round(lo, 4), 'ci_high': round(hi, 4)})
    write_csv(path, rows, RATES_COLUMNS)


def fmt_count(x):
    return int(x) if float(x).is_integer() else round(x, 2)


# ---------------------------------------------------------------- cells, shrinkage, targets

def build_cells(dealers, business, rates, min_n, include_selective=False):
    cells = []
    for (d, dep), b in sorted(business.items()):
        n, k = rates.get((d, dep), (0, 0))
        lo, hi = wilson(k, n)
        if dealers[d]['status'] != 'Open':
            reason = 'closed'
        elif d in SELECTIVE_COLLECTION and not include_selective:
            reason = 'selective_collection'
        elif n < min_n:
            reason = f'n<{min_n}'
        elif b['activity'] == 0:
            reason = 'no_activity'
        else:
            reason = ''
        cells.append({'dealer_code': d, 'dealership_name': dealers[d]['name'], 'department': dep,
                      'n': n, 'negative': k, 'rate': k / n if n else None, 'observed': k / n if n else None,
                      'ci_low': lo, 'ci_high': hi,
                      'precision': '' if not n else ('ok' if n >= LOW_PRECISION_N else 'low' if n >= min_n else 'insufficient'),
                      'eligible': reason == '', 'exclusion_reason': reason,
                      'annual_activity': b['activity'] if dealers[d]['status'] == 'Open' else 0,
                      'annual_revenue': b['revenue'],
                      'revenue_per_unit': b['revenue'] / b['activity'] if b['activity'] else None})
    return cells


def shrink(cells, include_selective=False):
    """Empirical-Bayes beta-binomial shrinkage per department (method of moments)."""
    prior = {}
    for dep in DEPARTMENTS:
        pool = [c for c in cells if c['department'] == dep and c['n'] > 0
                and (include_selective or c['dealer_code'] not in SELECTIVE_COLLECTION)]
        N = sum(c['n'] for c in pool)
        m = sum(c['negative'] for c in pool) / N
        S = sum(c['n'] * (c['rate'] - m) ** 2 for c in pool)
        tau2 = (S - (len(pool) - 1) * m * (1 - m)) / (N - sum(c['n'] ** 2 for c in pool) / N)
        M = 1e9 if tau2 <= 0 else max(m * (1 - m) / tau2 - 1, 0.0)
        prior[dep] = {'pooled_rate': m, 'between_cell_sd': math.sqrt(max(tau2, 0)), 'prior_strength': M}
        for c in cells:
            if c['department'] == dep:
                c['shrunk'] = (c['negative'] + m * M) / (c['n'] + M)
                c['post_a'], c['post_b'] = c['negative'] + m * M, c['n'] - c['negative'] + (1 - m) * M
    return prior


def targets(cells, key='shrunk'):
    out = {}
    for dep in DEPARTMENTS:
        vals = [c[key] for c in cells if c['department'] == dep and c['eligible']]
        q1 = statistics.quantiles(vals, n=4, method='inclusive')[0] if len(vals) >= 2 else vals[0]
        out[dep] = {'median': statistics.median(vals), 'best_quartile': q1, 'cells': len(vals)}
    return out


def annual_value(dep, revenue_per_unit, p):
    if dep == 'Service':
        return revenue_per_unit * p['service_visits_per_year']
    if dep == 'Sales':
        return revenue_per_unit / p['sales_cycle_years']
    return revenue_per_unit * p['parts_purchases_per_year']


def cell_value(c, target, p, rate=None):
    """Revenue at risk (AUD/year) and avoidable negatives for one cell."""
    if not c['eligible']:
        return 0.0, 0.0
    r = rate if rate is not None else c[p['gap_measure']]
    gap = max(0.0, r - target)
    avoidable = c['annual_activity'] * gap * p['representativeness']
    rar = avoidable * p['p_loss'] * annual_value(c['department'], c['revenue_per_unit'], p) * p['horizon_years']
    return rar, avoidable


def evaluate(cells, tg, p, target_name):
    return [cell_value(c, tg[c['department']][target_name], p) for c in cells]


def totals(cells, values):
    t = {dep: 0.0 for dep in DEPARTMENTS}
    for c, (v, _) in zip(cells, values):
        t[c['department']] += v
    t['All'] = sum(t.values())
    return t


def top_cells(cells, values, k=3):
    ranked = sorted(((v, c['dealer_code'], c['department']) for c, (v, _) in zip(cells, values) if v > 0), reverse=True)
    return [f'{d} {dep}' for _, d, dep in ranked[:k]]


# ---------------------------------------------------------------- uncertainty

def tri(rng, low, base, high):
    lo, hi = min(low, high), max(low, high)
    return rng.triangular(lo, hi, base)


def assumption_draws(cells, tg, draws, seed):
    """Monte Carlo over assumption values (triangular low/base/high), shrunk gap fixed. Per-cell arrays."""
    rng = random.Random(seed)
    sims = {t: [[0.0] * draws for _ in cells] for t in ('median', 'best_quartile')}
    for i in range(draws):
        p = {k: tri(rng, *v) for k, v in ASSUMPTIONS.items()}
        p.update(gap_measure='shrunk', horizon_years=HORIZON_YEARS)
        for t in sims:
            for j, c in enumerate(cells):
                sims[t][j][i] = cell_value(c, tg[c['department']][t], p)[0]
    return sims


def rank_stability(cells, draws, seed, min_eligible_target='median'):
    """Statistical noise only: draw each cell's true rate from its EB posterior, base assumptions."""
    rng = random.Random(seed + 1)
    p = scenario_params('base')
    top3 = [0] * len(cells)
    top10 = [0] * len(cells)
    above = [0] * len(cells)
    for _ in range(draws):
        drawn = [rng.betavariate(c['post_a'], c['post_b']) if c['n'] > 0 else 0.0 for c in cells]
        tgt = {}
        for dep in DEPARTMENTS:
            vals = [x for x, c in zip(drawn, cells) if c['department'] == dep and c['eligible']]
            tgt[dep] = statistics.median(vals)
        vals = [cell_value(c, tgt[c['department']], p, rate=x)[0] for c, x in zip(cells, drawn)]
        order = sorted(range(len(cells)), key=lambda j: vals[j], reverse=True)
        for r, j in enumerate(order[:10]):
            if vals[j] <= 0:
                break
            top10[j] += 1
            top3[j] += r < 3
        for j, (x, c) in enumerate(zip(drawn, cells)):
            above[j] += c['eligible'] and x > tgt[c['department']]
    return [(a / draws, b / draws, c / draws) for a, b, c in zip(top3, top10, above)]


def pct(xs, q):
    s = sorted(xs)
    return s[min(len(s) - 1, max(0, int(round(q * (len(s) - 1)))))]


# ---------------------------------------------------------------- full run for one configuration

def run_config(dealers, business, rates, min_n, include_selective=False):
    cells = build_cells(dealers, business, rates, min_n, include_selective)
    prior = shrink(cells, include_selective)
    return cells, prior, targets(cells)


def sensitivity(dealers, business, rates, alt_rates, min_n):
    base_cells, _, base_tg = run_config(dealers, business, rates, min_n)
    base_p = scenario_params('base')
    base_vals = evaluate(base_cells, base_tg, base_p, 'median')
    base_tot = totals(base_cells, base_vals)
    base_top = top_cells(base_cells, base_vals)
    rows = []

    def record(assumption, setting, value, cells, tg, p, target='median'):
        vals = evaluate(cells, tg, p, target)
        t = totals(cells, vals)
        top = top_cells(cells, vals)
        rows.append({'assumption': assumption, 'setting': setting, 'value': value,
                     **{f'total_{k}': round(v) for k, v in t.items()},
                     'change_vs_base_pct': round(100 * (t['All'] / base_tot['All'] - 1), 1),
                     'top3': '; '.join(top), 'top3_same_as_base': top == base_top})

    record('base case', 'base', '', base_cells, base_tg, base_p)
    for name, (lo, _, hi) in ASSUMPTIONS.items():
        for setting, v in (('low', lo), ('high', hi)):
            record(name, setting, v, base_cells, base_tg, {**base_p, name: v})
    for setting, gm in (('low', 'ci_low'), ('high', 'observed')):
        record('gap_measure', setting, gm, base_cells, base_tg, {**base_p, 'gap_measure': gm})
    record('target', 'stretch', 'best_quartile', base_cells, base_tg, base_p, target='best_quartile')
    record('horizon_years', 'high', HORIZON_ALT, base_cells, base_tg, {**base_p, 'horizon_years': HORIZON_ALT})
    for label, alt in alt_rates.items():
        cells, _, tg = run_config(dealers, business, alt, min_n)
        record(*label, cells, tg, base_p)
    cells, _, tg = run_config(dealers, business, rates, LOW_PRECISION_N)
    record('min_n', 'stricter', LOW_PRECISION_N, cells, tg, base_p)
    cells, _, tg = run_config(dealers, business, rates, min_n, include_selective=True)
    record('Noosa (D5)', 'include', 'QLD05 ranked', cells, tg, base_p)
    return rows


# ---------------------------------------------------------------- theme split (stage 4 hook)

def read_shares(shares_path):
    dept_sets, dealer_sets, dealer_n = {}, {}, {}
    with open(shares_path, newline='') as f:
        for row in csv.DictReader(f):
            d = (row.get('dealer_code') or '').strip()
            share = float(row['share'])
            if d in ('', '*'):
                dept_sets.setdefault(row['department'], {})[row['theme']] = share
            else:
                dealer_sets.setdefault((d, row['department']), {})[row['theme']] = share
                if row.get('n_negative_text'):
                    dealer_n[(d, row['department'])] = float(row['n_negative_text'])
    return dept_sets, dealer_sets, dealer_n


def normalise(shares):
    s = sum(shares.values())
    return s, ({t: v / s for t, v in shares.items()} if s > 1 else dict(shares, **({'unassigned': 1 - s} if s < 1 else {})))


def lever_split(dept_rows, shares_path):
    """Split each department's group-wide per-point lever by its department-level theme shares."""
    dept_sets = read_shares(shares_path)[0]
    out = []
    for r in dept_rows:
        if r['department'] not in dept_sets:
            continue
        s, used = normalise(dept_sets[r['department']])
        for theme, share in sorted(used.items(), key=lambda kv: -kv[1]):
            out.append({'department': r['department'], 'theme': theme, 'share_used': round(share, 4),
                        'rar_per_1pt_base': round(r['rar_per_1pt_base'] * share),
                        'gp_per_1pt_base': round(r['gp_per_1pt_base'] * share)})
    return out


def theme_split(cells, values, shares_path):
    """Split each cell's opportunity by stage-4 theme shares of negative comments.

    Input columns: department, theme, share, [dealer_code], [n_negative_text]. A dealer-specific share set is
    used when its n_negative_text >= THEME_MIN_N (or n is not given); otherwise the department set. Multi-label
    shares summing above 1 are normalised to 1; a shortfall becomes theme 'unassigned'.
    """
    dept_sets, dealer_sets, dealer_n = read_shares(shares_path)
    out = []
    for c, vals in zip(cells, values):
        if not c['eligible']:
            continue
        key = (c['dealer_code'], c['department'])
        if key in dealer_sets and dealer_n.get(key, THEME_MIN_N) >= THEME_MIN_N:
            shares, level = dealer_sets[key], 'dealer'
        elif c['department'] in dept_sets:
            shares, level = dept_sets[c['department']], 'department'
        else:
            continue
        s, used = normalise(shares)
        for theme, share in sorted(used.items()):
            out.append({'dealer_code': c['dealer_code'], 'department': c['department'], 'theme': theme,
                        'share_level': level, 'raw_share_sum': round(s, 3), 'share_used': round(share, 4),
                        **{k: round(v * share) for k, v in vals.items()}})
    return out


# ---------------------------------------------------------------- output helpers

def write_csv(path, rows, fields=None):
    fields = fields or list(rows[0].keys())
    with open(path, 'w', newline='') as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        w.writerows(rows)


def money(x):
    if x >= 1e6:
        return f'A${x / 1e6:.1f}m'
    if x >= 1e3:
        return f'A${x / 1e3:.0f}k'
    return f'A${x:.0f}'


def r4(x):
    return None if x is None else round(x, 4)


def sha256(path):
    h = hashlib.sha256()
    with open(path, 'rb') as f:
        for chunk in iter(lambda: f.read(1 << 20), b''):
            h.update(chunk)
    return h.hexdigest()


# ---------------------------------------------------------------- main

def main():
    ap = argparse.ArgumentParser(description=__doc__.split('\n')[0])
    ap.add_argument('--db', default=str(REPO / 'outputs/prepared/current/prepared.sqlite'))
    ap.add_argument('--policy', default=str(REPO / 'kestrel/analysis_policy.sql'))
    ap.add_argument('--out', default=str(REPO / 'results/value'))
    ap.add_argument('--rates', help='drop-in rates CSV (dealer_code,department,n,negative,rate,ci_low,ci_high)')
    ap.add_argument('--theme-shares', help='stage-4 theme shares CSV (see theme_split docstring)')
    ap.add_argument('--draws', type=int, default=4000)
    ap.add_argument('--seed', type=int, default=20261030)
    ap.add_argument('--min-n', type=int, default=30)
    a = ap.parse_args()
    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)

    con = connect(a.db, a.policy)
    dealers, monthly, business = load_business(con)
    checks = business_checks(dealers, monthly, business)
    db_rates = compute_rates(con)
    write_rates_csv(out / 'neg_rate_dealer_dept.csv', db_rates)

    rates, rate_source, comparison = db_rates, 'computed from DB with policy.sql', []
    if a.rates:
        rates, rate_source = read_rates_csv(a.rates), Path(a.rates).name
        for key in sorted(set(rates) | set(db_rates)):
            n1, k1 = db_rates.get(key, (0, 0))
            n2, k2 = rates.get(key, (0, 0))
            comparison.append({'dealer_code': key[0], 'department': key[1], 'n_db': n1, 'negative_db': k1,
                               'n_file': n2, 'negative_file': k2, 'match': (n1, k1) == (n2, k2)})
        write_csv(out / 'rates_comparison.csv', comparison)
    if any(k not in business for k in rates):
        print('warning: rates rows without business data ignored:', [k for k in rates if k not in business])

    alt_rates = {('rating bands (D2)', 'strict', 'strict bands'): compute_rates(con, 'strict'),
                 ('rating bands (D2)', 'broad', 'broad bands'): compute_rates(con, 'broad'),
                 ('Hunter file -> NSW05 (D3)', 'exclude', 'assumed-dealer events dropped'): compute_rates(con, exclude_assumed_dealer=True)}
    con.close()

    cells, prior, tg = run_config(dealers, business, rates, a.min_n)
    scen = {(t, lvl): evaluate(cells, tg, scenario_params(lvl), t)
            for t in ('median', 'best_quartile') for lvl in ('low', 'base', 'high')}
    sims = assumption_draws(cells, tg, a.draws, a.seed)
    stab = rank_stability(cells, a.draws, a.seed)

    # business profile
    write_csv(out / 'business_profile.csv', [
        {'dealer_code': c['dealer_code'], 'dealership_name': c['dealership_name'], 'department': c['department'],
         'status': dealers[c['dealer_code']]['status'], 'months_active': business[(c['dealer_code'], c['department'])]['months_active'],
         'activity_12m': business[(c['dealer_code'], c['department'])]['activity'], 'revenue_12m_aud': round(c['annual_revenue']),
         'revenue_per_unit_aud': r4(c['revenue_per_unit']) and round(c['revenue_per_unit'], 2),
         'annual_activity_forward': c['annual_activity'],
         'responses_rated': fmt_count(c['n']),
         'response_coverage': r4(c['n'] / business[(c['dealer_code'], c['department'])]['activity'])
         if business[(c['dealer_code'], c['department'])]['activity'] else None} for c in cells])
    write_csv(out / 'business_checks.csv', checks)

    # cell table
    base_p = scenario_params('base')
    rows = []
    for j, c in enumerate(cells):
        dep = c['department']
        conf = ''
        if c['eligible']:
            t = tg[dep]['median']
            conf = 'clear' if c['ci_low'] > t else 'likely' if c['shrunk'] > t else 'at_or_below_target'
        row = {k: c[k] for k in ('dealer_code', 'dealership_name', 'department')}
        row.update(n=fmt_count(c['n']), negative=fmt_count(c['negative']), rate=r4(c['rate']), ci_low=r4(c['ci_low']),
                   ci_high=r4(c['ci_high']), shrunk_rate=r4(c['shrunk']), precision=c['precision'],
                   eligible=int(c['eligible']), exclusion_reason=c['exclusion_reason'],
                   target_median=r4(tg[dep]['median']), target_best_quartile=r4(tg[dep]['best_quartile']),
                   above_median_confidence=conf, annual_activity=c['annual_activity'],
                   revenue_per_unit_aud=c['revenue_per_unit'] and round(c['revenue_per_unit'], 2),
                   annual_value_per_customer_base=c['revenue_per_unit'] and round(annual_value(dep, c['revenue_per_unit'], base_p)),
                   avoidable_negatives_median_base=round(scen[('median', 'base')][j][1], 1),
                   avoidable_negatives_bq_base=round(scen[('best_quartile', 'base')][j][1], 1))
        for t, short in (('median', 'median'), ('best_quartile', 'bq')):
            for lvl in ('low', 'base', 'high'):
                row[f'rar_{short}_{lvl}'] = round(scen[(t, lvl)][j][0])
            row[f'rar_{short}_mc_p10'] = round(pct(sims[t][j], 0.10))
            row[f'rar_{short}_mc_p90'] = round(pct(sims[t][j], 0.90))
        row['gp_median_base'] = round(scen[('median', 'base')][j][0] * GROSS_MARGIN[dep][1])
        row['gp_bq_base'] = round(scen[('best_quartile', 'base')][j][0] * GROSS_MARGIN[dep][1])
        row['p_top3'], row['p_top10'], row['p_above_median'] = (round(x, 3) for x in stab[j])
        rows.append(row)
    ranked = sorted([r for r in rows if r['eligible'] and (r['rar_median_base'] > 0 or r['rar_bq_base'] > 0)],
                    key=lambda r: (r['rar_median_base'], r['rar_bq_base']), reverse=True)
    for i, r in enumerate(ranked, 1):
        r['rank'] = i
    for r in rows:
        r.setdefault('rank', '')
    write_csv(out / 'opportunity_dealer_dept.csv', rows)

    write_csv(out / 'focus_list.csv', [
        {'rank': r['rank'], 'dealer_code': r['dealer_code'], 'dealership_name': r['dealership_name'],
         'department': r['department'], 'n': r['n'], 'negative_rate': r['rate'], 'ci_low': r['ci_low'], 'ci_high': r['ci_high'],
         'shrunk_rate': r['shrunk_rate'], 'target_median': r['target_median'], 'target_best_quartile': r['target_best_quartile'],
         'confidence_above_median': r['above_median_confidence'], 'p_top3': r['p_top3'],
         'annual_activity': r['annual_activity'], 'avoidable_negatives_base': r['avoidable_negatives_median_base'],
         'rar_median_base': r['rar_median_base'], 'rar_median_range': f"{money(r['rar_median_mc_p10'])}-{money(r['rar_median_mc_p90'])}",
         'rar_bq_base': r['rar_bq_base'], 'rar_bq_range': f"{money(r['rar_bq_mc_p10'])}-{money(r['rar_bq_mc_p90'])}",
         'gp_median_base': r['gp_median_base'], 'gp_bq_base': r['gp_bq_base']} for r in ranked])

    # department table (+ All)
    dept_rows = []
    for dep in DEPARTMENTS + ('All',):
        idx = [j for j, c in enumerate(cells) if dep == 'All' or c['department'] == dep]
        dc = [cells[j] for j in idx]
        row = {'department': dep}
        if dep != 'All':
            pool = [c for c in dc if c['dealer_code'] not in SELECTIVE_COLLECTION and c['n'] > 0]
            row.update(pooled_negative_rate=r4(prior[dep]['pooled_rate']), between_cell_sd=r4(prior[dep]['between_cell_sd']),
                       n_responses=fmt_count(sum(c['n'] for c in pool)), target_median=r4(tg[dep]['median']),
                       target_best_quartile=r4(tg[dep]['best_quartile']), ranked_cells=tg[dep]['cells'])
        row['annual_activity_open'] = sum(c['annual_activity'] for c in dc)
        row['activity_share_in_ranked_cells'] = r4(sum(c['annual_activity'] for c in dc if c['eligible']) / row['annual_activity_open'])
        for t, short in (('median', 'median'), ('best_quartile', 'bq')):
            for lvl in ('low', 'base', 'high'):
                row[f'rar_{short}_{lvl}'] = round(sum(scen[(t, lvl)][j][0] for j in idx))
            tot = [sum(sims[t][j][i] for j in idx) for i in range(a.draws)]
            row[f'rar_{short}_mc_p10'], row[f'rar_{short}_mc_p50'], row[f'rar_{short}_mc_p90'] = (round(pct(tot, q)) for q in (0.1, 0.5, 0.9))
            row[f'gp_{short}_base'] = round(sum(scen[(t, 'base')][j][0] * GROSS_MARGIN[cells[j]['department']][1] for j in idx))
            row[f'gp_{short}_low'] = round(sum(scen[(t, 'low')][j][0] * GROSS_MARGIN[cells[j]['department']][0] for j in idx))
            row[f'gp_{short}_high'] = round(sum(scen[(t, 'high')][j][0] * GROSS_MARGIN[cells[j]['department']][2] for j in idx))
        # systemic lever: every open dealer cuts this department's negative rate by 1 point (incl. unranked cells)
        row['rar_per_1pt_base'] = round(sum(c['annual_activity'] * 0.01 * base_p['representativeness'] * base_p['p_loss']
                                            * annual_value(c['department'], c['revenue_per_unit'], base_p)
                                            for c in dc if c['annual_activity']))
        row['gp_per_1pt_base'] = round(sum(c['annual_activity'] * 0.01 * base_p['representativeness'] * base_p['p_loss']
                                           * annual_value(c['department'], c['revenue_per_unit'], base_p) * GROSS_MARGIN[c['department']][1]
                                           for c in dc if c['annual_activity']))
        dept_rows.append(row)
    write_csv(out / 'opportunity_department.csv', dept_rows)

    sens = sensitivity(dealers, business, rates, alt_rates, a.min_n)
    write_csv(out / 'sensitivity.csv', sens)

    # theme-ready table and optional split
    theme_ready = [{'dealer_code': r['dealer_code'], 'department': r['department'],
                    'negative_responses': r['negative'], 'avoidable_negatives_median_base': r['avoidable_negatives_median_base'],
                    'rar_median_low': r['rar_median_low'], 'rar_median_base': r['rar_median_base'], 'rar_median_high': r['rar_median_high'],
                    'rar_bq_base': r['rar_bq_base']} for r in rows if r['eligible']]
    write_csv(out / 'opportunity_theme_ready.csv', theme_ready)
    write_csv(out / 'theme_shares_template.csv',
              [{'department': dep, 'theme': 'example_theme', 'share': '', 'dealer_code': '', 'n_negative_text': ''} for dep in DEPARTMENTS])
    if a.theme_shares:
        vals = [{k: r[k] for k in ('rar_median_low', 'rar_median_base', 'rar_median_high', 'rar_bq_base')} for r in rows]
        split = theme_split(cells, vals, a.theme_shares)
        write_csv(out / 'opportunity_by_theme.csv', split)
        write_csv(out / 'lever_by_theme.csv', lever_split(dept_rows, a.theme_shares))

    summary = {
        'inputs': {'db': Path(a.db).name, 'db_sha256': sha256(a.db), 'policy': Path(a.policy).name, 'policy_sha256': sha256(a.policy),
                   'rates_source': rate_source, 'rates_file_matches_db': all(r['match'] for r in comparison) if comparison else None,
                   'theme_shares': a.theme_shares and Path(a.theme_shares).name},
        'parameters': {'assumptions_low_base_high': ASSUMPTIONS, 'gap_measures_low_base_high': GAP_MEASURES,
                       'horizon_years': HORIZON_YEARS, 'gross_margin_low_base_high': GROSS_MARGIN, 'min_n': a.min_n,
                       'draws': a.draws, 'seed': a.seed},
        'shrinkage_prior': prior, 'targets': tg,
        'totals': {r['department']: {k: v for k, v in r.items() if k.startswith(('rar_', 'gp_'))} for r in dept_rows},
        'top5_base_median': [f"{r['dealer_code']} {r['department']}: {money(r['rar_median_base'])} "
                             f"(P10-P90 {money(r['rar_median_mc_p10'])}-{money(r['rar_median_mc_p90'])}), "
                             f"stretch {money(r['rar_bq_base'])}" for r in ranked[:5]],
        'business_checks': checks,
    }
    (out / 'run_summary.json').write_text(json.dumps(summary, indent=2, default=str))
    print(json.dumps({k: summary[k] for k in ('top5_base_median',)}, indent=2))
    allrow = dept_rows[-1]
    print('All departments, median target base', money(allrow['rar_median_base']),
          f"(P10-P90 {money(allrow['rar_median_mc_p10'])}-{money(allrow['rar_median_mc_p90'])});",
          'best-quartile base', money(allrow['rar_bq_base']))


if __name__ == '__main__':
    main()
