"""Minimal offline check workflow. Exit 0/1 is a completed gate; 2/3 is an error."""

import argparse
import sys
from pathlib import Path

from fixturedelta_lab.comparison import ComparisonError, compare_runs
from fixturedelta_lab.domain import ContractError
from fixturedelta_lab.gate_types import GatePolicy
from fixturedelta_lab.gates import GateError
from fixturedelta_lab.policies import parse_policy
from fixturedelta_lab.reporting import ReportError, render_reports, write_reports
from fixturedelta_lab.runner import RunError, RunErrorCode, evaluate_run


class _UsageError(ValueError):
    pass


class _Parser(argparse.ArgumentParser):
    def error(self, message: str) -> None:
        # argparse's message may echo arbitrary user arguments or paths.
        raise _UsageError("CLI_USAGE")


def _parser() -> argparse.ArgumentParser:
    parser = _Parser(
        prog="fixturedelta",
        description="Offline synthetic recorded-output checks.",
        allow_abbrev=False,
    )
    commands = parser.add_subparsers(dest="command", required=True)
    check = commands.add_parser(
        "check", help="evaluate, compare, gate and write reports", allow_abbrev=False
    )
    for name in ("dataset", "baseline", "candidate", "report-dir"):
        check.add_argument(f"--{name}", type=Path, required=True)
    check.add_argument(
        "--policy", type=Path, help="schema-v1 JSON policy; default is zero regressions"
    )
    for role in ("baseline", "candidate"):
        check.add_argument(f"--{role}-id", default=role, help=f"output-set label (default: {role})")
        check.add_argument(
            f"--{role}-version", default="1.0.0", help="output-set version (default: 1.0.0)"
        )
    return parser


def _error(code: str, action: str) -> None:
    print(f"ERROR {code}: {action}", file=sys.stderr)


def _read_input(path: Path) -> bytes:
    # Windows may raise PermissionError when read_bytes() receives a directory.
    if path.is_dir():
        raise IsADirectoryError
    return path.read_bytes()


def main(argv: list[str] | None = None) -> int:
    try:
        args = _parser().parse_args(argv)
        policy = GatePolicy() if args.policy is None else parse_policy(_read_input(args.policy))
        dataset_bytes = _read_input(args.dataset)
        baseline_bytes = _read_input(args.baseline)
        candidate_bytes = _read_input(args.candidate)
        baseline = evaluate_run(
            dataset_bytes,
            baseline_bytes,
            output_set_id=args.baseline_id,
            output_set_version=args.baseline_version,
        )
        candidate = evaluate_run(
            dataset_bytes,
            candidate_bytes,
            output_set_id=args.candidate_id,
            output_set_version=args.candidate_version,
        )
        comparison = compare_runs(baseline, candidate)
        bundle = render_reports(comparison, policy)
        # Output failures are runtime failures, including existing or unwritable directories.
        try:
            write_reports(args.report_dir, bundle)
        except OSError:
            _error(
                "REPORT_OUTPUT",
                "Choose a new writable report directory; reports were not published.",
            )
            return 3
        c = comparison.check_counts
        print(
            f"Gate {'PASS' if bundle.gate.passed else 'FAIL'} | cases={len(comparison.cases)} "
            f"checks={c.total} regressions={c.regressions} improvements={c.improvements} "
            f"candidate_failures={len(bundle.gate.candidate_failures)}"
        )
        print("Reports published: reports/report.json and reports/report.md")
        print(f"Report SHA-256: {bundle.report_sha256}")
        return 0 if bundle.gate.passed else 1
    except _UsageError:
        _error("CLI_USAGE", "Invalid arguments; use fixturedelta check --help.")
        return 2
    except FileNotFoundError:
        _error("INPUT_NOT_FOUND", "Check the dataset, recorded-output and policy file locations.")
        return 2
    except IsADirectoryError:
        _error("INPUT_NOT_FILE", "Input arguments must refer to readable files.")
        return 2
    except RunError as exc:
        runtime = exc.code in (RunErrorCode.EVALUATOR_ERROR, RunErrorCode.RESULT_INVALID)
        _error(
            str(exc.code), "Check recorded inputs and output-set labels; no reports were published."
        )
        return 3 if runtime else 2
    except (ContractError, ComparisonError, GateError, ReportError):
        _error(
            "INVALID_EVIDENCE_OR_POLICY",
            "Check contracts and non-confidential metadata; no reports published.",
        )
        return 2
    except Exception:
        _error("RUNTIME_FAILURE", "The operation could not complete; check file access and retry.")
        return 3
