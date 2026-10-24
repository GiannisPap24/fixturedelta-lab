"""Offline CLI integration, subprocess exit codes and sanitized failure diagnostics."""

import json
import os
import runpy
import socket
import subprocess
import sys
from dataclasses import replace
from pathlib import Path

import pytest

from fixturedelta_lab import cli
from fixturedelta_lab.provenance import result_sha256
from fixturedelta_lab.runner import RunError, RunErrorCode


def arguments(fixture_dir, output):
    return [
        "check",
        "--dataset",
        str(fixture_dir / "golden-v1.0.0.json"),
        "--baseline",
        str(fixture_dir / "baseline-v1.json"),
        "--candidate",
        str(fixture_dir / "candidate-v2.json"),
        "--report-dir",
        str(output),
    ]


def set_arg(args, name, value):
    args[args.index(name) + 1] = str(value)


def test_default_fixture_and_unchanged_inputs(fixture_dir, tmp_path, capsys):
    snapshots = {p: p.read_bytes() for p in fixture_dir.glob("*.json")}
    output = tmp_path / "output"
    assert cli.main(arguments(fixture_dir, output)) == 1
    stdout, stderr = capsys.readouterr()
    assert (
        "Gate FAIL | cases=6 checks=8 regressions=2 improvements=1 candidate_failures=2" in stdout
    )
    assert stderr == "" and str(tmp_path) not in stdout
    assert all(p.read_bytes() == before for p, before in snapshots.items())
    assert (output / "reports/report.md").is_file()


def test_explicit_policy_pass(fixture_dir, tmp_path, capsys):
    args = arguments(fixture_dir, tmp_path / "output")
    args += ["--policy", str(fixture_dir / "policy-allow-v1.json")]
    assert cli.main(args) == 0
    assert "Gate PASS" in capsys.readouterr().out


def test_identical_runs_default_pass_with_unchanged_failure(fixture_dir, tmp_path):
    output = tmp_path / "output"
    args = arguments(fixture_dir, output)
    set_arg(args, "--candidate", fixture_dir / "baseline-v1.json")
    assert cli.main(args) == 0
    value = json.loads((output / "reports/report.json").read_bytes())
    assert value["counts"]["checks"]["unchanged_failures"] == 1


@pytest.mark.parametrize(
    "kind", ["missing-case", "duplicate-case", "dataset-version", "dataset-id", "invalid-json"]
)
def test_bad_recorded_outputs(fixture_dir, tmp_path, capsys, kind):
    value = json.loads((fixture_dir / "candidate-v2.json").read_bytes())
    if kind == "missing-case":
        value["outputs"].pop()
    elif kind == "duplicate-case":
        value["outputs"].append(value["outputs"][0])
    elif kind == "dataset-version":
        value["dataset_version"] = "99.0.0"
    elif kind == "dataset-id":
        value["dataset_id"] = "different"
    file = tmp_path / "private-input.json"
    file.write_bytes(b"secret broken" if kind == "invalid-json" else json.dumps(value).encode())
    output = tmp_path / "output"
    args = arguments(fixture_dir, output)
    set_arg(args, "--candidate", file)
    assert cli.main(args) == 2
    assert not output.exists()
    stdout, stderr = capsys.readouterr()
    assert not stdout and "ERROR" in stderr
    assert "private" not in stderr and "Traceback" not in stderr


@pytest.mark.parametrize("name", ["--dataset", "--baseline", "--candidate", "--policy"])
def test_missing_input(fixture_dir, tmp_path, capsys, name):
    args = arguments(fixture_dir, tmp_path / "output")
    if name == "--policy":
        args += [name, str(tmp_path / "missing-private.json")]
    else:
        set_arg(args, name, tmp_path / "missing-private.json")
    assert cli.main(args) == 2
    assert "INPUT_NOT_FOUND" in capsys.readouterr().err
    assert not (tmp_path / "output").exists()


@pytest.mark.parametrize(
    "args", [[], ["unknown-private"], ["check"], ["--secret=hidden"], ["check", "--dat", "private"]]
)
def test_usage_sanitized(args, capsys):
    assert cli.main(args) == 2
    stdout, stderr = capsys.readouterr()
    assert not stdout and "CLI_USAGE" in stderr
    assert "private" not in stderr and "hidden" not in stderr


def test_invalid_policy_before_output(fixture_dir, tmp_path, capsys):
    file = tmp_path / "private-policy.json"
    file.write_text('{"secret":"hidden"}')
    args = arguments(fixture_dir, tmp_path / "output") + ["--policy", str(file)]
    assert cli.main(args) == 2
    assert not (tmp_path / "output").exists()
    assert "INVALID_EVIDENCE_OR_POLICY" in capsys.readouterr().err


def test_directory_input_is_invalid_on_windows_too(fixture_dir, tmp_path, capsys):
    args = arguments(fixture_dir, tmp_path / "output")
    set_arg(args, "--dataset", tmp_path)
    assert cli.main(args) == 2
    assert "INPUT_NOT_FILE" in capsys.readouterr().err
    assert not (tmp_path / "output").exists()


@pytest.mark.parametrize(
    "exception,expected",
    [
        (IsADirectoryError("private"), 2),
        (PermissionError("private"), 3),
        (OSError("private"), 3),
    ],
)
def test_read_failure_sanitized(fixture_dir, tmp_path, capsys, monkeypatch, exception, expected):
    def fail(*args):
        raise exception

    monkeypatch.setattr(Path, "read_bytes", fail)
    assert cli.main(arguments(fixture_dir, tmp_path / "output")) == expected
    assert "private" not in capsys.readouterr().err
    assert not (tmp_path / "output").exists()


