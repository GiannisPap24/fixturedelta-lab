"""Pure, atomic baseline/candidate comparison; no gates, reports, or runner execution."""

from enum import StrEnum

from fixturedelta_lab.comparison_types import (
    CaseComparison,
    CheckComparison,
    ComparisonProvenance,
    ComparisonResult,
    RunReference,
)
from fixturedelta_lab.domain import CaseResult, CheckResult, ContractError, RunProvenance, RunResult
from fixturedelta_lab.provenance import (
    COMPARISON_CONTRACT_VERSION,
    EVALUATION_CONTRACT_VERSION,
    comparison_sha256,
    result_sha256,
)


class ComparisonErrorCode(StrEnum):
    INVALID_RUN_TYPE = "INVALID_RUN_TYPE"
    INVALID_RESULT_STRUCTURE = "INVALID_RESULT_STRUCTURE"
    INCOMPLETE_PROVENANCE = "INCOMPLETE_PROVENANCE"
    RUN_FINGERPRINT_MISMATCH = "RUN_FINGERPRINT_MISMATCH"
    UNSUPPORTED_EVALUATION_CONTRACT = "UNSUPPORTED_EVALUATION_CONTRACT"
    DATASET_MISMATCH = "DATASET_MISMATCH"
    EVALUATION_CONTRACT_MISMATCH = "EVALUATION_CONTRACT_MISMATCH"
    EVALUATOR_SUITE_MISMATCH = "EVALUATOR_SUITE_MISMATCH"
    RUNTIME_SETTINGS_MISMATCH = "RUNTIME_SETTINGS_MISMATCH"
    DUPLICATE_CASE_ID = "DUPLICATE_CASE_ID"
    CASE_ID_MISMATCH = "CASE_ID_MISMATCH"
    DUPLICATE_EVALUATOR_ID = "DUPLICATE_EVALUATOR_ID"
    EVALUATOR_ID_MISMATCH = "EVALUATOR_ID_MISMATCH"
    EVALUATOR_VERSION_MISMATCH = "EVALUATOR_VERSION_MISMATCH"


class ComparisonError(ValueError):
    """Invalid evidence, never a regression; contains no partial comparison."""

    def __init__(
        self,
        code: ComparisonErrorCode,
        message: str,
        *,
        role: str | None = None,
        case_id: str | None = None,
    ) -> None:
        self.code = code
        self.role = role
        self.case_id = case_id
        super().__init__(f"{code}: {message}")


def _validate_run(run: RunResult, role: str) -> None:
    # Recheck nested values: frozen dataclasses can still arrive from unsafe construction.
    if type(run) is not RunResult:
        raise ComparisonError(
            ComparisonErrorCode.INVALID_RUN_TYPE, "Supply a RunResult from the runner.", role=role
        )
    try:
        if type(run.provenance) is not RunProvenance:
            raise ContractError("provenance: expected RunProvenance")
        run.provenance.__post_init__()
        if not isinstance(run.results, tuple) or not run.results:
            raise ContractError("results: expected a nonempty tuple")
        seen_cases: set[str] = set()
        versions: dict[str, str] = {}
        for case in run.results:
            if type(case) is not CaseResult:
                raise ContractError("results: expected CaseResult values")
            if not isinstance(case.case_id, str):
                raise ContractError("case_id: expected a string")
            if case.case_id in seen_cases:
                raise ComparisonError(
                    ComparisonErrorCode.DUPLICATE_CASE_ID,
                    "Provide exactly one result per case ID.",
                    role=role,
                    case_id=case.case_id,
                )
            seen_cases.add(case.case_id)
            if not isinstance(case.checks, tuple) or not case.checks:
                raise ContractError("checks: expected a nonempty tuple")
            seen_checks: set[str] = set()
            for check in case.checks:
                if type(check) is not CheckResult:
                    raise ContractError("checks: expected CheckResult values")
                check.__post_init__()
                if check.evaluator_id in seen_checks:
                    raise ComparisonError(
                        ComparisonErrorCode.DUPLICATE_EVALUATOR_ID,
                        "Provide exactly one check per evaluator ID in each case.",
                        role=role,
                        case_id=case.case_id,
                    )
                seen_checks.add(check.evaluator_id)
                previous = versions.setdefault(check.evaluator_id, check.evaluator_version)
                if previous != check.evaluator_version:
                    raise ComparisonError(
                        ComparisonErrorCode.EVALUATOR_VERSION_MISMATCH,
                        "Use one version of each evaluator throughout a run.",
                        role=role,
                        case_id=case.case_id,
                    )
            case.__post_init__()
        run.__post_init__()
    except (ContractError, AttributeError, TypeError) as exc:
        raise ComparisonError(
            ComparisonErrorCode.INVALID_RESULT_STRUCTURE,
            "Recreate valid immutable evidence with the runner; inspect the chained cause.",
            role=role,
        ) from exc
    if run.provenance.output_set_id is None or run.result_sha256 is None:
        raise ComparisonError(
            ComparisonErrorCode.INCOMPLETE_PROVENANCE,
            "Rerun evaluation to supply complete 1C provenance and its fingerprint.",
            role=role,
        )
    if result_sha256(run.provenance, run.results) != run.result_sha256:
        raise ComparisonError(
            ComparisonErrorCode.RUN_FINGERPRINT_MISMATCH,
            "Evidence differs from its fingerprint; recreate the run from recorded inputs.",
            role=role,
        )


