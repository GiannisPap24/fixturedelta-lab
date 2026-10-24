"""Offline quality-gate decisions, boundary oracles and invalid-evidence rejection."""

import copy
import hashlib
import json
from dataclasses import FrozenInstanceError, asdict, replace
from fractions import Fraction
from pathlib import Path

import pytest

from fixturedelta_lab.comparison import compare_runs
from fixturedelta_lab.comparison_types import CaseSummary, ComparisonResult
from fixturedelta_lab.domain import ContractError
from fixturedelta_lab.gate_types import (
    CheckIdentity,
    GatePolicy,
    GateProvenance,
    GateResult,
    GateRuleId,
    GateRuleResult,
)
from fixturedelta_lab.gates import GateError, GateErrorCode, evaluate_gate
from fixturedelta_lab.provenance import comparison_sha256, policy_sha256
from fixturedelta_lab.runner import evaluate_run, run_evaluation


@pytest.fixture
def comparison(fixture_dir: Path) -> ComparisonResult:
    dataset = fixture_dir / "golden-v1.0.0.json"
    baseline = run_evaluation(
        dataset,
        fixture_dir / "baseline-v1.json",
        output_set_id="baseline",
        output_set_version="1.0.0",
    )
    candidate = run_evaluation(
        dataset,
        fixture_dir / "candidate-v2.json",
        output_set_id="candidate",
        output_set_version="2.0.0",
    )
    return compare_runs(baseline, candidate)


def rehash(value: ComparisonResult) -> ComparisonResult:
    return replace(value, comparison_sha256=comparison_sha256(value.provenance, value.cases))


def statuses(comparison, before, after):
    # Signed synthetic paired evidence; real evaluator integration is tested separately.
    check = comparison.cases[0].checks[0]
    checks = tuple(
        replace(check, evaluator_id=f"check-{i}", baseline_passed=b, candidate_passed=c)
        for i, (b, c) in enumerate(zip(before, after, strict=True))
    )
    return rehash(replace(comparison, cases=(replace(comparison.cases[0], checks=checks),)))


def test_fixture_fails_default_despite_improvement(comparison) -> None:
    result = evaluate_gate(comparison, GatePolicy())
    assert not result.passed
    assert comparison.check_counts.improvements == 1
    assert result.rules == (GateRuleResult(GateRuleId.MAX_REGRESSIONS, 2, 0),)
    assert [(x.case_id, x.evaluator_id) for x in result.regressions] == [
        ("en-label-001", "exact-match"),
        ("en-json-001", "json-object"),
    ]
    assert result.candidate_failures == result.regressions
    assert result.total_checks == 8 and result.candidate_passes == 6
    assert "FAIL" in result.rules[0].explanation and "observed 2" in result.rules[0].explanation
    assert "at most 0" in result.rules[0].explanation
    assert result.provenance.comparison_sha256 == comparison.comparison_sha256


@pytest.mark.parametrize(
    "before,after,passed,count",
    [
        ((True,), (True,), True, 0),
        ((True,), (False,), False, 1),
        ((False,), (True,), True, 0),
        ((False,), (False,), True, 0),
        ((True, False), (False, True), False, 1),
        ((True, False), (False, False), False, 1),
        ((True, True), (False, False), False, 2),
    ],
)
def test_check_level_regressions(before, after, passed, count, comparison) -> None:
    evidence = statuses(comparison, before, after)
    result = evaluate_gate(evidence, GatePolicy())
    assert result.passed is passed
    assert result.rules[0].observed == count
    assert len(result.regressions) == count


@pytest.mark.parametrize("limit,passed", [(0, False), (1, False), (2, True), (3, True)])
def test_regression_inclusive_boundary(limit, passed, comparison) -> None:
    assert evaluate_gate(comparison, GatePolicy(max_regressions=limit)).passed is passed


@pytest.mark.parametrize("limit,passed", [(0, False), (1, False), (2, True), (3, True)])
def test_candidate_failure_inclusive_boundary(limit, passed, comparison) -> None:
    result = evaluate_gate(comparison, GatePolicy(max_regressions=2, max_candidate_failures=limit))
    assert result.passed is passed
    assert result.rules[1].observed == 2 and result.rules[1].permitted == limit


