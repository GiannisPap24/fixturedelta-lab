"""Pure evaluator-level quality gates over validated comparison evidence."""

from enum import StrEnum
from fractions import Fraction

from fixturedelta_lab.comparison_types import (
    CaseComparison,
    CheckComparison,
    ComparisonProvenance,
    ComparisonResult,
    RunReference,
)
from fixturedelta_lab.domain import ContractError
from fixturedelta_lab.gate_types import (
    CheckIdentity,
    GatePolicy,
    GateProvenance,
    GateResult,
    GateRuleId,
    GateRuleResult,
)
from fixturedelta_lab.provenance import (
    COMPARISON_CONTRACT_VERSION,
    EVALUATION_CONTRACT_VERSION,
    GATE_CONTRACT_VERSION,
    comparison_sha256,
    gate_sha256,
    policy_sha256,
)


class GateErrorCode(StrEnum):
    INVALID_POLICY = "INVALID_POLICY"
    INVALID_COMPARISON = "INVALID_COMPARISON"
    INCOMPATIBLE_COMPARISON = "INCOMPATIBLE_COMPARISON"
    COMPARISON_FINGERPRINT_MISMATCH = "COMPARISON_FINGERPRINT_MISMATCH"


class GateError(ValueError):
    """Invalid input evidence or policy; never an ordinary failed gate."""

    def __init__(self, code: GateErrorCode, message: str) -> None:
        self.code = code
        super().__init__(f"{code}: {message}")


def _validate_comparison(value: ComparisonResult) -> None:
    try:
        if (
            type(value) is not ComparisonResult
            or type(value.provenance) is not ComparisonProvenance
        ):
            raise ContractError("comparison: expected ComparisonResult and ComparisonProvenance")
        p = value.provenance
        for ref in (p.baseline, p.candidate):
            if type(ref) is not RunReference:
                raise ContractError("references: expected RunReference")
            ref.__post_init__()
        p.__post_init__()
        value.__post_init__()
        versions: dict[str, str] = {}
        for case in value.cases:
            if type(case) is not CaseComparison:
                raise ContractError("cases: expected CaseComparison")
            case.__post_init__()
            for check in case.checks:
                if type(check) is not CheckComparison:
                    raise ContractError("checks: expected CheckComparison")
                check.__post_init__()
                previous = versions.setdefault(check.evaluator_id, check.evaluator_version)
                if previous != check.evaluator_version:
                    raise ContractError("evaluator version: inconsistent across cases")
    except (ContractError, AttributeError, TypeError) as exc:
        raise GateError(
            GateErrorCode.INVALID_COMPARISON,
            "Supply complete immutable evidence from compare_runs; inspect the chained cause.",
        ) from exc
    if (
        p.comparison_contract_version != COMPARISON_CONTRACT_VERSION
        or p.evaluation_contract_version != EVALUATION_CONTRACT_VERSION
    ):
        raise GateError(
            GateErrorCode.INCOMPATIBLE_COMPARISON,
            "Use comparison contract 1.0.0 and evaluation contract 1.1.0.",
        )
    if comparison_sha256(p, value.cases) != value.comparison_sha256:
        raise GateError(
            GateErrorCode.COMPARISON_FINGERPRINT_MISMATCH,
            "Comparison evidence differs from its digest; recreate it with compare_runs.",
        )


def evaluate_gate(comparison: ComparisonResult, policy: GatePolicy) -> GateResult:
    """Evaluate all configured inclusive limits; invalid inputs raise GateError.

    Counts are check-level. Pass rate is passing candidate checks / all paired checks.
    Rate thresholds must be exact Fraction values. No improvements offset regressions.
    """
    try:
        if type(policy) is not GatePolicy:
            raise ContractError("policy: expected GatePolicy")
        policy.__post_init__()
    except (ContractError, AttributeError, TypeError) as exc:
        raise GateError(GateErrorCode.INVALID_POLICY, "Supply a validated GatePolicy.") from exc
    _validate_comparison(comparison)
    regressions: list[CheckIdentity] = []
    failures: list[CheckIdentity] = []
    total = 0
    for case in comparison.cases:
        for check in case.checks:
            total += 1
            identity = CheckIdentity(case.case_id, check.evaluator_id, check.evaluator_version)
            if not check.candidate_passed:
                failures.append(identity)
                if check.baseline_passed:
                    regressions.append(identity)
    passes = total - len(failures)
    rules = [GateRuleResult(GateRuleId.MAX_REGRESSIONS, len(regressions), policy.max_regressions)]
    if policy.max_candidate_failures is not None:
        rules.append(
            GateRuleResult(
                GateRuleId.MAX_CANDIDATE_FAILURES, len(failures), policy.max_candidate_failures
            )
        )
    if policy.min_candidate_pass_rate is not None:
        rules.append(
            GateRuleResult(
                GateRuleId.MIN_CANDIDATE_PASS_RATE,
                Fraction(passes, total),
                policy.min_candidate_pass_rate,
            )
        )
    provenance = GateProvenance(
        comparison.comparison_sha256,
        comparison.provenance.comparison_contract_version,
        policy.policy_id,
        policy.policy_version,
        policy_sha256(policy),
        GATE_CONTRACT_VERSION,
    )
    ordered_rules, ordered_regressions, ordered_failures = (
        tuple(rules),
        tuple(regressions),
        tuple(failures),
    )
    digest = gate_sha256(
        provenance, ordered_rules, ordered_regressions, ordered_failures, total, passes
    )
    return GateResult(
        provenance, ordered_rules, ordered_regressions, ordered_failures, total, passes, digest
    )
