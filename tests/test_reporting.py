"""Report content, independent hash oracle, escaping and publication failure boundaries."""

import hashlib
import json
from dataclasses import replace
from fractions import Fraction
from pathlib import Path

import pytest

from fixturedelta_lab.comparison import compare_runs
from fixturedelta_lab.gate_types import GatePolicy
from fixturedelta_lab.provenance import comparison_sha256
from fixturedelta_lab.reporting import ReportError, escape_markdown, render_reports, write_reports
from fixturedelta_lab.runner import evaluate_run


@pytest.fixture
def evidence(fixture_dir):
    dataset = (fixture_dir / "golden-v1.0.0.json").read_bytes()
    runs = [
        evaluate_run(
            dataset,
            (fixture_dir / file).read_bytes(),
            output_set_id=label,
            output_set_version="1.0.0",
        )
        for file, label in [("baseline-v1.json", "baseline"), ("candidate-v2.json", "candidate")]
    ]
    return compare_runs(*runs)


def rehash(evidence):
    return replace(
        evidence, comparison_sha256=comparison_sha256(evidence.provenance, evidence.cases)
    )


def test_report_contract_and_independent_digest(evidence):
    bundle = render_reports(evidence, GatePolicy())
    assert bundle.markdown_bytes.startswith(b"# FixtureDelta Lab synthetic evaluation\n")
    value = json.loads(bundle.json_bytes)
    assert value["report_contract_version"] == "1.0.0"
    assert value["report_fingerprint_version"] == "trustbench-report-v1"
    assert value["counts"]["checks"] == {
        "regressions": 2,
        "improvements": 1,
        "unchanged_passes": 5,
        "unchanged_failures": 0,
        "total": 8,
    }
    assert value["counts"]["cases"]["total"] == 6
    assert value["gate"]["passed"] is False
    assert value["gate"]["candidate_passes"] == 6
    assert [c["case_id"] for c in value["cases"]] == [c.case_id for c in evidence.cases]
    assert {c["evaluator_id"] for case in value["cases"] for c in case["checks"]} == {
        "exact-match",
        "required-content",
        "forbidden-content",
        "json-object",
    }
    digest = value.pop("report_sha256")
    canonical = json.dumps(
        value, ensure_ascii=True, sort_keys=True, separators=(",", ":"), allow_nan=False
    ).encode()
    assert hashlib.sha256(canonical).hexdigest() == digest == bundle.report_sha256
    assert digest.encode() in bundle.markdown_bytes
    assert bundle.json_bytes.endswith(b"\n") and bundle.markdown_bytes.endswith(b"\n")
    assert b"\r" not in bundle.json_bytes + bundle.markdown_bytes
    assert (
        b"Raw responses, prompts, and evaluator text previews are omitted." in bundle.markdown_bytes
    )
    assert b"READY" not in bundle.json_bytes + bundle.markdown_bytes
    assert b"baseline_explanation" not in bundle.json_bytes


def test_repeatability_and_policy_sensitivity(evidence):
    strict = render_reports(evidence, GatePolicy())
    assert strict == render_reports(evidence, GatePolicy())
    permitted = render_reports(
        evidence,
        GatePolicy(
            max_regressions=2, max_candidate_failures=2, min_candidate_pass_rate=Fraction(3, 4)
        ),
    )
    value = json.loads(permitted.json_bytes)
    assert value["gate"]["passed"] is True
    assert len(value["gate"]["rules"]) == 3
    assert value["policy"]["min_candidate_pass_rate"] == {"numerator": 3, "denominator": 4}
    assert strict.report_sha256 != permitted.report_sha256


def test_mixed_case_preserved(evidence):
    first = evidence.cases[0]
    regression = first.checks[0]
    improvement = replace(
        regression, evaluator_id="second-check", baseline_passed=False, candidate_passed=True
    )
    mixed = rehash(replace(evidence, cases=(replace(first, checks=(regression, improvement)),)))
    value = json.loads(render_reports(mixed, GatePolicy()).json_bytes)
    assert value["counts"]["mixed_cases"] == 1
    assert value["cases"][0]["summary"] == "mixed"
    assert value["gate"]["passed"] is False
    assert value["counts"]["checks"]["regressions"] == 1
    assert value["counts"]["checks"]["improvements"] == 1


