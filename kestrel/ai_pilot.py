"""Stage-three AI pilot: frozen inputs, sample splits, labelling and scoring.

Only the redacted, allowlisted stage-two export is read. The untouched test
split is drawn first, before any comment text is inspected, and split files
record identifiers and hashes, never comment text.
"""

from collections import Counter
import hashlib
import json
import math
from pathlib import Path
import random

from .classifier import CONFIGS, OVERALL, POLARITY, TAXONOMY, THEMES, Budget, cached_rows, run_config
from .pilot import PilotError

ROOT = Path(__file__).resolve().parents[1]
FROZEN_RUN = "outputs/prepared/runs/ec6f5be3bf88fff169456310a93d249704fab9b3553b9611833d522b7f6b3b3f"
FROZEN_INPUT_SHA256 = "4f1db5d6c3d7865614d34c897bc9036e79c22e8e09587c381bfded7e12b7b09a"
PILOT_DIR = "outputs/ai_pilot"

SEED = 20261030
TEST_SIZE = 100
# Calibration is stratified so every department, and unresolved departments,
# appear among the first examples the reviewer labels.
CALIBRATION_QUOTAS = {"Service": 12, "Sales": 4, "Parts": 2, None: 2}
DESIGN_SIZE = 80


def load_frozen_input(root=ROOT):
    path = Path(root) / FROZEN_RUN / "model_input.jsonl"
    try:
        payload = path.read_bytes()
    except OSError as exc:
        raise PilotError(f"Frozen model input is missing: {FROZEN_RUN}") from exc
    digest = hashlib.sha256(payload).hexdigest()
    if digest != FROZEN_INPUT_SHA256:
        raise PilotError("Frozen model input hash differs; do not sample a changed export")
    records = [json.loads(line) for line in payload.decode("utf-8").splitlines()]
    ids = [r["event_id"] for r in records]
    if len(ids) != len(set(ids)):
        raise PilotError("Frozen model input has duplicate event IDs")
    for r in records:
        if hashlib.sha256(r["text"].encode()).hexdigest() != r["text_sha256"]:
            raise PilotError("Frozen model input text does not match its hash")
    return records, digest


def draw_splits(records, seed=SEED):
    """Reserve the random test split first, then calibration, then design."""
    rng = random.Random(seed)
    pool = sorted(records, key=lambda r: r["event_id"])
    test = rng.sample(pool, TEST_SIZE)
    taken = {r["event_id"] for r in test}
    calibration = []
    for department, quota in CALIBRATION_QUOTAS.items():
        stratum = [r for r in pool if r["event_id"] not in taken and r["department"] == department]
        if len(stratum) < quota:
            raise PilotError(f"Too few candidates to sample calibration stratum {department}")
        chosen = rng.sample(stratum, quota)
        calibration += chosen
        taken |= {r["event_id"] for r in chosen}
    remaining = [r for r in pool if r["event_id"] not in taken]
    design = rng.sample(remaining, DESIGN_SIZE)
    return {"test": test, "calibration": calibration, "design": design}


def split_manifest(splits, input_sha256, seed=SEED):
    def item(r):
        return {"event_id": r["event_id"], "text_sha256": r["text_sha256"], "department": r["department"]}
    return {
        "manifest_version": 1,
        "seed": seed,
        "input": {"run": FROZEN_RUN, "model_input_sha256": input_sha256},
        "order": ["test", "calibration", "design"],
        "rules": {
            "test": f"simple random sample of {TEST_SIZE} from all candidates, drawn first; untouched until a configuration is frozen",
            "calibration": "stratified by department from the remainder: " + ", ".join(
                f"{d or 'unresolved'} {n}" for d, n in CALIBRATION_QUOTAS.items()),
            "design": f"simple random sample of {DESIGN_SIZE} from the remainder; read to draft the theme list and prompt",
        },
        "counts": {name: len(rows) for name, rows in splits.items()},
        "department_counts": {name: dict(Counter(r["department"] or "unresolved" for r in rows))
                              for name, rows in splits.items()},
        "splits": {name: [item(r) for r in rows] for name, rows in splits.items()},
    }


