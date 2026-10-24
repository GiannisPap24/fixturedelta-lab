# Milestone 1B completion record

> Historical verification record using the names and tools at that checkpoint.
> For current commands, names and licence, see [README](../README.md) and
> [portfolio release verification](portfolio-release.md).

Completed **2026-10-24**, in the existing independent repository
the project checkout. Package/import names remain
`trustbench-ai` / `trustbench_ai`; unreleased package version remains `0.1.0`.
GoldenDiff Lab is still the preferred possible final name. No renaming occurred.

## A. Exact files created and modified

Compared with the 29-file 1A baseline, **9 files were created and 10 modified**.
The distinction was verified using SHA-256 hashes saved before implementation;
Git still reports all files as untracked because no initial commit exists.

Created:

```text
.vscode/launch.json
.vscode/tasks.json
docs/milestone-1b.md
docs/vscode.md
src/trustbench_ai/metrics/_common.py
src/trustbench_ai/metrics/content.py
src/trustbench_ai/metrics/exact.py
src/trustbench_ai/metrics/json_structure.py
tests/test_metrics.py
```

Modified:

```text
.vscode/extensions.json
.vscode/settings.json
AGENTS.md
README.md
docs/architecture.md
docs/evaluation-contract.md
docs/roadmap.md
pyproject.toml
src/trustbench_ai/metrics/__init__.py
uv.lock
```

The original domain/loader implementations, three synthetic fixture files, all 63
foundation tests, and historical 1A completion record are byte-for-byte unchanged.
Runner, comparison, reporting, and CLI placeholders are unchanged.

Ignored local verification artifacts include `artifacts/milestone-1b-baseline.json`,
`artifacts/.coverage-metrics`, `artifacts/coverage-metrics.json`,
`artifacts/verify_workspace.py`, `artifacts/verify_debugger.py`, and
`artifacts/debug-adapter.log`. Existing `.venv`, `.venv-package`, caches, and
`dist/trustbench_ai-0.1.0.{tar.gz,whl}` outputs were updated as applicable (the actual
wheel filename is `trustbench_ai-0.1.0-py3-none-any.whl`). Development artifacts
are ignored and are not application evaluation reports.

## B. Interfaces and semantics

All public functions are exported from `trustbench_ai.metrics`:

| Interface | Behavior |
| --- | --- |
| `evaluate_exact_match(output, ExactMatch)` | One `CheckResult`; literal code-point equality, no trimming/case folding/normalization; first-difference offset and escaped bounded previews |
| `evaluate_content_rules(output, ContentRules)` | Immutable tuple of checks, required then forbidden; empty groups omitted; each rule has an indexed presence/absence and pass/fail explanation |
| `evaluate_json_object(output, JsonObject)` | One `CheckResult`; strict whole-response JSON, root object, required types, null/missing distinction, explicit extras policy |
| `evaluate_case(Case, RecordedOutput)` | Requires matching IDs; dispatches one family and returns `CaseResult`; no dataset orchestration or run creation |

Stable evaluator IDs are `exact-match`, `required-content`, `forbidden-content`,
and `json-object`, all version **1.0.0**. Explanation prefixes provide deterministic
diagnostics without altering the 1A result model. Inputs and results are immutable;
no model, filesystem, clock, or network access occurs inside evaluators.

JSON rejects duplicate keys at any depth, malformed text/fences/trailing documents,
non-finite constants and float overflow. Integer and number checks exclude booleans;
`2.0` does not match integer. Required-field diagnostics follow schema order; extra
keys are sorted. Explicit limits are 64 nested containers and 4300 digits per integer
token. Nested object/array contents are not schema-validated. See the
[full contract](evaluation-contract.md) for diagnostics and limitations.

## C. Existing and new tests

| Test file | Count | Result |
| --- | ---: | --- |
| Existing `test_datasets.py` | 40 | Passed unchanged |
| Existing `test_domain.py` | 23 | Passed unchanged |
| New `test_metrics.py` | 123 | Passed |
| **Total** | **186** | **Passed on both interpreters** |

New tests cover literal English/Greek text, accents/NFC-NFD differences, case,
whitespace/newlines, empty strings, substring/regex distinctions, multi-rule
explanations, invalid configurations, a 49-combination JSON type matrix, duplicate
keys, null/missing/extra fields, non-finite numbers, resource boundaries, repeatability,
input immutability, adapter type/ID errors, and all twelve synthetic fixture outcomes.
Existing socket/DNS guards remain enabled. The test changing the interpreter's
integer limit restores it in `finally`; production code never changes interpreter limits.

## D. Coverage, quality, dependencies, packaging

| Check | Actual result |
| --- | --- |
| `uv run --locked --offline coverage run -m pytest` | 186 passed, Python 3.12.10 |
| Targeted evaluator statement coverage | **130/130, 100%** |
| Targeted evaluator branch coverage | **46/46, 100%**, no excluded lines or partial branches |
| `uv run --locked --offline ruff check .` | Passed |
| `uv run --locked --offline ruff format --check .` | Passed |
| `uv lock --check --offline` | Passed; 9 resolved packages including this project |
| `uv sync --locked --offline --no-python-downloads` | Passed |
| `uv pip check` in `.venv` and `.venv-package` | All installed packages compatible |
| `uv build --offline` | Source distribution and wheel built; wheel built from source distribution |
| Offline wheel reinstall in `.venv-package` | Passed; `trustbench_ai.metrics` resolves inside `site-packages` |

