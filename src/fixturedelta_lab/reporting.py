"""Versioned report projection/rendering and exclusive publication of a report pair."""

import json
import re
import string
from dataclasses import asdict, dataclass
from pathlib import Path

from fixturedelta_lab.comparison_types import ComparisonResult, TransitionCounts
from fixturedelta_lab.gate_types import GatePolicy, GateResult
from fixturedelta_lab.gates import evaluate_gate
from fixturedelta_lab.provenance import _canonical_sha256, _gate_value

REPORT_CONTRACT_VERSION = "1.0.0"
REPORT_FINGERPRINT_VERSION = "trustbench-report-v1"


class ReportError(ValueError):
    """Metadata unsuitable for a public report; diagnostics never echo that metadata."""


@dataclass(frozen=True, slots=True)
class ReportBundle:
    json_bytes: bytes
    markdown_bytes: bytes
    report_sha256: str
    gate: GateResult


def _safe_metadata(value: object) -> None:
    """Reject recognizable paths/credentials; never claim general secret detection."""
    if isinstance(value, dict):
        for item in value.values():
            _safe_metadata(item)
    elif isinstance(value, list):
        for item in value:
            _safe_metadata(item)
    elif isinstance(value, str):
        if re.search(
            r"[A-Za-z]:[\\/]|\\\\|(?:^|\s)/(?:[^\s/]+/)*[^\s]+|"
            r"-----BEGIN .*PRIVATE KEY|\b(?:sk-|gh[pousr]_|github_pat_)[A-Za-z0-9_-]{12,}|"
            r"\bAKIA[A-Z0-9]{16}\b|(?:api[_-]?key|password|secret|token)\s*[:=]",
            value,
            re.IGNORECASE,
        ) or any(0xD800 <= ord(char) <= 0xDFFF for char in value):
            raise ReportError("UNSAFE_REPORT_METADATA")


def escape_markdown(value: object) -> str:
    """Escape punctuation, controls and newlines as entities, preserving Unicode text."""
    return "".join(
        f"&#{ord(char)};"
        if char in string.punctuation or ord(char) < 32 or ord(char) == 127
        else char
        for char in str(value)
    )


def _counts(value: TransitionCounts) -> dict[str, int]:
    return {**asdict(value), "total": value.total}


