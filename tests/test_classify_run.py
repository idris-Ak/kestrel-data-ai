"""Prepared-run classification. Synthetic run directory; keyword config only, no network."""
import hashlib
import json
from pathlib import Path
import sqlite3
from tempfile import TemporaryDirectory
import unittest

from kestrel.classify_run import CLASSIFIED_DIR, load_run_input, run_classification
from kestrel.pilot import PilotError


def make_run(root, ratings=(1, 5, 3)):
    run = root / "outputs/prepared/runs/synthetic"
    run.mkdir(parents=True)
    texts = ["Nobody rang me back. Terrible.", "Friendly staff, quick service, thanks.", "It was a service."]
    records = [{"event_id": f"e{i}", "text": t, "department": "Service",
                "text_sha256": hashlib.sha256(t.encode()).hexdigest()} for i, t in enumerate(texts)]
    payload = "".join(json.dumps(r) + "\n" for r in records).encode()
    (run / "model_input.jsonl").write_bytes(payload)
    (run / "manifest.json").write_text(json.dumps({
        "run_id": "synthetic-run", "input_snapshot": "snap", "redaction_version": "rules-3",
        "artifacts": {"model_input.jsonl": hashlib.sha256(payload).hexdigest()}}))
    db = sqlite3.connect(run / "prepared.sqlite")
    db.executescript("""CREATE TABLE source_files(source_id TEXT, path TEXT);
        CREATE TABLE source_observations(observation_id TEXT, source_id TEXT);
        CREATE TABLE feedback_events(event_id TEXT, canonical_observation_id TEXT, rating_value INTEGER,
            rating_scale_max INTEGER, rating_kind TEXT, rating_direction TEXT);
        INSERT INTO source_files VALUES ('s', 'feedback/synthetic.csv');""")
    for i, rating in enumerate(ratings):
        db.execute("INSERT INTO source_observations VALUES (?, 's')", (f"o{i}",))
        db.execute("INSERT INTO feedback_events VALUES (?, ?, ?, 5, 'numeric', 'unspecified')", (f"e{i}", f"o{i}", rating))
    db.commit()
    db.close()
    return run


class ClassifyRunTests(unittest.TestCase):
    def setUp(self):
        self.temporary = TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)
        self.run = make_run(self.root)

    def test_export_must_match_its_manifest(self):
        records, manifest = load_run_input(self.run)
        self.assertEqual((len(records), manifest["run_id"]), (3, "synthetic-run"))
        with (self.run / "model_input.jsonl").open("a") as stream:
            stream.write("\n")
        with self.assertRaisesRegex(PilotError, "does not match the run manifest"):
            load_run_input(self.run)

    def test_classification_writes_labels_summary_and_rating_check(self):
        out, summary = run_classification(self.run, "rules", self.root)
        self.assertEqual(out, self.root / CLASSIFIED_DIR / "synthetic-run")
        lines = [json.loads(l) for l in (out / "labels.jsonl").read_text().splitlines()]
        self.assertEqual([l["event_id"] for l in lines], ["e0", "e1", "e2"])
        self.assertEqual((summary["eligible"], summary["classified"], summary["failed"]), (3, 3, 0))
        self.assertEqual(summary["redaction_version"], "rules-3")
        self.assertEqual(summary["rating_band_check"]["pairs"].get("negative->negative"), 1)
        self.assertNotIn("Nobody rang", (out / "summary.json").read_text())
        for path in [out / "labels.jsonl", *self.root.glob("outputs/ai_pilot/cache/*.jsonl")]:
            payload = path.read_text()
            self.assertNotIn('"evidence":', payload)
            self.assertNotIn('"raw_outputs":', payload)
        reference = lines[0]["themes"][0]["evidence_reference"]
        self.assertEqual(len(reference["sha256"]), 64)
        self.assertLess(reference["normalised_start"], reference["normalised_end"])

    def test_unknown_config_is_refused(self):
        with self.assertRaisesRegex(PilotError, "Unknown configuration"):
            run_classification(self.run, "gpt-9", self.root)


if __name__ == "__main__":
    unittest.main()
