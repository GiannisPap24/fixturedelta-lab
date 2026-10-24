"""Verify real CLI processes and their reports; no alternate evaluation implementation."""

import argparse
import hashlib
import json
import os
import subprocess
import sys
import tomllib
from pathlib import Path


class DemoError(ValueError):
    pass


class Parser(argparse.ArgumentParser):
    def error(self, message: str) -> None:
        raise DemoError("arguments")


def require(condition: bool, invariant: str) -> None:
    if not condition:
        raise DemoError(invariant)


def sha(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def canonical(value: object) -> str:
    return sha(
        json.dumps(
            value, sort_keys=True, ensure_ascii=True, separators=(",", ":"), allow_nan=False
        ).encode("ascii")
    )


def verify_report(directory: Path, inputs: dict[str, bytes], passing: bool) -> dict:
    require(sorted(p.name for p in directory.iterdir()) == ["reports"], "publication")
    report_dir = directory / "reports"
    require(sorted(p.name for p in report_dir.iterdir()) == ["report.json", "report.md"], "pair")
    raw = (report_dir / "report.json").read_bytes()
    markdown = (report_dir / "report.md").read_text(encoding="utf-8")
    value = json.loads(raw)
    digest = value.pop("report_sha256")
    require(canonical(value) == digest, "report fingerprint")
    value["report_sha256"] = digest
    require(
        raw
        == (
            json.dumps(value, sort_keys=True, ensure_ascii=False, indent=2, allow_nan=False) + "\n"
        ).encode("utf-8"),
        "JSON encoding",
    )
    require(
        value["report_contract_version"] == "1.0.0"
        and value["report_fingerprint_version"] == "trustbench-report-v1",
        "report versions",
    )
    p = value["provenance"]["comparison"]
    require(
        (p["dataset_id"], p["dataset_version"], p["dataset_sha256"])
        == ("synthetic-foundation", "1.0.0", sha(inputs["golden-v1.0.0.json"])),
        "dataset",
    )
    require(
        (
            p["evaluation_contract_version"],
            p["comparison_contract_version"],
            p["evaluator_suite_version"],
        )
        == ("1.1.0", "1.0.0", "1.0.0"),
        "contracts",
    )
    hashes = [digest, p["dataset_sha256"], value["provenance"]["comparison_sha256"]]
    for role, name in (
        ("baseline", "baseline-v1.json"),
        ("candidate", "baseline-v1.json" if passing else "candidate-v2.json"),
    ):
        ref = p[role]
        require(
            (
                ref["output_set_id"],
                ref["output_set_version"],
                ref["outputs_sha256"],
                ref["candidate_version"],
            )
            == (role, "1.0.0", sha(inputs[name]), json.loads(inputs[name])["candidate_version"]),
            "run reference",
        )
        hashes += [ref["outputs_sha256"], ref["run_sha256"]]
    expected = (0, 0, 7, 1) if passing else (2, 1, 5, 0)
    counts = value["counts"]["checks"]
    require(
        tuple(
            counts[k]
            for k in ("regressions", "improvements", "unchanged_passes", "unchanged_failures")
        )
        == expected,
        "check counts",
    )
    require(counts["total"] == 8 and value["counts"]["cases"]["total"] == 6, "coverage")
    case_counts = value["counts"]["cases"]
    require(
        tuple(
            case_counts[k]
            for k in ("regressions", "improvements", "unchanged_passes", "unchanged_failures")
        )
        == ((0, 0, 5, 1) if passing else (2, 1, 3, 0)),
        "case counts",
    )
    expected_ids = [c["case_id"] for c in json.loads(inputs["golden-v1.0.0.json"])["cases"]]
    require([c["case_id"] for c in value["cases"]] == expected_ids, "case order")
    families = [
        ("exact-match",),
        ("exact-match",),
        ("required-content", "forbidden-content"),
        ("required-content", "forbidden-content"),
        ("json-object",),
        ("json-object",),
    ]
    for case, ids in zip(value["cases"], families, strict=True):
        require(tuple(c["evaluator_id"] for c in case["checks"]) == ids, "evaluator order")
        require(all(c["evaluator_version"] == "1.0.0" for c in case["checks"]), "evaluators")
    require(
        value["cases"][1]["candidate_passed"] is True
        and value["cases"][5]["candidate_passed"] is True,
        "Greek outcomes",
    )
    require(
        value["policy"]
        == {
            "policy_id": "strict-regression",
            "policy_version": "1.0.0",
            "max_regressions": 0,
            "max_candidate_failures": None,
            "min_candidate_pass_rate": None,
        },
        "strict policy",
    )
    gate = value["gate"]
    gp = value["provenance"]["gate"]
    require(
        gate["passed"] is passing and gate["candidate_passes"] == (7 if passing else 6),
        "gate decision",
    )
    require(gate["total_checks"] == 8 and len(gate["rules"]) == 1, "gate coverage")
    rule = gate["rules"][0]
    require(
        (rule["rule_id"], rule["observed"], rule["permitted"], rule["passed"])
        == ("max-regressions", expected[0], 0, passing),
        "independent regression rule",
    )
    affected = [(x["case_id"], x["evaluator_id"]) for x in gate["regressions"]]
    require(
        affected
        == ([] if passing else [("en-label-001", "exact-match"), ("en-json-001", "json-object")]),
        "regressions",
    )
    require(
        gp["comparison_sha256"] == value["provenance"]["comparison_sha256"]
        and gp["gate_contract_version"] == "1.0.0",
        "gate provenance",
    )
    require(
        gp["policy_sha256"]
        == canonical(
            {"fingerprint_version": "trustbench-gate-policy-v1", "policy": value["policy"]}
        ),
        "policy fingerprint",
    )
    require(
        value["provenance"]["gate_sha256"]
        == canonical({"fingerprint_version": "trustbench-gate-v1", "provenance": gp, **gate}),
        "gate fingerprint",
    )
    hashes += [gp["policy_sha256"], value["provenance"]["gate_sha256"]]
    require(
        all(len(h) == 64 and set(h) <= set("0123456789abcdef") and h in markdown for h in hashes),
        "Markdown provenance",
    )
    require(
        f"Gate: **{'PASS' if passing else 'FAIL'}**" in markdown
        and f"| Checks | {' | '.join(map(str, expected))} | 8 |" in markdown,
        "Markdown decision",
    )
    require("el&#45;label&#45;001" in markdown, "Markdown escaping")
    return value


def run_demo(target: str) -> dict:
    root = Path(__file__).resolve().parents[1]
    require(Path.cwd().resolve() == root, "project root")
    project = tomllib.loads((root / "pyproject.toml").read_text(encoding="utf-8"))
    require(
        project["project"]["name"] == "fixturedelta-lab" and (root / "uv.lock").is_file(),
        "project identity",
    )
    require(
        Path(sys.prefix).resolve() in (root / ".venv", root / ".venv-package"),
        "existing project environment",
    )
    artifacts = root / "artifacts"
    require(artifacts.resolve() == artifacts, "local artifacts directory")
    output = (root / target).resolve()
    require(
        output.is_relative_to(artifacts) and output != artifacts and not output.exists(),
        "new output directory under artifacts",
    )
    fixtures = root / "tests/fixtures"
    inputs = {
        name: (fixtures / name).read_bytes()
        for name in ("golden-v1.0.0.json", "baseline-v1.json", "candidate-v2.json")
    }
    console = Path(sys.executable).parent / (
        "fixturedelta.exe" if os.name == "nt" else "fixturedelta"
    )
    require(console.is_file(), "installed console")
    env = {k: v for k, v in os.environ.items() if not k.upper().startswith("PYTHON")}
    output.parent.mkdir(parents=True, exist_ok=True)
    output.mkdir()  # Exclusive: never reuse or recursively clean a caller directory.

    def invoke(command: list[str], candidate: Path, destination: Path, code: int) -> str:
        result = subprocess.run(
            [
                *command,
                "check",
                "--dataset",
                str(fixtures / "golden-v1.0.0.json"),
                "--baseline",
                str(fixtures / "baseline-v1.json"),
                "--candidate",
                str(candidate),
                "--report-dir",
                str(destination),
            ],
            cwd=output,
            env=env,
            capture_output=True,
            text=True,
            encoding="utf-8",
            timeout=30,
        )
        require(result.returncode == code, "CLI exit")
        require("Traceback" not in result.stderr and str(root) not in result.stderr, "diagnostics")
        if code in (0, 1):
            require(not result.stderr and "Reports published:" in result.stdout, "CLI completion")
        else:
            require(not result.stdout and result.stderr.startswith("ERROR "), "CLI failure")
        return result.stdout

    commands = {
        "console": [str(console)],
        "module": [sys.executable, "-I", "-m", "fixturedelta_lab"],
    }
    reports = {}
    for scenario, passing in (("fail", False), ("pass", True)):
        candidate = fixtures / ("baseline-v1.json" if passing else "candidate-v2.json")
        for entry, command in commands.items():
            destination = output / f"{scenario}-{entry}"
            stdout = invoke(command, candidate, destination, 0 if passing else 1)
            report = verify_report(destination, inputs, passing)
            require(report["report_sha256"] in stdout, "terminal fingerprint")
            reports[f"{scenario}-{entry}"] = report
        for name in ("report.json", "report.md"):
            left = (output / f"{scenario}-console/reports" / name).read_bytes()
            right = (output / f"{scenario}-module/reports" / name).read_bytes()
            require(left == right and b"\r" not in left, "byte determinism")
            require(
                str(root).encode() not in left
                and b"C:\\\\" not in left
                and b"READY!" not in left
                and b"baseline_explanation" not in left,
                "report privacy",
            )

    variants = output / "inputs"
    variants.mkdir()
    (variants / "malformed.json").write_bytes(b"{invalid synthetic JSON}")
    mismatch = json.loads(inputs["candidate-v2.json"])
    mismatch["dataset_version"] = "99.0.0"
    (variants / "incompatible.json").write_bytes(json.dumps(mismatch, ensure_ascii=False).encode())
    for name in ("malformed", "incompatible"):
        destination = output / name
        invoke(commands["console"], variants / f"{name}.json", destination, 2)
        require(not destination.exists(), "invalid input publishes nothing")
    occupied = output / "fail-console"
    before = {p.name: p.read_bytes() for p in (occupied / "reports").iterdir()}
    invoke(commands["console"], fixtures / "candidate-v2.json", occupied, 3)
    require(
        before == {p.name: p.read_bytes() for p in (occupied / "reports").iterdir()},
        "existing report protection",
    )
    require(
        all((fixtures / name).read_bytes() == raw for name, raw in inputs.items()), "input bytes"
    )
    require(
        all(p.resolve().is_relative_to(output) for p in output.rglob("*")), "output containment"
    )
    summary = {
        "demo_contract_version": "1.0.0",
        "verified": True,
        "input_sha256": {name: sha(raw) for name, raw in inputs.items()},
        "exit_codes": {"fail": 1, "pass": 0, "malformed": 2, "incompatible": 2, "occupied": 3},
        "report_sha256": {name: value["report_sha256"] for name, value in reports.items()},
    }
    pending = output / ".verification.pending"
    with pending.open("xb") as file:
        file.write((json.dumps(summary, sort_keys=True, indent=2) + "\n").encode())
    pending.rename(output / "verification.json")
    return summary


def main() -> int:
    try:
        parser = Parser(description="Verify the synthetic CLI demo from the project root.")
        parser.add_argument("--report-dir", default="artifacts/demo")
        summary = run_demo(parser.parse_args().report_dir)
        print("DEMO PASS: all end-to-end invariants verified")
        print("DEMO fail: exit 1 expected; 2 regressions, 1 improvement, strict gate FAIL")
        print(
            "DEMO pass: exit 0; 0 regressions, 0 improvements, strict gate PASS; "
            "1 unchanged failure"
        )
        print("DEMO errors: malformed/incompatible exit 2; occupied output exit 3; no new reports")
        print("DEMO determinism: console/module JSON and Markdown bytes match; inputs unchanged")
        for scenario in ("fail", "pass"):
            print(f"DEMO {scenario} SHA-256: {summary['report_sha256'][scenario + '-console']}")
        print("DEMO reports: fail-console/reports and pass-console/reports; verification.json")
        return 0
    except DemoError as error:
        print(f"DEMO FAIL: invariant '{error}' failed; inspect the demo guide.", file=sys.stderr)
        return 1
    except Exception:
        print(
            "DEMO FAIL: Check the existing environment, file access and fresh output destination.",
            file=sys.stderr,
        )
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
