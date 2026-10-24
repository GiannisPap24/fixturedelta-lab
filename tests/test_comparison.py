"""Comparison oracles, evidence validation, ordering and immutable provenance."""

import copy
import hashlib
import json
from dataclasses import FrozenInstanceError, asdict, replace
from pathlib import Path

import pytest

from fixturedelta_lab.comparison import ComparisonError, compare_runs
from fixturedelta_lab.comparison import ComparisonErrorCode as Code
from fixturedelta_lab.comparison_types import (
    CaseComparison,
    CaseSummary,
    CheckComparison,
    ComparisonProvenance,
    ComparisonResult,
    RunReference,
    Transition,
    TransitionCounts,
)
from fixturedelta_lab.domain import CaseResult, CheckResult, ContractError, RunProvenance, RunResult
from fixturedelta_lab.provenance import comparison_sha256, result_sha256
from fixturedelta_lab.runner import run_evaluation


@pytest.fixture
def runs(fixture_dir: Path) -> tuple[RunResult, RunResult]:
    dataset = fixture_dir / "golden-v1.0.0.json"
    return (
        run_evaluation(
            dataset,
            fixture_dir / "baseline-v1.json",
            output_set_id="baseline",
            output_set_version="1.0.0",
        ),
        run_evaluation(
            dataset,
            fixture_dir / "candidate-v2.json",
            output_set_id="candidate",
            output_set_version="2.0.0",
        ),
    )


def signed(run: RunResult, *, results=None, provenance=None) -> RunResult:
    p = run.provenance if provenance is None else provenance
    rows = run.results if results is None else results
    return RunResult(p, rows, result_sha256=result_sha256(p, rows))


def synthetic(run: RunResult, statuses: tuple[bool, ...]) -> RunResult:
    checks = tuple(
        CheckResult(f"check-{i}", "1.0.0", value, "Έτοιμο / ready")
        for i, value in enumerate(statuses)
    )
    return signed(run, results=(CaseResult("mixed-demo", checks),))


def test_fixture_oracle(runs: tuple[RunResult, RunResult]) -> None:
    result = compare_runs(*runs)
    assert [case.case_id for case in result.cases] == [case.case_id for case in runs[0].results]
    assert [case.transition for case in result.cases] == [
        Transition.REGRESSION,
        Transition.UNCHANGED_PASS,
        Transition.UNCHANGED_PASS,
        Transition.IMPROVEMENT,
        Transition.REGRESSION,
        Transition.UNCHANGED_PASS,
    ]
    assert [case.summary.value for case in result.cases] == [
        "regression",
        "unchanged_pass",
        "unchanged_pass",
        "improvement",
        "regression",
        "unchanged_pass",
    ]
    assert result.case_counts == TransitionCounts(2, 1, 3, 0)
    assert result.check_counts == TransitionCounts(2, 1, 5, 0)
    assert result.case_counts.total == 6
    assert result.check_counts.total == 8
    assert result.cases_with_regressions == 2
    assert result.cases_with_improvements == 1
    assert result.mixed_case_count == 0
    assert result.cases[3].check_counts == TransitionCounts(0, 1, 1, 0)
    assert result.provenance.baseline.run_sha256 == runs[0].result_sha256
    assert result.provenance.candidate.run_sha256 == runs[1].result_sha256
    assert result.provenance.baseline.candidate_version == "synthetic-baseline-v1"
    assert result.provenance.candidate.candidate_version == "synthetic-candidate-v2"
    for case, original in zip(result.cases, runs[0].results, strict=True):
        for check, before in zip(case.checks, original.checks, strict=True):
            assert check.baseline_explanation == before.explanation
            assert check.evaluator_id == before.evaluator_id
            assert check.evaluator_version == before.evaluator_version


def test_identical_runs_keep_unchanged_failures(runs: tuple[RunResult, RunResult]) -> None:
    result = compare_runs(runs[0], runs[0])
    assert result.case_counts == TransitionCounts(0, 0, 5, 1)
    assert result.check_counts == TransitionCounts(0, 0, 7, 1)
    assert result.cases[3].summary is CaseSummary.UNCHANGED_FAIL
    assert result.cases_with_regressions == result.cases_with_improvements == 0