def render_reports(comparison: ComparisonResult, policy: GatePolicy) -> ReportBundle:
    """Validate and evaluate the gate once, then render safe status-only comparison evidence."""
    gate = evaluate_gate(comparison, policy)
    p = comparison.provenance
    policy_values = asdict(policy)
    policy_values["min_candidate_pass_rate"] = _gate_value(policy.min_candidate_pass_rate)
    cases = [
        {
            "case_id": case.case_id,
            "baseline_passed": case.baseline_passed,
            "candidate_passed": case.candidate_passed,
            "transition": case.transition,
            "summary": case.summary,
            "checks": [
                {
                    "evaluator_id": check.evaluator_id,
                    "evaluator_version": check.evaluator_version,
                    "baseline_passed": check.baseline_passed,
                    "candidate_passed": check.candidate_passed,
                    "transition": check.transition,
                }
                for check in case.checks
            ],
        }
        for case in comparison.cases
    ]
    payload = {
        "report_contract_version": REPORT_CONTRACT_VERSION,
        "report_fingerprint_version": REPORT_FINGERPRINT_VERSION,
        "provenance": {
            "comparison": asdict(p),
            "comparison_sha256": comparison.comparison_sha256,
            "gate": asdict(gate.provenance),
            "gate_sha256": gate.result_sha256,
        },
        "counts": {
            "cases": _counts(comparison.case_counts),
            "checks": _counts(comparison.check_counts),
            "cases_with_regressions": comparison.cases_with_regressions,
            "cases_with_improvements": comparison.cases_with_improvements,
            "mixed_cases": comparison.mixed_case_count,
        },
        "cases": cases,
        "policy": policy_values,
        "gate": {
            "passed": gate.passed,
            "total_checks": gate.total_checks,
            "candidate_passes": gate.candidate_passes,
            "rules": [
                {
                    "rule_id": rule.rule_id,
                    "observed": _gate_value(rule.observed),
                    "permitted": _gate_value(rule.permitted),
                    "passed": rule.passed,
                    "explanation": rule.explanation,
                }
                for rule in gate.rules
            ],
            "regressions": [asdict(item) for item in gate.regressions],
            "candidate_failures": [asdict(item) for item in gate.candidate_failures],
        },
    }
    _safe_metadata(payload)
    digest = _canonical_sha256(payload)
    payload["report_sha256"] = digest
    json_bytes = (
        json.dumps(payload, sort_keys=True, ensure_ascii=False, indent=2, allow_nan=False) + "\n"
    ).encode("utf-8")
    e = escape_markdown
    lines = [
        "# FixtureDelta Lab synthetic evaluation",
        "",
        f"Gate: **{'PASS' if gate.passed else 'FAIL'}**",
        "",
        f"Dataset: {e(p.dataset_id)} / {e(p.dataset_version)}",
        f"Baseline: {e(p.baseline.output_set_id)} / {e(p.baseline.output_set_version)} "
        f"(application {e(p.baseline.candidate_version)})",
        f"Candidate: {e(p.candidate.output_set_id)} / {e(p.candidate.output_set_version)} "
        f"(application {e(p.candidate.candidate_version)})",
        "",
        "| Unit | Regressions | Improvements | Unchanged pass | Unchanged fail | Total |",
        "| --- | --- | --- | --- | --- | --- |",
    ]
    for label, count in (("Cases", comparison.case_counts), ("Checks", comparison.check_counts)):
        lines.append(
            f"| {label} | {count.regressions} | {count.improvements} | "
            f"{count.unchanged_passes} | {count.unchanged_failures} | {count.total} |"
        )
    lines += [
        "",
        f"Mixed cases: {comparison.mixed_case_count}. Improvements never offset regressions.",
        "",
        "## Case and evaluator transitions",
        "",
        "| Case | Case summary | Evaluator / version | Baseline | Candidate | Transition |",
        "| --- | --- | --- | --- | --- | --- |",
    ]
    for case in comparison.cases:
        for check in case.checks:
            lines.append(
                f"| {e(case.case_id)} | {e(case.summary)} | {e(check.evaluator_id)} / "
                f"{e(check.evaluator_version)} | {'pass' if check.baseline_passed else 'fail'} | "
                f"{'pass' if check.candidate_passed else 'fail'} | {e(check.transition)} |"
            )
    lines += [
        "",
        "## Policy rules",
        "",
        f"Policy: {e(policy.policy_id)} / {e(policy.policy_version)}",
        "",
        "| Rule | Observation | Permitted | Outcome | Explanation |",
        "| --- | --- | --- | --- | --- |",
    ]
    for rule in gate.rules:
        lines.append(
            f"| {e(rule.rule_id)} | {e(rule.observed)} | {e(rule.permitted)} | "
            f"{'PASS' if rule.passed else 'FAIL'} | {e(rule.explanation)} |"
        )
    lines += [
        "",
        f"Candidate passes: {gate.candidate_passes}/{gate.total_checks} evaluator checks.",
        "",
        "## Reproducibility",
        "",
        f"Report contract: {REPORT_CONTRACT_VERSION}; evaluation contract: "
        f"{e(p.evaluation_contract_version)}; comparison contract: "
        f"{e(p.comparison_contract_version)}; gate contract: "
        f"{e(gate.provenance.gate_contract_version)}.",
        f"Evaluator suite: {e(p.evaluator_suite_version)}; "
        f"recorded integer limit: {p.python_integer_limit}.",
        "",
    ]
    for label, value in (
        ("Dataset", p.dataset_sha256),
        ("Baseline outputs", p.baseline.outputs_sha256),
        ("Candidate outputs", p.candidate.outputs_sha256),
        ("Baseline run", p.baseline.run_sha256),
        ("Candidate run", p.candidate.run_sha256),
        ("Comparison", comparison.comparison_sha256),
        ("Policy", gate.provenance.policy_sha256),
        ("Gate", gate.result_sha256),
        ("Report", digest),
    ):
        lines.append(f"- {label} SHA-256: {e(value)}")
    lines += [
        "",
        "Synthetic literal/structure conformance only; no truth, safety, or model-quality score.",
        "Raw responses, prompts, and evaluator text previews are omitted.",
        "",
    ]
    return ReportBundle(json_bytes, "\n".join(lines).encode("utf-8"), digest, gate)


def write_reports(directory: Path, bundle: ReportBundle) -> None:
    """Reserve a new directory and publish both files together under reports/.

    A private .pending directory is renamed only after both files close successfully.
    Cleanup only touches our known files/directories, never recursively deletes inputs.
    """
    directory.parent.mkdir(parents=True, exist_ok=True)
    directory.mkdir()  # Exclusive reservation; never reuse even an empty directory.
    pending = directory / ".pending"
    try:
        pending.mkdir()
        for name, data in (
            ("report.json", bundle.json_bytes),
            ("report.md", bundle.markdown_bytes),
        ):
            with (pending / name).open("xb") as file:
                file.write(data)
        pending.rename(directory / "reports")
    except OSError:
        for path in (pending / "report.md", pending / "report.json", pending, directory):
            try:
                path.rmdir() if path in (pending, directory) else path.unlink(missing_ok=True)
            except OSError:
                pass  # Failed cleanup still propagates the original failure, never success.
        raise
