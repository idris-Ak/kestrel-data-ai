"""Public command boundaries; no source data, credentials or model calls."""

from contextlib import redirect_stderr, redirect_stdout
import io
import sys
import unittest
from unittest.mock import patch

from kestrel.__main__ import main
from kestrel.classifier import CONFIGS


class CommandTests(unittest.TestCase):
    def invoke(self, *arguments):
        output = io.StringIO()
        with patch.object(sys, "argv", ["kestrel", *arguments]), \
                redirect_stdout(output), redirect_stderr(output):
            with self.assertRaises(SystemExit) as stopped:
                main()
        return stopped.exception.code, output.getvalue()

    def test_help_exposes_only_current_workflow(self):
        code, output = self.invoke("--help")
        self.assertEqual(code, 0)
        self.assertIn("{prepare,classify,ask}", output)
        self.assertNotIn("pilot", output)

    def test_obsolete_commands_are_rejected_before_work(self):
        for command in ("pilot", "pilot-sheet", "pilot-run"):
            with self.subTest(command=command):
                code, _ = self.invoke(command)
                self.assertEqual(code, 2)

    def test_ask_help_makes_no_provider_request(self):
        with patch("kestrel.ask.anthropic.Anthropic") as client:
            code, output = self.invoke("ask", "--help")
        self.assertEqual(code, 0)
        self.assertIn("question", output)
        client.assert_not_called()

    def test_classification_requires_a_run_and_one_configuration(self):
        code, _ = self.invoke("classify")
        self.assertEqual(code, 2)
        code, _ = self.invoke("classify", "--run", "synthetic", "--configs", "haiku-5.5,sonnet-5.5")
        self.assertEqual(code, 2)

    def test_delivered_classifier_fingerprint_is_unchanged(self):
        self.assertEqual(CONFIGS["haiku-5.5"].fingerprint(), "abd37feedbfbab89")


if __name__ == "__main__":
    unittest.main()