@pytest.mark.parametrize(
    "rate,passed",
    [
        (Fraction(0), True),
        (Fraction(3, 4), True),
        (Fraction(750000000001, 10**12), False),
        (Fraction(749999999999, 10**12), True),
        (Fraction(1), False),
    ],
)
def test_rate_exact_boundaries(rate, passed, comparison) -> None:
    result = evaluate_gate(comparison, GatePolicy(max_regressions=2, min_candidate_pass_rate=rate))
    assert result.passed is passed
    assert result.rules[1].observed == Fraction(3, 4)
    assert result.rules[1].permitted == rate
    assert result.total_checks == 8  # denominator is checks, not six cases


@pytest.mark.parametrize(
    "after,rate,passed",
    [
        ((False, False), Fraction(0), True),
        ((False, False), Fraction(1, 100), False),
        ((True, True), Fraction(1), True),
        ((True, False, False), Fraction(1, 3), True),
        ((True, False, False), Fraction(333333333333333334, 10**18), False),
    ],
)
def test_rate_extremes_and_repeating_fractions(after, rate, passed, comparison) -> None:
    evidence = statuses(comparison, tuple(False for _ in after), after)
    result = evaluate_gate(evidence, GatePolicy(min_candidate_pass_rate=rate))
    assert result.passed is passed
    assert result.rules[1].observed == Fraction(sum(after), len(after))


def test_rules_are_independent_and_ordered(comparison) -> None:
    policy = GatePolicy(max_candidate_failures=2, min_candidate_pass_rate=Fraction(4, 5))
    result = evaluate_gate(comparison, policy)
    assert [rule.rule_id for rule in result.rules] == list(GateRuleId)
    assert [rule.passed for rule in result.rules] == [False, True, False]
    assert not result.passed
    all_pass = evaluate_gate(
        comparison, replace(policy, max_regressions=2, min_candidate_pass_rate=Fraction(3, 4))
    )
    assert all_pass.passed
    assert all("PASS" in rule.explanation for rule in all_pass.rules)


def test_real_mixed_english_and_greek_evidence(fixture_dir: Path) -> None:
    raw = (fixture_dir / "golden-v1.0.0.json").read_bytes()
    left = json.loads((fixture_dir / "baseline-v1.json").read_bytes())
    right = copy.deepcopy(left)
    left["outputs"][2]["output"] = "blue triangle red square"
    right["outputs"][2]["output"] = "nothing"
    left["outputs"][3]["output"] = "πράσινος κύκλος μαύρο τρίγωνο"
    right["outputs"][3]["output"] = "τίποτα"
    runs = [
        evaluate_run(
            raw,
            json.dumps(data, ensure_ascii=False).encode("utf-8"),
            output_set_id=label,
            output_set_version="1.0.0",
        )
        for data, label in [(left, "baseline"), (right, "candidate")]
    ]
    evidence = compare_runs(*runs)
    assert evidence.cases[2].summary is evidence.cases[3].summary is CaseSummary.MIXED
    assert evidence.case_counts.regressions == 0
    result = evaluate_gate(evidence, GatePolicy())
    assert not result.passed and len(result.regressions) == 2
    assert [x.case_id for x in result.regressions] == ["en-rules-001", "el-rules-001"]
    assert all(x.evaluator_id == "required-content" for x in result.regressions)


def test_stable_affected_order(comparison) -> None:
    reordered = rehash(replace(comparison, cases=tuple(reversed(comparison.cases))))
    result = evaluate_gate(reordered, GatePolicy())
    assert [x.case_id for x in result.regressions] == ["en-json-001", "en-label-001"]
    assert result.candidate_failures == result.regressions


@pytest.mark.parametrize("field", ["max_regressions", "max_candidate_failures"])
@pytest.mark.parametrize("value", [-1, True, False, 1.0, "1", Fraction(1), float("nan")])
def test_bad_counts(field, value) -> None:
    with pytest.raises(ContractError):
        GatePolicy(**{field: value})


@pytest.mark.parametrize(
    "value",
    [
        -1,
        0,
        1,
        True,
        False,
        0.5,
        float("inf"),
        float("nan"),
        "0.5",
        Fraction(-1, 4),
        Fraction(5, 4),
        {"numerator": 1, "denominator": 2},
    ],
)
def test_bad_rates(value) -> None:
    with pytest.raises(ContractError):
        GatePolicy(min_candidate_pass_rate=value)


