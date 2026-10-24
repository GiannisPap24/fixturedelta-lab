"""Strict JSON parsing and the schema-v1 shallow object contract."""

import json
import math

from fixturedelta_lab.domain import CheckResult, JsonObject, JsonType
from fixturedelta_lab.metrics._common import preview, validate_inputs

EVALUATOR_ID = "json-object"
EVALUATOR_VERSION = "1.0.0"
MAX_JSON_DEPTH = 64
MAX_INTEGER_DIGITS = 4300


class _InvalidJson(ValueError):
    """Stable internal parse diagnostic, converted to a failed response check."""


def _check_depth(output: str) -> None:
    # Resolve quoted spans right-to-left so an unterminated string cannot cause
    # repeated scans of its suffix. Preserve the original lexical tokenization,
    # including malformed text: backslash escapes one non-newline character.
    quoted_ends: dict[int, int] = {}
    next_end = after_next_end = None
    for index in range(len(output) - 1, -1, -1):
        character = output[index]
        if character == '"':
            if next_end is not None:
                quoted_ends[index] = next_end + 1
            end = index
        elif character == "\\":
            end = after_next_end if index + 1 < len(output) and output[index + 1] != "\n" else None
        else:
            end = next_end
        after_next_end, next_end = next_end, end

    # Syntax validation remains json.loads' responsibility. Both passes are linear.
    depth = 0
    index = 0
    while index < len(output):
        if index in quoted_ends:
            index = quoted_ends[index]
            continue
        value = output[index]
        if value in ("{", "["):
            depth += 1
            if depth > MAX_JSON_DEPTH:
                raise _InvalidJson(f"nesting exceeds {MAX_JSON_DEPTH} containers")
        elif value in ("}", "]"):
            depth -= 1
        index += 1


def _integer(value: str) -> int:
    if len(value.lstrip("-")) > MAX_INTEGER_DIGITS:
        raise _InvalidJson(f"integer exceeds {MAX_INTEGER_DIGITS} digits")
    return int(value)


def _object(pairs: list[tuple[str, object]]) -> dict[str, object]:
    result: dict[str, object] = {}
    for key, value in pairs:
        if key in result:
            raise _InvalidJson(f"duplicate key {preview(key)}")
        result[key] = value
    return result


def _constant(value: str) -> None:
    raise _InvalidJson(f"non-finite constant {value}")


def _float(value: str) -> float:
    number = float(value)
    if not math.isfinite(number):
        raise _InvalidJson("non-finite number (float overflow)")
    return number


def _type(value: object) -> JsonType:
    # Values originate only from json.loads; bool must be checked before int.
    if value is None:
        return JsonType.NULL
    return {
        str: JsonType.STRING,
        bool: JsonType.BOOLEAN,
        int: JsonType.INTEGER,
        float: JsonType.NUMBER,
        dict: JsonType.OBJECT,
        list: JsonType.ARRAY,
    }[type(value)]


def evaluate_json_object(output: str, expectation: JsonObject) -> CheckResult:
    validate_inputs(output, expectation, JsonObject)
    try:
        _check_depth(output)
        value = json.loads(
            output,
            object_pairs_hook=_object,
            parse_constant=_constant,
            parse_float=_float,
            parse_int=_integer,
        )
    except _InvalidJson as exc:
        return CheckResult(EVALUATOR_ID, EVALUATOR_VERSION, False, f"JSON_INVALID: {exc}.")
    except json.JSONDecodeError as exc:
        return CheckResult(
            EVALUATOR_ID,
            EVALUATOR_VERSION,
            False,
            f"JSON_INVALID: malformed JSON at line {exc.lineno}, column {exc.colno}.",
        )
    except (ValueError, RecursionError):
        return CheckResult(
            EVALUATOR_ID,
            EVALUATOR_VERSION,
            False,
            "JSON_INVALID: parser numeric or nesting limit exceeded.",
        )
    if not isinstance(value, dict):
        return CheckResult(
            EVALUATOR_ID,
            EVALUATOR_VERSION,
            False,
            f"JSON_ROOT_TYPE: expected object; observed {_type(value).value}.",
        )

    details: list[str] = []
    passed = True
    for field in expectation.required_fields:
        name = preview(field.name)
        if field.name not in value:
            details.append(f"MISSING_FIELD {name}: expected {field.value_type.value}")
            passed = False
            continue
        actual_type = _type(value[field.name])
        matches = actual_type == field.value_type or (
            field.value_type == JsonType.NUMBER and actual_type == JsonType.INTEGER
        )
        if matches:
            details.append(f"FIELD_OK {name}: {actual_type.value}")
        else:
            details.append(
                f"FIELD_TYPE {name}: expected {field.value_type.value}; "
                f"observed {actual_type.value}"
            )
            passed = False
    extras = sorted(value.keys() - {field.name for field in expectation.required_fields})
    if extras:
        allowed = expectation.allow_extra_fields
        details.append(
            f"{'EXTRA_FIELDS_ALLOWED' if allowed else 'EXTRA_FIELDS'}: "
            + ", ".join(preview(name) for name in extras)
        )
        passed = passed and allowed
    summary = "; ".join(details) if details else "empty object matches the contract"
    code = "JSON_OBJECT_MATCH" if passed else "JSON_OBJECT_MISMATCH"
    return CheckResult(EVALUATOR_ID, EVALUATOR_VERSION, passed, f"{code}: {summary}.")
