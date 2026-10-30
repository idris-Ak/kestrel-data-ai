"""Synthetic-only tests for the analysis scripts, plus a customer-text check of committed results."""
import csv
import hashlib
import importlib.util
import json
import re
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("themes", ROOT / "analysis/themes.py")
themes = importlib.util.module_from_spec(spec)
spec.loader.exec_module(themes)
value_spec = importlib.util.spec_from_file_location("value_model", ROOT / "analysis/value_model.py")
value_model = importlib.util.module_from_spec(value_spec)
value_spec.loader.exec_module(value_model)

FORBIDDEN_COLUMNS = {"event_id", "comment_raw", "redacted_text", "text", "evidence", "text_sha256",
                     "request_sha256", "raw_outputs"}
SCRIPT_TEXT_COLUMNS = {"check", "note", "detail", "headline", "scenario_description", "value"}   # written by the scripts


def rec(neg=(), dept="Service", half="H1", band="negative", overall="negative"):
    return {"dealer": "NSW01", "dept": dept, "half": half, "band": band, "eligible": True,
            "overall": overall, "neg": frozenset(neg)}


class ThemeMaths(unittest.TestCase):
    def test_fractional_shares_count_each_comment_once(self):
        rs = [rec(["timeliness"]), rec(["timeliness", "communication"]), rec()]
        shares = themes.fractional_shares(rs)
        self.assertAlmostEqual(shares["timeliness"], 1.5 / 3)
        self.assertAlmostEqual(shares["communication"], 0.5 / 3)
        self.assertAlmostEqual(sum(shares.values()), 2 / 3)   # the theme-less comment stays unassigned

    def test_shares_suppressed_below_min_n(self):
        rows = themes.theme_rows([rec(["timeliness"])] * 29)
        self.assertIsNone(rows[0]["share"])
        self.assertEqual(rows[0]["k"], 29)
        rows = themes.theme_rows([rec(["timeliness"])] * 15 + [rec()] * 15)
        top = rows[0]
        self.assertEqual((top["theme"], top["share"]), ("timeliness", 0.5))
        self.assertLess(top["ci_low"], 0.5)
        self.assertEqual(rows[-1]["theme"], "(no negative theme)")

    def test_bases(self):
        rs = [rec(), rec(band="positive", overall="mixed"), rec(band="neutral", overall="positive")]
        self.assertEqual(len(themes.base(rs)), 1)
        self.assertEqual(len(themes.base(rs, "ai_negative")), 2)

    def test_change_needs_min_n_both_halves(self):
        rate = {"H1": [100, 20], "H2": [100, 25]}
        rs = [rec(["timeliness"], half="H1")] * 30 + [rec(half="H2")] * 29
        self.assertFalse(any(r["tested"] for r in themes.change_rows(rs, "x", rate)))
        rs.append(rec(half="H2"))
        row = next(r for r in themes.change_rows(rs, "x", rate) if r["theme"] == "timeliness")
        self.assertEqual(row["tested"], 1)
        self.assertAlmostEqual(row["diff"], -1.0)
        self.assertAlmostEqual(row["per100_h1"], 20.0)