@pytest.mark.parametrize(
    "kwargs",
    [
        {"policy_id": "INVALID"},
        {"policy_id": ""},
        {"policy_version": "v1"},
        {"max_regressions": None},
    ],
)
def test_bad_policy_metadata(kwargs) -> None:
    with pytest.raises(ContractError):
        GatePolicy(**kwargs)


def test_unknown_policy_fields_rejected() -> None:
    with pytest.raises(TypeError):
        GatePolicy(weighted_score=0.7)


@pytest.mark.parametrize("bad", [None, {}, "policy"])
def test_wrong_policy_argument(bad, comparison) -> None:
    with pytest.raises(GateError) as error:
        evaluate_gate(comparison, bad)
    assert error.value.code is GateErrorCode.INVALID_POLICY


def test_policy_revalidated_and_errors_precede_evidence(comparison) -> None:
    policy = GatePolicy()
    object.__setattr__(policy, "max_regressions", True)
    with pytest.raises(GateError) as error:
        evaluate_gate(None, policy)
    assert error.value.code is GateErrorCode.INVALID_POLICY
    with pytest.raises(GateError):
        evaluate_gate(comparison, object.__new__(GatePolicy))


@pytest.mark.parametrize("bad", [None, {}, "comparison"])
def test_missing_comparison(bad) -> None:
    with pytest.raises(GateError) as error:
        evaluate_gate(bad, GatePolicy())
    assert error.value.code is GateErrorCode.INVALID_COMPARISON


@pytest.mark.parametrize(
    "target,field,value",
    [
        ("root", "provenance", None),
        ("root", "cases", ()),
        ("root", "cases", []),
        ("root", "cases", ({},)),
        ("root", "comparison_sha256", None),
        ("provenance", "baseline", None),
        ("provenance", "candidate", {}),
        ("provenance", "dataset_sha256", "bad"),
        ("provenance", "python_integer_limit", True),
        ("reference", "output_set_id", None),
        ("reference", "run_sha256", "bad"),
        ("case", "case_id", []),
        ("case", "checks", ()),
        ("case", "checks", ({},)),
        ("check", "baseline_passed", 1),
        ("check", "candidate_passed", None),
        ("check", "candidate_explanation", ""),
        ("check", "evaluator_id", "INVALID"),
    ],
)
def test_nested_evidence_revalidation(target, field, value, comparison) -> None:
    damaged = copy.deepcopy(comparison)
    obj = {
        "root": damaged,
        "provenance": damaged.provenance,
        "reference": damaged.provenance.baseline,
        "case": damaged.cases[0],
        "check": damaged.cases[0].checks[0],
    }[target]
    object.__setattr__(obj, field, value)
    with pytest.raises(GateError) as error:
        evaluate_gate(damaged, GatePolicy())
    assert error.value.code is GateErrorCode.INVALID_COMPARISON
    assert error.value.__cause__ is not None
    assert not hasattr(error.value, "rules")


@pytest.mark.parametrize("kind", ["case", "check", "version"])
def test_duplicate_or_inconsistent_evidence(kind, comparison) -> None:
    damaged = copy.deepcopy(comparison)
    if kind == "case":
        object.__setattr__(damaged, "cases", (*damaged.cases, damaged.cases[0]))
    elif kind == "check":
        case = damaged.cases[0]
        object.__setattr__(case, "checks", (*case.checks, case.checks[0]))
    else:
        object.__setattr__(damaged.cases[1].checks[0], "evaluator_version", "2.0.0")
    with pytest.raises(GateError) as error:
        evaluate_gate(damaged, GatePolicy())
    assert error.value.code is GateErrorCode.INVALID_COMPARISON


@pytest.mark.parametrize("field", ["comparison_contract_version", "evaluation_contract_version"])
def test_incompatible_contract(field, comparison) -> None:
    damaged = rehash(
        replace(comparison, provenance=replace(comparison.provenance, **{field: "9.0.0"}))
    )
    with pytest.raises(GateError) as error:
        evaluate_gate(damaged, GatePolicy())
    assert error.value.code is GateErrorCode.INCOMPATIBLE_COMPARISON


