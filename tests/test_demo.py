"""Windows demo launcher regression checks with isolated synthetic tool stubs."""

import os
import shutil
import subprocess
import sys
from pathlib import Path

import pytest


@pytest.mark.skipif(sys.platform != "win32", reason="Windows PowerShell launcher")
def test_demo_selects_first_uv_when_path_contains_multiple_copies(tmp_path: Path) -> None:
    powershell = shutil.which("powershell.exe")
    if powershell is None:
        pytest.skip("Windows PowerShell is not installed")
    root = tmp_path / "project"
    scripts = root / "scripts"
    scripts.mkdir(parents=True)
    shutil.copyfile(Path(__file__).parents[1] / "scripts/demo.ps1", scripts / "demo.ps1")
    shutil.copyfile(Path(__file__).parents[1] / "scripts/uv.ps1", scripts / "uv.ps1")
    (root / "pyproject.toml").write_text('name = "fixturedelta-lab"\n', encoding="utf-8")
    (root / "uv.lock").touch()
    source = root / "src/fixturedelta_lab"
    source.mkdir(parents=True)
    (source / "cli.py").touch()
    python = root / ".venv/Scripts"
    python.mkdir(parents=True)
    (python / "python.exe").touch()
    paths = []
    for name in ("first", "second"):
        directory = tmp_path / name
        directory.mkdir()
        (directory / "uv.cmd").write_text(
            '@echo off\nif "%1"=="--version" (echo uv 0.13.4& exit /b 0)\n'
            f'if "%1"=="lock" exit /b 0\necho DEMO selected {name}\nexit /b 0\n',
            encoding="ascii",
        )
        paths.append(str(directory))
    env = {k: v for k, v in os.environ.items() if k.upper() != "UV_PROJECT_ENVIRONMENT"}
    env["PATH"] = os.pathsep.join([*paths, env.get("PATH", "")])
    result = subprocess.run(
        [powershell, "-NoProfile", "-File", str(scripts / "demo.ps1")],
        cwd=root,
        env=env,
        capture_output=True,
        text=True,
        timeout=15,
    )
    assert result.returncode == 0, result.stderr
    assert result.stdout.strip() == "DEMO selected first"


@pytest.mark.skipif(sys.platform != "win32", reason="Windows PowerShell launcher")
@pytest.mark.parametrize("version", ["0.13.3", "0.14.0", "0.13.4rc1", "invalid"])
def test_toolchain_rejects_unsupported_uv_before_command(tmp_path: Path, version: str) -> None:
    result, marker = _run_toolchain_stub(tmp_path, version, 0)
    assert result.returncode == 3
    assert "TOOLCHAIN_ERROR" in result.stderr
    assert not marker.exists()


@pytest.mark.skipif(sys.platform != "win32", reason="Windows PowerShell launcher")
@pytest.mark.parametrize("exit_code", [0, 1, 2, 3])
def test_toolchain_preserves_arguments_and_exit_codes(tmp_path: Path, exit_code: int) -> None:
    result, marker = _run_toolchain_stub(tmp_path, "0.13.4", exit_code)
    assert result.returncode == exit_code
    assert marker.read_text().strip() == "check --offline"
    assert "TOOLCHAIN_ERROR" not in result.stderr


def _run_toolchain_stub(
    root: Path, version: str, exit_code: int
) -> tuple[subprocess.CompletedProcess[str], Path]:
    powershell = shutil.which("powershell.exe")
    if powershell is None:
        pytest.skip("Windows PowerShell is not installed")
    scripts = root / "scripts"
    scripts.mkdir()
    shutil.copyfile(Path(__file__).parents[1] / "scripts/uv.ps1", scripts / "uv.ps1")
    tools = root / "tools"
    tools.mkdir()
    (tools / "uv.cmd").write_text(
        f'@echo off\nif "%1"=="--version" (echo uv {version}& exit /b 0)\n'
        f"echo %*>invoked.txt\nexit /b {exit_code}\n",
        encoding="ascii",
    )
    env = dict(os.environ)
    env["PATH"] = str(tools) + os.pathsep + env.get("PATH", "")
    result = subprocess.run(
        [powershell, "-NoProfile", "-File", str(scripts / "uv.ps1"), "check", "--offline"],
        cwd=root,
        env=env,
        capture_output=True,
        text=True,
        timeout=15,
    )
    return result, root / "invoked.txt"
