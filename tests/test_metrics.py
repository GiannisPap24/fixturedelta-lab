"""Offline behavioral tests for evaluator semantics and the single-case interface."""

import json
from collections.abc import Callable
from dataclasses import asdict
from pathlib import Path

import pytest

from fixturedelta_lab.datasets import load_dataset, load_outputs
from fixturedelta_lab.domain import (
    Case,
    ContentRules,
    ContractError,
    ExactMatch,
    JsonField,
    JsonObject,
    JsonType,
    RecordedOutput,
)
from fixturedelta_lab.metrics import (
    evaluate_case,
    evaluate_content_rules,
    evaluate_exact_match,
    evaluate_json_object,
)


@pytest.mark.parametrize(
    ("expected", "output", "passed"),
    [
        ("READY", "READY", True),
        ("Έτοιμο", "Έτοιμο", True),
        ("", "", True),
        ("Έτοιμο", "Ε\u0301τοιμο", False),
        ("Έτοιμο", "Ετοιμο", False),
        ("σ", "ς", False),
        ("READY", "ready", False),
        ("έτοιμο", "Έτοιμο", False),
        ("ok", " ok", False),
        ("ok", "ok ", False),
        ("ok\n", "ok\r\n", False),
        ("ok", "ok\n", False),
        ("", " ", False),
        ("ok", "", False),
        ("", "ok", False),
        ("a\tb", "a b", False),
        ("a b", "a\u00a0b", False),
        ("🙂", "🙂", True),
    ],
)
def test_literal_exact_match(expected: str, output: str, passed: bool) -> None:
    check = evaluate_exact_match(output, ExactMatch(expected))
    assert check.passed is passed
    assert (check.evaluator_id, check.evaluator_version) == ("exact-match", "1.0.0")
    assert check.explanation.startswith("EXACT_MATCH:" if passed else "EXACT_MISMATCH:")


def test_exact_failure_diagnostic_is_stable_and_escaped() -> None:
    check = evaluate_exact_match("ok\n", ExactMatch("ok"))
    assert check.explanation == (
        'EXACT_MISMATCH: first difference at code-point offset 2; expected "ok"; '
        'observed "ok\\n". Case, whitespace, and Unicode normalization forms are significant.'
    )
    assert "offset 0" in evaluate_exact_match("a", ExactMatch("b")).explanation
    long_check = evaluate_exact_match("x" * 100 + "PRIVATE_SUFFIX", ExactMatch("x" * 101))
    assert "truncated; 114 code points" in long_check.explanation
    assert "PRIVATE_SUFFIX" not in long_check.explanation


def test_each_content_rule_is_explained_in_declared_order() -> None:
    rules = ContentRules(required=("blue", "triangle"), forbidden=("red", "square"))
    checks = evaluate_content_rules("blue square", rules)
    assert [check.evaluator_id for check in checks] == ["required-content", "forbidden-content"]
    assert [check.passed for check in checks] == [False, False]
    assert checks[0].explanation == (
        'REQUIRED_CONTENT: 1: PASS "blue" (present); 2: FAIL "triangle" (absent).'
    )
    assert checks[1].explanation == (
        'FORBIDDEN_CONTENT: 1: PASS "red" (absent); 2: FAIL "square" (present).'
    )


@pytest.mark.parametrize(
    ("output", "rules", "statuses"),
    [
        ("blue triangle", ContentRules(("blue", "triangle"), ("red",)), (True, True)),
        ("πράσινος κύκλος", ContentRules(("πράσινος", "κύκλος")), (True,)),
        ("Πράσινος", ContentRules(("πράσινος",)), (False,)),
        ("Ε\u0301τοιμο", ContentRules(("Έτοιμο",)), (False,)),
        ("", ContentRules(("blue",)), (False,)),
        ("", ContentRules(forbidden=("red",)), (True,)),
        ("μαύρο τρίγωνο", ContentRules(forbidden=("μαύρο",)), (False,)),
        ("RED", ContentRules(forbidden=("red",)), (True,)),
        ("thread", ContentRules(forbidden=("read",)), (False,)),
        ("a.b", ContentRules(("a.b",)), (True,)),
        ("acb", ContentRules(("a.b",)), (False,)),
        ("blue\ntriangle", ContentRules(("blue triangle",)), (False,)),
    ],
)
def test_content_is_literal(output: str, rules: ContentRules, statuses: tuple[bool, ...]) -> None:
    checks = evaluate_content_rules(output, rules)
    assert tuple(check.passed for check in checks) == statuses
    assert all(check.evaluator_version == "1.0.0" for check in checks)


