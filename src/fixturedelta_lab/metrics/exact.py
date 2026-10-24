"""Literal Unicode equality: no normalization, trimming, or case folding."""

from fixturedelta_lab.domain import CheckResult, ExactMatch
from fixturedelta_lab.metrics._common import preview, validate_inputs

EVALUATOR_ID = "exact-match"
EVALUATOR_VERSION = "1.0.0"


def evaluate_exact_match(output: str, expectation: ExactMatch) -> CheckResult:
    validate_inputs(output, expectation, ExactMatch)
    expected = expectation.expected
    passed = output == expected
    if passed:
        reason = f"EXACT_MATCH: identical text ({len(output)} code points)."
    else:
        offset = next(
            (
                i
                for i, (actual, wanted) in enumerate(zip(output, expected, strict=False))
                if actual != wanted
            ),
            min(len(output), len(expected)),
        )
        reason = (
            f"EXACT_MISMATCH: first difference at code-point offset {offset}; "
            f"expected {preview(expected)}; observed {preview(output)}. "
            "Case, whitespace, and Unicode normalization forms are significant."
        )
    return CheckResult(EVALUATOR_ID, EVALUATOR_VERSION, passed, reason)
