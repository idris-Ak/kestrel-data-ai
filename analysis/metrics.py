#!/usr/bin/env python3
"""Rating-based negative-feedback metrics (stage 5, Kestrel take-home).

Usage:
    python3 -I analysis/metrics.py [--db PATH] [--policy PATH] [--out DIR]
                          [--expect-individual 7055] [--expect-aggregate 71]

Standard library only. Opens the prepared SQLite run read-only, applies the shared
kestrel/analysis_policy.sql (TEMP views, decisions D1-D5), and writes aggregate CSVs only. No
customer text is ever selected. Reconciliation failures raise AssertionError.
"""
import argparse
import csv
import hashlib
import json
import math
import sqlite3
from collections import defaultdict
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parent
DEPTS = ("Sales", "Service", "Parts")
MONTHS = ["2025-10", "2025-11", "2025-12", "2026-01", "2026-02", "2026-03",
          "2026-04", "2026-05", "2026-06", "2026-07", "2026-08", "2026-09"]
QUARTERS = ["2025Q4", "2026Q1", "2026Q2", "2026Q3"]
MIN_N = 30      # D5: report a rate only when n >= 30
LOW_N = 50      # 30-49 flagged low precision
Z = 1.959963984540054
NEG_KEYS = {"primary": "neg", "strict": "neg_strict", "broad": "neg_broad"}


# ---------------------------------------------------------------- statistics

def wilson(x, n):
    if n == 0:
        return None, None
    p = x / n
    d = 1 + Z * Z / n
    c = (p + Z * Z / (2 * n)) / d
    h = Z * math.sqrt(p * (1 - p) / n + Z * Z / (4 * n * n)) / d
    return max(0.0, c - h), min(1.0, c + h)


def newcombe(x1, n1, x2, n2):
    """95% CI for p2 - p1 (Newcombe hybrid score, method 10)."""
    p1, p2 = x1 / n1, x2 / n2
    l1, u1 = wilson(x1, n1)
    l2, u2 = wilson(x2, n2)
    d = p2 - p1
    return d - math.sqrt((p2 - l2) ** 2 + (u1 - p1) ** 2), d + math.sqrt((u2 - p2) ** 2 + (p1 - l1) ** 2)


def p_two_sided(z):
    return math.erfc(abs(z) / math.sqrt(2))


def two_prop(x1, n1, x2, n2):
    """Pooled two-proportion z-test of p2 vs p1."""
    p = (x1 + x2) / (n1 + n2)
    se = math.sqrt(p * (1 - p) * (1 / n1 + 1 / n2))
    if se == 0:
        return 0.0, 1.0
    z = (x2 / n2 - x1 / n1) / se
    return z, p_two_sided(z)


def bh(pvals):
    """Benjamini-Hochberg q-values."""
    m = len(pvals)
    order = sorted(range(m), key=lambda i: pvals[i])
    q, prev = [0.0] * m, 1.0
    for rank in range(m, 0, -1):
        i = order[rank - 1]
        prev = min(prev, pvals[i] * m / rank)
        q[i] = prev
    return q


def ca_trend(points):
    """Cochran-Armitage trend test over ordered periods: points = [(score, n, x)]."""
    n_tot = sum(n for _, n, _ in points)
    x_tot = sum(x for _, _, x in points)
    if n_tot == 0 or x_tot in (0, n_tot):
        return None, None
    tbar = sum(s * n for s, n, _ in points) / n_tot
    t = sum(x * (s - tbar) for s, _, x in points)
    p = x_tot / n_tot
    v = p * (1 - p) * sum(n * (s - tbar) ** 2 for s, n, _ in points)
    if v == 0:
        return None, None
    z = t / math.sqrt(v)
    return z, p_two_sided(z)


def avg_ranks(vals):
    order = sorted(range(len(vals)), key=lambda i: vals[i])
    r = [0.0] * len(vals)
    i = 0
    while i < len(order):
        j = i
        while j + 1 < len(order) and vals[order[j + 1]] == vals[order[i]]:
            j += 1
        for k in range(i, j + 1):
            r[order[k]] = (i + j) / 2 + 1
        i = j + 1
    return r


def spearman(a, b):
    ra, rb = avg_ranks(a), avg_ranks(b)
    ma, mb = sum(ra) / len(ra), sum(rb) / len(rb)
    cov = sum((x - ma) * (y - mb) for x, y in zip(ra, rb))
    va = math.sqrt(sum((x - ma) ** 2 for x in ra))
    vb = math.sqrt(sum((y - mb) ** 2 for y in rb))
    return cov / (va * vb) if va and vb else None


def rnd(v, k=4):
    return None if v is None else round(v, k)


def precision(n):
    return "ok" if n >= LOW_N else "low" if n >= MIN_N else "suppress"


def rate_cols(n, x):
    lo, hi = wilson(x, n)
    return {"n": n, "negative": x, "rate": rnd(x / n) if n else None, "ci_low": rnd(lo), "ci_high": rnd(hi)}


# ---------------------------------------------------------------- data

INDIVIDUAL_SQL = """
SELECT dealer_final, department_final, feedback_month, quarter, half, rating_band,
       rating_final, rating_scale_max, negative_strict, negative_broad,
       dealer_assumed, department_assumed, selective_collection,
       has_text, model_eligible, privacy_status
FROM analysis_events WHERE compare_eligible = 1 AND rating_band IS NOT NULL
"""

AGGREGATE_SQL = """
SELECT dealer_final, department_final, feedback_month, quarter, half, rating_band,
       rating_final, response_count
FROM analysis_aggregates
"""


def load(con):
    rows = []
    for r in con.execute(INDIVIDUAL_SQL):
        (dealer, dept, month, quarter, half, band, rating, scale, strict, broad,
         d_assumed, dept_assumed, selective, has_text, model_eligible, privacy) = r
        rows.append({
            "dealer": dealer, "dept": dept, "month": month, "quarter": quarter, "half": half,
            "band": band, "rating": rating, "scale": scale, "w": 1, "kind": "individual",
            "neg": int(band == "negative"), "neg_strict": int(strict), "neg_broad": int(broad),
            "hunter": int(d_assumed), "bendigo": int(dept_assumed), "noosa": int(selective),
            "scale10": int(scale == 10), "has_text": int(has_text), "model_eligible": int(model_eligible),
            "withheld": int(privacy == "withheld"),
        })
    for dealer, dept, month, quarter, half, band, bucket, count in con.execute(AGGREGATE_SQL):
        if count == 0:
            continue
        rows.append({
            "dealer": dealer, "dept": dept, "month": month, "quarter": quarter, "half": half,
            "band": band, "rating": bucket, "scale": 5, "w": count, "kind": "aggregate",
            "neg": int(band == "negative"), "neg_strict": int(bucket == 1), "neg_broad": int(bucket <= 3),
            "hunter": 0, "bendigo": 0, "noosa": 0, "scale10": 0,
            "has_text": 0, "model_eligible": 0, "withheld": 0,
        })
    return rows


