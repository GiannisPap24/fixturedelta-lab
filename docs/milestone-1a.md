# Milestone 1A completion record

> Historical verification record using the names and tools at that checkpoint.
> For current commands, names and licence, see [README](../README.md) and
> [portfolio release verification](portfolio-release.md).

Completed locally on **2026-10-24** in
the project checkout.

## A. Environment assessment

| Component | Actual observation |
| --- | --- |
| Workspace | Independent directory; initially only an empty `.git` repository |
| Git | 2.54.0.windows.1; existing `master` branch has no commits; no remote configured |
| Default Python | 3.14.4, the installed Python 3.14 interpreter |
| Project Python | 3.12.10, installed interpreter selected for the project |
| Other interpreters | Only the two verified interpreters were used for this milestone |
| uv | 0.13.3, available on PATH |
| VS Code | 1.143.1, x64; `code --version` succeeded |
| Primary environment | `.venv`, Python 3.12.10, editable project installation |
| Wheel verification environment | `.venv-package`, Python 3.14.4, installed wheel rather than editable source |
| Dependencies | pytest 9.1.1, Ruff 0.17.2; exact transitive versions and hashes in `uv.lock` |

Both environments are project-local. Existing installed interpreters were used with
automatic Python downloads disabled. No global settings, execution policies, other
projects, Git remotes, or VS Code extensions were changed. No browser was needed or
tested, and no browser availability claim is made.

## B. Confirmed MVP and non-goals

The eventual MVP compares baseline and candidate recorded response sets on an
immutable synthetic dataset, using deterministic checks, explained results,
regression/improvement reporting, quality gates, and reproducible JSON/Markdown
with explicit dataset/evaluator/candidate provenance.

1A includes contracts, strict input loading and alignment, fixtures, testing,
packaging, and documentation. The evaluator, runner, comparison, reporting, and
CLI modules are documented placeholders. No engine or later milestone was started.
No LLM/API calls, real model benchmarks, private data, telemetry, training, frontend,
deployment, external repository creation, or publication occurred. Registry access
was used only for authorized development dependency setup; public web research was
used for naming and uv documentation.

## C. Architecture and decisions

Runtime dependencies are empty. Frozen dataclasses/enums define cases, expectations,
output sets, checks, case/run results, and provenance. Local JSON adapters reject
ambiguity and validate output coverage independently of evaluation. Greek/English
text is preserved literally. JSON structure expectations deliberately describe a
small top-level object contract, not general JSON Schema.

pytest and Ruff are the only direct development dependencies. `uv_build==0.13.3`
is the pinned build backend; uv supplied its bundled backend for the verified builds.
The generated lockfile records development dependencies; the backend is pinned
separately in `pyproject.toml`. No `.env.example` is needed because there are no
credentials or environment-driven application settings. No publication license was
selected. Full rationale: [architecture](architecture.md) and
[evaluation contract](evaluation-contract.md).

## D. Exact authored/generated project file inventory

All **29** files below are new. No pre-existing source files were modified. They
remain uncommitted in the existing local Git repository.

```text
.gitattributes
.gitignore
.python-version
.vscode/extensions.json
.vscode/settings.json
AGENTS.md
README.md
docs/architecture.md
docs/evaluation-contract.md
docs/milestone-1a.md
docs/naming.md
docs/roadmap.md
pyproject.toml
src/trustbench_ai/__init__.py
src/trustbench_ai/cli.py
src/trustbench_ai/comparison.py
src/trustbench_ai/datasets.py
src/trustbench_ai/domain.py
src/trustbench_ai/metrics/__init__.py
src/trustbench_ai/py.typed
src/trustbench_ai/reporting.py
src/trustbench_ai/runner.py
tests/conftest.py
tests/fixtures/baseline-v1.json
tests/fixtures/candidate-v2.json
tests/fixtures/golden-v1.0.0.json
tests/test_datasets.py
tests/test_domain.py
uv.lock
```

Ignored generated state: `.venv/`, `.venv-package/`, `.pytest_cache/`, `.ruff_cache/`,
Python `__pycache__/` directories, and uv's generated `dist/.gitignore`.
Additional ignored files:

