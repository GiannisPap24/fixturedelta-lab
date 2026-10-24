# FixtureDelta Lab

Offline regression testing for **recorded AI-application outputs**, using versioned
expectations, baseline/candidate comparisons and explicit quality gates.

A prompt, model or application change can break output contracts that previously
passed. FixtureDelta Lab checks saved responses for exact text, required/forbidden
content and JSON field types, then reports what regressed or improved. It uses the
Python standard library and has **no runtime dependencies or model calls**.

**Status:** sanitized local public-release candidate; GitHub publication awaits owner approval.
Verified on Windows with Python **3.12.10 and 3.14.4**. Python >=3.12 is declared;
other operating systems and interpreter versions have not been validated here.

## Quick start (Windows PowerShell)

Prerequisites: installed Python 3.12 and trusted **uv 0.13.4** (accepted range
`>=0.13.4,<0.14`). Use an executable on PATH or place it at `.tools/uv.exe`.
See the [official uv installation guide](https://docs.astral.sh/uv/getting-started/installation/).
The minimum version includes the [upstream certificate-store fix](https://github.com/astral-sh/uv/security/advisories/GHSA-hq85-5cpj-mr62).

From your checkout root:

```powershell
.\scripts\uv.ps1 --version
.\scripts\uv.ps1 sync --locked --python 3.12 --no-python-downloads
.\scripts\demo.ps1 -OutputDirectory artifacts/demo
```

The wrapper prefers `.tools/uv.exe`, otherwise checks the first uv executable on PATH.
It refuses unsupported versions before running the requested command. It does not
install tools or change global settings, PATH or execution policy. VS Code tasks and
the demo use this same wrapper. Local tool binaries are ignored, not committed.

The first sync creates `.venv` and may download development dependencies. Once cached,
use `sync --locked --offline --no-python-downloads`. Offline setup is not a promise
that an empty machine needs no downloads. uv 0.13.4 includes the exact pinned build
backend; another accepted uv version may need that backend cached separately.

Use a **new output directory** each time. A verified demo exits 0 and creates four
report pairs plus `verification.json` under the selected ignored directory:

| Scenario | Checks | Regressions | Improvements | Candidate passes | Gate / CLI exit |
| --- | --- | --- | --- | --- | --- |
| Baseline vs candidate | 8 across 6 cases | 2 | 1 | 6/8 | FAIL / 1 |
| Baseline vs baseline | 8 across 6 cases | 0 | 0 | 7/8 | PASS / 0 |

The passing scenario still has one unchanged failed check: the default policy permits
existing failures but rejects new regressions. The demo also verifies malformed and
incompatible input (exit 2), occupied output directories (exit 3), unchanged fixtures
and byte-identical console/module reports. These are **handwritten synthetic English
and Greek cases**, not live model measurements. See the [demo guide](docs/demo.md).

## Run a comparison

```powershell
.\scripts\uv.ps1 run --locked --offline fixturedelta check `
  --dataset tests/fixtures/golden-v1.0.0.json `
  --baseline tests/fixtures/baseline-v1.json `
  --candidate tests/fixtures/candidate-v2.json `
  --report-dir artifacts/my-comparison
```

This example intentionally returns **1**: two regressions fail the strict policy.
The installed entry points are `fixturedelta check` and
`python -m fixturedelta_lab check`; the distribution is `fixturedelta-lab`.
No old command or import alias is installed.

Add `--policy tests/fixtures/policy-allow-v1.json` to use the explicit example policy
allowing two regressions, at most two failed candidate checks and a minimum pass rate
of 3/4. That policy passes this candidate. Rule thresholds are inclusive; improvements
never cancel regressions. Pass rates use exact fractions over **individual checks**.

| Exit | Meaning |
| --- | --- |
| 0 | Valid comparison; every configured gate rule passed |
| 1 | Valid comparison; at least one gate rule failed |
| 2 | Invalid arguments, input, alignment, policy or evidence |
| 3 | Runtime, permission/read or report-output failure |

The toolchain wrapper separately returns 3 when its uv prerequisite fails.
Application diagnostics use stable codes and omit expected-error tracebacks and paths.
Inside the directory selected by `--report-dir`, `reports/report.json` contains
structured evidence and `reports/report.md` presents the
same counts, transitions, provenance and policy outcome. Existing output directories
are refused. Reports omit raw prompts/responses and evaluator text previews; labels
must still be nonconfidential. See the [CLI/report contract](docs/report-contract.md).

## Deterministic evaluators

| Evaluator | Checks | Important boundary |
| --- | --- | --- |
| Exact match | Literal string equality | No case, whitespace or Unicode normalization |
| Content rules | Required and forbidden substrings | Case-sensitive; each configured rule remains visible |
| JSON object | Required root fields, shallow types and extra-field policy | Not full JSON Schema; no nested schemas |

JSON validation rejects duplicate keys, non-finite numbers and boolean-as-integer
confusion. Recorded-response JSON supports at most 64 nested containers and 4300
digits per integer token. All cases must align by ID and dataset version. Runs follow
dataset order; comparisons join by case/evaluator ID and retain regressions even in
already-failing or mixed cases. Invalid evidence never becomes an ordinary gate failure.

```python
from fixturedelta_lab.domain import Case, ExactMatch, RecordedOutput
from fixturedelta_lab.metrics import evaluate_case

case = Case("el-demo", "exact-output", "el", "Return Έτοιμο", ExactMatch("Έτοιμο"))
assert evaluate_case(case, RecordedOutput("el-demo", "Έτοιμο")).passed
```

## Architecture and reproducibility

```text
CLI -> dataset/output snapshots -> deterministic evaluations
    -> compatible baseline/candidate comparison -> quality gate -> reports
```

Immutable domain contracts are separate from parsing, evaluation, comparison,
policy, reporting and filesystem publication. Raw input SHA-256 hashes and versioned
canonical fingerprints bind ordered evidence. No timestamps or machine paths affect
results. Formatting-only input changes intentionally change raw input hashes.

The rebrand preserves JSON reports and all fingerprints. Five legacy `trustbench-*-v1`
fingerprint identifiers remain intentional wire-format constants. Only the Markdown
product heading changed to FixtureDelta Lab; it is outside the JSON report digest.
See [release verification](docs/portfolio-release.md) for the exact compatibility decision.

| Location | Responsibility |
| --- | --- |
| `src/fixturedelta_lab/domain.py` | Immutable validated cases, expectations and results |
| `datasets.py`, `metrics/`, `runner.py` | Strict parsing, pure checks and complete runs |
| `comparison.py`, `comparison_types.py` | Compatible pairing and derived transitions |
| `gates.py`, `gate_types.py`, `policies.py` | Explicit policies, exact arithmetic and decisions |
| `provenance.py`, `reporting.py`, `cli.py` | Fingerprints, safe reports and CLI orchestration |
| `tests/fixtures/` | Immutable synthetic inputs and example policy |
| `scripts/`, `.vscode/` | Verified demo, checked uv selection, tasks/debugging |

Read the [architecture](docs/architecture.md), [evaluation contract](docs/evaluation-contract.md)
and [gate contract](docs/gate-contract.md) for detailed interfaces and trust boundaries.

## Validate and build

```powershell
.\scripts\uv.ps1 lock --check --offline
.\scripts\uv.ps1 run --locked --offline pytest
.\scripts\uv.ps1 run --locked --offline ruff check .
.\scripts\uv.ps1 run --locked --offline ruff format --check .
.\scripts\uv.ps1 run --locked --offline coverage run -m pytest
.\scripts\uv.ps1 run --locked --offline coverage report
.\scripts\uv.ps1 build --offline
```

The [public release verification record](docs/public-release.md) contains current test,
coverage, wheel-install and demo results. Tests guard Python socket creation and DNS;
this is not an OS network sandbox. The application contains no networking. `uv.lock`
pins development dependencies and archive hashes; `pyproject.toml` pins the backend.
The wheel includes the MIT licence and has zero runtime dependencies.

Open the checkout in VS Code with `code .`. The workspace selects `.venv/Scripts/python.exe`,
uses local Ruff, discovers pytest and provides manual tasks plus three debug targets.
Run **FixtureDelta Lab: verified end-to-end demo (expected exit 0)** or debug the synthetic
CLI (expected exit 1). See the [VS Code guide](docs/vscode.md).

## Limitations

- Deterministic checks establish conformance to supplied expectations, not factual or
  semantic correctness, comprehensive hallucination detection, safety or model quality.
- No live LLM benchmarking, production monitoring, training, UI or external AI services.
- Six synthetic cases demonstrate engineering behavior, not statistical significance
  or multilingual generalization. No latency, token usage or cost is fabricated.
- Schema v1 requires datasets to declare `origin: "synthetic"`. That declaration
  cannot verify data provenance or remove sensitive content; review inputs and labels
  before sharing them. Only handwritten synthetic evaluation data is supplied here.
- Files are read into memory. Nesting/digit limits are not total-size, CPU or memory
  quotas. Use bounded local inputs and trusted filesystem parent directories.
- Fingerprints establish consistency, not authenticity. No signatures or crash-durable
  filesystem guarantee are provided. Cross-OS CI and broader cases remain future work.

## Licence and attribution

MIT — **Copyright (c) 2026 GiannisPap24**. See [LICENSE](LICENSE).
The repository's synthetic fixtures are included under the same licence; they contain
no imported private datasets or measured model responses. Development/build tools keep
their own licences; see the [dependency licence inventory](docs/release-readiness.md#licence-options-and-dependencies).

The product was formerly developed as TrustBench AI. Historical milestone/audit records
retain their original names and results; private machine locations and development
commit identifiers are omitted. This repository starts from one sanitized release
snapshot; the private development Git history is not included.
The [release checklist](docs/release-readiness.md) records owner approval and the
publication handoff. No GitHub repository or release tag has been created by this work.