@pytest.mark.parametrize("change", ["digest", "missing-case", "status", "reference"])
def test_stale_comparison_digest(change, comparison) -> None:
    if change == "digest":
        damaged = replace(comparison, comparison_sha256="a" * 64)
    elif change == "missing-case":
        damaged = replace(comparison, cases=comparison.cases[:-1])
    elif change == "reference":
        p = comparison.provenance
        damaged = replace(
            comparison,
            provenance=replace(p, candidate=replace(p.candidate, candidate_version="new")),
        )
    else:
        first = comparison.cases[0]
        first = replace(first, checks=(replace(first.checks[0], candidate_passed=True),))
        damaged = replace(comparison, cases=(first, *comparison.cases[1:]))
    with pytest.raises(GateError) as error:
        evaluate_gate(damaged, GatePolicy())
    assert error.value.code is GateErrorCode.COMPARISON_FINGERPRINT_MISMATCH


def test_immutable_and_pure(comparison, monkeypatch) -> None:
    import fixturedelta_lab.comparison
    import fixturedelta_lab.runner

    def forbidden(*args, **kwargs):
        pytest.fail("Gate attempted I/O or reevaluation")

    monkeypatch.setattr(Path, "read_bytes", forbidden)
    monkeypatch.setattr(fixturedelta_lab.comparison, "compare_runs", forbidden)
    monkeypatch.setattr(fixturedelta_lab.runner, "evaluate_run", forbidden)
    policy = GatePolicy(min_candidate_pass_rate=Fraction(3, 4))
    before = copy.deepcopy((comparison, policy))
    result = evaluate_gate(comparison, policy)
    assert result == evaluate_gate(comparison, policy)
    assert (comparison, policy) == before
    for obj, field, value in [
        (policy, "max_regressions", 100),
        (result, "rules", ()),
        (result.provenance, "policy_id", "new"),
        (result.rules[0], "observed", 0),
        (result.regressions[0], "case_id", "new"),
    ]:
        with pytest.raises(FrozenInstanceError):
            setattr(obj, field, value)


def test_independent_policy_hash_and_fraction_normalization() -> None:
    policy = GatePolicy(min_candidate_pass_rate=Fraction(6, 8))
    expected = {
        "fingerprint_version": "trustbench-gate-policy-v1",
        "policy": {
            "policy_id": "strict-regression",
            "policy_version": "1.0.0",
            "max_regressions": 0,
            "max_candidate_failures": None,
            "min_candidate_pass_rate": {"numerator": 3, "denominator": 4},
        },
    }
    encoded = json.dumps(
        expected, sort_keys=True, ensure_ascii=True, separators=(",", ":"), allow_nan=False
    ).encode("ascii")
    assert policy_sha256(policy) == hashlib.sha256(encoded).hexdigest()
    assert policy_sha256(policy) == policy_sha256(
        replace(policy, min_candidate_pass_rate=Fraction(3, 4))
    )


def test_independent_gate_hash_oracle(comparison) -> None:
    policy = GatePolicy()
    result = evaluate_gate(comparison, policy)
    identities = [
        {"case_id": "en-label-001", "evaluator_id": "exact-match", "evaluator_version": "1.0.0"},
        {"case_id": "en-json-001", "evaluator_id": "json-object", "evaluator_version": "1.0.0"},
    ]
    payload = {
        "fingerprint_version": "trustbench-gate-v1",
        "provenance": {
            "comparison_sha256": comparison.comparison_sha256,
            "comparison_contract_version": "1.0.0",
            "policy_id": "strict-regression",
            "policy_version": "1.0.0",
            "policy_sha256": policy_sha256(policy),
            "gate_contract_version": "1.0.0",
        },
        "rules": [
            {
                "rule_id": "max-regressions",
                "observed": 2,
                "permitted": 0,
                "passed": False,
                "explanation": "max-regressions: FAIL; observed 2 evaluator checks; "
                "permitted at most 0. Inspect affected checks and improve the candidate.",
            }
        ],
        "regressions": identities,
        "candidate_failures": identities,
        "total_checks": 8,
        "candidate_passes": 6,
        "passed": False,
    }
    raw = json.dumps(
        payload, sort_keys=True, ensure_ascii=True, separators=(",", ":"), allow_nan=False
    ).encode("ascii")
    assert result.result_sha256 == hashlib.sha256(raw).hexdigest()
    assert "timestamp" not in str(asdict(result.provenance))


@pytest.mark.parametrize(
    "field,value",
    [
        ("policy_id", "another"),
        ("policy_version", "2.0.0"),
        ("max_regressions", 2),
        ("max_candidate_failures", 2),
        ("min_candidate_pass_rate", Fraction(3, 4)),
    ],
)
def test_policy_changes_bind_fingerprints(field, value, comparison) -> None:
    first = GatePolicy()
    second = replace(first, **{field: value})
    assert policy_sha256(first) != policy_sha256(second)
    assert (
        evaluate_gate(comparison, first).result_sha256
        != evaluate_gate(comparison, second).result_sha256
    )


