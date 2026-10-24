"""Immutable, validated contracts with no file I/O or evaluator execution."""

import re
from dataclasses import dataclass
from dataclasses import field as dataclass_field
from enum import StrEnum


class ContractError(ValueError):
    """An input violates the versioned evaluation contract."""


def _text(value: object, field: str, *, empty: bool = False) -> str:
    if not isinstance(value, str) or (not empty and not value.strip()):
        raise ContractError(f"{field}: expected {'a string' if empty else 'a nonblank string'}")
    return value


def _identifier(value: object, field: str) -> None:
    text = _text(value, field)
    if re.fullmatch(r"[a-z][a-z0-9]*(?:[._-][a-z0-9]+)*", text) is None:
        raise ContractError(f"{field}: expected a lowercase ASCII identifier")


def _version(value: object, field: str) -> None:
    text = _text(value, field)
    if re.fullmatch(r"(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)", text) is None:
        raise ContractError(f"{field}: expected a major.minor.patch version")


def _items(value: object, item_type: type | tuple[type, ...], field: str) -> None:
    if not isinstance(value, tuple) or not all(isinstance(item, item_type) for item in value):
        raise ContractError(f"{field}: expected a tuple of validated contract values")


def _unique(values: tuple[str, ...], field: str) -> None:
    if len(set(values)) != len(values):
        raise ContractError(f"{field}: duplicate values are not allowed")


@dataclass(frozen=True, slots=True)
class ExactMatch:
    expected: str

    def __post_init__(self) -> None:
        _text(self.expected, "expected", empty=True)


@dataclass(frozen=True, slots=True)
class ContentRules:
    required: tuple[str, ...] = ()
    forbidden: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        for field in ("required", "forbidden"):
            values = getattr(self, field)
            _items(values, str, field)
            for value in values:
                _text(value, field)
            _unique(values, field)
        if not self.required and not self.forbidden:
            raise ContractError("content rules: at least one rule is required")
        if any(banned in required for required in self.required for banned in self.forbidden):
            raise ContractError("content rules: a required string contains forbidden content")


class JsonType(StrEnum):
    STRING = "string"
    INTEGER = "integer"
    NUMBER = "number"
    BOOLEAN = "boolean"
    OBJECT = "object"
    ARRAY = "array"
    NULL = "null"


@dataclass(frozen=True, slots=True)
class JsonField:
    name: str
    value_type: JsonType

    def __post_init__(self) -> None:
        _text(self.name, "JSON field name")
        if not isinstance(self.value_type, JsonType):
            raise ContractError("JSON field type: expected JsonType")


@dataclass(frozen=True, slots=True)
class JsonObject:
    """A deliberately small top-level object contract, not JSON Schema."""

    required_fields: tuple[JsonField, ...]
    allow_extra_fields: bool = False

    def __post_init__(self) -> None:
        _items(self.required_fields, JsonField, "required_fields")
        _unique(tuple(field.name for field in self.required_fields), "required_fields")
        if type(self.allow_extra_fields) is not bool:
            raise ContractError("allow_extra_fields: expected a boolean")


type Expectation = ExactMatch | ContentRules | JsonObject


@dataclass(frozen=True, slots=True)
class Case:
    case_id: str
    category: str
    language: str
    prompt: str
    expectation: Expectation

    def __post_init__(self) -> None:
        _identifier(self.case_id, "case_id")
        _identifier(self.category, "category")
        if self.language not in ("en", "el"):
            raise ContractError("language: schema v1 supports en and el")
        _text(self.prompt, "prompt")
        if not isinstance(self.expectation, (ExactMatch, ContentRules, JsonObject)):
            raise ContractError("expectation: expected a validated expectation")


@dataclass(frozen=True, slots=True)
class Dataset:
    dataset_id: str
    dataset_version: str
    cases: tuple[Case, ...]

    def __post_init__(self) -> None:
        _identifier(self.dataset_id, "dataset_id")
        _version(self.dataset_version, "dataset_version")
        _items(self.cases, Case, "cases")
        if not self.cases:
            raise ContractError("cases: dataset must not be empty")
        _unique(tuple(case.case_id for case in self.cases), "case_id")


