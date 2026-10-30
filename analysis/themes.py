#!/usr/bin/env python3
"""Theme drivers of negative feedback (stage 6, Kestrel take-home).

Usage:
    python3 -I analysis/themes.py [--db PATH] [--policy PATH] [--labels PATH] [--out DIR]

Joins the stage-4 labels (outputs/classified/<run_id>/labels.jsonl) to kestrel/analysis_policy.sql by
event_id and writes aggregate CSVs only: no comment text, evidence spans or event IDs leave this script.

Primary base: classified comments on rating-negative, comparable responses (Noosa excluded). A theme's
share is the proportion of those comments that carry it as a *negative* theme; comments can carry several
themes, so shares sum above 1. Sensitivity base: comments the model itself called negative or mixed.
Shares are quoted only when n >= 30 (D5), with Wilson 95% intervals.
"""
import argparse
import csv
import hashlib
import importlib.util
import json
import sqlite3
from collections import defaultdict
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parent
_spec = importlib.util.spec_from_file_location("kestrel_metrics", HERE / "metrics.py")
stats = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(stats)

DEPTS = stats.DEPTS
MIN_N = stats.MIN_N
THEME_MIN_N = 20     # value_model.py uses dealer-level shares only from 20 negative comments
THEMES = tuple(json.loads((REPO / "kestrel/ai_pilot_taxonomy.json").read_text())["themes"])
MOVERS = (("NSW01", "Service"), ("VIC01", "Service"), ("NSW04", "Sales"))

EVENTS_SQL = """
SELECT event_id, dealer_final, department_final, half, rating_band, compare_eligible,
       selective_collection, model_eligible, dealership_name
FROM analysis_events
"""


