"""Pure deterministic evaluators and a single-case adapter; no run orchestration."""

from fixturedelta_lab.domain import (
    Case,
    CaseResult,
    ContentRules,
    ContractError,
    ExactMatch,
    RecordedOutput,
)
from fixturedelta_lab.metrics.content import evaluate_content_rules
from fixturedelta_lab.metrics.exact import evaluate_exact_match
from fixturedelta_lab.metrics.json_structure import evaluate_json_object

__all__ = [
    "evaluate_case",
    "evaluate_content_rules",
    "evaluate_exact_match",
    "evaluate_json_object",
]


def evaluate_case(case: Case, output: RecordedOutput) -> CaseResult:
    """Evaluate one matching case/output pair without loading files or constructing a run."""
    if not isinstance(case, Case) or not isinstance(output, RecordedOutput):
        raise ContractError("evaluate_case: expected Case and RecordedOutput")
    if case.case_id != output.case_id:
        raise ContractError("evaluate_case: case_id mismatch")
    expectation = case.expectation
    if isinstance(expectation, ExactMatch):
        checks = (evaluate_exact_match(output.output, expectation),)
    elif isinstance(expectation, ContentRules):
        checks = evaluate_content_rules(output.output, expectation)
    else:
        checks = (evaluate_json_object(output.output, expectation),)
    return CaseResult(case.case_id, checks)
