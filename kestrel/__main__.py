"""Local pilot, full data preparation and AI pilot commands."""

import argparse
from pathlib import Path
import sys

from .pilot import PilotError, run_pilot
from .preparation import run_preparation

AI_COMMANDS = ["pilot-sample", "pilot-sheet", "pilot-import", "pilot-freeze", "pilot-run", "pilot-score",
               "pilot-agree", "pilot-adjudicate"]


def run_ai_command(args):
    from . import ai_pilot

    root = args.input_root
    names = [n for n in (args.configs or "").split(",") if n]
    if args.command == "pilot-sample":
        manifest, created = ai_pilot.run_sample(root)
        print(f"Split manifest {'created' if created else 'unchanged (frozen)'}: {manifest['counts']}")
    elif args.command == "pilot-sheet":
        print(f"Labelling page: {ai_pilot.write_label_sheet(root, args.split)}")
    elif args.command == "pilot-import":
        if not args.file:
            raise PilotError("Pass the exported label file with --file")
        target, value = ai_pilot.import_labels(args.file, root, replace=args.replace)
        print(f"Imported {len(value['labels'])} {value['split']} labels: {target}")
    elif args.command == "pilot-freeze":
        path, content = ai_pilot.freeze_comparison(names, root)
        print(f"Frozen comparison of {', '.join(content['configs'])}: {path}")
    elif args.command == "pilot-run":
        results, spent = ai_pilot.run_pilot_configs(names, args.split, root, cap_usd=args.cap)
        for name, rows in results.items():
            ok = sum(r["status"] == "ok" for r in rows)
            print(f"{name}: {ok}/{len(rows)} accepted, US${sum(r['cost_usd'] for r in rows):.4f}")
        print(f"Total pilot spend so far: US${spent:.4f} of US${args.cap:.2f} cap")
    elif args.command == "pilot-agree":
        if not (args.file and args.file2):
            raise PilotError("Pass both annotations with --file and --file2")
        result = ai_pilot.run_agreement(args.file, args.file2, root, args.split)
        print(f"Overall-sentiment kappa {result['overall_kappa']} (agreement {result['overall_agreement']}); "
              f"pooled theme kappa {result['theme_kappa_pooled']}; {len(result['disagreements'])}/{result['n']} comments to adjudicate")
    elif args.command == "pilot-adjudicate":
        if not (args.file and args.file2 and args.file3):
            raise PilotError("Pass annotation A, annotation B and the adjudication with --file, --file2 and --file3")
        path, value = ai_pilot.run_adjudication(args.file, args.file2, args.file3, root, args.split)
        print(f"Reference labels written ({sum(l['reference_source'] == 'adjudicated' for l in value['labels'])} adjudicated): {path}")
    elif args.command == "pilot-score":
        report = ai_pilot.write_scorecard(args.split, names, root)
        print(f"Scored {len(report['scores'])} configuration(s) on {report['labelled']} labels. "
              f"Selected: {report['selected'] or 'none'} ({report['verdict']})")
        print(f"Scorecard: {Path(root) / ai_pilot.PILOT_DIR / ('scorecard_' + args.split + '.md')}")
    return 0


def main():
    parser = argparse.ArgumentParser(description="Build local traceable feedback datasets")
    parser.add_argument("command", choices=["pilot", "prepare", *AI_COMMANDS])
    parser.add_argument("--input-root", type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument("--output-dir", type=Path, default=None)
    parser.add_argument("--split", default="calibration", help="AI pilot split: design, calibration or test")
    parser.add_argument("--configs", default="", help="Comma-separated AI pilot configurations")
    parser.add_argument("--file", type=Path, default=None, help="Exported label file to import")
    parser.add_argument("--file2", type=Path, default=None, help="Second annotation (pilot-agree, pilot-adjudicate)")
    parser.add_argument("--file3", type=Path, default=None, help="Adjudication file (pilot-adjudicate)")
    parser.add_argument("--replace", action="store_true", help="Replace previously imported labels")
    parser.add_argument("--cap", type=float, default=10.0, help="Pilot spending cap in USD")
    args = parser.parse_args()
    if args.command in AI_COMMANDS:
        try:
            return run_ai_command(args)
        except PilotError as exc:
            print(f"{args.command} failed: {exc}", file=sys.stderr)
            return 1
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