@pytest.mark.parametrize(
    "before,after,transition",
    [
        (True, False, Transition.REGRESSION),
        (False, True, Transition.IMPROVEMENT),
        (True, True, Transition.UNCHANGED_PASS),
        (False, False, Transition.UNCHANGED_FAIL),
    ],
)
def test_single_check_transitions(before, after, transition, runs) -> None:
    result = compare_runs(synthetic(runs[0], (before,)), synthetic(runs[1], (after,)))
    case = result.cases[0]
    assert case.transition is transition
    assert case.summary.value == transition.value
    assert case.checks[0].transition is transition
    assert case.baseline_passed is before and case.candidate_passed is after
    assert result.case_counts.total == result.check_counts.total == 1


@pytest.mark.parametrize(
    "before,after,summary,counts",
    [
        ((True, False), (False, True), CaseSummary.MIXED, TransitionCounts(1, 1, 0, 0)),
        ((True, False), (False, False), CaseSummary.REGRESSION, TransitionCounts(1, 0, 0, 1)),
        ((False, False), (True, False), CaseSummary.IMPROVEMENT, TransitionCounts(0, 1, 0, 1)),
        ((False, False), (False, False), CaseSummary.UNCHANGED_FAIL, TransitionCounts(0, 0, 0, 2)),
    ],
)
def test_changes_inside_already_failing_cases(before, after, summary, counts, runs) -> None:
    result = compare_runs(synthetic(runs[0], before), synthetic(runs[1], after))
    case = result.cases[0]
    assert case.transition is Transition.UNCHANGED_FAIL
    assert case.summary is summary
    assert case.check_counts == result.check_counts == counts
    assert result.case_counts == TransitionCounts(0, 0, 0, 1)
    assert result.cases_with_regressions == int(counts.regressions > 0)
    assert result.cases_with_improvements == int(counts.improvements > 0)
    assert result.mixed_case_count == int(summary is CaseSummary.MIXED)


def test_mixed_real_content_evaluators(fixture_dir: Path) -> None:
    from fixturedelta_lab.runner import evaluate_run

    raw = (fixture_dir / "golden-v1.0.0.json").read_bytes()
    before = json.loads((fixture_dir / "baseline-v1.json").read_bytes())
    after = copy.deepcopy(before)
    before["outputs"][2]["output"] = "blue triangle and red square"
    after["outputs"][2]["output"] = "nothing required or forbidden"
    baseline = evaluate_run(
        raw, json.dumps(before).encode(), output_set_id="before", output_set_version="1.0.0"
    )
    candidate = evaluate_run(
        raw, json.dumps(after).encode(), output_set_id="after", output_set_version="1.0.0"
    )
    case = compare_runs(baseline, candidate).cases[2]
    assert case.summary is CaseSummary.MIXED
    assert case.transition is Transition.UNCHANGED_FAIL
    assert [(c.evaluator_id, c.transition) for c in case.checks] == [
        ("required-content", Transition.REGRESSION),
        ("forbidden-content", Transition.IMPROVEMENT),
    ]


def test_align_by_ids_and_preserve_baseline_order(runs) -> None:
    baseline = signed(runs[0], results=tuple(reversed(runs[0].results)))
    candidate = signed(
        runs[1],
        results=tuple(
            replace(case, checks=tuple(reversed(case.checks))) for case in runs[1].results
        ),
    )
    result = compare_runs(baseline, candidate)
    assert [c.case_id for c in result.cases] == [c.case_id for c in baseline.results]
    assert [[c.evaluator_id for c in case.checks] for case in result.cases] == [
        [c.evaluator_id for c in case.checks] for case in baseline.results
    ]
    assert result.case_counts == TransitionCounts(2, 1, 3, 0)


def test_order_is_bound_to_input_fingerprints(runs) -> None:
    original = compare_runs(*runs)
    reordered = signed(runs[1], results=tuple(reversed(runs[1].results)))
    changed = compare_runs(runs[0], reordered)
    assert original.cases == changed.cases
    assert original.comparison_sha256 != changed.comparison_sha256