```text
artifacts/dev-requirements.txt
dist/trustbench_ai-0.1.0-py3-none-any.whl
dist/trustbench_ai-0.1.0.tar.gz
```

The requirements export was generated from the lockfile for the isolated wheel
verification environment. Ordinary uv package-cache population also occurred;
no global development configuration was changed.

## E. Actual checks and outcomes

| Check | Actual result |
| --- | --- |
| `uv run --locked --offline pytest` | **63 passed**, Python 3.12.10 |
| `.venv-package/Scripts/python.exe -I -m pytest` | **63 passed**, Python 3.14.4, installed wheel |
| `uv run --locked --offline ruff check .` | All checks passed |
| `uv run --locked --offline ruff format --check .` | All files already formatted |
| `uv lock --check --offline` | Success, 8 resolved packages including this project |
| `uv sync --locked --offline --no-python-downloads` | Success, environment consistent with lock |
| Editable import + installed metadata | Version `0.1.0` matched; source location inside this project |
| `uv build --offline` | Source archive and wheel built successfully; wheel built from source archive |
| Wheel installation with `uv pip install --offline --no-deps` | Success in `.venv-package` |
| Isolated `python -I` wheel import | Version matched; module resolved from `.venv-package/Lib/site-packages` |
| Archive inspection | Wheel contains package and `py.typed`, no tests/docs; metadata has no runtime requirements; source archive contains fixtures and `uv.lock` |
| Git status/remotes | Only project additions; no commits or remote |

Tests exercise valid fixtures/alignment; type/schema errors; missing/unknown fields;
duplicate keys and IDs; invalid UTF-8/BOM/nonstandard JSON constants; invalid
expectation configurations; exact text preservation including empty responses and
Greek Unicode variants; immutable contracts; derived case status; explanation and
provenance validation. Tests do not execute or imply a completed evaluation engine.

The initial lint pass found two long lines in `datasets.py`; Ruff formatting fixed
them and final checks passed. The first attempt to bootstrap the second environment
offline could not resolve Ruff from cached registry data. A hash-checked installation
from the lock export with registry access completed setup; wheel installation and
tests then succeeded locally. Offline reproducibility after setup is verified;
offline bootstrap from an empty cache is not claimed. No static type checker,
multi-OS CI, coverage threshold, or real model evaluation was run.

## F. Naming conflicts and alternatives

Public sources confirm several existing TrustBench uses, including a closely
related [evaluation harness](https://github.com/Umarfarook1/trustbench),
[evaluation product](https://www.trustbench.net/en), and
[attested evaluations](https://sdk.divinci.ai/server/trustbench/).
Recommend **GoldenDiff Lab**; **TraceVerdict** is another screened alternative.
Quoted searches surfaced no clear matches for those two names, which is not proof
of availability. The existing local name remains unchanged. See the dated
[research and source links](naming.md) for scope and discarded options.

## G. Technical risks

- Six synthetic cases validate mechanics, not real-world model quality or factuality.
- Literal Unicode checks are deliberately sensitive to normalization and formatting.
- JSON shape validation is shallow; nested semantic/schema constraints are deferred.
- Domain objects validate structure, not the truth of supplied provenance; future
  runners must compute hashes and enforce result coverage from actual inputs.
- Cross-platform behavior and static typing are not verified; only Windows Python
  3.12.10 and 3.14.4 were tested.
- Offline setup depends on cached tooling. Large/untrusted-input limits, final
  naming, and a publication license require later decisions.

## H. Roadmap with acceptance criteria

The [roadmap](roadmap.md) specifies separate acceptance criteria for 1B deterministic
evaluators, 1C single-run execution, 1D comparison/gates, 1E reports/CLI, and 1F
release-readiness review. Future work remains unimplemented and requires a new request.

## I. Recommended narrowly scoped Milestone 1B

Implement the three pure deterministic evaluator families and focused edge-case
tests only. They should return versioned, explained checks without I/O. Verify
Unicode literal matching, required/forbidden phrases, strict JSON parsing,
boolean/integer distinctions, extra/missing keys, and deterministic repeatability.
Do not add the runner, comparison, gates, reports, CLI, or external services yet.