@pytest.mark.parametrize("code", [RunErrorCode.EVALUATOR_ERROR, RunErrorCode.RESULT_INVALID])
def test_engine_runtime_errors(fixture_dir, tmp_path, capsys, monkeypatch, code):
    def fail(*args, **kwargs):
        raise RunError(code, "private output")

    monkeypatch.setattr(cli, "evaluate_run", fail)
    assert cli.main(arguments(fixture_dir, tmp_path / "output")) == 3
    assert "private" not in capsys.readouterr().err


def test_evaluator_version_mismatch(fixture_dir, tmp_path, monkeypatch, capsys):
    original = cli.evaluate_run

    def incompatible(*args, **kwargs):
        result = original(*args, **kwargs)
        if kwargs["output_set_id"] == "candidate":
            case = result.results[0]
            checks = (replace(case.checks[0], evaluator_version="9.0.0"),)
            results = (replace(case, checks=checks), *result.results[1:])
            result = replace(
                result, results=results, result_sha256=result_sha256(result.provenance, results)
            )
        return result

    monkeypatch.setattr(cli, "evaluate_run", incompatible)
    assert cli.main(arguments(fixture_dir, tmp_path / "output")) == 2
    assert not (tmp_path / "output").exists()
    assert "INVALID_EVIDENCE_OR_POLICY" in capsys.readouterr().err


def test_no_overwrite_success_claim(fixture_dir, tmp_path, capsys):
    output = tmp_path / "occupied"
    output.mkdir()
    keep = output / "keep.txt"
    keep.write_bytes(b"preserve")
    assert cli.main(arguments(fixture_dir, output)) == 3
    stdout, stderr = capsys.readouterr()
    assert not stdout and "REPORT_OUTPUT" in stderr and "Traceback" not in stderr
    assert keep.read_bytes() == b"preserve"


def test_dataset_snapshot_read_once(fixture_dir, tmp_path, monkeypatch):
    original = Path.read_bytes
    reads = []

    def read(path):
        reads.append(path)
        return original(path)

    monkeypatch.setattr(Path, "read_bytes", read)
    assert cli.main(arguments(fixture_dir, tmp_path / "output")) == 1
    assert reads.count(fixture_dir / "golden-v1.0.0.json") == 1
    assert len(reads) == 3


def test_recorded_code_is_inert(fixture_dir, tmp_path):
    marker = tmp_path / "must-not-exist"
    value = json.loads((fixture_dir / "candidate-v2.json").read_bytes())
    value["outputs"][0]["output"] = f"__import__('pathlib').Path({str(marker)!r}).touch()"
    file = tmp_path / "code.json"
    file.write_text(json.dumps(value), encoding="utf-8")
    args = arguments(fixture_dir, tmp_path / "output")
    set_arg(args, "--candidate", file)
    assert cli.main(args) == 1
    assert not marker.exists()
    report = (tmp_path / "output/reports/report.json").read_bytes()
    assert b"__import__" not in report and str(marker).encode() not in report


def test_main_module_under_network_guard(fixture_dir, tmp_path, monkeypatch):
    monkeypatch.setattr(sys, "argv", ["fixturedelta", *arguments(fixture_dir, tmp_path / "output")])
    with pytest.raises(AssertionError, match="Network access"):
        socket.getaddrinfo("example.invalid", 443)
    with pytest.raises(SystemExit) as result:
        runpy.run_module("fixturedelta_lab", run_name="__main__")
    assert result.value.code == 1


# Child processes install their own socket/DNS guards before importing the CLI.
GUARDED_MODULE = """
import runpy, socket
def blocked(*args, **kwargs):
    raise AssertionError('Network forbidden in CLI child')
socket.socket = socket.create_connection = socket.getaddrinfo = blocked
runpy.run_module('fixturedelta_lab', run_name='__main__')
"""


@pytest.mark.parametrize("expected", [0, 1, 2, 3])
def test_subprocess_exit_contract(fixture_dir, tmp_path, expected):
    output = tmp_path / "output"
    args = arguments(fixture_dir, output)
    if expected == 0:
        args += ["--policy", str(fixture_dir / "policy-allow-v1.json")]
    elif expected == 2:
        set_arg(args, "--baseline", tmp_path / "missing")
    elif expected == 3:
        output.mkdir()
    env = {key: value for key, value in os.environ.items() if key != "PYTHONPATH"}
    result = subprocess.run(
        [sys.executable, "-I", "-c", GUARDED_MODULE, *args],
        cwd=tmp_path,
        env=env,
        capture_output=True,
        timeout=30,
    )
    assert result.returncode == expected, result.stderr
    assert b"Traceback" not in result.stderr and str(tmp_path).encode() not in result.stderr
    assert (output / "reports/report.json").exists() is (expected in (0, 1))


def test_module_entrypoint_and_path_independent_bytes(fixture_dir, tmp_path):
    original = arguments(fixture_dir, tmp_path / "first")
    assert cli.main(original) == 1
    copied = tmp_path / "copied"
    copied.mkdir()
    for path in fixture_dir.glob("*.json"):
        (copied / path.name).write_bytes(path.read_bytes())
    result = subprocess.run(
        [sys.executable, "-I", "-m", "fixturedelta_lab", *arguments(copied, tmp_path / "second")],
        cwd=tmp_path,
        capture_output=True,
        timeout=30,
    )
    assert result.returncode == 1, result.stderr
    for name in ("report.json", "report.md"):
        assert (tmp_path / "first/reports" / name).read_bytes() == (
            tmp_path / "second/reports" / name
        ).read_bytes()


def test_help():
    result = subprocess.run(
        [sys.executable, "-I", "-m", "fixturedelta_lab", "check", "--help"],
        capture_output=True,
        timeout=30,
    )
    assert result.returncode == 0 and b"--report-dir" in result.stdout and not result.stderr