def test_evidence_changes_bind_gate_identity(comparison) -> None:
    before = evaluate_gate(comparison, GatePolicy())
    last = comparison.cases[-1]
    last = replace(last, checks=(replace(last.checks[0], candidate_explanation="Νέα εξήγηση"),))
    changed = rehash(replace(comparison, cases=(*comparison.cases[:-1], last)))
    after = evaluate_gate(changed, GatePolicy())
    assert before.rules == after.rules
    assert before.result_sha256 != after.result_sha256


@pytest.mark.parametrize(
    "field,value",
    [
        ("rule_id", "max-regressions"),
        ("observed", True),
        ("permitted", -1),
    ],
)
def test_rule_contract(field, value) -> None:
    with pytest.raises(ContractError):
        replace(GateRuleResult(GateRuleId.MAX_REGRESSIONS, 0, 0), **{field: value})


@pytest.mark.parametrize(
    "field,value",
    [
        ("case_id", "INVALID"),
        ("evaluator_id", "INVALID"),
        ("evaluator_version", ""),
    ],
)
def test_identity_contract(field, value) -> None:
    with pytest.raises(ContractError):
        replace(CheckIdentity("case", "check", "1.0.0"), **{field: value})


@pytest.mark.parametrize(
    "field,value",
    [
        ("comparison_sha256", "bad"),
        ("comparison_contract_version", "v1"),
        ("policy_id", "INVALID"),
        ("policy_version", "v1"),
        ("policy_sha256", "bad"),
        ("gate_contract_version", "v1"),
    ],
)
def test_provenance_contract(field, value, comparison) -> None:
    p = evaluate_gate(comparison, GatePolicy()).provenance
    assert isinstance(p, GateProvenance)
    with pytest.raises(ContractError):
        replace(p, **{field: value})


@pytest.mark.parametrize(
    "field,value",
    [
        ("provenance", None),
        ("rules", ()),
        ("rules", []),
        ("regressions", []),
        ("candidate_failures", ()),
        ("candidate_passes", True),
        ("total_checks", -1),
        ("total_checks", 0),
        ("result_sha256", "bad"),
    ],
)
def test_result_contract(field, value, comparison) -> None:
    result = evaluate_gate(comparison, GatePolicy())
    assert isinstance(result, GateResult)
    with pytest.raises(ContractError):
        replace(result, **{field: value})


@pytest.mark.parametrize(
    "fault", ["rule-duplicate", "rule-order", "identity-duplicate", "not-failure", "observation"]
)
def test_inconsistent_result_contract(fault, comparison) -> None:
    result = evaluate_gate(
        comparison, GatePolicy(max_candidate_failures=3, min_candidate_pass_rate=Fraction(1, 2))
    )
    with pytest.raises(ContractError):
        if fault == "rule-duplicate":
            replace(result, rules=(result.rules[0], result.rules[0]))
        elif fault == "rule-order":
            replace(result, rules=(result.rules[0], result.rules[2], result.rules[1]))
        elif fault == "identity-duplicate":
            replace(result, regressions=(result.regressions[0], result.regressions[0]))
        elif fault == "not-failure":
            replace(result, regressions=(CheckIdentity("absent-case", "exact-match", "1.0.0"),))
        else:
            replace(result, rules=(replace(result.rules[0], observed=0), *result.rules[1:]))


@pytest.mark.parametrize("level", ["case", "check"])
def test_subclass_evidence_is_not_the_versioned_contract(level, comparison) -> None:
    from fixturedelta_lab.comparison_types import CaseComparison, CheckComparison

    class OtherCase(CaseComparison):
        pass

    class OtherCheck(CheckComparison):
        pass

    first = comparison.cases[0]
    if level == "case":
        first = OtherCase(first.case_id, first.checks)
    else:
        first = replace(first, checks=(OtherCheck(**asdict(first.checks[0])),))
    changed = replace(comparison, cases=(first, *comparison.cases[1:]))
    with pytest.raises(GateError) as error:
        evaluate_gate(changed, GatePolicy())
    assert error.value.code is GateErrorCode.INVALID_COMPARISON
