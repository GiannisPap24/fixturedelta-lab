"""Immutable comparison values and derived counts; no I/O or evaluation execution."""

import re
from dataclasses import dataclass
from enum import StrEnum

from fixturedelta_lab.domain import ContractError, _identifier, _items, _text, _unique, _version


class Transition(StrEnum):
    REGRESSION = "regression"
    IMPROVEMENT = "improvement"
    UNCHANGED_PASS = "unchanged_pass"
    UNCHANGED_FAIL = "unchanged_fail"


class CaseSummary(StrEnum):
    REGRESSION = "regression"
    IMPROVEMENT = "improvement"
    MIXED = "mixed"
    UNCHANGED_PASS = "unchanged_pass"
    UNCHANGED_FAIL = "unchanged_fail"


def _transition(baseline: bool, candidate: bool) -> Transition:
    return {
        (True, False): Transition.REGRESSION,
        (False, True): Transition.IMPROVEMENT,
        (True, True): Transition.UNCHANGED_PASS,
        (False, False): Transition.UNCHANGED_FAIL,
    }[baseline, candidate]


def _digest(value: object, name: str) -> None:
    if not isinstance(value, str) or re.fullmatch(r"[0-9a-f]{64}", value) is None:
        raise ContractError(f"{name}: expected a lowercase SHA-256 digest")


@dataclass(frozen=True, slots=True)
class TransitionCounts:
    regressions: int
    improvements: int
    unchanged_passes: int
    unchanged_failures: int

    def __post_init__(self) -> None:
        for value in (
            self.regressions,
            self.improvements,
            self.unchanged_passes,
            self.unchanged_failures,
        ):
            if type(value) is not int or value < 0:
                raise ContractError("counts: expected nonnegative integers")

    @property
    def total(self) -> int:
        return (
            self.regressions + self.improvements + self.unchanged_passes + self.unchanged_failures
        )


def _counts(transitions: tuple[Transition, ...]) -> TransitionCounts:
    return TransitionCounts(*(transitions.count(value) for value in Transition))


@dataclass(frozen=True, slots=True)
class CheckComparison:
    evaluator_id: str
    evaluator_version: str
    baseline_passed: bool
    candidate_passed: bool
    baseline_explanation: str
    candidate_explanation: str

    def __post_init__(self) -> None:
        _identifier(self.evaluator_id, "evaluator_id")
        _text(self.evaluator_version, "evaluator_version")
        if type(self.baseline_passed) is not bool or type(self.candidate_passed) is not bool:
            raise ContractError("comparison statuses: expected booleans")
        _text(self.baseline_explanation, "baseline_explanation")
        _text(self.candidate_explanation, "candidate_explanation")

    @property
    def transition(self) -> Transition:
        return _transition(self.baseline_passed, self.candidate_passed)


@dataclass(frozen=True, slots=True)
class CaseComparison:
    case_id: str
    checks: tuple[CheckComparison, ...]

    def __post_init__(self) -> None:
        _identifier(self.case_id, "case_id")
        _items(self.checks, CheckComparison, "checks")
        if not self.checks:
            raise ContractError("checks: comparison must not be empty")
        _unique(tuple(check.evaluator_id for check in self.checks), "evaluator_id")

    @property
    def baseline_passed(self) -> bool:
        return all(check.baseline_passed for check in self.checks)

    @property
    def candidate_passed(self) -> bool:
        return all(check.candidate_passed for check in self.checks)

    @property
    def transition(self) -> Transition:
        """All-checks-pass transition; inspect summary/checks for hidden changes."""
        return _transition(self.baseline_passed, self.candidate_passed)

    @property
    def check_counts(self) -> TransitionCounts:
        return _counts(tuple(check.transition for check in self.checks))

    @property
    def summary(self) -> CaseSummary:
        counts = self.check_counts
        if counts.regressions and counts.improvements:
            return CaseSummary.MIXED
        if counts.regressions:
            return CaseSummary.REGRESSION
        if counts.improvements:
            return CaseSummary.IMPROVEMENT
        return CaseSummary(self.transition.value)


@dataclass(frozen=True, slots=True)
class RunReference:
    output_set_id: str
    output_set_version: str
    candidate_version: str
    outputs_sha256: str
    run_sha256: str

    def __post_init__(self) -> None:
        _identifier(self.output_set_id, "output_set_id")
        _version(self.output_set_version, "output_set_version")
        _text(self.candidate_version, "candidate_version")
        _digest(self.outputs_sha256, "outputs_sha256")
        _digest(self.run_sha256, "run_sha256")


@dataclass(frozen=True, slots=True)
class ComparisonProvenance:
    baseline: RunReference
    candidate: RunReference
    dataset_id: str
    dataset_version: str
    dataset_sha256: str
    evaluation_contract_version: str
    evaluator_suite_version: str
    python_integer_limit: int
    comparison_contract_version: str

    def __post_init__(self) -> None:
        if not isinstance(self.baseline, RunReference) or not isinstance(
            self.candidate, RunReference
        ):
            raise ContractError("run references: expected RunReference")
        _identifier(self.dataset_id, "dataset_id")
        _version(self.dataset_version, "dataset_version")
        _digest(self.dataset_sha256, "dataset_sha256")
        _version(self.evaluation_contract_version, "evaluation_contract_version")
        _text(self.evaluator_suite_version, "evaluator_suite_version")
        _version(self.comparison_contract_version, "comparison_contract_version")
        if type(self.python_integer_limit) is not int or self.python_integer_limit < 0:
            raise ContractError("python_integer_limit: expected a nonnegative integer")


@dataclass(frozen=True, slots=True)
class ComparisonResult:
    provenance: ComparisonProvenance
    cases: tuple[CaseComparison, ...]
    comparison_sha256: str

    def __post_init__(self) -> None:
        if not isinstance(self.provenance, ComparisonProvenance):
            raise ContractError("provenance: expected ComparisonProvenance")
        _items(self.cases, CaseComparison, "cases")
        if not self.cases:
            raise ContractError("cases: comparison must not be empty")
        _unique(tuple(case.case_id for case in self.cases), "case_id")
        _digest(self.comparison_sha256, "comparison_sha256")

    @property
    def case_counts(self) -> TransitionCounts:
        """Counts of aggregate all-checks-pass transitions, not summaries."""
        return _counts(tuple(case.transition for case in self.cases))

    @property
    def check_counts(self) -> TransitionCounts:
        return _counts(tuple(check.transition for case in self.cases for check in case.checks))

    @property
    def cases_with_regressions(self) -> int:
        """Includes mixed cases and regressions within already-failing cases."""
        return sum(case.check_counts.regressions > 0 for case in self.cases)

    @property
    def cases_with_improvements(self) -> int:
        return sum(case.check_counts.improvements > 0 for case in self.cases)

    @property
    def mixed_case_count(self) -> int:
        return sum(case.summary is CaseSummary.MIXED for case in self.cases)