def test_roles_are_explicit_and_not_inferred_from_labels(runs) -> None:
    forward = compare_runs(*runs)
    backward = compare_runs(runs[1], runs[0])
    assert backward.case_counts == TransitionCounts(1, 2, 3, 0)
    assert forward.comparison_sha256 != backward.comparison_sha256
    renamed = signed(
        runs[1],
        provenance=replace(
            runs[1].provenance,
            output_set_id="baseline",
            output_set_version="1.0.0",
            candidate_version="anything",
        ),
    )
    assert compare_runs(runs[0], renamed).cases == forward.cases


@pytest.mark.parametrize(
    "field,value,code",
    [
        ("dataset_id", "other", Code.DATASET_MISMATCH),
        ("dataset_version", "2.0.0", Code.DATASET_MISMATCH),
        ("dataset_sha256", "a" * 64, Code.DATASET_MISMATCH),
        ("evaluation_contract_version", "2.0.0", Code.EVALUATION_CONTRACT_MISMATCH),
        ("evaluator_suite_version", "2.0.0", Code.EVALUATOR_SUITE_MISMATCH),
        ("python_integer_limit", 640, Code.RUNTIME_SETTINGS_MISMATCH),
    ],
)
def test_incompatible_provenance(field, value, code, runs) -> None:
    changed = signed(runs[1], provenance=replace(runs[1].provenance, **{field: value}))
    with pytest.raises(ComparisonError) as error:
        compare_runs(runs[0], changed)
    assert error.value.code is code
    assert error.value.role is None
    assert not hasattr(error.value, "cases")


def test_equal_unknown_evaluation_contract_is_unsupported(runs) -> None:
    altered = tuple(
        signed(run, provenance=replace(run.provenance, evaluation_contract_version="9.0.0"))
        for run in runs
    )
    with pytest.raises(ComparisonError) as error:
        compare_runs(*altered)
    assert error.value.code is Code.UNSUPPORTED_EVALUATION_CONTRACT


@pytest.mark.parametrize("side", [0, 1])
@pytest.mark.parametrize("mutation", ["missing", "extra", "unexpected"])
def test_case_coverage_mismatch(side, mutation, runs) -> None:
    modified = list(runs)
    cases = runs[side].results
    if mutation == "missing":
        cases = cases[:-1]
    elif mutation == "extra":
        cases += (replace(cases[0], case_id="extra-case"),)
    else:
        cases = (*cases[:-1], replace(cases[-1], case_id="replacement-case"))
    modified[side] = signed(runs[side], results=cases)
    with pytest.raises(ComparisonError) as error:
        compare_runs(*modified)
    assert error.value.code is Code.CASE_ID_MISMATCH
    assert "missing" in str(error.value) and "unexpected" in str(error.value)


@pytest.mark.parametrize("mutation", ["missing", "extra", "unexpected", "version"])
def test_evaluator_compatibility(mutation, runs) -> None:
    baseline = synthetic(runs[0], (True, False))
    candidate = synthetic(runs[1], (False, True))
    case = candidate.results[0]
    if mutation == "missing":
        checks = case.checks[:1]
    elif mutation == "extra":
        checks = (*case.checks, replace(case.checks[0], evaluator_id="extra-check"))
    elif mutation == "unexpected":
        checks = (case.checks[0], replace(case.checks[1], evaluator_id="replacement-check"))
    else:
        checks = (replace(case.checks[0], evaluator_version="2.0.0"), case.checks[1])
    candidate = signed(candidate, results=(replace(case, checks=checks),))
    with pytest.raises(ComparisonError) as error:
        compare_runs(baseline, candidate)
    assert error.value.code is (
        Code.EVALUATOR_VERSION_MISMATCH if mutation == "version" else Code.EVALUATOR_ID_MISMATCH
    )
    assert error.value.case_id == "mixed-demo"


def test_evaluator_version_inconsistent_within_run(runs) -> None:
    case = runs[1].results[1]
    case = replace(case, checks=(replace(case.checks[0], evaluator_version="2.0.0"),))
    altered = signed(runs[1], results=(runs[1].results[0], case, *runs[1].results[2:]))
    with pytest.raises(ComparisonError) as error:
        compare_runs(runs[0], altered)
    assert error.value.code is Code.EVALUATOR_VERSION_MISMATCH
    assert error.value.role == "candidate"