def write_frozen(path, content):
    """Write once; an existing file must match exactly, so splits cannot be silently redrawn."""
    text = json.dumps(content, indent=2, ensure_ascii=False) + "\n"
    if path.exists():
        if path.read_text(encoding="utf-8") != text:
            raise PilotError(f"{path.name} already exists with different content; it is frozen")
        return False
    path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    path.write_text(text, encoding="utf-8")
    return True


def run_sample(root=ROOT):
    records, digest = load_frozen_input(root)
    manifest = split_manifest(draw_splits(records), digest)
    created = write_frozen(Path(root) / PILOT_DIR / "split_manifest.json", manifest)
    return manifest, created


def manifest_path(root=ROOT):
    return Path(root) / PILOT_DIR / "split_manifest.json"


def split_records(root=ROOT, split="design"):
    """Return frozen-input records for one split, in manifest order."""
    records, _ = load_frozen_input(root)
    try:
        manifest = json.loads(manifest_path(root).read_text(encoding="utf-8"))
    except OSError as exc:
        raise PilotError("No split manifest; run `python -m kestrel pilot-sample` first") from exc
    if split not in manifest["splits"]:
        raise PilotError(f"Unknown split: {split}")
    by_id = {r["event_id"]: r for r in records}
    rows = [by_id[item["event_id"]] for item in manifest["splits"][split]]
    if any(r["text_sha256"] != item["text_sha256"] for r, item in zip(rows, manifest["splits"][split])):
        raise PilotError("Split manifest hashes do not match the frozen input")
    return rows


def manifest_sha256(root=ROOT):
    return hashlib.sha256(manifest_path(root).read_bytes()).hexdigest()


# ---------------------------------------------------------------- labelling

LABEL_SPLITS = ("calibration", "test")


def write_label_sheet(root=ROOT, split="calibration"):
    """A self-contained offline page: comment text and department only, no ratings or predictions."""
    if split not in LABEL_SPLITS:
        raise PilotError(f"Human labels are collected only for {', '.join(LABEL_SPLITS)}")
    records = split_records(root, split)
    data = {"split": split, "manifest_sha256": manifest_sha256(root),
            "taxonomy_version": TAXONOMY["taxonomy_version"],
            "overall": TAXONOMY["overall_sentiment"],
            "themes": {k: {"label": t["label"], "definition": t["definition"]} for k, t in TAXONOMY["themes"].items()},
            "records": [{"event_id": r["event_id"], "text_sha256": r["text_sha256"],
                         "text": r["text"], "department": r["department"]} for r in records]}
    # Escaping "<" keeps comment text from closing the script element.
    payload = json.dumps(data, ensure_ascii=False).replace("<", "\\u003c")
    template = (Path(__file__).parent / "label_sheet.html").read_text(encoding="utf-8")
    path = Path(root) / PILOT_DIR / "labelling" / f"{split}.html"
    path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    path.write_text(template.replace("__DATA__", payload), encoding="utf-8")
    path.chmod(0o600)
    return path


def validate_labels(value, records, expected_manifest):
    """Check an exported label file against the frozen split; return problems."""
    problems = []
    if value.get("label_format") != 1:
        problems.append("unsupported label_format")
    if value.get("manifest_sha256") != expected_manifest:
        problems.append("labels were made against a different split manifest")
    if value.get("taxonomy_version") != TAXONOMY["taxonomy_version"]:
        problems.append("labels use a different taxonomy version")
    expected = {r["event_id"]: r["text_sha256"] for r in records}
    labels = value.get("labels", [])
    ids = [label.get("event_id") for label in labels]
    if sorted(ids) != sorted(expected) or len(ids) != len(set(ids)):
        problems.append("labels do not cover exactly the split's events")
    for label in labels:
        where = str(label.get("event_id", "?"))[:12]
        if expected.get(label.get("event_id")) != label.get("text_sha256"):
            problems.append(f"{where}: text hash differs")
        if label.get("overall_sentiment") not in OVERALL:
            problems.append(f"{where}: overall sentiment missing")
        seen = set()
        for theme in label.get("themes", []):
            if theme.get("theme") not in THEMES or theme.get("sentiment") not in POLARITY or theme.get("theme") in seen:
                problems.append(f"{where}: invalid theme label")
            seen.add(theme.get("theme"))
    return problems


