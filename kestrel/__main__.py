"""Local pilot and full data preparation commands."""

import argparse
from pathlib import Path
import sys

from .pilot import PilotError, run_pilot
from .preparation import run_preparation


def main():
    parser = argparse.ArgumentParser(description="Build local traceable feedback datasets")
    parser.add_argument("command", choices=["pilot", "prepare"])
    parser.add_argument("--input-root", type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument("--output-dir", type=Path, default=None)
    args = parser.parse_args()
    try:
        result = (run_pilot if args.command == 'pilot' else run_preparation)(args.input_root, args.output_dir)
    except PilotError as exc:
        print(f"{args.command.capitalize()} failed: {exc}", file=sys.stderr)
        return 1
    if args.command == 'pilot':
        print("Pilot complete: 844 individual observations, 732 events, 112 version links; 71 aggregate responses separate.")
    else:
        counts=result['counts']
        print(f"Preparation complete: {counts['individual_observations']} individual observations, {counts['individual_events']} events, {counts['duplicate_observations']} copy links, {counts['excluded_tests']} test exclusions.")
        print(f"Redacted model-input candidates: {result['model_input']}")
    print(f"Checks: {sum(c['passed'] for c in result['checks'])}/{len(result['checks'])} passed.")
    print(f"Database: {result['database']}")
    print(f"Report: {result['report']}")
    print(('Stage two' if args.command == 'pilot' else 'Stage three')+' awaits user confirmation.')
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