@pytest.mark.parametrize("side", [0, 1])
@pytest.mark.parametrize("target", ["cases", "checks"])
def test_duplicate_evidence_rejected_even_if_constructor_bypassed(side, target, runs) -> None:
    modified = copy.deepcopy(list(runs))
    run = modified[side]
    if target == "cases":
        object.__setattr__(run, "results", (*run.results, run.results[0]))
    else:
        case = run.results[0]
        object.__setattr__(case, "checks", (*case.checks, case.checks[0]))
    with pytest.raises(ComparisonError) as error:
        compare_runs(*modified)
    assert error.value.code is (
        Code.DUPLICATE_CASE_ID if target == "cases" else Code.DUPLICATE_EVALUATOR_ID
    )
    assert error.value.role == ("baseline", "candidate")[side]


@pytest.mark.parametrize("side", [0, 1])
@pytest.mark.parametrize("bad", [None, {}, (), "run"])
def test_wrong_run_types(side, bad, runs) -> None:
    args = list(runs)
    args[side] = bad
    with pytest.raises(ComparisonError) as error:
        compare_runs(*args)
    assert error.value.code is Code.INVALID_RUN_TYPE
    assert error.value.role == ("baseline", "candidate")[side]


@pytest.mark.parametrize(
    "target,field,value",
    [
        ("run", "provenance", {}),
        ("run", "results", []),
        ("run", "results", ()),
        ("run", "results", ({},)),
        ("run", "result_sha256", "not-a-digest"),
        ("provenance", "dataset_sha256", "bad"),
        ("provenance", "python_integer_limit", True),
        ("case", "case_id", []),
        ("case", "case_id", "INVALID"),
        ("case", "checks", []),
        ("case", "checks", ()),
        ("case", "checks", ({},)),
        ("check", "passed", 1),
        ("check", "passed", None),
        ("check", "evaluator_id", []),
        ("check", "evaluator_version", ""),
        ("check", "explanation", ""),
    ],
)
def test_revalidate_nested_structure(target, field, value, runs) -> None:
    run = copy.deepcopy(runs[1])
    obj = {
        "run": run,
        "provenance": run.provenance,
        "case": run.results[0],
        "check": run.results[0].checks[0],
    }[target]
    object.__setattr__(obj, field, value)
    with pytest.raises(ComparisonError) as error:
        compare_runs(runs[0], run)
    assert error.value.code is Code.INVALID_RESULT_STRUCTURE
    assert error.value.role == "candidate"
    assert error.value.__cause__ is not None


def test_uninitialized_run_has_a_coded_error(runs) -> None:
    with pytest.raises(ComparisonError) as error:
        compare_runs(object.__new__(RunResult), runs[1])
    assert error.value.code is Code.INVALID_RESULT_STRUCTURE


@pytest.mark.parametrize("missing", ["provenance", "fingerprint"])
def test_incomplete_legacy_evidence(missing, runs) -> None:
    run = runs[0]
    if missing == "provenance":
        p = run.provenance
        legacy = RunProvenance(
            p.dataset_id,
            p.dataset_version,
            p.dataset_sha256,
            p.outputs_sha256,
            p.candidate_version,
            p.evaluator_suite_version,
        )
        run = signed(run, provenance=legacy)
    else:
        run = replace(run, result_sha256=None)
    with pytest.raises(ComparisonError) as error:
        compare_runs(run, runs[1])
    assert error.value.code is Code.INCOMPLETE_PROVENANCE


@pytest.mark.parametrize("mutation", ["status", "explanation", "labels", "digest"])
def test_stale_fingerprints_rejected(mutation, runs) -> None:
    run = runs[1]
    if mutation in ("status", "explanation"):
        case = run.results[0]
        changes = (
            {"passed": not case.checks[0].passed}
            if mutation == "status"
            else {"explanation": "A different explanation"}
        )
        changed = replace(case, checks=(replace(case.checks[0], **changes),))
        run = replace(run, results=(changed, *run.results[1:]))
    elif mutation == "labels":
        run = replace(run, provenance=replace(run.provenance, candidate_version="new"))
    else:
        run = replace(run, result_sha256="0" * 64)
    with pytest.raises(ComparisonError) as error:
        compare_runs(runs[0], run)
    assert error.value.code is Code.RUN_FINGERPRINT_MISMATCH