def import_labels(source, root=ROOT, replace=False):
    try:
        value = json.loads(Path(source).read_text(encoding="utf-8"))
    except OSError as exc:
        raise PilotError(f"Label file not found: {source}. Export it from the labelling page first; "
                         "browsers may add a suffix such as ' (1)'.") from exc
    except ValueError as exc:
        raise PilotError(f"Label file is not valid JSON: {source}") from exc
    split = value.get("split")
    if split not in LABEL_SPLITS:
        raise PilotError("Label file names an unknown split")
    problems = validate_labels(value, split_records(root, split), manifest_sha256(root))
    if problems:
        raise PilotError("Label file rejected: " + "; ".join(problems[:10]))
    target = Path(root) / PILOT_DIR / "labels" / f"{split}.json"
    if replace and target.exists():
        target.unlink()
    write_frozen(target, value)
    target.chmod(0o600)
    return target, value


def load_labels(root=ROOT, split="test"):
    path = Path(root) / PILOT_DIR / "labels" / f"{split}.json"
    try:
        return {label["event_id"]: label for label in json.loads(path.read_text(encoding="utf-8"))["labels"]}
    except OSError as exc:
        raise PilotError(f"No imported {split} labels; label and import them first") from exc


# ------------------------------------------------------------------ running

SELECTION = {
    "rule": "Among configurations with at most 2% failures, choose the cheapest per comment whose "
            "negative-theme micro-F1 and overall-sentiment accuracy are each within 0.05 of the best configuration.",
    "acceptance": {"overall_accuracy_min": 0.85, "negative_theme_micro_f1_min": 0.75, "max_failure_rate": 0.02},
    "note": "Targets confirmed by the user on 30 October 2026, before any test-split call. Test reference labels are AI-made (user decision).",
    # Reference annotators run on Opus 5.5, so its agreement with them is partly self-agreement.
    "not_selectable": {"opus-5.5": "same model as the reference annotators; reported as self-evaluation only"},
    "reference": "Two independent blind AI annotations of the test split; disagreements settled by a third blind AI adjudicator.",
}


def freeze_comparison(names, root=ROOT):
    """Record which configurations go to the test split, and how one is chosen, before any test call."""
    unknown = [n for n in names if n not in CONFIGS]
    if unknown:
        raise PilotError(f"Unknown configuration(s): {', '.join(unknown)}")
    content = {"frozen_version": 1, "manifest_sha256": manifest_sha256(root),
               "taxonomy_version": TAXONOMY["taxonomy_version"],
               "configs": {n: {"provider": CONFIGS[n].provider, "model": CONFIGS[n].model,
                               "effort": CONFIGS[n].effort, "fingerprint": CONFIGS[n].fingerprint()} for n in names},
               "selection": SELECTION}
    path = Path(root) / PILOT_DIR / "frozen_config.json"
    write_frozen(path, content)
    return path, content


def run_pilot_configs(names, split, root=ROOT, cap_usd=10.0, workers=4):
    unknown = [n for n in names if n not in CONFIGS]
    if unknown:
        raise PilotError(f"Unknown configuration(s): {', '.join(unknown)}")
    if split == "test":
        frozen_path = Path(root) / PILOT_DIR / "frozen_config.json"
        if not frozen_path.exists():
            raise PilotError("The test split stays untouched until `pilot-freeze` records the comparison")
        frozen = json.loads(frozen_path.read_text(encoding="utf-8"))
        for name in names:
            if frozen["configs"].get(name, {}).get("fingerprint") != CONFIGS[name].fingerprint():
                raise PilotError(f"{name} is not in the frozen comparison, or its prompt/settings changed since freezing")
    records = split_records(root, split)
    budget = Budget(Path(root) / PILOT_DIR / "spend_ledger.jsonl", cap_usd)
    results = {}
    for name in names:
        results[name] = run_config(CONFIGS[name], records, Path(root) / PILOT_DIR / "cache", budget, workers)
    return results, budget.spent()


