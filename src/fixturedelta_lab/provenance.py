"""Versioned internal fingerprint encoding; no report export or file access."""

import hashlib
import json
from dataclasses import asdict
from fractions import Fraction

from fixturedelta_lab.comparison_types import CaseComparison, ComparisonProvenance
from fixturedelta_lab.domain import CaseResult, RunProvenance
from fixturedelta_lab.gate_types import CheckIdentity, GatePolicy, GateProvenance, GateRuleResult

EVALUATION_CONTRACT_VERSION = "1.1.0"
EVALUATOR_SUITE_VERSION = "1.0.0"
FINGERPRINT_VERSION = "trustbench-run-v1"
COMPARISON_CONTRACT_VERSION = "1.0.0"
COMPARISON_FINGERPRINT_VERSION = "trustbench-comparison-v1"
GATE_CONTRACT_VERSION = "1.0.0"
POLICY_FINGERPRINT_VERSION = "trustbench-gate-policy-v1"
GATE_FINGERPRINT_VERSION = "trustbench-gate-v1"


def content_sha256(raw: bytes) -> str:
    """Hash the exact input bytes, including whitespace and line endings."""
    return hashlib.sha256(raw).hexdigest()


def result_sha256(provenance: RunProvenance, results: tuple[CaseResult, ...]) -> str:
    """Hash canonical ASCII JSON, preserving case/check order and every explanation."""
    payload = {
        "fingerprint_version": FINGERPRINT_VERSION,
        "provenance": asdict(provenance),
        "results": [asdict(result) for result in results],
    }
    canonical = json.dumps(
        payload, sort_keys=True, ensure_ascii=True, separators=(",", ":"), allow_nan=False
    ).encode("ascii")
    return content_sha256(canonical)


def comparison_sha256(provenance: ComparisonProvenance, cases: tuple[CaseComparison, ...]) -> str:
    """Bind ordered check evidence and role-specific run references; exclude derived counts."""
    payload = {
        "fingerprint_version": COMPARISON_FINGERPRINT_VERSION,
        "provenance": asdict(provenance),
        "cases": [asdict(case) for case in cases],
    }
    canonical = json.dumps(
        payload, sort_keys=True, ensure_ascii=True, separators=(",", ":"), allow_nan=False
    ).encode("ascii")
    return content_sha256(canonical)


def _gate_value(value: int | Fraction | None) -> object:
    if isinstance(value, Fraction):
        return {"numerator": value.numerator, "denominator": value.denominator}
    return value


def _canonical_sha256(payload: object) -> str:
    return content_sha256(
        json.dumps(
            payload, sort_keys=True, ensure_ascii=True, separators=(",", ":"), allow_nan=False
        ).encode("ascii")
    )


def policy_sha256(policy: GatePolicy) -> str:
    values = asdict(policy)
    values["min_candidate_pass_rate"] = _gate_value(policy.min_candidate_pass_rate)
    return _canonical_sha256({"fingerprint_version": POLICY_FINGERPRINT_VERSION, "policy": values})


def gate_sha256(
    provenance: GateProvenance,
    rules: tuple[GateRuleResult, ...],
    regressions: tuple[CheckIdentity, ...],
    candidate_failures: tuple[CheckIdentity, ...],
    total_checks: int,
    candidate_passes: int,
) -> str:
    return _canonical_sha256(
        {
            "fingerprint_version": GATE_FINGERPRINT_VERSION,
            "provenance": asdict(provenance),
            "rules": [
                {
                    "rule_id": rule.rule_id,
                    "observed": _gate_value(rule.observed),
                    "permitted": _gate_value(rule.permitted),
                    "passed": rule.passed,
                    "explanation": rule.explanation,
                }
                for rule in rules
            ],
            "regressions": [asdict(item) for item in regressions],
            "candidate_failures": [asdict(item) for item in candidate_failures],
            "total_checks": total_checks,
            "candidate_passes": candidate_passes,
            "passed": all(rule.passed for rule in rules),
        }
    )
