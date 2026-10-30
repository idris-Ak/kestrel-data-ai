"""Rating checks shared by classification and the frozen evaluation study."""

from collections import Counter
import math
from pathlib import Path


def wilson(successes, n, z=1.96):
    if n == 0:
        return (None, None)
    p = successes / n
    centre = (p + z * z / (2 * n)) / (1 + z * z / n)
    half = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / (1 + z * z / n)
    return (round(centre - half, 3), round(centre + half, 3))


def rating_band(value, scale, kind, direction):
    """Band a native rating on the oriented (higher-is-better) scale: bottom-2/top-2 box on 5 points.

    Unlabelled scales are treated as higher-is-better; explicit reversed
    legends are honoured. Ratings are read locally and never sent to a model.
    """
    if value is None:
        return None
    oriented = scale + 1 - value if direction == "low_is_good" else value
    if scale == 3:
        return {1: "negative", 2: "neutral", 3: "positive"}[oriented]
    five = math.ceil(oriented / 2) if scale == 10 else oriented
    return "negative" if five <= 2 else "neutral" if five == 3 else "positive"


def band_agreement(records, rows, database):
    """Compare predicted overall sentiment with each customer's rating band (no reference labels involved)."""
    import sqlite3
    rows = {r["event_id"]: r for r in rows}
    db = sqlite3.connect(f"file:{Path(database)}?mode=ro", uri=True)
    try:
        ratings = {e: (v, s, k, d, path) for e, v, s, k, d, path in db.execute(
            """SELECT e.event_id, e.rating_value, e.rating_scale_max, e.rating_kind, e.rating_direction, f.path
               FROM feedback_events e JOIN source_observations o ON o.observation_id = e.canonical_observation_id
               JOIN source_files f USING(source_id)""")}
    finally:
        db.close()
    pairs, by_source = Counter(), {}
    for record in records:
        row = rows.get(record["event_id"])
        value, scale, kind, direction, path = ratings[record["event_id"]]
        band = rating_band(value, scale, kind, direction)
        predicted = row["labels"]["overall_sentiment"] if row and row["status"] == "ok" else "failed"
        pairs[(band or "no_rating", predicted)] += 1
        source = by_source.setdefault(Path(path).stem, Counter())
        if band in ("positive", "negative") and predicted in ("positive", "negative"):
            source["comparable"] += 1
            source["agree"] += band == predicted
    comparable = sum(n for (b, p), n in pairs.items() if b in ("positive", "negative") and p in ("positive", "negative"))
    agree = sum(n for (b, p), n in pairs.items() if b == p and b in ("positive", "negative"))
    return {"comparable": comparable, "agree": agree,
            "agreement": round(agree / comparable, 3) if comparable else None, "agreement_ci": wilson(agree, comparable),
            "pairs": {f"{b}->{p}": n for (b, p), n in sorted(pairs.items())},
            "disagreeing_sources": {s: dict(c) for s, c in sorted(by_source.items()) if c["comparable"] > c["agree"]}}