@pytest.mark.parametrize(
    ("output", "reason"),
    [
        ("", "malformed JSON at line 1, column 1"),
        ("{", "malformed JSON"),
        ('{"x": 1,}', "malformed JSON"),
        ('{"x": 01}', "malformed JSON"),
        ("```json\n{}\n```", "malformed JSON"),
        ("{} {}", "malformed JSON"),
        ('{"x": "line\nbreak"}', "malformed JSON"),
        ("\ufeff{}", "malformed JSON"),
        ('{"x": 1, "x": 2}', 'duplicate key "x"'),
        ('{"x": {"a": 1, "a": 2}}', 'duplicate key "a"'),
        ('{"x": [{"a": 1, "\\u0061": 2}]}', 'duplicate key "a"'),
        ('{"x": NaN}', "non-finite constant NaN"),
        ('{"x": Infinity}', "non-finite constant Infinity"),
        ('{"x": -Infinity}', "non-finite constant -Infinity"),
        ('{"x": [1e999]}', "non-finite number (float overflow)"),
        ('{"x": {"nested": -1e999}}', "non-finite number (float overflow)"),
        pytest.param(
            "[" * 10000 + "]" * 10000,
            "nesting exceeds 64 containers",
            id="parser-nesting-limit",
        ),
        pytest.param(
            '{"x": ' + "1" * 5000 + "}",
            "integer exceeds 4300 digits",
            id="parser-integer-limit",
        ),
    ],
)
def test_json_rejects_invalid_documents(output: str, reason: str) -> None:
    result = evaluate_json_object(output, JsonObject((), allow_extra_fields=True))
    assert result.passed is False
    assert result.explanation.startswith("JSON_INVALID:")
    assert reason in result.explanation


@pytest.mark.parametrize("output", ["null", "[]", '"text"', "false", "2", "2.0"])
def test_json_requires_root_object(output: str) -> None:
    result = evaluate_json_object(output, JsonObject(()))
    assert result.passed is False
    assert result.explanation.startswith("JSON_ROOT_TYPE: expected object; observed ")


@pytest.mark.parametrize("expected_type", list(JsonType))
@pytest.mark.parametrize(
    ("value", "actual_type"),
    [
        ("κείμενο", JsonType.STRING),
        (4, JsonType.INTEGER),
        (2.0, JsonType.NUMBER),
        (True, JsonType.BOOLEAN),
        ({"nested": [1]}, JsonType.OBJECT),
        ([False, None], JsonType.ARRAY),
        (None, JsonType.NULL),
    ],
)
def test_json_type_matrix(expected_type: JsonType, value: object, actual_type: JsonType) -> None:
    spec = JsonObject((JsonField("τιμή", expected_type),))
    check = evaluate_json_object(json.dumps({"τιμή": value}, ensure_ascii=False), spec)
    matches = expected_type == actual_type or (
        expected_type == JsonType.NUMBER and actual_type == JsonType.INTEGER
    )
    assert check.passed is matches
    assert (check.evaluator_id, check.evaluator_version) == ("json-object", "1.0.0")
    if not matches:
        assert f"expected {expected_type.value}; observed {actual_type.value}" in check.explanation


def test_json_missing_null_and_extra_keys_have_stable_distinct_diagnostics() -> None:
    spec = JsonObject((JsonField("missing", JsonType.NULL), JsonField("present", JsonType.STRING)))
    check = evaluate_json_object('{"z": 1, "present": null, "a": 2}', spec)
    assert check.explanation == (
        'JSON_OBJECT_MISMATCH: MISSING_FIELD "missing": expected null; '
        'FIELD_TYPE "present": expected string; observed null; EXTRA_FIELDS: "a", "z".'
    )
    reordered = evaluate_json_object('{"a": 2, "present": null, "z": 1}', spec)
    assert check == reordered
    assert evaluate_json_object('{"x": null}', JsonObject((JsonField("x", JsonType.NULL),))).passed


def test_json_empty_and_extra_field_policies() -> None:
    assert evaluate_json_object(" \r\n{}\t", JsonObject(())).passed
    assert not evaluate_json_object('{"x": 0}', JsonObject(())).passed
    check = evaluate_json_object('{"x": 0}', JsonObject((), True))
    assert check.passed
    assert 'EXTRA_FIELDS_ALLOWED: "x"' in check.explanation
    assert not evaluate_json_object(
        '{"x": false, "extra": 0}', JsonObject((JsonField("x", JsonType.INTEGER),), True)
    ).passed


def test_json_resource_boundaries_and_quoted_delimiters() -> None:
    spec = JsonObject((), True)
    within_depth = '{"x":' + "[" * 63 + "0" + "]" * 63 + "}"
    beyond_depth = '{"x":' + "[" * 64 + "0" + "]" * 64 + "}"
    assert evaluate_json_object(within_depth, spec).passed
    assert "nesting exceeds 64" in evaluate_json_object(beyond_depth, spec).explanation
    assert evaluate_json_object(json.dumps({"x": '[\\"' * 100}), spec).passed
    assert evaluate_json_object('{"x":' + "1" * 4300 + "}", spec).passed
    assert evaluate_json_object('{"x":-' + "1" * 4300 + "}", spec).passed
    assert (
        "integer exceeds 4300"
        in evaluate_json_object('{"x":-' + "1" * 4301 + "}", spec).explanation
    )


