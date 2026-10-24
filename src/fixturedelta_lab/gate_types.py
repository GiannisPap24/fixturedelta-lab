"""Immutable policies and gate evidence. All thresholds refer to evaluator checks."""

from dataclasses import dataclass
from enum import StrEnum
from fractions import Fraction

from fixturedelta_lab.comparison_types import _digest
from fixturedelta_lab.domain import ContractError, _identifier, _items, _unique, _version


def _count(value: object) -> None:
    if type(value) is not int or value < 0:
        raise ContractError("count: expected a nonnegative integer, not a boolean")


def _rate(value: object) -> None:
    if type(value) is not Fraction or not 0 <= value <= 1:
        raise ContractError("pass rate: expected Fraction in [0, 1]")


@dataclass(frozen=True, slots=True)
class GatePolicy:
    policy_id: str = "strict-regression"
    policy_version: str = "1.0.0"
    max_regressions: int = 0
    max_candidate_failures: int | None = None
    min_candidate_pass_rate: Fraction | None = None

    def __post_init__(self) -> None:
        _identifier(self.policy_id, "policy_id")
        _version(self.policy_version, "policy_version")
        _count(self.max_regressions)
        if self.max_candidate_failures is not None:
            _count(self.max_candidate_failures)
        if self.min_candidate_pass_rate is not None:
            _rate(self.min_candidate_pass_rate)


class GateRuleId(StrEnum):
    MAX_REGRESSIONS = "max-regressions"
    MAX_CANDIDATE_FAILURES = "max-candidate-failures"
    MIN_CANDIDATE_PASS_RATE = "min-candidate-pass-rate"


@dataclass(frozen=True, slots=True)
class CheckIdentity:
    case_id: str
    evaluator_id: str
    evaluator_version: str

    def __post_init__(self) -> None:
        _identifier(self.case_id, "case_id")
        _identifier(self.evaluator_id, "evaluator_id")
        if not isinstance(self.evaluator_version, str) or not self.evaluator_version.strip():
            raise ContractError("evaluator_version: expected a nonblank string")


@dataclass(frozen=True, slots=True)
class GateRuleResult:
    rule_id: GateRuleId
    observed: int | Fraction
    permitted: int | Fraction

    def __post_init__(self) -> None:
        if not isinstance(self.rule_id, GateRuleId):
            raise ContractError("rule_id: expected GateRuleId")
        validate = _rate if self.rule_id is GateRuleId.MIN_CANDIDATE_PASS_RATE else _count
        validate(self.observed)
        validate(self.permitted)

    @property
    def passed(self) -> bool:
        if self.rule_id is GateRuleId.MIN_CANDIDATE_PASS_RATE:
            return self.observed >= self.permitted
        return self.observed <= self.permitted

    @property
    def explanation(self) -> str:
        bound = "at least" if self.rule_id is GateRuleId.MIN_CANDIDATE_PASS_RATE else "at most"
        unit = "candidate check pass rate" if bound == "at least" else "evaluator checks"
        action = (
            "Rule satisfied."
            if self.passed
            else "Inspect affected checks and improve the candidate."
        )
        return (
            f"{self.rule_id}: {'PASS' if self.passed else 'FAIL'}; observed {self.observed} "
            f"{unit}; permitted {bound} {self.permitted}. {action}"
        )


@dataclass(frozen=True, slots=True)
class GateProvenance:
    comparison_sha256: str
    comparison_contract_version: str
    policy_id: str
    policy_version: str
    policy_sha256: str
    gate_contract_version: str

    def __post_init__(self) -> None:
        _digest(self.comparison_sha256, "comparison_sha256")
        _version(self.comparison_contract_version, "comparison_contract_version")
        _identifier(self.policy_id, "policy_id")
        _version(self.policy_version, "policy_version")
        _digest(self.policy_sha256, "policy_sha256")
        _version(self.gate_contract_version, "gate_contract_version")


@dataclass(frozen=True, slots=True)
class GateResult:
    provenance: GateProvenance
    rules: tuple[GateRuleResult, ...]
    regressions: tuple[CheckIdentity, ...]
    candidate_failures: tuple[CheckIdentity, ...]
    total_checks: int
    candidate_passes: int
    result_sha256: str

    def __post_init__(self) -> None:
        if not isinstance(self.provenance, GateProvenance):
            raise ContractError("provenance: expected GateProvenance")
        _items(self.rules, GateRuleResult, "rules")
        ids = tuple(rule.rule_id for rule in self.rules)
        if not ids or ids[0] is not GateRuleId.MAX_REGRESSIONS:
            raise ContractError("rules: max-regressions must be first")
        _unique(ids, "rule_id")
        if ids != tuple(rule for rule in GateRuleId if rule in ids):
            raise ContractError("rules: unexpected order")
        for name in ("regressions", "candidate_failures"):
            values = getattr(self, name)
            _items(values, CheckIdentity, name)
            identities = tuple((value.case_id, value.evaluator_id) for value in values)
            if len(set(identities)) != len(identities):
                raise ContractError(f"{name}: duplicate check identities")
        _count(self.total_checks)
        _count(self.candidate_passes)
        if (
            not self.total_checks
            or self.candidate_passes + len(self.candidate_failures) != self.total_checks
        ):
            raise ContractError("counts: require complete nonempty check evidence")
        if not set(self.regressions) <= set(self.candidate_failures):
            raise ContractError("regressions: must be a subset of candidate failures")
        observed = {
            GateRuleId.MAX_REGRESSIONS: len(self.regressions),
            GateRuleId.MAX_CANDIDATE_FAILURES: len(self.candidate_failures),
            GateRuleId.MIN_CANDIDATE_PASS_RATE: Fraction(self.candidate_passes, self.total_checks),
        }
        if any(rule.observed != observed[rule.rule_id] for rule in self.rules):
            raise ContractError("rules: observations disagree with check evidence")
        _digest(self.result_sha256, "result_sha256")

    @property
    def passed(self) -> bool:
        return all(rule.passed for rule in self.rules)