Coverage scope is only the new `trustbench_ai.metrics` package; it is not whole-project
coverage or proof of complete correctness. Per-module statement/branch counts:

| Module | Statements covered/total | Branches covered/total |
| --- | ---: | ---: |
| `metrics/__init__.py` | 17/17 | 8/8 |
| `metrics/_common.py` | 10/10 | 4/4 |
| `metrics/content.py` | 13/13 | 4/4 |
| `metrics/exact.py` | 13/13 | 2/2 |
| `metrics/json_structure.py` | 77/77 | 28/28 |

The only added dependency is development-only **Coverage.py 7.17.0**, justified
by the requested statement/branch measurement. pytest remains 9.1.1 and Ruff 0.17.2;
runtime dependencies remain empty. uv regenerated `uv.lock`; no hashes were edited.
Initial coverage installation used authorized registry access. Tests, subsequent
dependency checks, and builds ran offline. No new Python interpreter was installed.

Source distributions include tests, fixtures, documentation, lockfile, and the VS Code
workspace configuration. Wheels contain the typed runtime package, with no runtime
dependencies or development artifacts. No package was uploaded.

## E. Python compatibility

- Python **3.12.10**, project `.venv`, editable source: 186 tests passed.
- Python **3.14.4**, independent `.venv-package`, installed wheel with `python -I`:
  186 tests passed. Import location was checked to exclude accidental source imports.
- Other interpreters/platforms were not tested; no CI matrix or static type checker
  was introduced.

Compatibility testing caught different built-in JSON nesting behavior between 3.12
and 3.14. The first draft's runtime-dependent assumption was replaced with explicit
evaluator bounds and boundary tests. Initial Ruff formatting/import issues were
also fixed; the final checks pass. Domain contracts and existing loader behavior
were preserved throughout.

## F. VS Code configuration

- `settings.json`: workspace-relative Python 3.12 environment, pytest discovery,
  locked local Ruff executable, Python default formatter, lint enabled.
- `tasks.json`: offline pytest, Ruff lint, Ruff format check, sequential combined
  Ruff check, and offline lock verification. No automatic-on-open tasks.
- `launch.json`: focused evaluator-suite and current-test-file debugging with
  `debugpy`, project Python/cwd, explicit arguments and environment.
- `extensions.json`: Python, Python Debugger, Ruff, and official Codex recommendations.

See [docs/vscode.md](vscode.md) for the complete workflow. All JSON files parsed and
workspace-relative executable paths resolved correctly.

## G. Project opening

**Confirmed open in VS Code.** The supported `code --reuse-window` launcher was used
for the existing folder. A subsequent launcher invocation added `--wait` while the
workspace was verified. Native window inspection confirmed
`test_metrics.py - trustbench-ai - Visual Studio Code` and the correct Explorer root.
The editor status bar showed Python **3.12.10** from this project's `.venv` and Ruff.
No sandbox denial, security bypass, or duplicate project was involved.

## H. Official Codex extension

**Already installed; no installation necessary.** `code --list-extensions --show-versions`
reported `openai.chatgpt@26.1021.22027`. Its installed manifest identifies publisher
`openai` and display name “Codex – OpenAI’s coding agent”. The workspace UI exposed
the Codex sidebar and a loaded `openai.chatgpt` webview, confirming workspace availability.
The [official IDE documentation](https://learn.chatgpt.com/docs/codex/ide) informed the
workflow. Authentication and external inference were not exercised.

## I. Task and debugger readiness

Each executable task was read from `tasks.json` and its exact command/arguments/cwd
executed successfully. The combined task's references and sequential order were checked.
Both debug argument lists executed the focused tests using the configured interpreter.
The installed Python Debugger adapter was then exercised through its local stdio
interface: it launched pytest, verified a breakpoint in `metrics/exact.py`, stopped
at that breakpoint, returned the expected source stack frame, continued, and exited 0.
This adapter check used `internalConsole`; saved launch configs use `integratedTerminal`.
Interactive F5 terminal routing and task-menu clicks were not automated.

## J. Known limitations

- Literal/structural checks cannot establish factual truth, absence of hallucination,
  semantic equivalence, general safety, or real-world model quality.
- JSON support is shallow and has explicit resource limits. A host with a stricter
  integer conversion limit can reject additional inputs; the evaluator reports the
  failure and never changes that limit. Full untrusted-input hardening is deferred.
- Escaped previews are bounded per string, not a secret-redaction guarantee or a
  total report-size bound. Synthetic non-confidential inputs only.
- Editor configuration is Windows-specific; Python 3.12/3.14 on Windows were verified.
- The official extension is installed and loaded; no external chat request was sent.
- No unresolved failing checks remain within the verified scope. No orchestrator,
  comparison engine, gates, reports, CLI, frontend, database, deployment, or publication
  was added. No global development/security settings or other project files changed.

## K. Git state and next milestone

The existing `master` branch still has **no commits**, all 38 project files are
untracked, and no remote is configured. No commit, push, or external repository
creation was performed. After reviewing this milestone, create an initial local
checkpoint for the combined 1A/1B foundation; do not publish without separate approval.

Recommended **Milestone 1C**: one offline run orchestrator with complete coverage,
stable ordering, and hashes/provenance from the exact evaluated bytes. Keep comparison,
regression gates, reports, and CLI work outside 1C. See [acceptance criteria](roadmap.md).
Stop here until the owner requests further work.
