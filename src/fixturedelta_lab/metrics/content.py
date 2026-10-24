"""Case-sensitive literal substring rules; no semantic claims."""

from fixturedelta_lab.domain import CheckResult, ContentRules
from fixturedelta_lab.metrics._common import preview, validate_inputs

EVALUATOR_VERSION = "1.0.0"


def evaluate_content_rules(output: str, expectation: ContentRules) -> tuple[CheckResult, ...]:
    """Return required then forbidden checks, omitting empty rule groups."""
    validate_inputs(output, expectation, ContentRules)
    checks: list[CheckResult] = []
    for kind, rules, should_appear in (
        ("required", expectation.required, True),
        ("forbidden", expectation.forbidden, False),
    ):
        if not rules:
            continue
        outcomes = tuple((rule in output) == should_appear for rule in rules)
        details = "; ".join(
            f"{index}: {'PASS' if passed else 'FAIL'} {preview(rule)} "
            f"({'present' if rule in output else 'absent'})"
            for index, (rule, passed) in enumerate(zip(rules, outcomes, strict=True), start=1)
        )
        checks.append(
            CheckResult(
                f"{kind}-content",
                EVALUATOR_VERSION,
                all(outcomes),
                f"{kind.upper()}_CONTENT: {details}.",
            )
        )
    return tuple(checks)
