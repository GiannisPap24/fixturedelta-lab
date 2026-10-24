"""Offline integration, failure atomicity, and independent fingerprint oracles."""

import hashlib
import json
import sys
from dataclasses import FrozenInstanceError, asdict, replace
from pathlib import Path

import pytest

from fixturedelta_lab import runner
from fixturedelta_lab.datasets import parse_dataset, parse_outputs
from fixturedelta_lab.domain import CaseResult, CheckResult, ContractError, RunProvenance, RunResult
from fixturedelta_lab.provenance import content_sha256, result_sha256
from fixturedelta_lab.runner import RunError, RunErrorCode, evaluate_run, run_evaluation

LABELS = {"output_set_id": "synthetic-baseline", "output_set_version": "1.0.0"}


def encode(value: object) -> bytes:
    return json.dumps(value, ensure_ascii=False).encode("utf-8")


@pytest.fixture
def snapshots(fixture_dir: Path) -> tuple[bytes, bytes]:
    return (
        (fixture_dir / "golden-v1.0.0.json").read_bytes(),
        (fixture_dir / "baseline-v1.json").read_bytes(),
    )


def test_multi_case_oracles_and_versions(fixture_dir: Path, snapshots: tuple[bytes, bytes]) -> None:
    baseline = evaluate_run(*snapshots, **LABELS)
    candidate = run_evaluation(
        fixture_dir / "golden-v1.0.0.json",
        fixture_dir / "candidate-v2.json",
        output_set_id="synthetic-candidate",
        output_set_version="2.0.0",
    )
    assert [case.passed for case in baseline.results] == [True, True, True, False, True, True]
    assert [case.passed for case in candidate.results] == [False, True, True, True, False, True]
    assert [case.case_id for case in baseline.results] == [
        "en-label-001",
        "el-label-001",
        "en-rules-001",
        "el-rules-001",
        "en-json-001",
        "el-json-001",
    ]
    assert [[check.evaluator_id for check in case.checks] for case in baseline.results] == [
        ["exact-match"],
        ["exact-match"],
        ["required-content", "forbidden-content"],
        ["required-content", "forbidden-content"],
        ["json-object"],
        ["json-object"],
    ]
    assert {check.evaluator_version for case in baseline.results for check in case.checks} == {
        "1.0.0"
    }
    assert baseline.provenance.candidate_version == "synthetic-baseline-v1"
    assert candidate.provenance.candidate_version == "synthetic-candidate-v2"


@pytest.mark.parametrize("index", range(6))
def test_single_case(index: int, snapshots: tuple[bytes, bytes]) -> None:
    dataset, outputs = map(json.loads, snapshots)
    dataset["cases"] = [dataset["cases"][index]]
    outputs["outputs"] = [outputs["outputs"][index]]
    result = evaluate_run(encode(dataset), encode(outputs), **LABELS)
    assert len(result.results) == 1
    assert result.results[0].passed is (index != 3)


@pytest.mark.parametrize("empty_group", ["required", "forbidden"])
def test_content_with_only_one_group(empty_group: str, snapshots: tuple[bytes, bytes]) -> None:
    dataset, outputs = map(json.loads, snapshots)
    dataset["cases"] = [dataset["cases"][2]]
    outputs["outputs"] = [outputs["outputs"][2]]
    dataset["cases"][0]["expectation"][empty_group] = []
    result = evaluate_run(encode(dataset), encode(outputs), **LABELS)
    assert len(result.results[0].checks) == 1
    assert result.results[0].passed


def test_dataset_order_wins_over_output_order(snapshots: tuple[bytes, bytes]) -> None:
    dataset, outputs = map(json.loads, snapshots)
    dataset["cases"] = dataset["cases"][2:] + dataset["cases"][:2]
    outputs["outputs"].reverse()
    result = evaluate_run(encode(dataset), encode(outputs), **LABELS)
    assert [case.case_id for case in result.results] == [
        case["case_id"] for case in dataset["cases"]
    ]
    assert [case.passed for case in result.results] == [True, False, True, True, True, True]


@pytest.mark.parametrize("text", ["Έτοιμο ", "Ε\u0301τοιμο", "έτοιμο", "\nΈτοιμο"])
def test_no_unicode_or_whitespace_normalization(text: str, snapshots: tuple[bytes, bytes]) -> None:
    outputs = json.loads(snapshots[1])
    outputs["outputs"][1]["output"] = text
    raw = encode(outputs)
    assert parse_outputs(raw).outputs[1].output == text
    result = evaluate_run(snapshots[0], raw, **LABELS)
    assert not result.results[1].passed


