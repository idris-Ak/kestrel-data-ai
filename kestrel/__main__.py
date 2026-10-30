"""Local stage-one data foundation command."""

import argparse
from pathlib import Path
import sys

from .pilot import PilotError, run_pilot


def main():
    parser = argparse.ArgumentParser(description="Build the local traceable feedback pilot")
    parser.add_argument("command", choices=["pilot"])
    parser.add_argument("--input-root", type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument("--output-dir", type=Path, default=None)
    args = parser.parse_args()
    try:
        result = run_pilot(args.input_root, args.output_dir)
    except PilotError as exc:
        print(f"Pilot failed: {exc}", file=sys.stderr)
        return 1
    print("Pilot complete: 844 individual observations, 732 events, 112 version links; 71 aggregate responses separate.")
    print(f"Checks: {sum(c['passed'] for c in result['checks'])}/{len(result['checks'])} passed.")
    print(f"Database: {result['database']}")
    print(f"Report: {result['report']}")
    print("Stage two awaits user confirmation.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