# ------------------------------------------------------------------ scoring

def wilson(successes, n, z=1.96):
    if n == 0:
        return (None, None)
    p = successes / n
    centre = (p + z * z / (2 * n)) / (1 + z * z / n)
    half = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / (1 + z * z / n)
    return (round(centre - half, 3), round(centre + half, 3))


def prf(tp, fp, fn):
    precision = tp / (tp + fp) if tp + fp else None
    recall = tp / (tp + fn) if tp + fn else None
    f1 = 2 * tp / (2 * tp + fp + fn) if tp + fp + fn else None
    return precision, recall, f1


def pairs(themes, polarity=None):
    return {(t["theme"], t["sentiment"]) for t in themes if polarity is None or t["sentiment"] == polarity}


def micro_f1(gold_sets, pred_sets):
    tp = sum(len(g & p) for g, p in zip(gold_sets, pred_sets))
    fp = sum(len(p - g) for g, p in zip(gold_sets, pred_sets))
    fn = sum(len(g - p) for g, p in zip(gold_sets, pred_sets))
    return prf(tp, fp, fn)[2]


def bootstrap_ci(gold_sets, pred_sets, reps=1000, seed=SEED):
    """Comment-level bootstrap interval for micro-F1."""
    rng = random.Random(seed)
    n = len(gold_sets)
    values = []
    for _ in range(reps):
        idx = [rng.randrange(n) for _ in range(n)]
        value = micro_f1([gold_sets[i] for i in idx], [pred_sets[i] for i in idx])
        if value is not None:
            values.append(value)
    values.sort()
    if not values:
        return (None, None)
    return (round(values[int(0.025 * len(values))], 3), round(values[int(0.975 * len(values)) - 1], 3))


def score(rows, gold):
    """Score one configuration against human labels. Failures count as empty predictions."""
    by_id = {row["event_id"]: row for row in rows}
    ids = sorted(gold)
    preds = [by_id.get(i) for i in ids]
    ok = [p is not None and p["status"] == "ok" for p in preds]
    pred_labels = [p["labels"] if okay else {"overall_sentiment": None, "themes": []} for p, okay in zip(preds, ok)]
    n = len(ids)
    correct = sum(pl["overall_sentiment"] == gold[i]["overall_sentiment"] for pl, i in zip(pred_labels, ids))
    result = {"n": n, "coverage": sum(ok), "failures": n - sum(ok),
              "overall_accuracy": round(correct / n, 3) if n else None,
              "overall_accuracy_ci": wilson(correct, n),
              "cost_usd": round(sum(p["cost_usd"] for p in preds if p), 4),
              "input_tokens": sum(p["usage"].get("input_tokens", 0) for p in preds if p),
              "output_tokens": sum(p["usage"].get("output_tokens", 0) for p in preds if p),
              "mean_seconds": round(sum(p["seconds"] for p in preds if p) / n, 2) if n else None}
    confusion = Counter((gold[i]["overall_sentiment"], pl["overall_sentiment"] or "failed") for pl, i in zip(pred_labels, ids))
    result["overall_confusion"] = {f"{g}->{p}": c for (g, p), c in sorted(confusion.items())}
    for name, polarity in (("theme_sentiment", None), ("negative_theme", "negative"), ("positive_theme", "positive")):
        g = [pairs(gold[i]["themes"], polarity) for i in ids]
        p = [pairs(pl["themes"], polarity) for pl in pred_labels]
        result[f"{name}_micro_f1"] = None if micro_f1(g, p) is None else round(micro_f1(g, p), 3)
        result[f"{name}_micro_f1_ci"] = bootstrap_ci(g, p)
    per_theme = {}
    for theme in THEMES:
        for polarity in POLARITY:
            g = [(theme, polarity) in pairs(gold[i]["themes"]) for i in ids]
            p = [(theme, polarity) in pairs(pl["themes"]) for pl in pred_labels]
            tp = sum(a and b for a, b in zip(g, p))
            fp = sum(b and not a for a, b in zip(g, p))
            fn = sum(a and not b for a, b in zip(g, p))
            if tp + fn or fp:
                precision, recall, f1 = prf(tp, fp, fn)
                per_theme[f"{theme}:{polarity}"] = {"support": tp + fn, "predicted": tp + fp,
                    "precision": None if precision is None else round(precision, 3),
                    "recall": None if recall is None else round(recall, 3),
                    "f1": None if f1 is None else round(f1, 3)}
    result["per_theme"] = per_theme
    return result