def test_invalid_response_json_is_a_valid_failed_check(snapshots: tuple[bytes, bytes]) -> None:
    outputs = json.loads(snapshots[1])
    outputs["outputs"][4]["output"] = "{broken JSON"
    result = evaluate_run(snapshots[0], encode(outputs), **LABELS)
    assert len(result.results) == 6
    assert not result.results[4].passed
    assert result.results[4].checks[0].explanation.startswith("JSON_INVALID")


@pytest.mark.parametrize(
    "side,mutation,code",
    [
        (0, "empty", RunErrorCode.DATASET_INVALID),
        (1, "empty", RunErrorCode.OUTPUTS_INVALID),
        (0, "duplicate", RunErrorCode.DATASET_INVALID),
        (1, "duplicate", RunErrorCode.OUTPUTS_INVALID),
        (1, "missing", RunErrorCode.ALIGNMENT_INVALID),
        (1, "extra", RunErrorCode.ALIGNMENT_INVALID),
        (1, "version", RunErrorCode.ALIGNMENT_INVALID),
        (1, "identity", RunErrorCode.ALIGNMENT_INVALID),
        (0, "schema", RunErrorCode.DATASET_INVALID),
        (1, "schema", RunErrorCode.OUTPUTS_INVALID),
        (0, "config", RunErrorCode.DATASET_INVALID),
        (0, "contradictory", RunErrorCode.DATASET_INVALID),
        (0, "unknown-evaluator", RunErrorCode.DATASET_INVALID),
        (0, "origin", RunErrorCode.DATASET_INVALID),
        (0, "unknown-field", RunErrorCode.DATASET_INVALID),
        (1, "unknown-field", RunErrorCode.OUTPUTS_INVALID),
    ],
)
def test_invalid_inputs_never_start_evaluation(
    side: int,
    mutation: str,
    code: RunErrorCode,
    snapshots: tuple[bytes, bytes],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def must_not_run(*args: object) -> None:
        pytest.fail("Invalid run reached an evaluator")

    monkeypatch.setattr(runner, "evaluate_case", must_not_run)
    documents = list(map(json.loads, snapshots))
    data = documents[side]
    rows = data["cases" if side == 0 else "outputs"]
    if mutation == "empty":
        rows.clear()
    elif mutation == "duplicate":
        rows.append(rows[0])
    elif mutation == "missing":
        rows.pop()
    elif mutation == "extra":
        rows.append({"case_id": "unexpected", "output": ""})
    elif mutation == "version":
        data["dataset_version"] = "2.0.0"
    elif mutation == "identity":
        data["dataset_id"] = "another-dataset"
    elif mutation == "schema":
        data["schema_version"] = 2
    elif mutation == "config":
        rows[0]["expectation"]["expected"] = 42
    elif mutation == "contradictory":
        rows[2]["expectation"]["forbidden"] = ["blue"]
    elif mutation == "unknown-evaluator":
        rows[0]["expectation"]["kind"] = "semantic-score"
    elif mutation == "origin":
        data["origin"] = "real"
    else:
        data["unknown"] = True
    with pytest.raises(RunError) as caught:
        evaluate_run(*map(encode, documents), **LABELS)
    assert caught.value.code == code
    assert caught.value.case_id is None
    assert str(caught.value).startswith(f"{code}: ")
    assert isinstance(caught.value.__cause__, ContractError)
    assert not hasattr(caught.value, "results")


@pytest.mark.parametrize("side", [0, 1])
@pytest.mark.parametrize(
    "raw",
    [
        b"",
        b"{",
        b"[]",
        b"\xff",
        b"\xef\xbb\xbf{}",
        b'{"x":1,"x":2}',
        b'{"x":NaN}',
        b"[" * 2000 + b"]" * 2000,
        b'{"x":' + b"1" * 10000 + b"}",
        "not bytes",
        bytearray(b"{}"),
    ],
)
def test_malformed_snapshots(side: int, raw: object, snapshots: tuple[bytes, bytes]) -> None:
    inputs = list(snapshots)
    inputs[side] = raw
    with pytest.raises(RunError) as caught:
        evaluate_run(*inputs, **LABELS)
    assert caught.value.code == (RunErrorCode.DATASET_INVALID, RunErrorCode.OUTPUTS_INVALID)[side]


@pytest.mark.parametrize(
    "labels",
    [
        {"output_set_id": "", "output_set_version": "1.0.0"},
        {"output_set_id": "Absolute/Path", "output_set_version": "1.0.0"},
        {"output_set_id": "valid", "output_set_version": "v1"},
        {"output_set_id": "valid", "output_set_version": "01.0.0"},
        {"output_set_id": None, "output_set_version": "1.0.0"},
    ],
)
def test_invalid_provenance_labels(
    labels: dict,
    snapshots: tuple[bytes, bytes],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(runner, "evaluate_case", lambda *args: pytest.fail("evaluation started"))
    with pytest.raises(RunError) as caught:
        evaluate_run(*snapshots, **labels)
    assert caught.value.code == RunErrorCode.PROVENANCE_INVALID


@pytest.mark.parametrize("side", [0, 1])
@pytest.mark.parametrize("kind", ["missing", "directory", "permission"])
def test_read_errors(
    side: int,
    kind: str,
    tmp_path: Path,
    snapshots: tuple[bytes, bytes],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    paths = [tmp_path / "dataset.json", tmp_path / "outputs.json"]
    for path, raw in zip(paths, snapshots, strict=True):
        path.write_bytes(raw)
    if kind == "missing":
        paths[side] = tmp_path / "absent.json"
    elif kind == "directory":
        paths[side] = tmp_path
    else:
        read = Path.read_bytes

        def deny(path: Path) -> bytes:
            if path == paths[side]:
                raise PermissionError("synthetic permission failure")
            return read(path)

        monkeypatch.setattr(Path, "read_bytes", deny)
    with pytest.raises(RunError) as caught:
        run_evaluation(*paths, **LABELS)
    assert (
        caught.value.code
        == (RunErrorCode.DATASET_READ_ERROR, RunErrorCode.OUTPUTS_READ_ERROR)[side]
    )
    assert isinstance(caught.value.__cause__, OSError)
    assert str(tmp_path) not in str(caught.value)


def test_evaluator_error_discards_partial_results(
    snapshots: tuple[bytes, bytes],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    actual = runner.evaluate_case
    calls = []
    error = RuntimeError("synthetic evaluator crash")

    def crash(case, output):
        calls.append(case.case_id)
        if len(calls) == 3:
            raise error
        return actual(case, output)

    monkeypatch.setattr(runner, "evaluate_case", crash)
    with pytest.raises(RunError) as caught:
        evaluate_run(*snapshots, **LABELS)
    assert calls == ["en-label-001", "el-label-001", "en-rules-001"]
    assert caught.value.code == RunErrorCode.EVALUATOR_ERROR
    assert caught.value.case_id == "en-rules-001"
    assert caught.value.__cause__ is error
    assert not hasattr(caught.value, "results")
    monkeypatch.setattr(runner, "evaluate_case", actual)
    assert len(evaluate_run(*snapshots, **LABELS).results) == 6


@pytest.mark.parametrize(
    "fault", ["type", "case-id", "check-id", "version", "missing-check", "order"]
)
def test_inconsistent_evaluator_result_is_rejected(
    fault: str,
    snapshots: tuple[bytes, bytes],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    actual = runner.evaluate_case

    def corrupt(case, output):
        result = actual(case, output)
        if case.case_id != "en-rules-001":
            return result
        if fault == "type":
            return None
        if fault == "case-id":
            return replace(result, case_id="wrong-case")
        if fault == "check-id":
            return replace(result, checks=(replace(result.checks[0], evaluator_id="unknown"),))
        if fault == "version":
            return replace(result, checks=(replace(result.checks[0], evaluator_version="2.0.0"),))
        if fault == "missing-check":
            return replace(result, checks=result.checks[:1])
        return replace(result, checks=tuple(reversed(result.checks)))

    monkeypatch.setattr(runner, "evaluate_case", corrupt)
    with pytest.raises(RunError) as caught:
        evaluate_run(*snapshots, **LABELS)
    assert caught.value.code == RunErrorCode.RESULT_INVALID
    assert caught.value.case_id == "en-rules-001"
    assert not hasattr(caught.value, "results")


def test_user_interrupt_is_not_wrapped(
    snapshots: tuple[bytes, bytes],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def interrupt(*args):
        raise KeyboardInterrupt

    monkeypatch.setattr(runner, "evaluate_case", interrupt)
    with pytest.raises(KeyboardInterrupt):
        evaluate_run(*snapshots, **LABELS)


def test_inputs_and_results_are_immutable(snapshots: tuple[bytes, bytes]) -> None:
    before = tuple(bytes(bytearray(raw)) for raw in snapshots)
    dataset, outputs = parse_dataset(snapshots[0]), parse_outputs(snapshots[1])
    objects_before = (asdict(dataset), asdict(outputs))
    result = evaluate_run(*snapshots, **LABELS)
    assert snapshots == before
    assert (asdict(dataset), asdict(outputs)) == objects_before
    for obj, field, value in [
        (result, "results", ()),
        (result.provenance, "output_set_id", "changed"),
        (result.results[0], "case_id", "changed"),
        (result.results[0].checks[0], "passed", False),
    ]:
        with pytest.raises(FrozenInstanceError):
            setattr(obj, field, value)


def test_read_once_hashes_actual_evaluated_bytes(
    tmp_path: Path,
    snapshots: tuple[bytes, bytes],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    paths = [tmp_path / "dataset.json", tmp_path / "outputs.json"]
    for path, raw in zip(paths, snapshots, strict=True):
        path.write_bytes(raw)
    read = Path.read_bytes
    calls = []

    def changing_file(path: Path) -> bytes:
        calls.append(path)
        raw = read(path)
        path.write_bytes(b"This replaced the file after its first read.")
        return raw

    monkeypatch.setattr(Path, "read_bytes", changing_file)
    result = run_evaluation(*paths, **LABELS)
    assert calls == paths
    assert result == evaluate_run(*snapshots, **LABELS)
    assert result.provenance.dataset_sha256 == hashlib.sha256(snapshots[0]).hexdigest()
    assert result.provenance.outputs_sha256 == hashlib.sha256(snapshots[1]).hexdigest()


def test_reproducibility_and_path_independence(
    tmp_path: Path, snapshots: tuple[bytes, bytes]
) -> None:
    expected = evaluate_run(*snapshots, **LABELS)
    for folder in [tmp_path / "first", tmp_path / "second"]:
        folder.mkdir()
        paths = [folder / "arbitrary-name.json", folder / "another-name.json"]
        for path, raw in zip(paths, snapshots, strict=True):
            path.write_bytes(raw)
        assert run_evaluation(*paths, **LABELS) == expected
    assert evaluate_run(*snapshots, **LABELS) == expected
    assert expected.provenance.output_set_id == "synthetic-baseline"
    assert expected.provenance.output_set_version == "1.0.0"
    assert expected.provenance.evaluation_contract_version == "1.1.0"
    assert expected.provenance.evaluator_suite_version == "1.0.0"
    assert expected.provenance.python_integer_limit == sys.get_int_max_str_digits()
    serialized = json.dumps(asdict(expected))
    assert str(tmp_path) not in serialized
    assert "timestamp" not in serialized
    assert "source" not in asdict(expected.provenance)


def test_canonical_fingerprint_independent_oracle() -> None:
    provenance = RunProvenance(
        "demo",
        "1.0.0",
        "a" * 64,
        "b" * 64,
        "app-v1",
        "1.0.0",
        output_set_id="outputs",
        output_set_version="1.0.0",
        evaluation_contract_version="1.1.0",
        python_integer_limit=4300,
    )
    results = (CaseResult("el-demo", (CheckResult("exact-match", "1.0.0", True, "Έτοιμο"),)),)
    # Spell out the contract independently; no production asdict or hashing helper.
    expected_payload = {
        "fingerprint_version": "trustbench-run-v1",
        "provenance": {
            "dataset_id": "demo",
            "dataset_version": "1.0.0",
            "dataset_sha256": "a" * 64,
            "outputs_sha256": "b" * 64,
            "candidate_version": "app-v1",
            "evaluator_suite_version": "1.0.0",
            "output_set_id": "outputs",
            "output_set_version": "1.0.0",
            "evaluation_contract_version": "1.1.0",
            "python_integer_limit": 4300,
        },
        "results": [
            {
                "case_id": "el-demo",
                "checks": [
                    {
                        "evaluator_id": "exact-match",
                        "evaluator_version": "1.0.0",
                        "passed": True,
                        "explanation": "Έτοιμο",
                    }
                ],
            }
        ],
    }
    canonical = json.dumps(
        expected_payload, sort_keys=True, separators=(",", ":"), ensure_ascii=True
    )
    assert (
        result_sha256(provenance, results) == hashlib.sha256(canonical.encode("ascii")).hexdigest()
    )
    assert (
        content_sha256(b"abc") == "ba7816bf8f01cfea414140de5dae2223b00361a396177a9cb410ff61f20015ad"
    )


@pytest.mark.parametrize(
    "change",
    [
        "dataset-format",
        "outputs-format",
        "candidate-version",
        "output-content",
        "source",
        "output-set-id",
        "output-set-version",
        "case-order",
        "output-order",
    ],
)
def test_fingerprint_changes_with_evidence_or_identity(
    change: str,
    snapshots: tuple[bytes, bytes],
) -> None:
    first = evaluate_run(*snapshots, **LABELS)
    raw = list(snapshots)
    labels = dict(LABELS)
    if change == "dataset-format":
        raw[0] += b"\n"
    elif change == "outputs-format":
        raw[1] += b"\n"
    elif change in ("output-set-id", "output-set-version"):
        labels[change.replace("-", "_")] = "another" if change.endswith("id") else "2.0.0"
    elif change == "case-order":
        data = json.loads(raw[0])
        data["cases"].reverse()
        raw[0] = encode(data)
    else:
        data = json.loads(raw[1])
        if change == "candidate-version":
            data["candidate_version"] = "new-app-version"
        elif change == "output-content":
            data["outputs"][0]["output"] = "wrong"
        elif change == "source":
            data["source"] = "another synthetic source statement"
        else:
            data["outputs"].reverse()
        raw[1] = encode(data)
    second = evaluate_run(*raw, **labels)
    assert first.result_sha256 != second.result_sha256
    if change in ("dataset-format", "outputs-format", "output-order", "source"):
        assert first.results == second.results


@pytest.mark.parametrize(
    "field,value",
    [
        ("evaluator_suite_version", "2.0.0"),
        ("evaluation_contract_version", "2.0.0"),
        ("python_integer_limit", 640),
    ],
)
def test_fingerprint_includes_behavior_settings(
    field: str,
    value: object,
    snapshots: tuple[bytes, bytes],
) -> None:
    result = evaluate_run(*snapshots, **LABELS)
    changed = replace(result.provenance, **{field: value})
    assert result_sha256(changed, result.results) != result.result_sha256


def test_host_integer_limit_is_captured(snapshots: tuple[bytes, bytes]) -> None:
    before = sys.get_int_max_str_digits()
    try:
        sys.set_int_max_str_digits(640)
        result = evaluate_run(*snapshots, **LABELS)
        assert result.provenance.python_integer_limit == 640
    finally:
        sys.set_int_max_str_digits(before)


@pytest.mark.parametrize(
    "field,value",
    [
        ("passed", False),
        ("explanation", "different explanation"),
        ("evaluator_id", "different-check"),
        ("evaluator_version", "2.0.0"),
    ],
)
def test_fingerprint_includes_every_check_field(
    field: str,
    value: object,
    snapshots: tuple[bytes, bytes],
) -> None:
    result = evaluate_run(*snapshots, **LABELS)
    case = result.results[0]
    changed = replace(case, checks=(replace(case.checks[0], **{field: value}),))
    assert result_sha256(result.provenance, (changed, *result.results[1:])) != result.result_sha256


@pytest.mark.parametrize("value", [-1, True, None, "4300"])
def test_new_provenance_fields_validate_as_a_group(value: object, snapshots: tuple[bytes, bytes]):
    result = evaluate_run(*snapshots, **LABELS)
    with pytest.raises(ContractError, match="python_integer_limit"):
        replace(result.provenance, python_integer_limit=value)
    with pytest.raises(ContractError, match="output_set_id"):
        replace(result.provenance, output_set_id=None)


@pytest.mark.parametrize("value", ["", "A" * 64, "g" * 64, 1])
def test_result_fingerprint_validation(value: object, snapshots: tuple[bytes, bytes]) -> None:
    result = evaluate_run(*snapshots, **LABELS)
    with pytest.raises(ContractError, match="result_sha256"):
        replace(result, result_sha256=value)
    assert isinstance(result, RunResult)