@dataclass(frozen=True, slots=True)
class RecordedOutput:
    case_id: str
    output: str

    def __post_init__(self) -> None:
        _identifier(self.case_id, "case_id")
        _text(self.output, "output", empty=True)


@dataclass(frozen=True, slots=True)
class OutputSet:
    dataset_id: str
    dataset_version: str
    candidate_version: str
    source: str
    outputs: tuple[RecordedOutput, ...]

    def __post_init__(self) -> None:
        _identifier(self.dataset_id, "dataset_id")
        _version(self.dataset_version, "dataset_version")
        _text(self.candidate_version, "candidate_version")
        _text(self.source, "source")
        _items(self.outputs, RecordedOutput, "outputs")
        if not self.outputs:
            raise ContractError("outputs: output set must not be empty")
        _unique(tuple(output.case_id for output in self.outputs), "case_id")


@dataclass(frozen=True, slots=True)
class RunProvenance:
    dataset_id: str
    dataset_version: str
    dataset_sha256: str
    outputs_sha256: str
    candidate_version: str
    evaluator_suite_version: str
    # Optional only for compatibility with the original 1A constructors.
    # The runner always supplies this entire group.
    output_set_id: str | None = dataclass_field(default=None, kw_only=True)
    output_set_version: str | None = dataclass_field(default=None, kw_only=True)
    evaluation_contract_version: str | None = dataclass_field(default=None, kw_only=True)
    python_integer_limit: int | None = dataclass_field(default=None, kw_only=True)

    def __post_init__(self) -> None:
        _identifier(self.dataset_id, "dataset_id")
        _version(self.dataset_version, "dataset_version")
        for field in ("dataset_sha256", "outputs_sha256"):
            value = getattr(self, field)
            if not isinstance(value, str) or re.fullmatch(r"[0-9a-f]{64}", value) is None:
                raise ContractError(f"{field}: expected a lowercase SHA-256 digest")
        _text(self.candidate_version, "candidate_version")
        _text(self.evaluator_suite_version, "evaluator_suite_version")
        additions = (
            self.output_set_id,
            self.output_set_version,
            self.evaluation_contract_version,
            self.python_integer_limit,
        )
        if any(value is not None for value in additions):
            _identifier(self.output_set_id, "output_set_id")
            _version(self.output_set_version, "output_set_version")
            _version(self.evaluation_contract_version, "evaluation_contract_version")
            if type(self.python_integer_limit) is not int or self.python_integer_limit < 0:
                raise ContractError("python_integer_limit: expected a nonnegative integer")


@dataclass(frozen=True, slots=True)
class CheckResult:
    evaluator_id: str
    evaluator_version: str
    passed: bool
    explanation: str

    def __post_init__(self) -> None:
        _identifier(self.evaluator_id, "evaluator_id")
        _text(self.evaluator_version, "evaluator_version")
        if type(self.passed) is not bool:
            raise ContractError("passed: expected a boolean")
        _text(self.explanation, "explanation")


@dataclass(frozen=True, slots=True)
class CaseResult:
    case_id: str
    checks: tuple[CheckResult, ...]

    def __post_init__(self) -> None:
        _identifier(self.case_id, "case_id")
        _items(self.checks, CheckResult, "checks")
        if not self.checks:
            raise ContractError("checks: a case result must contain at least one check")
        _unique(tuple(check.evaluator_id for check in self.checks), "evaluator_id")

    @property
    def passed(self) -> bool:
        """Derive status to prevent disagreement with constituent checks."""
        return all(check.passed for check in self.checks)


@dataclass(frozen=True, slots=True)
class RunResult:
    provenance: RunProvenance
    results: tuple[CaseResult, ...]
    result_sha256: str | None = dataclass_field(default=None, kw_only=True)

    def __post_init__(self) -> None:
        if not isinstance(self.provenance, RunProvenance):
            raise ContractError("provenance: expected RunProvenance")
        _items(self.results, CaseResult, "results")
        if not self.results:
            raise ContractError("results: a run must not be empty")
        _unique(tuple(result.case_id for result in self.results), "case_id")
        if self.result_sha256 is not None and (
            not isinstance(self.result_sha256, str)
            or re.fullmatch(r"[0-9a-f]{64}", self.result_sha256) is None
        ):
            raise ContractError("result_sha256: expected a lowercase SHA-256 digest")