def select(scores):
    """Apply the predeclared selection rule to scored configurations."""
    eligible = {n: s for n, s in scores.items()
                if n != "rules" and n not in SELECTION["not_selectable"]
                and s["n"] and s["failures"] / s["n"] <= SELECTION["acceptance"]["max_failure_rate"]}
    if not eligible:
        return None, "no model configuration met the failure limit"
    best_f1 = max(s["negative_theme_micro_f1"] or 0 for s in eligible.values())
    best_acc = max(s["overall_accuracy"] or 0 for s in eligible.values())
    near = {n: s for n, s in eligible.items()
            if (s["negative_theme_micro_f1"] or 0) >= best_f1 - 0.05 and (s["overall_accuracy"] or 0) >= best_acc - 0.05}
    chosen = min(near, key=lambda n: (near[n]["cost_usd"] / near[n]["n"], n))
    s, a = near[chosen], SELECTION["acceptance"]
    passed = (s["overall_accuracy"] >= a["overall_accuracy_min"]
              and (s["negative_theme_micro_f1"] or 0) >= a["negative_theme_micro_f1_min"])
    return chosen, "meets acceptance targets" if passed else "best available, but below acceptance targets"


def write_scorecard(split, names, root=ROOT):
    """Score saved results against human labels; makes no model calls."""
    gold = load_labels(root, split)
    records = split_records(root, split)
    cache_dir = Path(root) / PILOT_DIR / "cache"
    scores = {n: score(cached_rows(CONFIGS[n], records, cache_dir), gold) for n in names}
    chosen, verdict = select(scores) if split == "test" else (None, "development split: no selection")
    flags = {k: sum(bool(g.get(k)) for g in gold.values()) for k in ("privacy_issue", "not_english", "other")}
    report = {"split": split, "manifest_sha256": manifest_sha256(root), "labelled": len(gold),
              "reviewer_flags": flags, "scores": scores, "selected": chosen, "verdict": verdict,
              "selection": SELECTION}
    out = Path(root) / PILOT_DIR / f"scorecard_{split}.json"
    out.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")

    def fmt(value, ci=None):
        if value is None:
            return "–"
        return f"{value:.2f}" + (f" ({ci[0]:.2f}–{ci[1]:.2f})" if ci and ci[0] is not None else "")

    lines = [f"# AI pilot scorecard: {split} split", "",
             f"{len(gold)} reference-labelled comments. Reviewer flags: {flags['privacy_issue']} personal-info, "
             f"{flags['not_english']} not English, {flags['other']} other-opinion. 95% intervals in brackets.", "",
             "Reference labels are AI-generated, not human: " + (SELECTION["reference"] if split == "test"
                 else "one blind AI annotator, used for prompt development only."), "",
             "| Config | Coverage | Overall accuracy | Negative-theme F1 | Theme+sentiment F1 | Cost (US$) | Cost / 1k comments | Mean s |",
             "|---|---:|---:|---:|---:|---:|---:|---:|"]
    for n, s in scores.items():
        per_k = s["cost_usd"] / s["n"] * 1000 if s["n"] else 0
        shown = f"{n} (self-evaluation, not selectable)" if n in SELECTION["not_selectable"] else n
        lines.append(f"| {shown} | {s['coverage']}/{s['n']} | {fmt(s['overall_accuracy'], s['overall_accuracy_ci'])} | "
                     f"{fmt(s['negative_theme_micro_f1'], s['negative_theme_micro_f1_ci'])} | "
                     f"{fmt(s['theme_sentiment_micro_f1'], s['theme_sentiment_micro_f1_ci'])} | "
                     f"{s['cost_usd']:.4f} | {per_k:.2f} | {s['mean_seconds']} |")
    lines += ["", f"**Selection:** {chosen or 'none'} — {verdict}.", "", f"Rule: {SELECTION['rule']}", "",
              "Per-theme results, confusion matrices and token counts: `scorecard_" + split + ".json`. No comment text is included.", ""]
    (Path(root) / PILOT_DIR / f"scorecard_{split}.md").write_text("\n".join(lines), encoding="utf-8")
    return report


