"""Synthetic-only tests for the analysis scripts, plus a customer-text check of committed results."""
import csv
import importlib.util
import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("themes", ROOT / "analysis/themes.py")
themes = importlib.util.module_from_spec(spec)
spec.loader.exec_module(themes)

FORBIDDEN_COLUMNS = {"event_id", "comment_raw", "redacted_text", "text", "evidence", "text_sha256"}
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


class CommittedResultsAreAggregates(unittest.TestCase):
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


if __name__ == "__main__":
    unittest.main()