def sha256(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def verify_label_lineage(db, labels_path, summary_path=None):
    """Bind saved labels to this prepared export without requiring an identical run ID.

    A code/runtime change or the brief migration changes the prepared run ID even
    when its model input is byte-identical. Content hashes are the replay boundary.
    """
    db, labels_path = Path(db).resolve(), Path(labels_path).resolve()
    summary_path = Path(summary_path or labels_path.with_name("summary.json"))
    summary = json.loads(summary_path.read_text())
    manifest = json.loads((db.parent / "manifest.json").read_text())
    for name, path in (("prepared.sqlite", db), ("model_input.jsonl", db.parent / "model_input.jsonl")):
        if sha256(path) != manifest["artifacts"][name]:
            raise ValueError(f"{name} does not match the prepared run manifest")
    if sha256(labels_path) != summary["labels_sha256"]:
        raise ValueError("labels.jsonl does not match the classification summary")
    if summary["model_input_sha256"] != manifest["artifacts"]["model_input.jsonl"]:
        raise ValueError("classification model-input hash does not match this prepared run")
    return summary, manifest


def load_labels(path):
    labels, failed, seen = {}, 0, set()
    with open(path, encoding="utf-8") as f:
        for line in f:
            r = json.loads(line)
            if r["event_id"] in seen:
                raise ValueError("duplicate event_id in labels")
            seen.add(r["event_id"])
            if r["status"] != "ok":
                failed += 1
                continue
            labels[r["event_id"]] = {
                "overall": r["overall_sentiment"],
                "neg": frozenset(t["theme"] for t in r["themes"] if t["sentiment"] == "negative"),
            }
    return labels, failed


def join(con, labels):
    events = {row[0]: row for row in con.execute(EVENTS_SQL)}
    unknown = [e for e in labels if e not in events or not events[e][7]]
    if unknown:
        raise ValueError(f"{len(unknown)} labels do not match a model-eligible event")
    recs, names = [], {}
    for event_id, lab in labels.items():
        _, dealer, dept, half, band, comparable, selective, _, name = events[event_id]
        names[dealer] = name
        recs.append({"dealer": dealer, "dept": dept, "half": half, "band": band,
                     "eligible": bool(comparable and not selective), **lab})
    model_eligible = sum(1 for row in events.values() if row[7])
    return recs, names, model_eligible


def base(recs, basis="rating_negative"):
    if basis == "rating_negative":
        return [r for r in recs if r["eligible"] and r["band"] == "negative"]
    return [r for r in recs if r["eligible"] and r["overall"] in ("negative", "mixed")]


def share_cols(k, n, suffix=""):
    ok = n >= MIN_N
    lo, hi = stats.wilson(k, n) if ok else (None, None)
    return {f"n{suffix}": n, f"k{suffix}": k, f"share{suffix}": k / n if ok else None,
            f"ci_low{suffix}": lo, f"ci_high{suffix}": hi, f"precision{suffix}": stats.precision(n)}


def theme_rows(rs, **scope):
    n = len(rs)
    out = [{**scope, "theme": t, **share_cols(sum(t in r["neg"] for r in rs), n)} for t in THEMES]
    out.sort(key=lambda row: -row["k"])
    out.append({**scope, "theme": "(no negative theme)", **share_cols(sum(not r["neg"] for r in rs), n)})
    return out


def fractional_shares(rs):
    """Each comment counts once, split equally across its negative themes; the rest is unassigned."""
    total = defaultdict(float)
    for r in rs:
        for t in r["neg"]:
            total[t] += 1 / len(r["neg"])
    return {t: total[t] / len(rs) for t in THEMES if total[t]}


def negative_rates(con):
    """(scope) -> {half: (weighted responses, weighted negatives)} from rated_responses, Noosa excluded."""
    rates = defaultdict(lambda: defaultdict(lambda: [0, 0]))
    for dealer, dept, half, band, w in con.execute(
            "SELECT dealer_final, department_final, half, rating_band, weight FROM rated_responses "
            "WHERE selective_collection = 0 AND half IS NOT NULL"):
        for key in ("Group", dept, (dealer, dept)):
            cell = rates[key][half]
            cell[0] += w
            cell[1] += w * (band == "negative")
    return rates


def change_rows(rs, scope, rate):
    h1 = [r for r in rs if r["half"] == "H1"]
    h2 = [r for r in rs if r["half"] == "H2"]
    nr1 = rate["H1"][1] / rate["H1"][0] if rate["H1"][0] else None
    nr2 = rate["H2"][1] / rate["H2"][0] if rate["H2"][0] else None
    out = []
    for t in THEMES:
        k1, k2 = sum(t in r["neg"] for r in h1), sum(t in r["neg"] for r in h2)
        row = {"scope": scope, "theme": t, **share_cols(k1, len(h1), "_h1"), **share_cols(k2, len(h2), "_h2"),
               "neg_rate_h1": nr1, "neg_rate_h2": nr2}
        tested = len(h1) >= MIN_N and len(h2) >= MIN_N
        if tested:
            lo, hi = stats.newcombe(k1, len(h1), k2, len(h2))
            _, p = stats.two_prop(k1, len(h1), k2, len(h2))
            i1, i2 = nr1 * k1 / len(h1), nr2 * k2 / len(h2)
            row.update(diff=k2 / len(h2) - k1 / len(h1), diff_ci_low=lo, diff_ci_high=hi, p_value=p,
                       per100_h1=100 * i1, per100_h2=100 * i2, per100_diff=100 * (i2 - i1))
        row["tested"] = int(tested)
        out.append(row)
    return out


def write_csv(out, name, records):
    fields = list(dict.fromkeys(k for rec in records for k in rec))
    with open(out / name, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        for rec in records:
            w.writerow({k: stats.rnd(v) if isinstance(v, float) else v for k, v in rec.items()})


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--db", default=str(REPO / "outputs/prepared/current/prepared.sqlite"))
    ap.add_argument("--policy", default=str(REPO / "kestrel/analysis_policy.sql"))
    ap.add_argument("--labels", help="labels.jsonl (default: outputs/classified/<run_id of --db>/labels.jsonl)")
    ap.add_argument("--summary", help="classification summary.json (default: beside --labels)")
    ap.add_argument("--out", default=str(REPO / "results/themes"))
    args = ap.parse_args()
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)

    db = Path(args.db).resolve()
    con = sqlite3.connect(f"file:{db}?mode=ro", uri=True)
    policy_text = Path(args.policy).read_text()
    con.executescript(policy_text)
    run_id = con.execute("SELECT value FROM run_metadata WHERE key = 'run_id'").fetchone()[0]
    labels_path = Path(args.labels or REPO / "outputs/classified" / run_id / "labels.jsonl")
    summary, manifest = verify_label_lineage(db, labels_path, args.summary)
    if manifest["run_id"] != run_id:
        raise ValueError("prepared database run ID does not match its manifest")
    labels, failed = load_labels(labels_path)
    recs, names, model_eligible = join(con, labels)
    if (summary["eligible"], summary["classified"], summary["failed"]) != (model_eligible, len(labels), failed):
        raise ValueError("classification counts do not cover this prepared model-input population")
    neg = base(recs)

    # 1. Coverage: how many negative responses carry a classified comment
    rated = {(r[0], r[1]): r[2:] for r in con.execute(
        "SELECT department_final, rating_band, SUM(weight) "
        "FROM rated_responses WHERE selective_collection = 0 GROUP BY 1, 2")}
    coverage = [{"scope": "labels", "model_eligible_in_db": model_eligible, "classified_ok": len(labels),
                 "failed": failed}]
    for d in DEPTS + ("All",):
        n_neg = sum(v[0] for (dd, b), v in rated.items() if b == "negative" and d in (dd, "All"))
        k = sum(1 for r in neg if d in (r["dept"], "All"))
        coverage.append({"scope": d, "negative_responses": n_neg, "negative_with_classified_comment": k,
                         "coverage": k / n_neg if n_neg else None})
    write_csv(out, "coverage.csv", coverage)

    # 2. Shares among negative comments: overall (two bases), department, dealer and dealer x department
    overall = theme_rows(neg, basis="rating_negative") + theme_rows(base(recs, "ai_negative"), basis="ai_negative")
    write_csv(out, "theme_share_overall.csv", overall)
    write_csv(out, "theme_share_department.csv",
              [row for d in DEPTS for row in theme_rows([r for r in neg if r["dept"] == d], department=d)])
    dealer_rows = []
    for dealer in sorted({r["dealer"] for r in neg}):
        for d in ("All",) + DEPTS:
            rs = [r for r in neg if r["dealer"] == dealer and d in (r["dept"], "All")]
            if len(rs) >= MIN_N:
                dealer_rows += theme_rows(rs, dealer_code=dealer, dealership=names[dealer], department=d)
    write_csv(out, "theme_share_dealer.csv", dealer_rows)

    # 3. H1 vs H2: group, departments and the three movers
    rates = negative_rates(con)
    changes = change_rows(neg, "Group", rates["Group"])
    for d in DEPTS:
        changes += change_rows([r for r in neg if r["dept"] == d], d, rates[d])
    for dealer, d in MOVERS:
        changes += change_rows([r for r in neg if (r["dealer"], r["dept"]) == (dealer, d)],
                               f"{names[dealer]} {d}", rates[(dealer, d)])
    tested = [c for c in changes if c["tested"]]
    for c, q in zip(tested, stats.bh([c["p_value"] for c in tested])):
        c["q_value_bh"] = q
    write_csv(out, "theme_change_h1_h2.csv", changes)

    # 4. Shares for value_model.py --theme-shares (fractional, so each cell's shares sum to <= 1)
    shares = []
    for d in DEPTS:
        rs = [r for r in neg if r["dept"] == d]
        shares += [{"department": d, "theme": t, "share": s, "dealer_code": "", "n_negative_text": len(rs)}
                   for t, s in fractional_shares(rs).items()]
    cells = defaultdict(list)
    for r in neg:
        cells[(r["dealer"], r["dept"])].append(r)
    for (dealer, d), rs in sorted(cells.items()):
        if len(rs) >= THEME_MIN_N:
            shares += [{"department": d, "theme": t, "share": s, "dealer_code": dealer, "n_negative_text": len(rs)}
                       for t, s in fractional_shares(rs).items()]
    write_csv(out, "theme_shares.csv", shares)

    info = {"db": db.name, "db_sha256": hashlib.sha256(db.read_bytes()).hexdigest(), "run_id": run_id,
            "policy_sha256": hashlib.sha256(policy_text.encode()).hexdigest(),
            "labels_sha256": summary["labels_sha256"],
            "classification_run_id": summary["run_id"],
            "model_input_sha256": summary["model_input_sha256"],
            "labels_ok": len(labels), "labels_failed": failed, "negative_comments_primary": len(neg),
            "min_n": MIN_N, "themes": list(THEMES)}
    (out / "run_info.json").write_text(json.dumps(info, indent=2) + "\n")
    con.close()
    top = [f"{r['theme']} {r['share']:.1%}" for r in overall[:3] if r["share"] is not None]
    print(f"OK: {len(labels)} labels joined; {len(neg)} negative comments; top themes: {', '.join(top)}")


if __name__ == "__main__":
    main()