# ------------------------------------------------------- reference agreement

def label_value(path):
    try:
        return json.loads(Path(path).read_text(encoding="utf-8"))
    except OSError as exc:
        raise PilotError(f"Label file not found: {path}") from exc


def theme_state(label, theme):
    return next((t["sentiment"] for t in label["themes"] if t["theme"] == theme), "none")


def cohen_kappa(a, b):
    """Cohen's kappa for two equal-length sequences of category values."""
    n = len(a)
    if n == 0:
        return None
    observed = sum(x == y for x, y in zip(a, b)) / n
    count_a, count_b = Counter(a), Counter(b)
    expected = sum(count_a[c] * count_b[c] for c in set(a) | set(b)) / (n * n)
    if expected == 1:
        return 1.0 if observed == 1 else None
    return round((observed - expected) / (1 - expected), 3)


def agreement(value_a, value_b):
    """Inter-annotator agreement and the list of comments needing adjudication (IDs only)."""
    a = {label["event_id"]: label for label in value_a["labels"]}
    b = {label["event_id"]: label for label in value_b["labels"]}
    if set(a) != set(b):
        raise PilotError("The two annotations cover different comments")
    ids = sorted(a)
    overall_a = [a[i]["overall_sentiment"] for i in ids]
    overall_b = [b[i]["overall_sentiment"] for i in ids]
    pooled_a = [theme_state(a[i], t) for i in ids for t in THEMES]
    pooled_b = [theme_state(b[i], t) for i in ids for t in THEMES]
    per_theme = {}
    for theme in THEMES:
        ta, tb = [theme_state(a[i], theme) for i in ids], [theme_state(b[i], theme) for i in ids]
        if any(v != "none" for v in ta + tb):
            per_theme[theme] = {"kappa": cohen_kappa(ta, tb), "agreement": round(sum(x == y for x, y in zip(ta, tb)) / len(ids), 3),
                                "marked_a": sum(v != "none" for v in ta), "marked_b": sum(v != "none" for v in tb)}
    disagreements = []
    for i in ids:
        fields = [t for t in THEMES if theme_state(a[i], t) != theme_state(b[i], t)]
        if a[i]["overall_sentiment"] != b[i]["overall_sentiment"]:
            fields = ["overall_sentiment"] + fields
        if fields:
            disagreements.append({"event_id": i, "text_sha256": a[i]["text_sha256"], "fields": fields,
                                  "annotator_a": {"overall_sentiment": a[i]["overall_sentiment"], "themes": a[i]["themes"]},
                                  "annotator_b": {"overall_sentiment": b[i]["overall_sentiment"], "themes": b[i]["themes"]}})
    return {"n": len(ids),
            "overall_kappa": cohen_kappa(overall_a, overall_b),
            "overall_agreement": round(sum(x == y for x, y in zip(overall_a, overall_b)) / len(ids), 3),
            "theme_kappa_pooled": cohen_kappa(pooled_a, pooled_b),
            "comments_identical": len(ids) - len(disagreements),
            "per_theme": per_theme, "disagreements": disagreements}