def _reference(run: RunResult) -> RunReference:
    p = run.provenance
    # _validate_run has rejected absent labels/digest before this construction.
    return RunReference(
        p.output_set_id,
        p.output_set_version,
        p.candidate_version,
        p.outputs_sha256,
        run.result_sha256,
    )


def compare_runs(baseline: RunResult, candidate: RunResult) -> ComparisonResult:
    """Compare validated evidence by ID in baseline case/check order, or raise.

    Case transitions use all-checks-pass. Per-check transitions and the mixed summary
    retain regressions that aggregate case status alone would conceal.
    """
    _validate_run(baseline, "baseline")
    _validate_run(candidate, "candidate")
    left, right = baseline.provenance, candidate.provenance
    for fields, code, message in (
        (
            ("dataset_id", "dataset_version", "dataset_sha256"),
            ComparisonErrorCode.DATASET_MISMATCH,
            "Use the same dataset identity, version and bytes.",
        ),
        (
            ("evaluation_contract_version",),
            ComparisonErrorCode.EVALUATION_CONTRACT_MISMATCH,
            "Evaluate both runs under the same evaluation contract.",
        ),
        (
            ("evaluator_suite_version",),
            ComparisonErrorCode.EVALUATOR_SUITE_MISMATCH,
            "Evaluate both runs with the same evaluator suite version.",
        ),
        (
            ("python_integer_limit",),
            ComparisonErrorCode.RUNTIME_SETTINGS_MISMATCH,
            "Evaluate both runs with identical Python integer conversion limits.",
        ),
    ):
        if any(getattr(left, field) != getattr(right, field) for field in fields):
            raise ComparisonError(code, message)
    if left.evaluation_contract_version != EVALUATION_CONTRACT_VERSION:
        raise ComparisonError(
            ComparisonErrorCode.UNSUPPORTED_EVALUATION_CONTRACT,
            f"This comparator supports evaluation contract {EVALUATION_CONTRACT_VERSION} only.",
        )
    baseline_ids = {case.case_id for case in baseline.results}
    candidate_by_id = {case.case_id: case for case in candidate.results}
    if baseline_ids != candidate_by_id.keys():
        raise ComparisonError(
            ComparisonErrorCode.CASE_ID_MISMATCH,
            f"Match case coverage; missing {sorted(baseline_ids - candidate_by_id.keys())}; "
            f"unexpected {sorted(candidate_by_id.keys() - baseline_ids)}.",
        )
    # Validate every pair before constructing any comparison values.
    for case in baseline.results:
        other = candidate_by_id[case.case_id]
        expected = {check.evaluator_id for check in case.checks}
        actual = {check.evaluator_id: check for check in other.checks}
        if expected != actual.keys():
            raise ComparisonError(
                ComparisonErrorCode.EVALUATOR_ID_MISMATCH,
                f"Match evaluator coverage; missing {sorted(expected - actual.keys())}; "
                f"unexpected {sorted(actual.keys() - expected)}.",
                case_id=case.case_id,
            )
        if any(
            check.evaluator_version != actual[check.evaluator_id].evaluator_version
            for check in case.checks
        ):
            raise ComparisonError(
                ComparisonErrorCode.EVALUATOR_VERSION_MISMATCH,
                "Reevaluate with matching evaluator versions.",
                case_id=case.case_id,
            )
    cases: list[CaseComparison] = []
    for case in baseline.results:
        actual = {check.evaluator_id: check for check in candidate_by_id[case.case_id].checks}
        checks = tuple(
            CheckComparison(
                check.evaluator_id,
                check.evaluator_version,
                check.passed,
                actual[check.evaluator_id].passed,
                check.explanation,
                actual[check.evaluator_id].explanation,
            )
            for check in case.checks
        )
        cases.append(CaseComparison(case.case_id, checks))
    ordered = tuple(cases)
    provenance = ComparisonProvenance(
        baseline=_reference(baseline),
        candidate=_reference(candidate),
        dataset_id=left.dataset_id,
        dataset_version=left.dataset_version,
        dataset_sha256=left.dataset_sha256,
        evaluation_contract_version=left.evaluation_contract_version,
        evaluator_suite_version=left.evaluator_suite_version,
        python_integer_limit=left.python_integer_limit,
        comparison_contract_version=COMPARISON_CONTRACT_VERSION,
    )
    return ComparisonResult(provenance, ordered, comparison_sha256(provenance, ordered))
