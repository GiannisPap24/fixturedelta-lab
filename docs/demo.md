# Reproducible synthetic regression demo

FixtureDelta Lab is a local Python tool for comparing recorded outputs from two versions
of an AI application. A response can remain plausible while violating an application
contract: an exact label gains punctuation, a required phrase disappears, or JSON
contains a boolean where an integer is required. FixtureDelta Lab evaluates those explicit
contracts and shows which checks regressed, improved or stayed unchanged.

The implementation is Python 3.12+, standard library only at runtime. It separates
immutable contracts, strict input parsing, pure evaluators, run provenance, comparison,
policy evaluation and report publication. The demonstration uses those real components
through their CLI, with the existing six handwritten English/Greek cases.

The JSON fingerprints are unchanged by rebranding. The Markdown title now reads
`FixtureDelta Lab synthetic evaluation`; see [release verification](portfolio-release.md).

## Run the complete demonstration

Use the existing configured project environment with cached dependencies. From the
project root in PowerShell:

```powershell
.\scripts\demo.ps1 -OutputDirectory artifacts/demo
$LASTEXITCODE
```

Or run **Terminal: Run Task → FixtureDelta Lab: verified end-to-end demo (expected exit 0)**
in VS Code and enter a fresh directory under `artifacts/`. Nothing runs on workspace
open. Existing pytest, Ruff and direct CLI tasks remain available.

The wrapper verifies the working directory and existing `.venv`, checks the offline
lock, and invokes the version-checked `scripts/uv.ps1` wrapper with the project
Python. It does not create another environment or change execution policies. If a
machine's policy blocks PowerShell scripts, use the allowed Python command below;
do not bypass or change that policy. Ordinary setup is documented in the README.

```powershell
.venv/Scripts/python.exe -I scripts/demo.py --report-dir artifacts/demo-python
```

`scripts/demo.py` is a repository verification helper, not an alternate evaluator.
It launches the installed `fixturedelta` executable and `python -I -m fixturedelta_lab` from
the selected artifact directory. It removes inherited Python environment overrides
from child processes, including `PYTHONPATH`, and verifies actual output files.
Its standard-library hash checks follow the documented report/policy/gate contracts;
it does not calculate evaluation scores or implement another comparison engine.

The script exits **0 when the demonstration succeeds**, including the deliberately
rejected candidate. A script exit of 1 means a precondition or verification failed.
The underlying application retains its own 0/1/2/3 exit-code contract.

## Inputs and expected decisions

Workflow: versioned dataset → baseline/candidate recorded outputs → deterministic
checks → comparison → strict quality gate → JSON/Markdown → process exit.

The unchanged files under `tests/fixtures/` are:

- `golden-v1.0.0.json`: dataset `synthetic-foundation`, version `1.0.0`, six cases.
- `baseline-v1.json`: application label `synthetic-baseline-v1`.
- `candidate-v2.json`: application label `synthetic-candidate-v2`.

The three evaluator families are literal exact match, case-sensitive required/forbidden
substrings, and limited JSON object/type checks. Greek code points are preserved;
there is no trimming, case folding or Unicode normalization. Required and forbidden
content are separate checks, so six cases produce eight evaluator checks.

| Scenario | Regressions | Improvements | Candidate passing checks | Default gate | CLI exit |
| --- | --- | --- | --- | --- | --- |
| Baseline → candidate-v2 | 2 | 1 | 6/8 | FAIL | 1 |
| Baseline → identical baseline | 0 | 0 | 7/8 | PASS | 0 |

The rejection is intentional: `en-label-001` changes `READY` to `READY!`, and
`en-json-001` supplies a boolean where an integer is required. `el-rules-001` improves
by adding `πράσινος κύκλος`, but that improvement cancels neither regression.

The passing scenario reuses the baseline file in both roles. It does **not** alter the
candidate fixture or relax the default policy. One required-content check remains an
unchanged failure. Zero regressions therefore means no deterioration, not all checks
passing. Optional candidate-failure and exact rational pass-rate policies can impose
additional requirements; see the [gate contract](gate-contract.md).

## Equivalent direct CLI commands

These use separate new directories and the default strict zero-regression policy:

```powershell
.\scripts\uv.ps1 run --locked --offline fixturedelta check --dataset tests/fixtures/golden-v1.0.0.json --baseline tests/fixtures/baseline-v1.json --candidate tests/fixtures/candidate-v2.json --report-dir artifacts/direct-fail
# Expected $LASTEXITCODE: 1

.\scripts\uv.ps1 run --locked --offline fixturedelta check --dataset tests/fixtures/golden-v1.0.0.json --baseline tests/fixtures/baseline-v1.json --candidate tests/fixtures/baseline-v1.json --report-dir artifacts/direct-pass
# Expected $LASTEXITCODE: 0
```

Replace `fixturedelta` with `python -m fixturedelta_lab` for the module entry point. The
script checks both entry points. Optional output-set identity flags are separate
from application labels: defaults are `baseline` and `candidate`, both version
`1.0.0`. Recorded application labels come from the selected input files.