def run_agreement(file_a, file_b, root=ROOT, split="test"):
    value_a, value_b = label_value(file_a), label_value(file_b)
    records = split_records(root, split)
    for value in (value_a, value_b):
        problems = validate_labels(value, records, manifest_sha256(root))
        if problems:
            raise PilotError("Annotation rejected: " + "; ".join(problems[:10]))
    result = agreement(value_a, value_b)
    result.update(annotator_a=value_a.get("reviewer", ""), annotator_b=value_b.get("reviewer", ""))
    staging = Path(root) / PILOT_DIR / "labels-staging"
    (staging / f"{split}_agreement.json").write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    return result


def adjudicate(value_a, value_b, adjudication):
    """Agreed comments keep the shared label; every disputed comment takes the adjudicator's full label."""
    result = agreement(value_a, value_b)
    disputed = {d["event_id"] for d in result["disagreements"]}
    decided = {label["event_id"]: label for label in adjudication["labels"]}
    if set(decided) != disputed:
        raise PilotError(f"Adjudication must cover exactly the {len(disputed)} disputed comments")
    labels = []
    for label in value_a["labels"]:
        source = decided.get(label["event_id"])
        merged = dict(label)
        if source:
            merged.update(overall_sentiment=source["overall_sentiment"], themes=source["themes"],
                          note=source.get("note", ""), reference_source="adjudicated")
        else:
            merged["reference_source"] = "annotators_agreed"
        labels.append(merged)
    return {**{k: value_a[k] for k in ("label_format", "split", "manifest_sha256", "taxonomy_version")},
            "reviewer": (f"AI reference: annotator A ({value_a.get('reviewer', '')}); annotator B ({value_b.get('reviewer', '')}); "
                         f"adjudicator ({adjudication.get('reviewer', '')}). Not human labels."),
            "agreement": {k: result[k] for k in ("n", "overall_kappa", "overall_agreement", "theme_kappa_pooled", "comments_identical")},
            "labels": labels}


def run_adjudication(file_a, file_b, file_adjudication, root=ROOT, split="test"):
    value = adjudicate(label_value(file_a), label_value(file_b), label_value(file_adjudication))
    problems = validate_labels(value, split_records(root, split), manifest_sha256(root))
    if problems:
        raise PilotError("Adjudicated labels rejected: " + "; ".join(problems[:10]))
    path = Path(root) / PILOT_DIR / "labels-staging" / f"{split}_reference.json"
    path.write_text(json.dumps(value, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    path.chmod(0o600)
    return path, value


# ------------------------------------------------------ model-free check

def rating_band(value, scale, kind, direction):
    """Band a native rating on the oriented (higher-is-better) scale: bottom-2/top-2 box on 5 points.

    Unlabelled scales are treated as higher-is-better (analysis decision D1); explicit reversed
    legends are honoured. Ratings are read locally and never sent to a model.
    """
    if value is None:
        return None
    oriented = scale + 1 - value if direction == "low_is_good" else value
    if scale == 3:
        return {1: "negative", 2: "neutral", 3: "positive"}[oriented]
    five = math.ceil(oriented / 2) if scale == 10 else oriented
    return "negative" if five <= 2 else "neutral" if five == 3 else "positive"


def rating_agreement(config_name, split="test", root=ROOT):
    """Compare predicted overall sentiment with the customer's own rating band (no labels involved)."""
    import sqlite3
    records = split_records(root, split)
    rows = {r["event_id"]: r for r in cached_rows(CONFIGS[config_name], records, Path(root) / PILOT_DIR / "cache")}
    db = sqlite3.connect(f"file:{Path(root) / FROZEN_RUN / 'prepared.sqlite'}?mode=ro", uri=True)
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
    return {"config": config_name, "split": split, "comparable": comparable, "agree": agree,
            "agreement": round(agree / comparable, 3) if comparable else None, "agreement_ci": wilson(agree, comparable),
            "pairs": {f"{b}->{p}": n for (b, p), n in sorted(pairs.items())},
            "disagreeing_sources": {s: dict(c) for s, c in sorted(by_source.items()) if c["comparable"] > c["agree"]}}
