from collections.abc import Callable
from dataclasses import FrozenInstanceError

import pytest

from fixturedelta_lab.domain import (
    Case,
    CaseResult,
    CheckResult,
    ContentRules,
    ContractError,
    Dataset,
    ExactMatch,
    JsonField,
    JsonObject,
    JsonType,
    RunProvenance,
    RunResult,
)


@pytest.mark.parametrize(
    "factory",
    [
        lambda: ContentRules(),
        lambda: ContentRules(required=("",)),
        lambda: ContentRules(required=("x", "x")),
        lambda: ContentRules(required=("red square",), forbidden=("red",)),
        lambda: ContentRules(required=["mutable"]),
        lambda: JsonObject((JsonField("x", JsonType.STRING), JsonField("x", JsonType.INTEGER))),
        lambda: JsonField("x", "string"),
        lambda: JsonObject((), 1),
        lambda: Case("bad id", "labels", "en", "prompt", ExactMatch("x")),
        lambda: Dataset("demo", "01.0.0", ()),
        lambda: Dataset("demo", "1.0.0", ("not a case",)),
        lambda: CheckResult("exact-match", "1.0.0", 1, "reason"),
        lambda: CheckResult("exact-match", "1.0.0", True, " "),
        lambda: CaseResult("case-1", ()),
        lambda: CaseResult("case-1", ("not a check",)),
    ],
)
def test_invalid_direct_construction_is_rejected(factory: Callable[[], object]) -> None:
    with pytest.raises(ContractError):
        factory()


def test_result_status_is_derived_and_explanations_are_preserved() -> None:
    passed = CheckResult("required-content", "1.0.0", True, "Required phrase present.")
    failed = CheckResult("forbidden-content", "1.0.0", False, "Forbidden phrase present.")
    assert CaseResult("case-1", (passed,)).passed is True
    result = CaseResult("case-1", (passed, failed))
    assert result.passed is False
    assert result.checks[1].explanation == "Forbidden phrase present."
    with pytest.raises(ContractError, match="duplicate"):
        CaseResult("case-1", (passed, passed))


def test_contracts_are_immutable() -> None:
    expectation = ExactMatch("Έτοιμο")
    with pytest.raises(FrozenInstanceError):
        expectation.expected = "changed"
    assert ExactMatch("").expected == ""
    assert JsonObject(()).required_fields == ()


def test_run_requires_provenance_and_unique_nonempty_results() -> None:
    provenance = RunProvenance(
        "demo", "1.0.0", "a" * 64, "b" * 64, "synthetic-v1", "planned-suite-v1"
    )
    result = CaseResult("case-1", (CheckResult("exact-match", "1.0.0", True, "Equal."),))
    run = RunResult(provenance, (result,))
    assert run.provenance.candidate_version == "synthetic-v1"
    for results in ((), (result, result)):
        with pytest.raises(ContractError):
            RunResult(provenance, results)
    with pytest.raises(ContractError, match="provenance"):
        RunResult(None, (result,))


@pytest.mark.parametrize("digest", ["", "abc", "g" * 64, "A" * 64, None])
def test_invalid_provenance_digests_rejected(digest: object) -> None:
    with pytest.raises(ContractError, match="SHA-256"):
        RunProvenance("demo", "1.0.0", digest, "b" * 64, "synthetic-v1", "suite-v1")
