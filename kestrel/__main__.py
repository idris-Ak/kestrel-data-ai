"""Prepare, classify and question source-traceable feedback aggregates."""

import argparse
from pathlib import Path
import sys

from .classifier import CONFIGS
from .classify_run import run_classification
from .pilot import PilotError
from .preparation import run_preparation

ROOT = Path(__file__).resolve().parents[1]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    prepare = commands.add_parser("prepare", help="Build and validate the complete local dataset")
    prepare.add_argument("--input-root", type=Path, default=ROOT, help="Assignment pack directory")
    prepare.add_argument("--output-dir", type=Path, help="Prepared-run output directory")
    classify = commands.add_parser("classify", help="Classify a prepared run's redacted model input")
    classify.add_argument("--input-root", type=Path, default=ROOT, help="Project directory holding private state")
    classify.add_argument("--run", type=Path, required=True, help="Prepared run directory")
    classify.add_argument("--configs", choices=tuple(CONFIGS), default="haiku-5.5", metavar="CONFIG",
                          help="Classifier configuration (default: haiku-5.5)")
    classify.add_argument("--cap", type=float, default=10.0, help="Cumulative API spending cap in USD")
    ask = commands.add_parser("ask", help="Ask an independent question about saved aggregate results")
    ask.add_argument("question", nargs="?", help="Question (omit for an interactive terminal session)")
    ask.add_argument("--input-root", type=Path, default=ROOT, help="Project directory holding aggregates and private spend state")
    ask.add_argument("--cap", type=float, default=10.0, help="Cumulative API spending cap in USD (at most 10)")
    args = parser.parse_args()
    try:
        if args.command == "prepare":
            result = run_preparation(args.input_root, args.output_dir)
            counts = result["counts"]
            print(f"Preparation complete: {counts['individual_observations']} individual observations, "
                  f"{counts['individual_events']} events, {counts['duplicate_observations']} copy links, "
                  f"{counts['excluded_tests']} test exclusions.")
            print(f"Model input: {result['model_input']}")
            print(f"Checks: {sum(c['passed'] for c in result['checks'])}/{len(result['checks'])} passed.")
            print(f"Database: {result['database']}")
            print(f"Report: {result['report']}")
        elif args.command == "classify":
            out, summary = run_classification(args.run, args.configs, args.input_root, cap_usd=args.cap)
            check = summary["rating_band_check"]
            print(f"Classified {summary['classified']}/{summary['eligible']} comments "
                  f"({summary['failed']} failed) with {summary['config']}; "
                  f"US${summary['pilot_and_stage4_spend_usd']:.4f} cumulative spend "
                  f"of US${args.cap:.2f} cap")
            print(f"Rating-band agreement: {check['agree']}/{check['comparable']} clear-cut cases")
            print(f"Labels: {out / 'labels.jsonl'}")
        else:
            from .ask import ask_question, interactive
            if args.question is None:
                return interactive(args.input_root, args.cap)
            result = ask_question(args.question, args.input_root, args.cap)
            print(result['answer'])
            print(f"Cost: US${result['cost_usd']:.4f}; cumulative US${result['total_spend_usd']:.4f}/US${args.cap:.2f}")
    except PilotError as exc:
        print(f"{args.command.capitalize()} failed: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
