"""Strict schema-v1 policy parsing; no file access or policy evaluation."""

from fractions import Fraction

from fixturedelta_lab.datasets import _decode, _keys, _object, _schema_version
from fixturedelta_lab.domain import ContractError
from fixturedelta_lab.gate_types import GatePolicy


def parse_policy(raw: bytes) -> GatePolicy:
    data = _decode(raw)
    required = {"schema_version", "policy_id", "policy_version", "max_regressions"}
    optional = {"max_candidate_failures", "min_candidate_pass_rate"}
    if not required <= data.keys() or data.keys() - required - optional:
        raise ContractError("policy: missing required or unsupported fields")
    _schema_version(data["schema_version"])
    rate = data.get("min_candidate_pass_rate")
    if rate is not None:
        ratio = _object(rate, "min_candidate_pass_rate")
        _keys(ratio, {"numerator", "denominator"}, "min_candidate_pass_rate")
        n, d = ratio["numerator"], ratio["denominator"]
        if type(n) is not int or type(d) is not int or d <= 0:
            raise ContractError("pass rate: expected integer numerator and positive denominator")
        rate = Fraction(n, d)
    return GatePolicy(
        policy_id=data["policy_id"],
        policy_version=data["policy_version"],
        max_regressions=data["max_regressions"],
        max_candidate_failures=data.get("max_candidate_failures"),
        min_candidate_pass_rate=rate,
    )