def test_unicode_and_markdown_injection(evidence):
    label = 'Έτοιμο | <img> [link](x) & "quote"\n# heading\t'
    p = evidence.provenance
    changed = rehash(
        replace(
            evidence, provenance=replace(p, candidate=replace(p.candidate, candidate_version=label))
        )
    )
    bundle = render_reports(changed, GatePolicy())
    assert (
        label
        == json.loads(bundle.json_bytes)["provenance"]["comparison"]["candidate"][
            "candidate_version"
        ]
    )
    markdown = bundle.markdown_bytes.decode()
    assert "Έτοιμο" in markdown and "Έτοιμο".encode() in bundle.json_bytes
    assert "<img>" not in markdown and "\n# heading" not in markdown
    assert "&#124;" in markdown and "&#10;" in markdown and "&#38;" in markdown
    assert escape_markdown("a\x7fb\x00") == "a&#127;b&#0;"


@pytest.mark.parametrize(
    "label",
    [
        r"C:\private\data",
        "/home/private/data",
        r"\\server\share",
        "token=hidden",
        "sk-abcdefghijklmnopqrst",
        "-----BEGIN PRIVATE KEY-----",
        "bad\ud800",
    ],
)
def test_sensitive_metadata_rejected(evidence, label):
    p = evidence.provenance
    changed = rehash(
        replace(
            evidence, provenance=replace(p, candidate=replace(p.candidate, candidate_version=label))
        )
    )
    with pytest.raises(ReportError, match="UNSAFE_REPORT_METADATA"):
        render_reports(changed, GatePolicy())


def test_preview_text_never_exported(evidence):
    first = evidence.cases[0]
    secret = "token=do-not-export C:\\private\\file"
    changed = rehash(
        replace(
            evidence,
            cases=(
                replace(
                    first,
                    checks=(
                        replace(
                            first.checks[0],
                            baseline_explanation=secret,
                            candidate_explanation=secret,
                        ),
                    ),
                ),
                *evidence.cases[1:],
            ),
        )
    )
    bundle = render_reports(changed, GatePolicy())
    assert b"do-not-export" not in bundle.json_bytes + bundle.markdown_bytes
    assert bundle.report_sha256 != render_reports(evidence, GatePolicy()).report_sha256


def test_publish_new_directory_and_reject_overwrite(evidence, tmp_path):
    bundle = render_reports(evidence, GatePolicy())
    output = tmp_path / "parent" / "new"
    write_reports(output, bundle)
    assert sorted(p.name for p in output.iterdir()) == ["reports"]
    assert (output / "reports/report.json").read_bytes() == bundle.json_bytes
    assert (output / "reports/report.md").read_bytes() == bundle.markdown_bytes
    with pytest.raises(FileExistsError):
        write_reports(output, bundle)
    assert (output / "reports/report.json").read_bytes() == bundle.json_bytes


@pytest.mark.parametrize("kind", ["file", "directory", "parent-file"])
def test_existing_targets_preserved(evidence, tmp_path, kind):
    output = tmp_path / "occupied"
    if kind == "directory":
        output.mkdir()
    else:
        output.write_bytes(b"preserve")
    target = output / "child" if kind == "parent-file" else output
    with pytest.raises(OSError):
        write_reports(target, render_reports(evidence, GatePolicy()))
    assert output.is_dir() if kind == "directory" else output.read_bytes() == b"preserve"


@pytest.mark.parametrize("failure", ["pending", "second-file", "rename", "cleanup"])
def test_write_failure_does_not_publish(evidence, tmp_path, monkeypatch, failure):
    output = tmp_path / "new"
    mkdir, open_file, rename, unlink = Path.mkdir, Path.open, Path.rename, Path.unlink

    def checked_mkdir(path, *args, **kwargs):
        if failure == "pending" and path.name == ".pending":
            raise PermissionError("private directory")
        return mkdir(path, *args, **kwargs)

    def checked_open(path, *args, **kwargs):
        if failure in ("second-file", "cleanup") and path.name == "report.md":
            raise OSError("private disk error")
        return open_file(path, *args, **kwargs)

    def checked_rename(path, *args, **kwargs):
        if failure == "rename":
            raise OSError("private rename error")
        return rename(path, *args, **kwargs)

    def checked_unlink(path, *args, **kwargs):
        if failure == "cleanup":
            raise PermissionError("private cleanup error")
        return unlink(path, *args, **kwargs)

    monkeypatch.setattr(Path, "mkdir", checked_mkdir)
    monkeypatch.setattr(Path, "open", checked_open)
    monkeypatch.setattr(Path, "rename", checked_rename)
    monkeypatch.setattr(Path, "unlink", checked_unlink)
    with pytest.raises(OSError):
        write_reports(output, render_reports(evidence, GatePolicy()))
    assert not (output / "reports").exists()
    assert not output.exists() if failure != "cleanup" else (output / ".pending").is_dir()
