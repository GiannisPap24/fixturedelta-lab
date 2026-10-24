"""Strict local JSON input loading and dataset/output alignment validation."""

import json
from pathlib import Path

from fixturedelta_lab.domain import (
    Case,
    ContentRules,
    ContractError,
    Dataset,
    ExactMatch,
    Expectation,
    JsonField,
    JsonObject,
    JsonType,
    OutputSet,
    RecordedOutput,
)


def _object(value: object, field: str) -> dict[str, object]:
    if not isinstance(value, dict) or not all(isinstance(key, str) for key in value):
        raise ContractError(f"{field}: expected a JSON object")
    return value


def _keys(value: dict[str, object], expected: set[str], field: str) -> None:
    missing = expected - value.keys()
    extra = value.keys() - expected
    if missing or extra:
        raise ContractError(
            f"{field}: missing fields {sorted(missing)}; unknown fields {sorted(extra)}"
        )


def _string(value: object, field: str) -> str:
    if not isinstance(value, str):
        raise ContractError(f"{field}: expected a string")
    return value


def _array(value: object, field: str) -> list[object]:
    if not isinstance(value, list):
        raise ContractError(f"{field}: expected an array")
    return value


def _strings(value: object, field: str) -> tuple[str, ...]:
    return tuple(_string(item, field) for item in _array(value, field))


def _pairs(pairs: list[tuple[str, object]]) -> dict[str, object]:
    result: dict[str, object] = {}
    for key, value in pairs:
        if key in result:
            raise ContractError("JSON: duplicate object keys are not allowed")
        result[key] = value
    return result


def _reject_constant(value: str) -> None:
    raise ContractError("JSON: non-finite constants are not allowed")


def _decode(raw: bytes) -> dict[str, object]:
    if not isinstance(raw, bytes):
        raise ContractError("input: expected immutable UTF-8 bytes")
    try:
        value = json.loads(
            raw.decode("utf-8"),
            object_pairs_hook=_pairs,
            parse_constant=_reject_constant,
        )
    except ContractError:
        raise
    except (ValueError, UnicodeError, RecursionError) as exc:
        raise ContractError("input: expected valid UTF-8 JSON without a BOM") from exc
    return _object(value, "document")


def _schema_version(value: object) -> None:
    if type(value) is not int or value != 1:
        raise ContractError("schema_version: only integer 1 is supported")


def _expectation(value: object) -> Expectation:
    data = _object(value, "expectation")
    kind = data.get("kind")
    if kind == "exact_match":
        _keys(data, {"kind", "expected"}, "exact_match")
        return ExactMatch(_string(data["expected"], "expected"))
    if kind == "content_rules":
        _keys(data, {"kind", "required", "forbidden"}, "content_rules")
        return ContentRules(
            required=_strings(data["required"], "required"),
            forbidden=_strings(data["forbidden"], "forbidden"),
        )
    if kind == "json_object":
        _keys(data, {"kind", "required_fields", "allow_extra_fields"}, "json_object")
        fields = _object(data["required_fields"], "required_fields")
        parsed_fields: list[JsonField] = []
        for name, field_type in fields.items():
            try:
                value_type = JsonType(_string(field_type, "JSON field type"))
            except ValueError as exc:
                raise ContractError("JSON field type: unsupported type") from exc
            parsed_fields.append(JsonField(name, value_type))
        allow_extra = data["allow_extra_fields"]
        if type(allow_extra) is not bool:
            raise ContractError("allow_extra_fields: expected a boolean")
        return JsonObject(tuple(parsed_fields), allow_extra)
    raise ContractError("expectation: unsupported kind")


def _case(value: object) -> Case:
    data = _object(value, "case")
    _keys(data, {"case_id", "category", "language", "prompt", "expectation"}, "case")
    return Case(
        case_id=_string(data["case_id"], "case_id"),
        category=_string(data["category"], "category"),
        language=_string(data["language"], "language"),
        prompt=_string(data["prompt"], "prompt"),
        expectation=_expectation(data["expectation"]),
    )


def load_dataset(path: Path) -> Dataset:
    """Load a schema-v1 synthetic dataset, preserving input order and text."""
    return parse_dataset(path.read_bytes())


def parse_dataset(raw: bytes) -> Dataset:
    """Validate one immutable snapshot; preserve declared case order and text."""
    data = _decode(raw)
    _keys(data, {"schema_version", "dataset_id", "dataset_version", "origin", "cases"}, "dataset")
    _schema_version(data["schema_version"])
    if data["origin"] != "synthetic":
        raise ContractError("origin: schema v1 accepts only synthetic datasets")
    return Dataset(
        dataset_id=_string(data["dataset_id"], "dataset_id"),
        dataset_version=_string(data["dataset_version"], "dataset_version"),
        cases=tuple(_case(value) for value in _array(data["cases"], "cases")),
    )


def _output(value: object) -> RecordedOutput:
    data = _object(value, "output record")
    _keys(data, {"case_id", "output"}, "output record")
    return RecordedOutput(
        case_id=_string(data["case_id"], "case_id"),
        output=_string(data["output"], "output"),
    )


def load_outputs(path: Path) -> OutputSet:
    """Load a local output set without evaluating or aligning it."""
    return parse_outputs(path.read_bytes())


def parse_outputs(raw: bytes) -> OutputSet:
    """Validate one immutable snapshot without evaluating or aligning it."""
    data = _decode(raw)
    _keys(
        data,
        {
            "schema_version",
            "dataset_id",
            "dataset_version",
            "candidate_version",
            "source",
            "outputs",
        },
        "output set",
    )
    _schema_version(data["schema_version"])
    return OutputSet(
        dataset_id=_string(data["dataset_id"], "dataset_id"),
        dataset_version=_string(data["dataset_version"], "dataset_version"),
        candidate_version=_string(data["candidate_version"], "candidate_version"),
        source=_string(data["source"], "source"),
        outputs=tuple(_output(value) for value in _array(data["outputs"], "outputs")),
    )


def validate_alignment(dataset: Dataset, outputs: OutputSet) -> None:
    """Require the same dataset identity/version and exactly one output per case."""
    if (dataset.dataset_id, dataset.dataset_version) != (
        outputs.dataset_id,
        outputs.dataset_version,
    ):
        raise ContractError("alignment: dataset identity/version mismatch")
    expected = {case.case_id for case in dataset.cases}
    actual = {output.case_id for output in outputs.outputs}
    if expected != actual:
        raise ContractError(
            f"alignment: missing case IDs {sorted(expected - actual)}; "
            f"unexpected case IDs {sorted(actual - expected)}"
        )