| Application exit | Meaning |
| --- | --- |
| 0 | Valid gate passes and reports publish; also ordinary help without evaluation |
| 1 | Valid gate fails and reports publish; expected in the regression demo |
| 2 | Invalid arguments, missing/non-file inputs, malformed data/policy or incompatible evidence |
| 3 | Runtime, input permission/read, or report-output failure |

The demo creates malformed JSON and a dataset-version mismatch **only inside its own
artifact directory** and verifies exit 2 with no output directory. It retries a valid
run against an occupied destination, verifies exit 3, no success summary, and unchanged
existing report bytes. Expected errors have fixed messages and no tracebacks or paths.

## Reports and independent verification

With destination `artifacts/demo`, the script writes:

```text
artifacts/demo/
  fail-console/reports/report.json + report.md
  fail-module/reports/report.json + report.md
  pass-console/reports/report.json + report.md
  pass-module/reports/report.json + report.md
  inputs/malformed.json + incompatible.json
  verification.json
```

Each scenario's console/module pair must have byte-identical JSON and Markdown. The
helper checks dataset/output raw hashes, identity/version labels, evaluator order,
exact counts, strict-policy rule observations, affected checks, Markdown evidence,
and report/policy/gate fingerprints independently. Original fixture bytes must stay
unchanged, and every generated path must remain inside the selected destination.
Only then is the verification manifest staged, closed and renamed to `verification.json`.
A failed/interrupted verification can leave completed scenario reports or staging
artifacts; the complete demo is verified only when the manifest publishes. A later
terminal failure can still cause a nonzero process exit after that publication.
Choose a fresh destination after inspecting remnants. The helper never recursively
deletes or overwrites outputs.

The failing report contains this excerpt (not a complete report):

```json
{
  "counts": {
    "checks": {
      "regressions": 2,
      "improvements": 1,
      "unchanged_passes": 5,
      "unchanged_failures": 0,
      "total": 8
    }
  },
  "gate": {"passed": false, "candidate_passes": 6, "total_checks": 8}
}
```

Its human-readable Markdown includes `Gate: **FAIL**`, case/evaluator transition
tables and the rule `max-regressions`: observed 2, permitted 0, FAIL. The passing
report shows PASS, zero regressions, seven unchanged passing checks and one unchanged
failing check. All dynamic punctuation/controls are escaped as numeric entities;
for example case ID hyphens appear as `&#45;` in Markdown source and render normally.

Report contract is `1.0.0`, fingerprint domain `trustbench-report-v1`. JSON uses sorted
keys, UTF-8, literal Unicode, LF and a final newline. The fingerprint hashes a compact
canonical ASCII JSON payload with its own digest removed. Reports omit raw recorded
responses, prompts and evaluator previews, so the English fixture application labels
remain the visible text; Greek response correctness is evidenced by the case/check
outcomes. Hashes transitively bind the original Unicode input bytes.

With current fixtures, default labels and integer limit 4300:

- Failing report: `08b2702208de2ac7caf0f38152939f4a7f907113f9e7444aa4954582c156b10e`.
- Passing report: `5d69da236056a383b4f6e1c0906cac9c6d794e0851470bb091f8cef717f8a638`.

Report/policy/gate digests are independently recomputed; run/comparison digests are
checked for repeatability and provenance linkage, not recomputed from the public
projection because it omits evaluator explanations. The complete
[report contract](report-contract.md) defines the serialization and trust boundary.

## Installed wheel and verification evidence

The existing Python 3.14 wheel environment can run the same helper without source-path
injection (the wheel must already be installed there):

```powershell
.venv-package/Scripts/python.exe -I scripts/demo.py --report-dir artifacts/demo-wheel
```

The helper intentionally accepts only the two existing project environments and must
run from this repository root; fixtures/scripts are included in the sdist, not the
runtime wheel. An installed wheel exposes the CLI independently with caller-provided
input paths. No extra environment is created by the demonstration.

Actual CLI demonstrations are distinct from the **632 current pytest tests**.
Both Python 3.12 project and Python 3.14 wheel demonstrations produced identical
report bytes and fingerprints for both decisions. Full test suites, targeted coverage,
packaging and a real debugger breakpoint are recorded in
[portfolio release verification](portfolio-release.md). [Milestone 3A](milestone-3a.md)
preserves the historical 621-test evidence before the audit and toolchain regressions.

## Limits and next decision

This demonstrates deterministic conformance, not semantic truth, hallucination
detection, live model quality or statistical significance. There is no model call,
network client, paid service, database, training, telemetry or frontend. Hashes prove
consistency, not authenticity or original execution. Use trusted small synthetic files,
non-confidential labels and local output directories; arbitrary-secret detection,
hostile-filesystem isolation, full resource limits and crash durability are not claimed.

The measured workflow has no reproduced defect blocking its documented local use.
Portability beyond the tested Windows interpreters and clean-machine bootstrap remain
verification gaps. Broader fixtures and richer diagnostics are optional improvements.
The owner selected FixtureDelta Lab and MIT after the completed audit. Active package
and command names now match that decision. The [naming review](naming.md) preserves
the earlier collision research. The Windows checkout directory stays in place.
Public GitHub publication awaits separate explicit approval; see
[release readiness](release-readiness.md).