def dealer_meta(con):
    return {code: {"name": name, "state": state, "region": region, "status": status}
            for code, name, state, region, status in con.execute(
                "SELECT dealer_code, dealership_name, state, region, status FROM dealerships")}


def tally(rows, key, neg="neg"):
    t = defaultdict(lambda: [0, 0])
    for r in rows:
        k = key(r)
        if k is None:
            continue
        t[k][0] += r["w"]
        t[k][1] += r["w"] * r[neg]
    return t


def total_n(rows):
    return sum(r["w"] for r in rows)


# ---------------------------------------------------------------- reconciliation

def reconcile(con, rows, args):
    checks = []

    def check(name, expected, observed, note="", hard=True):
        ok = expected == observed
        checks.append({"check": name, "expected": expected, "observed": observed,
                       "status": "pass" if ok else ("FAIL" if hard else "differs"), "note": note})
        return ok

    ind = [r for r in rows if r["kind"] == "individual"]
    agg_w = sum(r["w"] for r in rows if r["kind"] == "aggregate")
    rr = dict(con.execute("SELECT source_kind, SUM(weight) FROM rated_responses GROUP BY source_kind").fetchall())
    check("rated individual responses = policy.sql rated_responses (individual)", rr.get("individual"), len(ind))
    check("aggregate responses = policy.sql rated_responses (aggregate)", rr.get("aggregate"), agg_w)
    check("aggregate responses = SUM(rating_aggregates.response_count)",
          con.execute("SELECT SUM(response_count) FROM rating_aggregates").fetchone()[0], agg_w)
    check("rated individual responses vs expected default comparison set", args.expect_individual, len(ind),
          "pass --expect-individual N after a deliberate rebuild")
    check("aggregate responses vs expected default comparison set", args.expect_aggregate, agg_w,
          "pass --expect-aggregate N after a deliberate rebuild")

    # Explain the gap between all individual events and the comparison set.
    all_ind = con.execute("SELECT COUNT(*) FROM feedback_events WHERE population='individual'").fetchone()[0]
    by = dict(((ce, rated), c) for ce, rated, c in con.execute(
        "SELECT compare_eligible, rating_band IS NOT NULL, COUNT(*) FROM analysis_events GROUP BY 1, 2"))
    unrated = by.get((1, 0), 0)
    not_comparable = by.get((0, 0), 0) + by.get((0, 1), 0)
    check("individual events = rated comparison set + unrated + not comparable", all_ind,
          len(ind) + unrated + not_comparable,
          f"{all_ind} individual events = {len(ind)} rated & comparable + {unrated} comparable but no valid rating "
          f"+ {not_comparable} not comparable (time-ineligible or outside Oct 2025-Sep 2026)")
    noosa = sum(r["w"] for r in rows if r["noosa"])
    db_split = dict(con.execute("SELECT selective_collection, SUM(weight) FROM rated_responses GROUP BY 1").fetchall())
    check("Noosa responses = policy.sql selective_collection rows", db_split.get(1, 0), noosa)
    check("primary analysis set (Noosa excluded) = policy.sql non-selective rows", db_split.get(0, 0),
          total_n(rows) - noosa,
          f"{len(ind) + agg_w} comparison set = {total_n(rows) - noosa} primary (ranked) + {noosa} Noosa")
    for c in checks:
        if c["status"] == "FAIL":
            raise AssertionError(f"reconciliation failed: {c}")
    return checks


# ---------------------------------------------------------------- analysis helpers

def dept_rates(rows, neg="neg"):
    t = tally(rows, lambda r: r["dept"], neg)
    return {d: (t[d][1] / t[d][0] if t[d][0] else 0.0) for d in DEPTS}


def expected_neg(rows, rates):
    return sum(r["w"] * rates[r["dept"]] for r in rows)


def dealer_adjusted(rows, neg="neg"):
    """Indirect department standardisation: observed / expected negatives per dealer."""
    rates = dept_rates(rows, neg)
    group = sum(r["w"] * r[neg] for r in rows) / total_n(rows)
    out = {}
    by_dealer = defaultdict(list)
    for r in rows:
        by_dealer[r["dealer"]].append(r)
    for dealer, rs in by_dealer.items():
        n = total_n(rs)
        x = sum(r["w"] * r[neg] for r in rs)
        e = expected_neg(rs, rates)
        out[dealer] = {"n": n, "x": x, "expected": e, "oe": x / e if e else None,
                       "adj_rate": (x / e) * group if e else None}
    return out


def change_cells(rows, cellkey, neg="neg"):
    cells = defaultdict(lambda: [0, 0, 0, 0])
    for r in rows:
        i = 0 if r["half"] == "H1" else 2
        c = cells[cellkey(r)]
        c[i] += r["w"]
        c[i + 1] += r["w"] * r[neg]
    return cells


def mix_adjusted(cells):
    """H2 - H1 change holding the cell mix fixed at pooled (H1+H2) weights.

    Uses cells observed in both halves. Variance uses (x+1)/(n+2) smoothed rates so
    small all-zero cells do not get zero variance."""
    all_tot = sum(v[0] + v[2] for v in cells.values())
    use = {k: v for k, v in cells.items() if v[0] > 0 and v[2] > 0}
    tot = sum(v[0] + v[2] for v in use.values())
    a1 = a2 = var = 0.0
    contrib = {}
    for k, (n1, x1, n2, x2) in use.items():
        w = (n1 + n2) / tot
        p1, p2 = x1 / n1, x2 / n2
        a1 += w * p1
        a2 += w * p2
        q1, q2 = (x1 + 1) / (n1 + 2), (x2 + 1) / (n2 + 2)
        var += w * w * (q1 * (1 - q1) / n1 + q2 * (1 - q2) / n2)
        contrib[k] = w * (p2 - p1)
    se = math.sqrt(var)
    d = a2 - a1
    return {"adj_h1": a1, "adj_h2": a2, "adj_diff": d, "adj_ci_low": d - Z * se, "adj_ci_high": d + Z * se,
            "adj_p": p_two_sided(d / se) if se else 1.0, "cells_used": len(use),
            "coverage": tot / all_tot if all_tot else None}, contrib


