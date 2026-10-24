"""Complete, ordered single-run evaluation of local synthetic input snapshots."""

import sys
from enum import StrEnum
from pathlib import Path

from fixturedelta_lab.datasets import parse_dataset, parse_outputs, validate_alignment
from fixturedelta_lab.domain import (
    Case,
    CaseResult,
    ContentRules,
    ContractError,
    ExactMatch,
    RunProvenance,
    RunResult,
)
from fixturedelta_lab.metrics import content, evaluate_case, exact, json_structure
from fixturedelta_lab.provenance import (
    EVALUATION_CONTRACT_VERSION,
    EVALUATOR_SUITE_VERSION,
    content_sha256,
    result_sha256,
)


class RunErrorCode(StrEnum):
    DATASET_READ_ERROR = "DATASET_READ_ERROR"
    OUTPUTS_READ_ERROR = "OUTPUTS_READ_ERROR"
    DATASET_INVALID = "DATASET_INVALID"
    OUTPUTS_INVALID = "OUTPUTS_INVALID"
    ALIGNMENT_INVALID = "ALIGNMENT_INVALID"
    PROVENANCE_INVALID = "PROVENANCE_INVALID"
    EVALUATOR_ERROR = "EVALUATOR_ERROR"
    RESULT_INVALID = "RESULT_INVALID"


class RunError(RuntimeError):
    """An invalid run, with a stable code and no partial result payload."""

    def __init__(self, code: RunErrorCode, message: str, *, case_id: str | None = None):
        self.code = code
        self.case_id = case_id
        super().__init__(f"{code}: {message}")


def _expected_checks(case: Case) -> tuple[tuple[str, str], ...]:
    """Guard adapter output without duplicating any scoring logic."""
    if isinstance(case.expectation, ExactMatch):
        return ((exact.EVALUATOR_ID, exact.EVALUATOR_VERSION),)
    if isinstance(case.expectation, ContentRules):
        return tuple(
            (name, content.EVALUATOR_VERSION)
            for name, rules in (
                ("required-content", case.expectation.required),
                ("forbidden-content", case.expectation.forbidden),
            )
            if rules
        )
    return ((json_structure.EVALUATOR_ID, json_structure.EVALUATOR_VERSION),)


def evaluate_run(
    dataset_bytes: bytes,
    outputs_bytes: bytes,
    *,
    output_set_id: str,
    output_set_version: str,
) -> RunResult:
    """Validate and evaluate one pair of snapshots, or raise RunError atomically.

    Output-set labels are caller assertions because schema v1 has no such fields.
    They must be a lowercase ASCII identifier and a major.minor.patch version.
    False checks are valid evidence, never exceptions or an invalid run.
    """
    try:
        dataset = parse_dataset(dataset_bytes)
    except ContractError as exc:
        raise RunError(
            RunErrorCode.DATASET_INVALID, "Supply a valid, nonempty schema-v1 synthetic dataset."
        ) from exc
    try:
        outputs = parse_outputs(outputs_bytes)
    except ContractError as exc:
        raise RunError(
            RunErrorCode.OUTPUTS_INVALID, "Supply a valid, nonempty schema-v1 output set."
        ) from exc
    try:
        validate_alignment(dataset, outputs)
    except ContractError as exc:
        raise RunError(
            RunErrorCode.ALIGNMENT_INVALID,
            "Match dataset ID/version and provide exactly one output for every case ID.",
        ) from exc
    try:
        provenance = RunProvenance(
            dataset_id=dataset.dataset_id,
            dataset_version=dataset.dataset_version,
            dataset_sha256=content_sha256(dataset_bytes),
            outputs_sha256=content_sha256(outputs_bytes),
            candidate_version=outputs.candidate_version,
            evaluator_suite_version=EVALUATOR_SUITE_VERSION,
            output_set_id=output_set_id,
            output_set_version=output_set_version,
            evaluation_contract_version=EVALUATION_CONTRACT_VERSION,
            python_integer_limit=sys.get_int_max_str_digits(),
        )
    except ContractError as exc:
        raise RunError(
            RunErrorCode.PROVENANCE_INVALID,
            "Supply a lowercase output-set ID and a major.minor.patch output-set version.",
        ) from exc

    by_id = {output.case_id: output for output in outputs.outputs}
    results: list[CaseResult] = []
    for case in dataset.cases:
        try:
            result = evaluate_case(case, by_id[case.case_id])
        except Exception as exc:
            raise RunError(
                RunErrorCode.EVALUATOR_ERROR,
                "Evaluator execution failed; inspect the chained cause and rerun the whole run.",
                case_id=case.case_id,
            ) from exc
        if (
            not isinstance(result, CaseResult)
            or result.case_id != case.case_id
            or tuple((check.evaluator_id, check.evaluator_version) for check in result.checks)
            != _expected_checks(case)
        ):
            raise RunError(
                RunErrorCode.RESULT_INVALID,
                "Evaluator returned inconsistent case/check identities; repair the adapter.",
                case_id=case.case_id,
            )
        results.append(result)
    ordered = tuple(results)
    return RunResult(provenance, ordered, result_sha256=result_sha256(provenance, ordered))


def run_evaluation(
    dataset_path: Path,
    outputs_path: Path,
    *,
    output_set_id: str,
    output_set_version: str,
) -> RunResult:
    """Read each file once; hash and evaluate those same immutable snapshots."""
    try:
        dataset_bytes = dataset_path.read_bytes()
    except OSError as exc:
        raise RunError(
            RunErrorCode.DATASET_READ_ERROR, "Check that the dataset file exists and is readable."
        ) from exc
    try:
        outputs_bytes = outputs_path.read_bytes()
    except OSError as exc:
        raise RunError(
            RunErrorCode.OUTPUTS_READ_ERROR, "Check that the output file exists and is readable."
        ) from exc
    return evaluate_run(
        dataset_bytes,
        outputs_bytes,
        output_set_id=output_set_id,
        output_set_version=output_set_version,
    )