def test_no_partial_comparison_on_late_case_failure(runs) -> None:
    run = runs[1]
    last = run.results[-1]
    last = replace(last, checks=(replace(last.checks[0], evaluator_id="unexpected-check"),))
    broken = signed(run, results=(*run.results[:-1], last))
    with pytest.raises(ComparisonError) as error:
        compare_runs(runs[0], broken)
    assert error.value.code is Code.EVALUATOR_ID_MISMATCH
    assert error.value.case_id == last.case_id
    assert not hasattr(error.value, "result") and not hasattr(error.value, "cases")
    assert compare_runs(*runs).case_counts == TransitionCounts(2, 1, 3, 0)


def test_immutability_purity_and_repeatability(runs, monkeypatch) -> None:
    import fixturedelta_lab.metrics
    import fixturedelta_lab.runner

    before = copy.deepcopy(runs)

    def forbidden(*args, **kwargs):
        pytest.fail("Comparison attempted I/O or reevaluation")

    monkeypatch.setattr(Path, "read_bytes", forbidden)
    monkeypatch.setattr(fixturedelta_lab.metrics, "evaluate_case", forbidden)
    monkeypatch.setattr(fixturedelta_lab.runner, "evaluate_run", forbidden)
    result = compare_runs(*runs)
    assert compare_runs(*runs) == result
    assert runs == before
    for obj, name, value in [
        (result, "cases", ()),
        (result.cases[0], "checks", ()),
        (result.cases[0].checks[0], "candidate_passed", True),
        (result.provenance, "dataset_id", "new"),
        (result.provenance.baseline, "candidate_version", "new"),
        (result.case_counts, "regressions", 0),
    ]:
        with pytest.raises(FrozenInstanceError):
            setattr(obj, name, value)


def test_comparison_hash_independent_oracle(runs) -> None:
    left, right = synthetic(runs[0], (True,)), synthetic(runs[1], (False,))
    result = compare_runs(left, right)
    p = left.provenance
    payload = {
        "fingerprint_version": "trustbench-comparison-v1",
        "provenance": {
            "dataset_id": p.dataset_id,
            "dataset_version": p.dataset_version,
            "dataset_sha256": p.dataset_sha256,
            "evaluation_contract_version": "1.1.0",
            "evaluator_suite_version": "1.0.0",
            "python_integer_limit": p.python_integer_limit,
            "comparison_contract_version": "1.0.0",
            "baseline": {
                "output_set_id": "baseline",
                "output_set_version": "1.0.0",
                "candidate_version": p.candidate_version,
                "outputs_sha256": p.outputs_sha256,
                "run_sha256": left.result_sha256,
            },
            "candidate": {
                "output_set_id": "candidate",
                "output_set_version": "2.0.0",
                "candidate_version": right.provenance.candidate_version,
                "outputs_sha256": right.provenance.outputs_sha256,
                "run_sha256": right.result_sha256,
            },
        },
        "cases": [
            {
                "case_id": "mixed-demo",
                "checks": [
                    {
                        "evaluator_id": "check-0",
                        "evaluator_version": "1.0.0",
                        "baseline_passed": True,
                        "candidate_passed": False,
                        "baseline_explanation": "Έτοιμο / ready",
                        "candidate_explanation": "Έτοιμο / ready",
                    }
                ],
            }
        ],
    }
    canonical = json.dumps(
        payload, sort_keys=True, ensure_ascii=True, separators=(",", ":"), allow_nan=False
    ).encode("ascii")
    assert result.comparison_sha256 == hashlib.sha256(canonical).hexdigest()
    assert set(asdict(result)) == {"provenance", "cases", "comparison_sha256"}
    assert "timestamp" not in str(asdict(result))