def raw_change(cells):
    n1 = sum(v[0] for v in cells.values())
    x1 = sum(v[1] for v in cells.values())
    n2 = sum(v[2] for v in cells.values())
    x2 = sum(v[3] for v in cells.values())
    lo, hi = newcombe(x1, n1, x2, n2)
    z, p = two_prop(x1, n1, x2, n2)
    return {"n_h1": n1, "neg_h1": x1, "rate_h1": x1 / n1, "n_h2": n2, "neg_h2": x2, "rate_h2": x2 / n2,
            "raw_diff": x2 / n2 - x1 / n1, "raw_ci_low": lo, "raw_ci_high": hi, "raw_p": p}


def cell_ranking(rows, neg="neg"):
    """Ranked (non-Noosa) dealer x department cells with n >= MIN_N: {(dealer, dept): rate}."""
    t = tally([r for r in rows if not r["noosa"]], lambda r: (r["dealer"], r["dept"]), neg)
    return {k: v[1] / v[0] for k, v in t.items() if v[0] >= MIN_N}


def worst_best(ranking, k=5):
    order = sorted(ranking, key=lambda c: (-ranking[c], c))
    return order[:k], order[::-1][:k]


def cell_movers(rows, neg="neg"):
    """Dealer x department H1 vs H2 tests for cells with n >= MIN_N in both halves."""
    cells = change_cells(rows, lambda r: (r["dealer"], r["dept"]), neg)
    out = {}
    for k, (n1, x1, n2, x2) in cells.items():
        if n1 >= MIN_N and n2 >= MIN_N:
            z, p = two_prop(x1, n1, x2, n2)
            out[k] = {"diff": x2 / n2 - x1 / n1, "z": z, "p": p}
    qs = bh([v["p"] for v in out.values()])
    for (k, v), q in zip(out.items(), qs):
        v["q"] = q
    return out


def label(cell):
    return f"{cell[0]} {cell[1]}"


def pct(v):
    return "" if v is None else f"{100 * v:.1f}%"


def pp(v):
    return "" if v is None else f"{100 * v:+.1f}pp"


# ---------------------------------------------------------------- outputs

def write_csv(out, name, records, fields):
    with open(out / name, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fields, extrasaction="raise")
        w.writeheader()
        for rec in records:
            w.writerow({k: rnd(v) if isinstance(v, float) else v for k, v in rec.items()})


