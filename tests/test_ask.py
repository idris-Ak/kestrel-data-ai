"""Aggregate-question boundaries with synthetic evidence and a mocked provider."""

from contextlib import redirect_stdout
import io
import json
import os
from pathlib import Path
from types import SimpleNamespace
import tempfile
import unittest
from unittest.mock import Mock, patch

from kestrel import ask
from kestrel.pilot import PilotError


QUESTION = "What is the Service negative rate?"
CITATION = "[results/metrics/neg_rate_department.csv:L2]"
ANSWER = f"Service has 25 negatives among 100 rated responses (25%). {CITATION}"


def response(text=ANSWER, stop_reason="end_turn", input_tokens=1000, output_tokens=200):
    return SimpleNamespace(
        content=[SimpleNamespace(type="text", text=text)], stop_reason=stop_reason,
        usage=SimpleNamespace(input_tokens=input_tokens, output_tokens=output_tokens))


class AggregateQuestions(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        for relative in ask.ALLOWLIST:
            path = self.root / relative
            path.parent.mkdir(parents=True, exist_ok=True)
            if path.suffix == ".csv":
                path.write_text("department,n,negative,rate,ci_low,ci_high\nService,100,25,0.25,0.17,0.34\n")
            elif path.suffix == ".json":
                path.write_text(json.dumps({"eligible": 100, "classified": 99, "failed": 1}, indent=2))
            else:
                path.write_text("Synthetic aggregate methods. Voluntary respondents; no causal savings.\n")
        self.ledger = self.root / "outputs/ai_pilot/spend_ledger.jsonl"
        env = patch.dict(os.environ, {"ANTHROPIC_API_KEY": "synthetic-provider-key"})
        env.start()
        self.addCleanup(env.stop)
        self.client = Mock()
        self.client.messages.create.return_value = response()
        factory = patch("kestrel.ask.anthropic.Anthropic", return_value=self.client)
        self.factory = factory.start()
        self.addCleanup(factory.stop)

    def entries(self):
        return [json.loads(line) for line in self.ledger.read_text().splitlines()] if self.ledger.exists() else []

    def test_context_uses_allowlist_and_includes_citable_headers(self):
        private = self.root / "outputs/prepared/current/private.sqlite"
        private.parent.mkdir(parents=True)
        private.write_text("SYNTHETIC_PRIVATE_CANARY")
        (self.root / ".env").write_text("SYNTHETIC_SECRET_CANARY")
        context = ask.build_context(QUESTION, self.root)
        self.assertIn(CITATION, context)
        self.assertIn('[results/metrics/neg_rate_department.csv:L1] fields=', context)
        for field in ('"department"', '"negative"', '"rate"'):
            self.assertIn(field, context)
        self.assertNotIn("SYNTHETIC_PRIVATE_CANARY", context)
        self.assertNotIn("SYNTHETIC_SECRET_CANARY", context)
        self.assertLessEqual(len(context.encode()), ask.MAX_CONTEXT_BYTES)
        self.factory.assert_not_called()

    def test_missing_evidence_stops_before_provider(self):
        (self.root / "results/metrics/neg_rate_department.csv").unlink()
        with self.assertRaises(PilotError):
            ask.ask_question(QUESTION, self.root)
        self.factory.assert_not_called()

    def test_symlinks_cannot_redirect_evidence_to_private_files(self):
        with tempfile.TemporaryDirectory() as outside:
            for target in (Path(outside) / "outside.csv", self.root / "outputs/private.csv"):
                with self.subTest(target=target.name):
                    target.parent.mkdir(parents=True, exist_ok=True)
                    target.write_text("SYNTHETIC_PRIVATE_CANARY")
                    source = self.root / "results/metrics/neg_rate_department.csv"
                    source.unlink()
                    source.symlink_to(target)
                    with self.assertRaises(PilotError):
                        ask.ask_question(QUESTION, self.root)
                    self.factory.assert_not_called()

    def test_invalid_caps_stop_before_provider(self):
        for cap in (float("nan"), float("inf"), float("-inf"), 10.01, 0.0, -1.0):
            with self.subTest(cap=cap):
                with self.assertRaises(PilotError):
                    ask.ask_question(QUESTION, self.root, cap_usd=cap)
                self.factory.assert_not_called()

    def test_invalid_question_size_stops_before_provider(self):
        for question in ("", " \n ", "é" * (ask.MAX_QUESTION_BYTES // 2 + 1)):
            with self.subTest(length=len(question)):
                with self.assertRaises(PilotError):
                    ask.ask_question(question, self.root)
                self.factory.assert_not_called()

    def test_valid_answer_has_exact_usage_cost_and_shared_total(self):
        self.ledger.parent.mkdir(parents=True)
        self.ledger.write_text(json.dumps({"cost_usd": 3.0}) + "\n")
        result = ask.ask_question(QUESTION, self.root)
        self.assertEqual(result["answer"], ANSWER)
        self.assertAlmostEqual(result["cost_usd"], 0.0002)
        self.assertAlmostEqual(result["total_spend_usd"], 3.0002)
        self.assertGreater(result["source_count"], 0)
        self.assertEqual(self.client.messages.create.call_count, 1)
        self.assertAlmostEqual(self.entries()[-1]["cost_usd"], 0.0002)
        self.assertEqual(self.factory.call_args.kwargs["max_retries"], 0)
        self.assertLessEqual(self.factory.call_args.kwargs["timeout"], 60)
        payload = json.dumps(self.client.messages.create.call_args.kwargs)
        self.assertNotIn("synthetic-provider-key", payload)
        persisted = self.ledger.read_text()
        self.assertNotIn(QUESTION, persisted)
        self.assertNotIn(ANSWER, persisted)
        self.assertNotIn("synthetic-provider-key", persisted)

    def test_existing_spend_blocks_call_before_cap_is_exceeded(self):
        self.ledger.parent.mkdir(parents=True)
        self.ledger.write_text(json.dumps({"cost_usd": 9.9999999}) + "\n")
        with self.assertRaises(PilotError):
            ask.ask_question(QUESTION, self.root)
        self.client.messages.create.assert_not_called()
        self.assertEqual(len(self.entries()), 1)

    def test_invalid_citations_are_rejected_but_metered(self):
        for answer in ("No cited evidence.", "Claim [results/metrics/neg_rate_department.csv:L99999]",
                       "Claim [outputs/prepared/current/private.sqlite:L2]", "Claim [../../.env:L1]"):
            with self.subTest(answer=answer):
                before = len(self.entries())
                self.client.messages.create.return_value = response(answer)
                with self.assertRaises(PilotError):
                    ask.ask_question(QUESTION, self.root)
                self.assertEqual(len(self.entries()), before + 1)
                self.assertAlmostEqual(self.entries()[-1]["cost_usd"], 0.0002)

    def test_grouped_and_ranged_citations_accept_only_supplied_lines(self):
        path = self.root / "results/metrics/neg_rate_department.csv"
        path.write_text(path.read_text() + "Sales,100,10,0.10,0.05,0.18\n")
        for spec in ("2, L3", "2-L3", "2–3"):
            with self.subTest(spec=spec):
                answer = f"Compare the departments [results/metrics/neg_rate_department.csv:L{spec}]"
                self.client.messages.create.return_value = response(answer)
                result = ask.ask_question(QUESTION, self.root)
                self.assertEqual(result["answer"], answer)
                self.assertEqual(result["source_count"], 2)

    def test_unknown_or_malformed_reference_invalidates_other_valid_citations(self):
        for bad in ("[results/metrics/neg_rate_department.csv:L2, L99999]",
                    "[results/metrics/neg_rate_department.csv:L2-L3]",
                    "[results/metrics/neg_rate_department.csv:L3-L2]",
                    "[results/metrics/neg_rate_department.csv:L2-L30]",
                    "[results/metrics/neg_rate_department.csv:L2, unknown]",
                    "[docs/METHODS.md:1]"):
            with self.subTest(bad=bad):
                self.client.messages.create.return_value = response(f"Claim {CITATION} plus {bad}")
                before = len(self.entries())
                with self.assertRaises(PilotError):
                    ask.ask_question(QUESTION, self.root)
                self.assertEqual(len(self.entries()), before + 1)

    def test_semicolon_group_accepts_multiple_supplied_files(self):
        path = self.root / "results/metrics/sensitivity.csv"
        path.write_text(path.read_text() + "Sales,100,10,0.10,0.05,0.18\n")
        answer = ("Compare rates [results/metrics/neg_rate_department.csv:L2; "
                  "results/metrics/sensitivity.csv:L2-L3]")
        self.client.messages.create.return_value = response(answer)
        result = ask.ask_question(QUESTION, self.root)
        self.assertEqual(result["answer"], answer)
        self.assertEqual(result["source_count"], 3)

    def test_unknown_second_file_invalidates_semicolon_group(self):
        for second in ("results/metrics/sensitivity.csv:L99999", "outputs/private.csv:L1"):
            with self.subTest(second=second):
                answer = f"Claim [results/metrics/neg_rate_department.csv:L2; {second}]"
                self.client.messages.create.return_value = response(answer)
                before = len(self.entries())
                with self.assertRaises(PilotError):
                    ask.ask_question(QUESTION, self.root)
                self.assertEqual(len(self.entries()), before + 1)

    def test_refused_or_truncated_answer_is_not_returned_but_is_metered(self):
        for reason in ("refusal", "max_tokens"):
            with self.subTest(reason=reason):
                before = len(self.entries())
                self.client.messages.create.return_value = response("SYNTHETIC_RESPONSE_CANARY", reason)
                with self.assertRaises(PilotError) as stopped:
                    ask.ask_question(QUESTION, self.root)
                self.assertNotIn("SYNTHETIC_RESPONSE_CANARY", str(stopped.exception))
                self.assertEqual(len(self.entries()), before + 1)
                self.assertAlmostEqual(self.entries()[-1]["cost_usd"], 0.0002)
                self.assertNotIn("SYNTHETIC_RESPONSE_CANARY", self.ledger.read_text())

    def test_provider_errors_do_not_expose_secrets_or_raw_response(self):
        self.client.messages.create.side_effect = RuntimeError("SYNTHETIC_SECRET_CANARY RAW_RESPONSE_CANARY")
        with self.assertRaises(PilotError) as stopped:
            ask.ask_question(QUESTION, self.root)
        public = str(stopped.exception)
        persisted = self.ledger.read_text() if self.ledger.exists() else ""
        for canary in ("SYNTHETIC_SECRET_CANARY", "RAW_RESPONSE_CANARY", "synthetic-provider-key"):
            self.assertNotIn(canary, public)
            self.assertNotIn(canary, persisted)
        self.assertEqual(len(self.entries()), 1)
        self.assertTrue(self.entries()[0]["cost_estimated"])
        self.assertGreater(self.entries()[0]["cost_usd"], 0)

    def test_cancelled_request_keeps_conservative_budget_charge(self):
        self.client.messages.create.side_effect = KeyboardInterrupt()
        with self.assertRaises(PilotError):
            ask.ask_question(QUESTION, self.root)
        self.assertEqual(len(self.entries()), 1)
        self.assertTrue(self.entries()[0]["cost_estimated"])
        self.assertEqual(self.entries()[0]["status"], "cancelled")
        self.assertGreater(self.entries()[0]["cost_usd"], 0)

    def test_interactive_quit_does_not_call_provider(self):
        with patch("builtins.input", side_effect=["quit"]), \
                patch("kestrel.ask.ask_question") as question, redirect_stdout(io.StringIO()):
            ask.interactive(self.root)
        question.assert_not_called()
        self.factory.assert_not_called()


if __name__ == "__main__":
    unittest.main()
