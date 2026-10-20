"""Terminal entry point for the independent prototype."""

import argparse
import sys
from pathlib import Path

import httpx
from pydantic import ValidationError

from .cpic import CPICClient, load_snapshot, save_snapshot
from .errors import AppError
from .matching import match_patient
from .models import PatientCase
from .reporting import format_finding
from .scope import validate_scope


def parser() -> argparse.ArgumentParser:
    root = argparse.ArgumentParser(
        description="Match a fictional patient's reported genetic results to CPIC guidance."
    )
    root.add_argument("--case", type=Path, required=True, help="Patient JSON file")
    evidence = root.add_mutually_exclusive_group()
    evidence.add_argument(
        "--snapshot", type=Path, help="Use saved CPIC evidence instead of live requests"
    )
    evidence.add_argument("--save-snapshot", type=Path, help="Save this run's live CPIC evidence")
    root.add_argument(
        "--details", action="store_true", help="Show source comments and full provenance"
    )
    return root


def load_case(path: Path) -> PatientCase:
    try:
        return PatientCase.model_validate_json(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, ValidationError) as exc:
        raise AppError("invalid_case", f"Cannot load case: {exc}") from exc


def main(argv: list[str] | None = None) -> int:
    args = parser().parse_args(argv)
    try:
        case = load_case(args.case)
        validate_scope(case)
        if args.snapshot:
            evidence = load_snapshot(args.snapshot, case.medication)
        else:
            with httpx.Client() as http:
                evidence = CPICClient(http).retrieve(case.medication)
        finding = match_patient(case, evidence)
        if args.save_snapshot:
            save_snapshot(evidence, args.save_snapshot)
        print(format_finding(finding, details=args.details))
        return 0
    except AppError as exc:
        print(f"OUTCOME [{exc.code}]: {exc.message}", file=sys.stderr)
        print("No completed finding was produced.", file=sys.stderr)
        return 2
    except KeyboardInterrupt:
        print("Interrupted; no completed finding was produced.", file=sys.stderr)
        return 130


if __name__ == "__main__":
    raise SystemExit(main())
