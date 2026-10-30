"""Stage four: classify every model-eligible comment of a prepared run.

The run is identified by its own manifest; the model-input export must match
the artifact hash recorded there. Classification reuses the pilot's validated
runner, cache and spending ledger, so identical comments are never re-billed.
"""

from collections import Counter
import hashlib
import json
from pathlib import Path

from .ai_pilot import PILOT_DIR, ROOT, band_agreement
from .classifier import CONFIGS, Budget, run_config
from .pilot import PilotError

CLASSIFIED_DIR = "outputs/classified"


def load_run_input(run_dir):
    run_dir = Path(run_dir)
    try:
        manifest = json.loads((run_dir / "manifest.json").read_text(encoding="utf-8"))
        payload = (run_dir / "model_input.jsonl").read_bytes()
    except OSError as exc:
        raise PilotError(f"Not a complete prepared run: {run_dir}") from exc
    if hashlib.sha256(payload).hexdigest() != manifest["artifacts"]["model_input.jsonl"]:
        raise PilotError("model_input.jsonl does not match the run manifest; do not classify a changed export")
    records = [json.loads(line) for line in payload.decode("utf-8").splitlines()]
    if len({r["event_id"] for r in records}) != len(records):
        raise PilotError("Run export has duplicate event IDs")
    for r in records:
        if hashlib.sha256(r["text"].encode()).hexdigest() != r["text_sha256"]:
            raise PilotError("Run export text does not match its hash")
    return records, manifest


def run_classification(run_dir, config_name="haiku-5.5", root=ROOT, cap_usd=10.0, workers=4):
    if config_name not in CONFIGS:
        raise PilotError(f"Unknown configuration: {config_name}")
    records, manifest = load_run_input(run_dir)
    config = CONFIGS[config_name]
    budget = Budget(Path(root) / PILOT_DIR / "spend_ledger.jsonl", cap_usd)
    rows = run_config(config, records, Path(root) / PILOT_DIR / "cache", budget, workers)
    out = Path(root) / CLASSIFIED_DIR / manifest["run_id"]
    out.mkdir(parents=True, exist_ok=True, mode=0o700)
    with (out / "labels.jsonl").open("w", encoding="utf-8") as stream:
        for row in rows:
            labels = row["labels"] or {}
            stream.write(json.dumps({"event_id": row["event_id"], "text_sha256": row["text_sha256"],
                                     "config": config.name, "model": config.model,
                                     "config_fingerprint": row["config_fingerprint"], "status": row["status"],
                                     "overall_sentiment": labels.get("overall_sentiment"),
                                     "themes": labels.get("themes", []), "uncertain": labels.get("uncertain"),
                                     "problems": row["problems"]}, sort_keys=True) + "\n")
    ok = [r for r in rows if r["status"] == "ok"]
    summary = {
        "run_id": manifest["run_id"], "input_snapshot": manifest["input_snapshot"],
        "redaction_version": manifest["redaction_version"],
        "model_input_sha256": manifest["artifacts"]["model_input.jsonl"],
        "config": config.name, "model": config.model, "effort": config.effort,
        "config_fingerprint": config.fingerprint(),
        "eligible": len(records), "classified": len(ok), "failed": len(rows) - len(ok),
        "overall_sentiment": dict(Counter(r["labels"]["overall_sentiment"] for r in ok)),
        "themes": dict(sorted(Counter(f"{t['theme']}:{t['sentiment']}" for r in ok for t in r["labels"]["themes"]).items())),
        "cost_usd_this_config": round(sum(r["cost_usd"] for r in rows), 4),
        "pilot_and_stage4_spend_usd": round(budget.spent(), 4),
        "rating_band_check": band_agreement(records, rows, Path(run_dir) / "prepared.sqlite"),
    }
    (out / "summary.json").write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
    for path in out.iterdir():
        path.chmod(0o600)
    return out, summary