@pytest.mark.parametrize(
    "field,value",
    [
        ("candidate_version", "new-app"),
        ("output_set_id", "new-output-set"),
        ("output_set_version", "2.1.0"),
        ("outputs_sha256", "a" * 64),
    ],
)
def test_allowed_provenance_differences_change_fingerprint(field, value, runs) -> None:
    changed = signed(runs[1], provenance=replace(runs[1].provenance, **{field: value}))
    before, after = compare_runs(*runs), compare_runs(runs[0], changed)
    assert before.cases == after.cases
    assert before.comparison_sha256 != after.comparison_sha256


def test_explanation_only_change_is_not_regression(runs) -> None:
    base = runs[0]
    case = base.results[0]
    changed = replace(case, checks=(replace(case.checks[0], explanation="Νέα εξήγηση"),))
    candidate = signed(base, results=(changed, *base.results[1:]))
    before, after = compare_runs(base, base), compare_runs(base, candidate)
    assert before.case_counts == after.case_counts
    assert before.check_counts == after.check_counts
    assert before.comparison_sha256 != after.comparison_sha256
    assert after.cases[0].checks[0].candidate_explanation == "Νέα εξήγηση"


def test_contract_version_is_hashed(runs) -> None:
    result = compare_runs(*runs)
    p = replace(result.provenance, comparison_contract_version="2.0.0")
    assert comparison_sha256(p, result.cases) != result.comparison_sha256


@pytest.mark.parametrize("bad", [-1, True, "1"])
def test_count_contract(bad) -> None:
    with pytest.raises(ContractError):
        TransitionCounts(bad, 0, 0, 0)


@pytest.mark.parametrize(
    "field,value",
    [
        ("evaluator_id", "INVALID"),
        ("evaluator_version", ""),
        ("baseline_passed", 1),
        ("candidate_passed", None),
        ("baseline_explanation", ""),
        ("candidate_explanation", ""),
    ],
)
def test_check_comparison_contract(field, value, runs) -> None:
    check = compare_runs(*runs).cases[0].checks[0]
    with pytest.raises(ContractError):
        replace(check, **{field: value})


@pytest.mark.parametrize(
    "field,value",
    [
        ("output_set_id", "INVALID"),
        ("output_set_version", "v1"),
        ("candidate_version", ""),
        ("outputs_sha256", "bad"),
        ("run_sha256", None),
    ],
)
def test_run_reference_contract(field, value, runs) -> None:
    ref = compare_runs(*runs).provenance.baseline
    with pytest.raises(ContractError):
        replace(ref, **{field: value})


@pytest.mark.parametrize(
    "field,value",
    [
        ("baseline", None),
        ("candidate", None),
        ("dataset_id", "INVALID"),
        ("dataset_version", "v1"),
        ("dataset_sha256", "bad"),
        ("evaluation_contract_version", "v1"),
        ("evaluator_suite_version", ""),
        ("python_integer_limit", -1),
        ("python_integer_limit", True),
        ("comparison_contract_version", "v1"),
    ],
)
def test_comparison_provenance_contract(field, value, runs) -> None:
    p = compare_runs(*runs).provenance
    with pytest.raises(ContractError):
        replace(p, **{field: value})


@pytest.mark.parametrize("bad", [(), [], ("not-a-check",), "duplicate"])
def test_case_comparison_contract(bad, runs) -> None:
    case = compare_runs(*runs).cases[0]
    checks = (case.checks[0], case.checks[0]) if bad == "duplicate" else bad
    with pytest.raises(ContractError):
        replace(case, checks=checks)


@pytest.mark.parametrize(
    "field,value",
    [
        ("provenance", None),
        ("cases", ()),
        ("cases", []),
        ("cases", ("bad",)),
        ("comparison_sha256", "bad"),
        ("cases", "duplicate"),
    ],
)
def test_comparison_result_contract(field, value, runs) -> None:
    result = compare_runs(*runs)
    if value == "duplicate":
        value = (result.cases[0], result.cases[0])
    with pytest.raises(ContractError):
        replace(result, **{field: value})
    assert isinstance(result, ComparisonResult)
    assert isinstance(result.provenance, ComparisonProvenance)
    assert isinstance(result.provenance.baseline, RunReference)
    assert isinstance(result.cases[0], CaseComparison)
    assert isinstance(result.cases[0].checks[0], CheckComparison)