class SavedLabelLineage(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.db = self.root / "prepared.sqlite"
        self.db.write_bytes(b"synthetic prepared database")
        self.export = self.root / "model_input.jsonl"
        self.export.write_bytes(b"synthetic model input\n")
        self.labels = self.root / "labels.jsonl"
        self.labels.write_text(json.dumps({"event_id": "synthetic-1", "status": "failed"}) + "\n")
        digest = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
        self.manifest = {"run_id": "rebuilt-run", "artifacts": {
            "prepared.sqlite": digest(self.db), "model_input.jsonl": digest(self.export)}}
        self.summary = {"run_id": "original-classified-run", "labels_sha256": digest(self.labels),
                        "model_input_sha256": digest(self.export)}
        (self.root / "manifest.json").write_text(json.dumps(self.manifest))
        (self.root / "summary.json").write_text(json.dumps(self.summary))

    def test_identical_export_allows_rebuilt_run_id(self):
        summary, manifest = themes.verify_label_lineage(self.db, self.labels)
        self.assertNotEqual(summary["run_id"], manifest["run_id"])

    def test_changed_labels_are_rejected(self):
        self.labels.write_text(self.labels.read_text() + "\n")
        with self.assertRaisesRegex(ValueError, "labels.jsonl does not match"):
            themes.verify_label_lineage(self.db, self.labels)

    def test_different_classified_input_is_rejected(self):
        self.summary["model_input_sha256"] = "0" * 64
        (self.root / "summary.json").write_text(json.dumps(self.summary))
        with self.assertRaisesRegex(ValueError, "classification model-input hash"):
            themes.verify_label_lineage(self.db, self.labels)

    def test_changed_prepared_artifact_is_rejected(self):
        for path in (self.db, self.export):
            with self.subTest(artifact=path.name):
                original = path.read_bytes()
                path.write_bytes(original + b"changed")
                with self.assertRaisesRegex(ValueError, "does not match the prepared run manifest"):
                    themes.verify_label_lineage(self.db, self.labels)
                path.write_bytes(original)

    def test_duplicate_failed_event_ids_are_rejected(self):
        self.labels.write_text(self.labels.read_text() * 2)
        with self.assertRaisesRegex(ValueError, "duplicate event_id"):
            themes.load_labels(self.labels)


class ValueAllocation(unittest.TestCase):
    def test_rates_from_different_population_are_rejected(self):
        db = {("NSW01", "Service"): (100, 20), ("NSW02", "Parts"): (0, 0)}
        self.assertTrue(all(r["match"] for r in value_model.compare_rates(dict(db), db)))
        for changed in ({("NSW01", "Service"): (100, 21), ("NSW02", "Parts"): (0, 0)},
                        {("NSW01", "Service"): (100, 20)}):
            with self.subTest(rates=changed):
                with self.assertRaisesRegex(ValueError, "Rates file does not match"):
                    value_model.compare_rates(changed, db)

    def test_fractional_theme_allocation_preserves_value_and_unassigned(self):
        with tempfile.TemporaryDirectory() as tmp:
            shares = Path(tmp) / "shares.csv"
            shares.write_text("department,theme,share,dealer_code,n_negative_text\n"
                              "Service,timeliness,0.5,,100\n"
                              "Service,communication,0.25,,100\n"
                              "Service,work_quality,1.0,NSW01,19\n")
            values = [{"rar_base": 1000.0, "gp_base": 500.0}]
            cells = [{"dealer_code": "NSW01", "department": "Service", "eligible": True}]
            rows = value_model.theme_split(cells, values, shares)
            self.assertEqual({r["share_level"] for r in rows}, {"department"})
            self.assertEqual(sum(r["rar_base"] for r in rows), 1000)
            self.assertEqual(sum(r["gp_base"] for r in rows), 500)
            self.assertEqual(next(r["rar_base"] for r in rows if r["theme"] == "unassigned"), 250)


class CommittedResultsAreAggregates(unittest.TestCase):
    def test_metric_publication_index_matches_saved_tables(self):
        folder = ROOT / "results/metrics"
        index = json.loads((folder / "run_info.json").read_text())["files"]
        self.assertEqual(set(index), {p.name for p in folder.glob("*.csv")})

    def test_no_customer_text_or_identifiers(self):
        files = sorted((ROOT / "results").rglob("*.csv"))
        self.assertTrue(files)
        email = re.compile(r"[\w.+-]+@[\w-]+\.[\w.]+")
        phone = re.compile(r"\b0\d{3}\s?\d{3}\s?\d{3}\b")
        for path in files:
            with path.open(newline="") as f:
                reader = csv.DictReader(f)
                self.assertFalse(FORBIDDEN_COLUMNS & set(reader.fieldnames), path)
                for row in reader:
                    for column, value in row.items():
                        value = value or ""
                        self.assertIsNone(re.fullmatch(r"[0-9a-f]{32,64}", value), path)
                        self.assertFalse(email.search(value) or phone.search(value), path)
                        if column not in SCRIPT_TEXT_COLUMNS:
                            self.assertLessEqual(len(value.split()), 8, (path, column))

    def test_json_results_have_no_record_text_or_identifiers(self):
        def check(value, path):
            if isinstance(value, dict):
                self.assertFalse(FORBIDDEN_COLUMNS & value.keys(), path)
                for child in value.values():
                    check(child, path)
            elif isinstance(value, list):
                for child in value:
                    check(child, path)

        for path in sorted((ROOT / "results").rglob("*.json")):
            check(json.loads(path.read_text()), path)


if __name__ == "__main__":
    unittest.main()
