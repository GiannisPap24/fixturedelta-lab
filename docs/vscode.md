# VS Code workflow

Open the checkout root after the [README setup](../README.md):

```powershell
code --reuse-window .
```

Workspace settings select `${workspaceFolder}/.venv/Scripts/python.exe` and the local
Ruff executable. If a previously saved interpreter takes precedence, use **Python:
Select Interpreter** to select this project's `.venv`. The separate `.venv-package`
environment is only for installed-wheel verification.

## Toolchain selection

Every uv-based task invokes `powershell.exe -NoProfile -NonInteractive -File scripts/uv.ps1`.
The demo uses the same wrapper. It prefers the optional ignored `.tools/uv.exe`, otherwise
checks the first uv application on PATH. Unsupported or unparseable versions fail with
`TOOLCHAIN_ERROR` before the requested command. Accepted versions are >=0.13.4,<0.14.
The project-local copy here is 0.13.4; the older global 0.13.3 is not selected.
No PATH override, global upgrade, execution-policy bypass or automatic installation occurs.
On a fresh checkout, supply trusted patched uv as described in the README.

## Tasks

| Task | Operation / expected exit |
| --- | --- |
| Tests: offline pytest | Complete locked offline suite / 0 |
| Quality: Ruff lint | Locked offline lint / 0 |
| Quality: Ruff format check | Locked offline formatting check / 0 |
| Quality: Ruff checks | Lint then format check |
| Dependencies: verify lock offline | Lock consistency / 0 |
| FixtureDelta Lab: synthetic CLI demo (expected exit 1) | Real seeded regression comparison / 1 |
| FixtureDelta Lab: verified end-to-end demo (expected exit 0) | Fail/pass/error scenarios and report verification / 0 |

Tasks use the workspace root as cwd, process arguments and fresh output-directory
prompts. Nothing runs automatically when the workspace opens. Formatting and fixes
on save remain disabled; use Format Document manually if desired.

## Debugging

Three configurations use `.venv`: evaluator tests, the current test file and
`python -m fixturedelta_lab` with the synthetic CLI arguments. Put a breakpoint at
`comparison = compare_runs(baseline, candidate)` in `src/fixturedelta_lab/cli.py`,
select **Python: Debug synthetic CLI (expected exit 1)** and press F5. Enter a fresh
report directory, inspect the runs, and continue. Two seeded regressions mean exit 1;
that exit is expected. An occupied output directory instead returns 3.

The [portfolio verification record](portfolio-release.md) reports actual task execution,
all debug targets and a breakpoint/stack/continue session through the installed debug
adapter. That adapter check uses stdio/internal console; it does not claim automated
clicks through the task prompt or F5 integrated-terminal routing.

## Extensions and privacy

Recommendations remain Python, Python Debugger, Ruff and official `openai.chatgpt`.
They were already installed; no extension or global editor settings were changed.
Codex authentication and live inference were not exercised. Use the current checkout,
reference relevant files and provide a narrow stopping point. Review changes before
accepting a checkpoint. Earlier editor/version observations are preserved in the
historical [1B](milestone-1b.md), [2C](milestone-2c.md) and [3A](milestone-3a.md) records.