def test_restrictive_host_integer_limit_is_reported_without_changing_it() -> None:
    import sys

    original = sys.get_int_max_str_digits()
    try:
        sys.set_int_max_str_digits(640)
        result = evaluate_json_object('{"x":' + "1" * 641 + "}", JsonObject((), True))
        assert result.explanation == "JSON_INVALID: parser numeric or nesting limit exceeded."
        assert sys.get_int_max_str_digits() == 640
    finally:
        sys.set_int_max_str_digits(original)


def test_json_depth_scan_preserves_legacy_tokenization(monkeypatch: pytest.MonkeyPatch) -> None:
    """The resource fix must preserve diagnostics even for malformed quoted text."""
    import itertools
    import re

    from fixturedelta_lab.metrics import json_structure

    monkeypatch.setattr(json_structure, "MAX_JSON_DEPTH", 1)
    for size in range(6):
        for characters in itertools.product('"\\{}[]\nx', repeat=size):
            output = "".join(characters)
            depth = 0
            exceeds = False
            for token in re.finditer(r'"(?:\\.|[^"\\])*"|[{}\[\]]', output):
                if token.group() in ("{", "["):
                    depth += 1
                    if depth > 1:
                        exceeds = True
                        break
                elif token.group() in ("}", "]"):
                    depth -= 1
            if exceeds:
                with pytest.raises(ValueError, match="nesting exceeds 1"):
                    json_structure._check_depth(output)
            else:
                json_structure._check_depth(output)


def test_json_unterminated_escaped_quotes_have_bounded_processing() -> None:
    """A subprocess deadline catches the former repeated suffix scans safely."""
    import subprocess
    import sys

    code = (
        "from fixturedelta_lab.domain import JsonObject; "
        "from fixturedelta_lab.metrics import evaluate_json_object; "
        "output = chr(34) + (chr(92) + chr(34)) * 200000; "
        "result = evaluate_json_object(output, JsonObject(())); "
        "assert not result.passed and result.explanation.startswith('JSON_INVALID:')"
    )
    subprocess.run([sys.executable, "-I", "-c", code], check=True, timeout=10)


@pytest.mark.parametrize(
    ("evaluate", "spec"),
    [
        (evaluate_exact_match, ExactMatch("ok")),
        (evaluate_content_rules, ContentRules(("ok",))),
        (evaluate_json_object, JsonObject(())),
    ],
)
def test_invalid_evaluator_inputs_raise_contract_errors(evaluate: Callable, spec: object) -> None:
    for bad_output in (None, 1, b"ok"):
        with pytest.raises(ContractError, match="output: expected a string"):
            evaluate(bad_output, spec)
    for bad_spec in (None, {}, {"type": "array"}):
        with pytest.raises(ContractError, match="expectation: expected"):
            evaluate("", bad_spec)
    with pytest.raises(TypeError):
        evaluate("")


@pytest.mark.parametrize(
    "factory",
    [
        lambda: ExactMatch(None),
        lambda: ContentRules(),
        lambda: ContentRules(("x",), ("x",)),
        lambda: ContentRules(("x", "x")),
        lambda: ContentRules(forbidden=("",)),
        lambda: JsonField("x", "unsupported"),
        lambda: JsonObject((JsonField("x", JsonType.NULL),), "false"),
        lambda: JsonObject(("not a field",)),
    ],
)
def test_malformed_configuration_is_rejected_before_evaluation(factory: Callable) -> None:
    with pytest.raises(ContractError):
        factory()


@pytest.mark.parametrize(
    ("filename", "expected"),
    [
        ("baseline-v1.json", (True, True, True, False, True, True)),
        ("candidate-v2.json", (False, True, True, True, False, True)),
    ],
)
def test_each_fixture_case_is_repeatable_and_inputs_remain_immutable(
    fixture_dir: Path, filename: str, expected: tuple[bool, ...]
) -> None:
    dataset = load_dataset(fixture_dir / "golden-v1.0.0.json")
    outputs = load_outputs(fixture_dir / filename)
    before = (asdict(dataset), asdict(outputs))
    by_id = {item.case_id: item for item in outputs.outputs}
    for case, passed in zip(dataset.cases, expected, strict=True):
        result = evaluate_case(case, by_id[case.case_id])
        assert result.case_id == case.case_id
        assert result.passed is passed
        assert all(
            check.explanation and check.evaluator_version == "1.0.0" for check in result.checks
        )
        assert all(evaluate_case(case, by_id[case.case_id]) == result for _ in range(5))
    assert (asdict(dataset), asdict(outputs)) == before


def test_single_case_adapter_rejects_wrong_types_and_ids() -> None:
    case = Case("en-1", "exact", "en", "Reply ok", ExactMatch("ok"))
    with pytest.raises(ContractError, match="case_id mismatch"):
        evaluate_case(case, RecordedOutput("en-2", "ok"))
    with pytest.raises(ContractError, match="expected Case and RecordedOutput"):
        evaluate_case(None, RecordedOutput("en-1", "ok"))
    with pytest.raises(ContractError, match="expected Case and RecordedOutput"):
        evaluate_case(case, "ok")
