import json
from collections.abc import Callable
from dataclasses import replace
from pathlib import Path

import pytest

from fixturedelta_lab.datasets import load_dataset, load_outputs, validate_alignment
from fixturedelta_lab.domain import ContractError, Dataset, ExactMatch, OutputSet, RecordedOutput


def test_synthetic_fixtures_are_valid_and_aligned(fixture_dir: Path) -> None:
    dataset = load_dataset(fixture_dir / "golden-v1.0.0.json")
    assert len(dataset.cases) == 6
    assert {case.language for case in dataset.cases} == {"en", "el"}
    assert len({case.category for case in dataset.cases}) == 3
    assert dataset.cases[1].expectation == ExactMatch("Έτοιμο")
    for filename in ("baseline-v1.json", "candidate-v2.json"):
        outputs = load_outputs(fixture_dir / filename)
        validate_alignment(dataset, outputs)
        validate_alignment(dataset, replace(outputs, outputs=tuple(reversed(outputs.outputs))))
        assert outputs.source.startswith("synthetic-handwritten")


@pytest.mark.parametrize(
    ("field", "value", "message"),
    [
        ("schema_version", True, "schema_version"),
        ("schema_version", 1.0, "schema_version"),
        ("schema_version", 2, "schema_version"),
        ("dataset_version", "latest", "dataset_version"),
        ("dataset_id", "Not Stable", "dataset_id"),
        ("origin", "production", "origin"),
        ("cases", [], "must not be empty"),
        ("cases", {}, "expected an array"),
        ("unexpected", "value", "unknown fields"),
    ],
)
def test_reject_invalid_dataset_fields(
    fixture_dir: Path, tmp_path: Path, field: str, value: object, message: str
) -> None:
    data = json.loads((fixture_dir / "golden-v1.0.0.json").read_text(encoding="utf-8"))
    data[field] = value
    path = tmp_path / "invalid.json"
    path.write_text(json.dumps(data), encoding="utf-8")
    with pytest.raises(ContractError, match=message):
        load_dataset(path)


@pytest.mark.parametrize(
    ("field", "value", "message"),
    [
        ("case_id", "", "case_id"),
        ("language", "fr", "language"),
        ("prompt", 42, "prompt"),
        ("expectation", {"kind": "llm_judge"}, "unsupported kind"),
        ("expectation", {"kind": "exact_match"}, "missing fields"),
        ("expectation", {"kind": "exact_match", "expected": None}, "expected a string"),
        ("expectation", {"kind": "exact_match", "expected": "ok", "trim": True}, "unknown"),
        (
            "expectation",
            {"kind": "content_rules", "required": "ok", "forbidden": []},
            "expected an array",
        ),
        (
            "expectation",
            {"kind": "json_object", "required_fields": {"a": "int"}, "allow_extra_fields": False},
            "unsupported type",
        ),
        (
            "expectation",
            {"kind": "json_object", "required_fields": {}, "allow_extra_fields": 0},
            "expected a boolean",
        ),
    ],
)
def test_reject_invalid_case_fields(
    fixture_dir: Path, tmp_path: Path, field: str, value: object, message: str
) -> None:
    data = json.loads((fixture_dir / "golden-v1.0.0.json").read_text(encoding="utf-8"))
    data["cases"][0][field] = value
    path = tmp_path / "invalid.json"
    path.write_text(json.dumps(data), encoding="utf-8")
    with pytest.raises(ContractError, match=message):
        load_dataset(path)


@pytest.mark.parametrize(
    "payload",
    [
        b"{",
        b"[]",
        b"null",
        b'{"schema_version": 1, "schema_version": 1}',
        b'{"nested": {"x": 1, "x": 2}}',
        b'{"x": NaN}',
        b'{"x": Infinity}',
        b"\xff",
        b"\xef\xbb\xbf{}",
    ],
)
def test_reject_malformed_or_ambiguous_json(tmp_path: Path, payload: bytes) -> None:
    path = tmp_path / "invalid.json"
    path.write_bytes(payload)
    for loader in (load_dataset, load_outputs):
        with pytest.raises(ContractError):
            loader(path)


@pytest.mark.parametrize(
    ("filename", "collection", "loader"),
    [
        ("golden-v1.0.0.json", "cases", load_dataset),
        ("baseline-v1.json", "outputs", load_outputs),
    ],
)
def test_reject_duplicate_case_ids(
    fixture_dir: Path,
    tmp_path: Path,
    filename: str,
    collection: str,
    loader: Callable[[Path], Dataset | OutputSet],
) -> None:
    data = json.loads((fixture_dir / filename).read_text(encoding="utf-8"))
    data[collection].append(data[collection][0])
    path = tmp_path / "duplicate.json"
    path.write_text(json.dumps(data), encoding="utf-8")
    with pytest.raises(ContractError, match="duplicate"):
        loader(path)


@pytest.mark.parametrize(
    ("field", "value", "message"),
    [
        ("schema_version", "1", "schema_version"),
        ("candidate_version", " ", "candidate_version"),
        ("source", "", "source"),
        ("outputs", [], "must not be empty"),
        ("outputs", [{"case_id": "en-label-001", "output": None}], "expected a string"),
        ("outputs", [{"case_id": "en-label-001", "output": "ok", "cost": 0}], "unknown"),
    ],
)
def test_reject_invalid_outputs(
    fixture_dir: Path, tmp_path: Path, field: str, value: object, message: str
) -> None:
    data = json.loads((fixture_dir / "baseline-v1.json").read_text(encoding="utf-8"))
    data[field] = value
    path = tmp_path / "invalid.json"
    path.write_text(json.dumps(data), encoding="utf-8")
    with pytest.raises(ContractError, match=message):
        load_outputs(path)


def test_preserve_output_text_and_empty_responses(fixture_dir: Path, tmp_path: Path) -> None:
    data = json.loads((fixture_dir / "baseline-v1.json").read_text(encoding="utf-8"))
    examples = ("", "  Έτοιμο\r\n", "Ε\u0301τοιμο")
    for record, text in zip(data["outputs"], examples, strict=False):
        record["output"] = text
    path = tmp_path / "outputs.json"
    path.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
    outputs = load_outputs(path)
    assert tuple(record.output for record in outputs.outputs[:3]) == examples


def test_alignment_rejects_missing_extra_and_wrong_dataset(fixture_dir: Path) -> None:
    dataset = load_dataset(fixture_dir / "golden-v1.0.0.json")
    outputs = load_outputs(fixture_dir / "baseline-v1.json")
    invalid = (
        replace(outputs, dataset_id="other"),
        replace(outputs, dataset_version="2.0.0"),
        replace(outputs, outputs=outputs.outputs[:-1]),
        replace(outputs, outputs=(*outputs.outputs, RecordedOutput("extra", ""))),
        replace(outputs, outputs=(*outputs.outputs[:-1], RecordedOutput("extra", ""))),
    )
    for output_set in invalid:
        with pytest.raises(ContractError, match="alignment"):
            validate_alignment(dataset, output_set)


def test_missing_file_preserves_os_error(tmp_path: Path) -> None:
    with pytest.raises(FileNotFoundError):
        load_dataset(tmp_path / "missing.json")
