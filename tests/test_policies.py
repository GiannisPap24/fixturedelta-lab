"""Strict policy file parsing and exact, normalized thresholds."""

import json
from fractions import Fraction

import pytest

from fixturedelta_lab.domain import ContractError
from fixturedelta_lab.gate_types import GatePolicy
from fixturedelta_lab.policies import parse_policy
from fixturedelta_lab.provenance import policy_sha256


def policy(**changes):
    return {
        "schema_version": 1,
        "policy_id": "strict-regression",
        "policy_version": "1.0.0",
        "max_regressions": 0,
        **changes,
    }


def encode(value):
    return json.dumps(value).encode()


def test_default_and_null_disabled_rules():
    assert parse_policy(encode(policy())) == GatePolicy()
    assert (
        parse_policy(encode(policy(max_candidate_failures=None, min_candidate_pass_rate=None)))
        == GatePolicy()
    )


def test_exact_normalized_policy(fixture_dir):
    value = json.loads((fixture_dir / "policy-allow-v1.json").read_bytes())
    first = parse_policy(encode(value))
    assert first.min_candidate_pass_rate == Fraction(3, 4)
    value["min_candidate_pass_rate"] = {"numerator": 6, "denominator": 8}
    assert policy_sha256(first) == policy_sha256(parse_policy(encode(value)))


@pytest.mark.parametrize("field", list(policy()))
def test_missing_required(field):
    value = policy()
    del value[field]
    with pytest.raises(ContractError):
        parse_policy(encode(value))


@pytest.mark.parametrize(
    "changes",
    [
        {"extra": 1},
        {"schema_version": True},
        {"schema_version": 2},
        {"policy_id": "Bad Label"},
        {"policy_version": "v1"},
        {"max_regressions": -1},
        {"max_regressions": True},
        {"max_regressions": 1.0},
        {"max_candidate_failures": -1},
        {"max_candidate_failures": False},
    ],
)
def test_invalid_fields(changes):
    with pytest.raises(ContractError):
        parse_policy(encode(policy(**changes)))


@pytest.mark.parametrize(
    "rate",
    [
        True,
        0.75,
        "3/4",
        [],
        {},
        {"numerator": 1},
        {"numerator": 1, "denominator": 2, "extra": 3},
        {"numerator": True, "denominator": 2},
        {"numerator": 1, "denominator": False},
        {"numerator": 1.0, "denominator": 2},
        {"numerator": 1, "denominator": 2.0},
        {"numerator": 1, "denominator": 0},
        {"numerator": 1, "denominator": -2},
        {"numerator": -1, "denominator": 2},
        {"numerator": 3, "denominator": 2},
    ],
)
def test_invalid_rate(rate):
    with pytest.raises(ContractError):
        parse_policy(encode(policy(min_candidate_pass_rate=rate)))


@pytest.mark.parametrize("raw", [b"", b"[]", b"null", b"\xff", b'{"a":1,"a":2}', b'{"a":NaN}'])
def test_invalid_json(raw):
    with pytest.raises(ContractError):
        parse_policy(raw)