def dealer_notes(code, rows_d):
    notes = []
    if code == "QLD05":
        notes.append("selective card collection: excluded from rankings (D5)")
    if any(r["hunter"] for r in rows_d):
        notes.append("dealer assumed from 'Hunter Motors' file (D3)")
    if any(r["bendigo"] for r in rows_d):
        notes.append("departments assumed from S/SV/P codes (D4)")
    if any(r["kind"] == "aggregate" for r in rows_d):
        notes.append("Q4 2025 from aggregate rating buckets")
    if any(r["scale10"] for r in rows_d):
        notes.append("10-point scale from Feb 2026")
    if any(r["scale"] == 3 for r in rows_d):
        notes.append("3-label scale (bad/ok/good)")
    if code == "VIC06":
        notes.append("Q4 2025 legend reversed (1 = Excellent), re-oriented")
    if code == "VIC09":
        notes.append("closed 2026-03-31: H1 only")
    return "; ".join(notes)


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--db", default=str(REPO / "outputs/prepared/current/prepared.sqlite"))
    ap.add_argument("--policy", default=str(REPO / "kestrel/analysis_policy.sql"))
    ap.add_argument("--out", default=str(REPO / "results/metrics"))
    ap.add_argument("--expect-individual", type=int, default=7055)
    ap.add_argument("--expect-aggregate", type=int, default=71)
    args = ap.parse_args()
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)

    db = Path(args.db).resolve()
    con = sqlite3.connect(f"file:{db}?mode=ro", uri=True)
    policy_text = Path(args.policy).read_text()
    con.executescript(policy_text)
    rows = load(con)
    meta = dealer_meta(con)
    checks = reconcile(con, rows, args)
    for r in rows:
        r["state"] = meta[r["dealer"]]["state"]
        r["region"] = meta[r["dealer"]]["region"]

    A = [r for r in rows if not r["noosa"]]   # primary analysis set (ranked)
    N_A = total_n(A)
    X_A = sum(r["w"] * r["neg"] for r in A)
    group_rate = X_A / N_A
    rates_dept = dept_rates(A)
    files = {}

    # 1. Department -----------------------------------------------------------
    t = tally(A, lambda r: r["dept"])
    recs = []
    for d in DEPTS + ("All",):
        n, x = (N_A, X_A) if d == "All" else t[d]
        recs.append({"department": d, **rate_cols(n, x), "share_of_all_negatives": x / X_A,
                     "share_of_responses": n / N_A, "precision": precision(n)})
    assert sum(t[d][0] for d in DEPTS) == N_A
    write_csv(out, "neg_rate_department.csv", recs, list(recs[0]))
    files["neg_rate_department.csv"] = "negative rate by department (primary set, Noosa excluded)"

    # 2. Dealer (raw and department-adjusted) ---------------------------------
    adj_all = dealer_adjusted(A)
    noosa_rows = [r for r in rows if r["noosa"]]
    by_dealer = defaultdict(list)
    for r in rows:
        by_dealer[r["dealer"]].append(r)
    dealer_recs = []
    for code in sorted(by_dealer):
        rs = by_dealer[code]
        n, x = total_n(rs), sum(r["w"] * r["neg"] for r in rs)
        e = expected_neg(rs, rates_dept)
        lo, hi = wilson(x, n)
        five = [r for r in rs if r["scale"] == 5]
        dealer_recs.append({
            "dealer_code": code, "dealership_name": meta[code]["name"], "state": meta[code]["state"],
            "region": meta[code]["region"], **rate_cols(n, x),
            "service_share": sum(r["w"] for r in rs if r["dept"] == "Service") / n,
            "expected_negative": e, "oe_ratio": x / e,
            "oe_ci_low": lo * n / e, "oe_ci_high": hi * n / e,
            "dept_adjusted_rate": (x / e) * group_rate,
            "mean_rating_5pt": (sum(r["w"] * r["rating"] for r in five) / total_n(five)) if five else None,
            "n_5pt": total_n(five),
            "ranked": int(code != "QLD05" and n >= MIN_N), "precision": precision(n),
            "notes": dealer_notes(code, rs)})
    ranked = [d for d in dealer_recs if d["ranked"]]
    for key, col in (("rate", "rank_raw"), ("dept_adjusted_rate", "rank_adjusted")):
        for i, d in enumerate(sorted(ranked, key=lambda d: -d[key]), 1):
            d[col] = i
    for d in dealer_recs:
        d.setdefault("rank_raw", None)
        d.setdefault("rank_adjusted", None)
    assert sum(d["n"] for d in dealer_recs) == total_n(rows)
    fields = ["dealer_code", "dealership_name", "state", "region", "n", "negative", "rate", "ci_low", "ci_high",
              "rank_raw", "service_share", "expected_negative", "oe_ratio", "oe_ci_low", "oe_ci_high",
              "dept_adjusted_rate", "rank_adjusted", "mean_rating_5pt", "n_5pt", "ranked", "precision", "notes"]
    write_csv(out, "neg_rate_dealer.csv", dealer_recs, fields)
    files["neg_rate_dealer.csv"] = ("negative rate by dealer, raw and department-adjusted "
                                    "(observed/expected at group department rates); rank 1 = worst")

    # 3. Dealer x department --------------------------------------------------
    t = tally(rows, lambda r: (r["dealer"], r["dept"]))
    assert sum(v[0] for v in t.values()) == total_n(rows)
    simple, detail = [], []
    ranking = cell_ranking(rows)
    for (code, d) in sorted(t):
        n, x = t[(code, d)]
        rc = rate_cols(n, x)
        simple.append({"dealer_code": code, "department": d, **rc})
        dr = rates_dept[d]
        vs = ("higher" if rc["ci_low"] > dr else "lower" if rc["ci_high"] < dr else "not distinguishable")
        detail.append({"dealer_code": code, "dealership_name": meta[code]["name"], "state": meta[code]["state"],
                       "region": meta[code]["region"], "department": d, **rc, "department_rate": dr,
                       "ratio_to_department": (x / n) / dr if dr else None,
                       "vs_department": vs if n >= MIN_N else "n<30",
                       "ranked": int((code, d) in ranking), "precision": precision(n),
                       "notes": dealer_notes(code, [r for r in by_dealer[code] if r["dept"] == d])})
    for d in DEPTS:
        cells = sorted((c for c in ranking if c[1] == d), key=lambda c: -ranking[c])
        pos = {c: i for i, c in enumerate(cells, 1)}
        for rec in detail:
            if rec["department"] == d:
                rec["rank_in_department"] = pos.get((rec["dealer_code"], d))
                rec["cells_ranked_in_department"] = len(cells)
    write_csv(out, "neg_rate_dealer_dept.csv", simple,
              ["dealer_code", "department", "n", "negative", "rate", "ci_low", "ci_high"])
    write_csv(out, "neg_rate_dealer_dept_detail.csv", detail,
              ["dealer_code", "dealership_name", "state", "region", "department", "n", "negative", "rate",
               "ci_low", "ci_high", "department_rate", "ratio_to_department", "vs_department",
               "rank_in_department", "cells_ranked_in_department", "ranked", "precision", "notes"])
    files["neg_rate_dealer_dept.csv"] = ("dealer x department negative rate, all 24 dealers incl. Noosa and n<30 "
                                         "cells (fixed columns for the value workstream; filter n>=30, drop QLD05)")
    files["neg_rate_dealer_dept_detail.csv"] = "same cells with precision, ranking within department and flags"

    # 4. Region / state -------------------------------------------------------
    recs = []
    for level in ("state", "region"):
        groups = sorted({r[level] for r in A})
        for g in groups:
            rs = [r for r in A if r[level] == g]
            for d in ("All",) + DEPTS:
                sub = rs if d == "All" else [r for r in rs if r["dept"] == d]
                n, x = total_n(sub), sum(r["w"] * r["neg"] for r in sub)
                if n == 0:
                    continue
                e = expected_neg(sub, rates_dept)
                rc = rate_cols(n, x)
                recs.append({"level": level, "group": g, "department": d, **rc,
                             "dealers": len({r["dealer"] for r in sub}), "expected_negative": e,
                             "oe_ratio": x / e, "oe_ci_low": rc["ci_low"] * n / e, "oe_ci_high": rc["ci_high"] * n / e,
                             "dept_adjusted_rate": (x / e) * group_rate if d == "All" else None,
                             "precision": precision(n)})
        assert sum(rec["n"] for rec in recs if rec["level"] == level and rec["department"] == "All") == N_A
    write_csv(out, "neg_rate_region_state.csv", recs, list(recs[0]))
    files["neg_rate_region_state.csv"] = "by state and region, all departments and each department (Noosa excluded)"

    # 5. Series ---------------------------------------------------------------
    for period, plist, fname in (("month", MONTHS, "month"), ("quarter", QUARTERS, "quarter")):
        recs = []
        t = tally(A, lambda r: (r[period], r["dept"]))
        tall = tally(A, lambda r: r[period])
        for p in plist:
            for d in DEPTS + ("All",):
                n, x = tall[p] if d == "All" else t[(p, d)]
                recs.append({period: p, "department": d, **rate_cols(n, x), "precision": precision(n)})
        assert sum(rec["n"] for rec in recs if rec["department"] == "All") == N_A
        write_csv(out, f"series_{fname}_department.csv", recs, list(recs[0]))
        recs = []
        for code in sorted(by_dealer):
            rs = by_dealer[code]
            t = tally(rs, lambda r: r[period])
            five = tally([r for r in rs if r["scale"] == 5], lambda r: r[period])
            sums = defaultdict(float)
            for r in rs:
                if r["scale"] == 5:
                    sums[r[period]] += r["w"] * r["rating"]
            for p in plist:
                n, x = t[p]
                if n == 0:
                    continue
                n5 = five[p][0]
                recs.append({"dealer_code": code, period: p, **rate_cols(n, x),
                             "mean_rating_5pt": sums[p] / n5 if n5 else None, "n_5pt": n5,
                             "precision": precision(n), "ranked": int(code != "QLD05")})
        assert sum(rec["n"] for rec in recs) == total_n(rows)
        write_csv(out, f"series_{fname}_dealer.csv", recs, list(recs[0]))
    files["series_month_department.csv"] = "monthly negative rate by department and All (Noosa excluded)"
    files["series_quarter_department.csv"] = "quarterly negative rate by department and All (Noosa excluded)"
    files["series_month_dealer.csv"] = "monthly negative rate and 5-point mean rating by dealer (all dealers)"
    files["series_quarter_dealer.csv"] = "quarterly negative rate and 5-point mean rating by dealer (all dealers)"

    # 6. H1 vs H2 change ------------------------------------------------------
    cells = change_cells(A, lambda r: (r["dealer"], r["dept"]))
    group_adj, contrib = mix_adjusted(cells)
    month_t = tally(A, lambda r: (r["dealer"], r["dept"], r["month"]))
    cell_recs = []
    for (code, d) in sorted(cells):
        n1, x1, n2, x2 = cells[(code, d)]
        rec = {"dealer_code": code, "department": d, "n_h1": n1, "neg_h1": x1, "n_h2": n2, "neg_h2": x2}
        if n1 and n2:
            l1, h1 = wilson(x1, n1)
            l2, h2 = wilson(x2, n2)
            lo, hi = newcombe(x1, n1, x2, n2)
            z, p = two_prop(x1, n1, x2, n2)
            tz, tp = ca_trend([(i, month_t[(code, d, m)][0], month_t[(code, d, m)][1])
                               for i, m in enumerate(MONTHS, 1)])
            rec.update({"rate_h1": x1 / n1, "ci_low_h1": l1, "ci_high_h1": h1,
                        "rate_h2": x2 / n2, "ci_low_h2": l2, "ci_high_h2": h2,
                        "diff": x2 / n2 - x1 / n1, "diff_ci_low": lo, "diff_ci_high": hi, "z": z, "p_value": p,
                        "trend_z_monthly": tz, "trend_p_monthly": tp,
                        "contribution_to_group_change": contrib.get((code, d)),
                        "tested": int(n1 >= MIN_N and n2 >= MIN_N)})
        else:
            rec["tested"] = 0
        cell_recs.append(rec)
    tested = [rec for rec in cell_recs if rec["tested"]]
    for rec, q in zip(tested, bh([rec["p_value"] for rec in tested])):
        rec["q_value_bh"] = q
        rec["bonferroni_sig"] = int(rec["p_value"] < 0.05 / len(tested))
    fields = ["dealer_code", "department", "n_h1", "neg_h1", "rate_h1", "ci_low_h1", "ci_high_h1", "n_h2",
              "neg_h2", "rate_h2", "ci_low_h2", "ci_high_h2", "diff", "diff_ci_low", "diff_ci_high", "z",
              "p_value", "tested", "q_value_bh", "bonferroni_sig", "trend_z_monthly", "trend_p_monthly",
              "contribution_to_group_change"]
    for rec in cell_recs:
        for f in fields:
            rec.setdefault(f, None)
    write_csv(out, "change_h1_h2_dealer_dept.csv", cell_recs, fields)
    files["change_h1_h2_dealer_dept.csv"] = ("H1 (Oct-Mar) vs H2 (Apr-Sep) within dealer x department: Wilson CIs, "
                                             "Newcombe CI for the difference, pooled z-test, BH q over tested cells "
                                             "(n>=30 both halves), monthly Cochran-Armitage trend, contribution to "
                                             "the mix-adjusted group change (pp)")

    def summary_row(scope, group, dept, rs, cellkey):
        cs = change_cells(rs, cellkey)
        raw = raw_change(cs)
        adj, _ = mix_adjusted(cs)
        months = tally(rs, lambda r: r["month"])
        tz, tp = ca_trend([(i, months[m][0], months[m][1]) for i, m in enumerate(MONTHS, 1)])
        return {"scope": scope, "group": group, "department": dept, **raw, **adj,
                "mix_component": raw["raw_diff"] - adj["adj_diff"],
                "trend_z_monthly_raw": tz, "trend_p_monthly_raw": tp}

    dd = lambda r: (r["dealer"], r["dept"])
    robust = {k for k, v in cell_movers(A).items() if v["q"] < 0.05}
    not_robust = [r for r in A if dd(r) not in robust]
    summ = [summary_row("group", "All", "All", A, dd),
            summary_row("group_excl_robust_movers", "All", "All", not_robust, dd)]
    for d in DEPTS:
        summ.append(summary_row("department", d, d, [r for r in A if r["dept"] == d], lambda r: r["dealer"]))
        summ.append(summary_row("department_excl_robust_movers", d, d,
                                [r for r in not_robust if r["dept"] == d], lambda r: r["dealer"]))
    for level in ("state", "region"):
        for g in sorted({r[level] for r in A}):
            summ.append(summary_row(level, g, "All", [r for r in A if r[level] == g], dd))
    dealer_summ = []
    for code in sorted({r["dealer"] for r in A}):
        rs = [r for r in A if r["dealer"] == code]
        if any(r["half"] == "H2" for r in rs):
            dealer_summ.append(summary_row("dealer", code, "All", rs, lambda r: r["dept"]))
    for rec, q in zip(dealer_summ, bh([rec["adj_p"] for rec in dealer_summ])):
        rec["adj_q_bh"] = q
    summ += dealer_summ
    fields = ["scope", "group", "department", "n_h1", "neg_h1", "rate_h1", "n_h2", "neg_h2", "rate_h2",
              "raw_diff", "raw_ci_low", "raw_ci_high", "raw_p", "adj_h1", "adj_h2", "adj_diff", "adj_ci_low",
              "adj_ci_high", "adj_p", "adj_q_bh", "mix_component", "cells_used", "coverage",
              "trend_z_monthly_raw", "trend_p_monthly_raw"]
    for rec in summ:
        rec.setdefault("adj_q_bh", None)
    write_csv(out, "change_h1_h2_summary.csv", summ, fields)
    files["change_h1_h2_summary.csv"] = ("H1 vs H2 raw and mix-adjusted change: group (fixed dealer x dept mix), "
                                         "department (fixed dealer mix), state/region, dealer (fixed dept mix; "
                                         "BH q across dealers)")

    # 7. Movers ---------------------------------------------------------------
    movers = []

    def tier(p, q):
        return ("robust (BH q<0.05)" if q < 0.05 else "suggestive (BH q<0.10)" if q < 0.10
                else "nominal only (p<0.05, not significant after BH)")

    for rec in tested:
        if rec["p_value"] < 0.05:
            movers.append({"level": "dealer_x_department", "dealer_code": rec["dealer_code"],
                           "department": rec["department"], "n_h1": rec["n_h1"], "rate_h1": rec["rate_h1"],
                           "n_h2": rec["n_h2"], "rate_h2": rec["rate_h2"], "diff": rec["diff"],
                           "diff_ci_low": rec["diff_ci_low"], "diff_ci_high": rec["diff_ci_high"],
                           "p_value": rec["p_value"], "q_value_bh": rec["q_value_bh"],
                           "bonferroni_sig": rec["bonferroni_sig"], "tests_in_family": len(tested),
                           "expected_false_positives_at_p05": 0.05 * len(tested),
                           "trend_p_monthly": rec["trend_p_monthly"],
                           "direction": "worse" if rec["diff"] > 0 else "better",
                           "tier": tier(rec["p_value"], rec["q_value_bh"])})
    for rec in dealer_summ:
        if rec["adj_p"] < 0.05:
            movers.append({"level": "dealer (dept-mix adjusted)", "dealer_code": rec["group"], "department": "All",
                           "n_h1": rec["n_h1"], "rate_h1": rec["adj_h1"], "n_h2": rec["n_h2"],
                           "rate_h2": rec["adj_h2"], "diff": rec["adj_diff"], "diff_ci_low": rec["adj_ci_low"],
                           "diff_ci_high": rec["adj_ci_high"], "p_value": rec["adj_p"], "q_value_bh": rec["adj_q_bh"],
                           "bonferroni_sig": int(rec["adj_p"] < 0.05 / len(dealer_summ)),
                           "tests_in_family": len(dealer_summ),
                           "expected_false_positives_at_p05": 0.05 * len(dealer_summ),
                           "trend_p_monthly": rec["trend_p_monthly_raw"],
                           "direction": "worse" if rec["adj_diff"] > 0 else "better",
                           "tier": tier(rec["adj_p"], rec["adj_q_bh"])})
    movers.sort(key=lambda m: (m["level"] != "dealer (dept-mix adjusted)", m["p_value"]))
    write_csv(out, "movers.csv", movers, list(movers[0]) if movers else ["level"])
    files["movers.csv"] = "cells and dealers with p<0.05 for H1 vs H2, tiered by Benjamini-Hochberg q"

    # 8. Sensitivity ----------------------------------------------------------
    primary_rank = cell_ranking(rows)
    p_worst, p_best = worst_best(primary_rank)
    p_movers = {k: v for k, v in cell_movers(A).items() if v["q"] < 0.05}
    p_adj = {k: v["adj_rate"] for k, v in adj_all.items() if v["n"] >= MIN_N}
    scenarios = [
        ("primary", "Primary: bottom-2-box bands, Noosa excluded", lambda r: not r["noosa"], "neg"),
        ("strict_band", "Strict band (5-pt = 1; 10-pt 1-2; 3-label bad)", lambda r: not r["noosa"], "neg_strict"),
        ("broad_band", "Broad band (5-pt 1-3; 10-pt 1-6; 3-label bad+ok)", lambda r: not r["noosa"], "neg_broad"),
        ("excl_hunter", "Exclude Hunter Motors rows (NSW05 dealer assumed)",
         lambda r: not r["noosa"] and not r["hunter"], "neg"),
        ("incl_noosa", "Include Noosa (selective collection)", lambda r: True, "neg"),
        ("excl_toowoomba_agg", "Exclude Toowoomba Q4 2025 aggregate buckets",
         lambda r: not r["noosa"] and r["kind"] != "aggregate", "neg"),
        ("excl_ringwood_10pt", "Exclude Ringwood 10-point rows (Feb-Sep 2026)",
         lambda r: not r["noosa"] and not r["scale10"], "neg"),
        ("excl_bendigo_assumed", "Exclude Bendigo assumed departments",
         lambda r: not r["noosa"] and not r["bendigo"], "neg"),
        ("all_exclusions", "Exclude Hunter, Toowoomba aggregates, Ringwood 10-pt and Bendigo together",
         lambda r: not (r["noosa"] or r["hunter"] or r["kind"] == "aggregate" or r["scale10"] or r["bendigo"]),
         "neg"),
    ]
    sens = []
    for sid, desc, keep, neg in scenarios:
        S = [r for r in rows if keep(r)]
        R = [r for r in S if not r["noosa"]] if sid != "incl_noosa" else S
        n_s = total_n(S)

        def add(hid, headline, value, survives, detail=""):
            sens.append({"scenario": sid, "scenario_description": desc, "n": n_s, "headline_id": hid,
                         "headline": headline, "value": value, "survives": "yes" if survives else "NO",
                         "detail": detail})

        t = tally(S, lambda r: r["dept"], neg)
        ci = {d: wilson(t[d][1], t[d][0]) for d in DEPTS}
        rt = {d: t[d][1] / t[d][0] for d in DEPTS}
        add("H1", "Service has the highest negative rate (CI separated from Sales and Parts)",
            f"Service {pct(rt['Service'])} / Parts {pct(rt['Parts'])} / Sales {pct(rt['Sales'])}",
            ci["Service"][0] > max(ci["Sales"][1], ci["Parts"][1]),
            f"Service CI {pct(ci['Service'][0])}-{pct(ci['Service'][1])}")
        add("H1b", "Parts negative rate above Sales (CI separated)",
            f"Parts {pct(rt['Parts'])} vs Sales {pct(rt['Sales'])}", ci["Parts"][0] > ci["Sales"][1],
            f"Parts CI {pct(ci['Parts'][0])}-{pct(ci['Parts'][1])}; Sales CI {pct(ci['Sales'][0])}-{pct(ci['Sales'][1])}")
        cs = change_cells(S, dd, neg)
        raw = raw_change(cs)
        adj, _ = mix_adjusted(cs)
        add("H2", "Group negative rate rose from H1 to H2 (raw, CI excludes 0)",
            f"{pct(raw['rate_h1'])} -> {pct(raw['rate_h2'])} ({pp(raw['raw_diff'])})", raw["raw_ci_low"] > 0,
            f"95% CI {pp(raw['raw_ci_low'])} to {pp(raw['raw_ci_high'])}")
        add("H3", "Rise is not a mix shift: change at fixed dealer x dept mix (CI excludes 0)",
            f"{pct(adj['adj_h1'])} -> {pct(adj['adj_h2'])} ({pp(adj['adj_diff'])})", adj["adj_ci_low"] > 0,
            f"95% CI {pp(adj['adj_ci_low'])} to {pp(adj['adj_ci_high'])}; mix component "
            f"{pp(raw['raw_diff'] - adj['adj_diff'])}")
        rank_s = cell_ranking(R if sid != "incl_noosa" else [dict(r, noosa=0) for r in R], neg)
        w_s, b_s = worst_best(rank_s, 10)
        present = [c for c in p_worst if c in rank_s]
        kept = [c for c in present if c in w_s]
        add("H4", "Primary worst-5 dealer x dept cells stay in the scenario's worst 10",
            f"{len(kept)}/{len(present)}", len(present) > 0 and len(kept) >= len(present) - 1,
            "scenario worst 5: " + ", ".join(label(c) for c in w_s[:5]))
        present = [c for c in p_best if c in rank_s]
        kept = [c for c in present if c in b_s]
        add("H5", "Primary best-5 dealer x dept cells stay in the scenario's best 10",
            f"{len(kept)}/{len(present)}", len(present) > 0 and len(kept) >= len(present) - 1,
            "scenario best 5: " + ", ".join(label(c) for c in b_s[:5]))
        adj_s = {k: v["adj_rate"] for k, v in dealer_adjusted(R, neg).items() if v["n"] >= MIN_N}
        common = sorted(set(adj_s) & set(p_adj))
        rho = spearman([p_adj[c] for c in common], [adj_s[c] for c in common])
        add("H6", "Department-adjusted dealer ranking matches primary (Spearman rho >= 0.8)",
            f"rho = {rho:.2f} over {len(common)} dealers", rho is not None and rho >= 0.8)
        mv = cell_movers(R, neg)
        for k in sorted(p_movers, key=lambda c: p_movers[c]["p"]):
            v = mv.get(k)
            add("H7", f"Mover {label(k)} ({'worse' if p_movers[k]['diff'] > 0 else 'better'}) remains significant (p<0.05)",
                "not tested in scenario" if v is None else f"{pp(v['diff'])}, p={v['p']:.4f}, q={v['q']:.3f}",
                v is not None and v["p"] < 0.05 and (v["diff"] > 0) == (p_movers[k]["diff"] > 0))
        st = dealer_adjusted_by(R, "state", neg)
        add("H8", "No state differs from the group after department adjustment (all O/E 95% CIs include 1)",
            ", ".join(f"{s} {v['oe']:.2f} [{v['lo']:.2f}-{v['hi']:.2f}]" for s, v in st.items()),
            all(v["lo"] <= 1 <= v["hi"] for v in st.values()))
        da = dealer_adjusted(R, neg)
        elig = {k: v for k, v in da.items() if v["n"] >= MIN_N and k != "QLD05"}
        worst = max(elig, key=lambda k: elig[k]["oe"])
        p = da["NSW01"]
        lo = wilson(p["x"], p["n"])[0] * p["n"] / p["expected"]
        add("H9", "Parramatta (NSW01) is the worst dealer after department adjustment, O/E CI above 1",
            f"worst = {worst}; NSW01 O/E {p['oe']:.2f} (CI low {lo:.2f})", worst == "NSW01" and lo > 1)
        rest = [r for r in S if dd(r) not in robust]
        adj_r, _ = mix_adjusted(change_cells(rest, dd, neg))
        add("H10", "Group rise persists without the robust-mover cells (mix-adjusted CI excludes 0)",
            f"{pp(adj_r['adj_diff'])}", adj_r["adj_ci_low"] > 0,
            f"95% CI {pp(adj_r['adj_ci_low'])} to {pp(adj_r['adj_ci_high'])}; excluded: "
            + ", ".join(label(c) for c in sorted(robust)))
        for hid, d in (("H11", "Service"), ("H12", "Sales")):
            a, _ = mix_adjusted(change_cells([r for r in S if r["dept"] == d], lambda r: r["dealer"], neg))
            add(hid, f"{d} rose H1 to H2 at fixed dealer mix (CI excludes 0)", pp(a["adj_diff"]),
                a["adj_ci_low"] > 0, f"95% CI {pp(a['adj_ci_low'])} to {pp(a['adj_ci_high'])}")
    write_csv(out, "sensitivity.csv", sens, list(sens[0]))
    files["sensitivity.csv"] = "each headline under each sensitivity scenario, with survives yes/NO"

    # 9. Representativeness: text coverage ------------------------------------
    ind_all = [r for r in rows if r["kind"] == "individual"]
    recs = []
    for code in sorted({r["dealer"] for r in ind_all}) + ["ALL (primary set)"]:
        rs = [r for r in ind_all if (r["dealer"] == code if code != "ALL (primary set)" else not r["noosa"])]
        neg_r = [r for r in rs if r["neg"]]
        non = [r for r in rs if not r["neg"]]
        share = lambda xs, k: (sum(r[k] for r in xs) / len(xs)) if xs else None
        texted = sum(r["has_text"] for r in rs)
        z, p = (two_prop(sum(r["has_text"] for r in non), len(non), sum(r["has_text"] for r in neg_r), len(neg_r))
                if neg_r and non else (None, None))
        recs.append({"dealer_code": code, "n_rated_individual": len(rs),
                     "has_text": texted, "has_text_share": share(rs, "has_text"),
                     "model_eligible": sum(r["model_eligible"] for r in rs),
                     "model_eligible_share": share(rs, "model_eligible"),
                     "withheld": sum(r["withheld"] for r in rs),
                     "withheld_share_of_text": (sum(r["withheld"] for r in rs) / texted) if texted else None,
                     "n_negative": len(neg_r), "neg_has_text_share": share(neg_r, "has_text"),
                     "nonneg_has_text_share": share(non, "has_text"),
                     "neg_vs_nonneg_text_p": p,
                     "neg_model_eligible": sum(r["model_eligible"] for r in neg_r),
                     "neg_model_eligible_share": share(neg_r, "model_eligible"),
                     "nonneg_model_eligible_share": share(non, "model_eligible"),
                     "aggregate_responses_no_text": sum(r["w"] for r in rows
                                                        if r["kind"] == "aggregate" and r["dealer"] == code),
                     "ranked": int(code != "QLD05")})
    write_csv(out, "text_coverage_dealer.csv", recs, list(recs[0]))
    recs = []
    ind_A = [r for r in A if r["kind"] == "individual"]
    for d in DEPTS + ("All",):
        rs = ind_A if d == "All" else [r for r in ind_A if r["dept"] == d]
        for band in ("negative", "neutral", "positive"):
            b = [r for r in rs if r["band"] == band]
            ht, me = sum(r["has_text"] for r in b), sum(r["model_eligible"] for r in b)
            l1, h1 = wilson(ht, len(b))
            l2, h2 = wilson(me, len(b))
            recs.append({"department": d, "band": band, "n": len(b), "has_text": ht, "has_text_share": ht / len(b),
                         "has_text_ci_low": l1, "has_text_ci_high": h1, "model_eligible": me,
                         "model_eligible_share": me / len(b), "model_eligible_ci_low": l2,
                         "model_eligible_ci_high": h2, "share_of_model_eligible": None})
        tot_me = sum(rec["model_eligible"] for rec in recs if rec["department"] == d)
        for rec in recs:
            if rec["department"] == d:
                rec["share_of_model_eligible"] = rec["model_eligible"] / tot_me
    write_csv(out, "text_coverage_band.csv", recs, list(recs[0]))
    t_ind = defaultdict(lambda: [0, 0, 0, 0])
    for r in ind_all:
        c = t_ind[(r["dealer"], r["dept"])]
        c[0] += 1
        c[1] += r["neg"]
        c[2] += r["model_eligible"]
        c[3] += r["neg"] * r["model_eligible"]
    recs = [{"dealer_code": k[0], "department": k[1], "n_rated_individual": v[0], "n_negative": v[1],
             "model_eligible": v[2], "neg_model_eligible": v[3],
             "neg_model_eligible_share": v[3] / v[1] if v[1] else None}
            for k, v in sorted(t_ind.items())]
    write_csv(out, "text_coverage_dealer_dept.csv", recs, list(recs[0]))
    files["text_coverage_dealer.csv"] = ("text and model-eligible coverage by dealer; negative vs non-negative "
                                         "comment rates (individual responses only)")
    files["text_coverage_band.csv"] = "comment and model-eligible share by rating band and department (Noosa excluded)"
    files["text_coverage_dealer_dept.csv"] = "theme base: model-eligible negative responses per dealer x department"

    # 10. Response volume per activity (coverage, not satisfaction) -----------
    act = defaultdict(lambda: [0, 0])
    for code, month, d, a in con.execute(
            "SELECT dealer_code, month, department, activity_count FROM business_monthly "
            "WHERE month BETWEEN '2025-10' AND '2026-09'"):
        act[(code, d)][0 if month <= "2026-03" else 1] += a
    resp = defaultdict(lambda: [0, 0])
    for r in rows:
        resp[(r["dealer"], r["dept"])][0 if r["half"] == "H1" else 1] += r["w"]
    recs = []
    for k in sorted(set(act) | set(resp)):
        a1, a2 = act[k]
        r1, r2 = resp[k]
        per = lambda r_, a_: 1000 * r_ / a_ if a_ else None
        recs.append({"dealer_code": k[0], "department": k[1], "responses": r1 + r2, "activity": a1 + a2,
                     "responses_per_1000_activity": per(r1 + r2, a1 + a2),
                     "responses_h1": r1, "activity_h1": a1, "per_1000_h1": per(r1, a1),
                     "responses_h2": r2, "activity_h2": a2, "per_1000_h2": per(r2, a2),
                     "h2_vs_h1_coverage_ratio": (per(r2, a2) / per(r1, a1)) if a1 and a2 and r1 else None})
    assert sum(rec["responses"] for rec in recs) == total_n(rows)
    write_csv(out, "response_coverage_dealer_dept.csv", recs, list(recs[0]))
    files["response_coverage_dealer_dept.csv"] = ("rated responses per 1,000 sales/service jobs/parts transactions "
                                                  "by dealer x department and half (coverage indicator only)")

    write_csv(out, "reconciliation.csv", checks, ["check", "expected", "observed", "status", "note"])
    files["reconciliation.csv"] = "reconciliation checks (script raises on FAIL)"

    info = {
        "db": db.name, "db_sha256": hashlib.sha256(db.read_bytes()).hexdigest(),
        "policy_sha256": hashlib.sha256(policy_text.encode()).hexdigest(),
        "run_metadata": {k: v for k, v in con.execute(
            "SELECT key, value FROM run_metadata WHERE key IN ('run_id','input_snapshot','parser_version',"
            "'redaction_version','schema_version')")},
        "comparison_set": {"individual": len([r for r in rows if r["kind"] == "individual"]),
                           "aggregate": sum(r["w"] for r in rows if r["kind"] == "aggregate"),
                           "primary_analysis_set_excl_noosa": N_A, "noosa": total_n(noosa_rows)},
        "group_negative_rate": group_rate, "min_n": MIN_N, "low_precision_below": LOW_N, "files": files,
    }
    (out / "run_info.json").write_text(json.dumps(info, indent=2) + "\n")
    con.close()
    print(f"OK: {len(files)} CSVs written to {out}; primary set n={N_A}, negative rate {group_rate:.4f}; "
          f"group H1->H2 raw {summ[0]['raw_diff']:+.4f}, mix-adjusted {group_adj['adj_diff']:+.4f}")


def dealer_adjusted_by(rows, level, neg="neg"):
    """Observed/expected negatives (department-standardised) by a grouping column."""
    rates = dept_rates(rows, neg)
    out = {}
    for g in sorted({r[level] for r in rows}):
        rs = [r for r in rows if r[level] == g]
        x, n = sum(r["w"] * r[neg] for r in rs), total_n(rs)
        e = expected_neg(rs, rates)
        lo, hi = wilson(x, n)
        out[g] = {"oe": x / e, "lo": lo * n / e, "hi": hi * n / e}
    return out


if __name__ == "__main__":
    main()
