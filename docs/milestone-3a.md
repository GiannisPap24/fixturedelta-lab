# Milestone 3A verification

> Historical verification record using the names and tools at that checkpoint.
> For current commands, names and licence, see [README](../README.md) and
> [portfolio release verification](portfolio-release.md).

Verified locally on Windows on 2026-10-24. Scope: audit/checkpoint 2C, demonstrate the
existing application end to end, and prepare portfolio documentation. No new runtime
feature/evaluator, environment, external integration, rename or publication.

## A. Milestone 2C checkpoint

- Branch: `main`.
- Commit: **`private-checkpoint`**.
- Message: `feat: add TrustBench CLI and deterministic reports`.
- Parent: `private-checkpoint` (2B checkpoint).
- Read project instructions, README, 2C verification, roadmap, evaluation/gate/report
  contracts; inspected actual CLI, runner, comparison, gates, reporting and policy parser.
- Audited exactly 12 modified and 8 new 2C files. Verified identity, branch/HEAD,
  unstaged/untracked inventory, no remote, ignore guards and no unexpected artifacts.
  Credential review found only intentional synthetic negative-test token markers;
  no real credentials, private-key payloads or private data were identified.
- Before staging: 621 offline tests, Ruff lint/format, offline lock and Git whitespace
  checks passed. Used the approved repository-local GitHub noreply identity.
- Staged only the audited 20 files, committed locally, then verified the commit,
  parent and clean tree **before starting 3A**. No push or remote creation occurred.

## B. Exact created and modified files

Created (4):

1. `scripts/demo.ps1` — project/environment guard, offline lock check, locked invocation,
   sanitized summary and demonstration exit handling.
2. `scripts/demo.py` — real console/module subprocess scenarios, report/hash/byte checks,
   input preservation, safe output guard and verification manifest.
3. `docs/demo.md` — portfolio guide with commands, outcomes, report examples and limits.
4. `docs/milestone-3a.md` — this A–L completion report.

Modified (7):

1. `.vscode/tasks.json` — prompted verified demo task, expected outer exit 0.
2. `AGENTS.md` — 3A scope, stop boundary and uncommitted-work instruction.
3. `README.md` — recruiter-facing problem statement and quick demonstration.
4. `docs/gate-contract.md` — correct stale wording about the existing policy JSON parser.
5. `docs/roadmap.md` — completed 3A and proposed Final MVP Audit scope.
6. `docs/vscode.md` — new task usage and distinction from the direct CLI task.
7. `pyproject.toml` — include `scripts/**` in the source distribution.

All application source files, all 621 tests, released fixtures, `uv.lock`, `.gitignore`,
VS Code settings/launch configurations and extension recommendations are unchanged.
No runtime or development dependency was added. Generated reports, variants, helper
measurements and verification files are ignored under `artifacts/`; distributions
remain under ignored `dist/`. The two existing Python environments were reused.

## C. Actual failing-gate demonstration

The existing dataset and baseline/candidate-v2 files were evaluated by real CLI
processes. Default strict policy, no threshold relaxation:

```text
Gate FAIL | cases=6 checks=8 regressions=2 improvements=1 candidate_failures=2
```

- Exactly two regressions: `en-label-001` / `exact-match` and `en-json-001` / `json-object`.
- Exactly one improvement: `el-rules-001` / `required-content`.
- 3 unchanged passing cases; 5 unchanged passing checks; 6/8 candidate checks pass.
- `max-regressions`: observed 2, permitted 0, FAIL. The improvement cancels neither.
- **CLI exit 1**, with a complete valid JSON/Markdown pair: expected rejection,
  not an execution error.
- Report SHA-256:
  `08b2702208de2ac7caf0f38152939f4a7f907113f9e7444aa4954582c156b10e`.

## D. Actual passing-gate demonstration

The same baseline file was supplied in both roles, using default strict policy:

```text
Gate PASS | cases=6 checks=8 regressions=0 improvements=0 candidate_failures=1
```

- Zero regressions and improvements; 5 unchanged passing cases, 1 unchanged failing case.
- 7 unchanged passing checks, 1 unchanged failing check; 7/8 candidate checks pass.
- `max-regressions`: observed 0, permitted 0, PASS.
- **CLI exit 0**, with complete deterministic JSON/Markdown reports.
- Report SHA-256:
  `5d69da236056a383b4f6e1c0906cac9c6d794e0851470bb091f8cef717f8a638`.

The unchanged failure is deliberate and documented: a regression-only gate does not
require an all-pass candidate. Neither original fixture was modified to manufacture
this result. Baseline/candidate are output-set role labels, both version `1.0.0`;
the application label in both references is `synthetic-baseline-v1`.

## E. Reports and determinism

Actual demonstrations ran in the Python 3.12 project environment and Python 3.14
installed-wheel environment. Each launched both the installed console and isolated
module entry point from its selected artifact directory, removing inherited Python
environment overrides. The 3.14 import probe confirmed `site-packages`, without local
source-path injection.

Final generated examples:

- `artifacts/demo-3a-final/fail-console/reports/report.json` and `report.md`.
- `artifacts/demo-3a-final/pass-console/reports/report.json` and `report.md`.
- Matching `fail-module` and `pass-module` directories in the same destination.
- `artifacts/demo-3a-final/verification.json` and generated invalid variants in `inputs/`.
- Matching installed-wheel results under `artifacts/demo-3a-wheel-final/`.

All four report pairs and the manifest matched byte for byte across environments;
repeated fresh destinations also matched. No report contains timestamps, machine
paths, raw responses or evaluator text previews. Input hashes/bytes are unchanged.
Greek exact-match and JSON checks pass; the Greek required-content improvement is
preserved. Text is not normalized, and raw Greek responses remain intentionally omitted
from public reports. Existing tests verify arbitrary safe Unicode labels and escaping.

The demo independently recomputes report/policy/gate canonical digests, verifies
dataset/output hashes, labels/versions, evaluator order, exact counts, rule observations,
affected regressions and Markdown provenance. Run/comparison digests are checked for
linkage and repeatability; their omitted explanations prevent rehashing them from
public reports alone. The existing contracts and fingerprint encodings are unchanged.

The selected output must be a fresh child of the project's ignored `artifacts/` tree.
Scenario outputs remain inside it; existing targets are never overwritten or recursively
deleted. Each application's pair still uses its existing atomic publication contract.
The helper stages and closes its verification manifest before renaming it into place.

## F. Exit codes and safety checks

| Actual scenario | CLI exit | Observed result |
| --- | --- | --- |
| Valid regression candidate | 1 | Full failed-gate reports; expected demonstration outcome |
| Baseline versus identical baseline | 0 | Full passing-gate reports |
| Malformed synthetic JSON | 2 | Sanitized error, no output directory |
| Incompatible dataset version | 2 | Sanitized error, no output directory |
| Occupied report destination | 3 | Sanitized output error; existing report bytes preserved |

Every helper execution invokes seven real CLI subprocesses: two entries per valid
scenario plus the three error cases. No unexpected traceback or success summary
appeared for invalid/output errors. Recorded data passes only through the existing
strict parsers/evaluators and is never executed as code; existing inert-code tests remain
unchanged. Safe invalid variants are generated locally without editing released fixtures.

The PowerShell wrapper and Python verifier return **0 only for a verified demo**;
their own failed preconditions/invariants return 1. Direct guard checks verified safe
refusal for an existing destination, an outside-artifacts destination, incorrect working
directory, invalid helper arguments, and the corresponding PowerShell wrong-directory/
occupied cases. Existing report snapshots were preserved. These are actual demo/guard
checks, not added pytest cases or inflated test counts.

## G. Python test results

| Environment | Full unchanged offline suite |
| --- | --- |
| Existing `.venv`, Python 3.12.10 | **621 passed** |
| Existing `.venv-package`, Python 3.14.4 installed wheel | **621 passed** |

No tests were removed, weakened or added. Pytest retains socket/DNS guards, including
the existing guarded CLI subprocess tests. Actual demo processes use the offline
implementation and no networking client; neither mechanism is an OS network sandbox.
The source distribution includes the repository demonstration; the runtime wheel
exposes the existing CLI and does not bundle repository fixtures/scripts.

## H. Coverage, Ruff, lock and packaging

| Verification | Result |
| --- | --- |
| Existing targeted application coverage | **100%**, 933 statements, 258 branches, zero misses |
| Separate demonstration-helper coverage | **98% combined**; 151/154 statements, 19/20 branches |
| Ruff lint and format | Passed |
| Offline lock | Passed, 9 packages; lockfile unchanged |
| Dependency compatibility | Passed in both existing environments |
| Source distribution / wheel | Built offline, including wheel from sdist |
| Distribution contents | Application source and console entry point verified; sdist contains both demo scripts and guide |
| Installed CLI | Console and module scenarios verified; wheel import origin confirmed |
| Git whitespace | Passed |

Application coverage is the existing configured module scope, not whole-package
coverage. The separate helper measurement covers real successful demonstrations and
refusal paths, not all exception simulation: the unexercised generic unexpected-error
fallback and import-only branch are reported honestly. No PowerShell coverage percentage
is claimed. No artificial tests were added to force these measurements to 100%.

## I. VS Code task and debugger

- Added **TrustBench: verified end-to-end demo (expected exit 0)** with a new-directory
  prompt; its exact command ran successfully via Windows PowerShell **5.1.26100.9711**.
  The wrapper also ran in PowerShell **7.6.5**. No execution policy was changed.
- The original direct CLI task still returns expected exit 1. All saved executable
  tasks ran with their expected codes; aggregate Ruff dependency order was verified.
- The configured `.venv` discovered/executed all 621 tests. Existing launch argument
  lists passed 123 evaluator tests, 35 CLI tests, and the direct CLI scenario.
- The installed debug adapter stopped at **`cli.py:79`**, returned the expected stack
  frame, resumed, published both reports and exited 1.
- Debug verification used stdio/internal console. Saved launches still use integrated
  terminal; interactive menu/prompt clicks and F5 terminal routing were not automated.
- Extension CLI confirmed official `openai.chatgpt@26.1021.22027`, Python 2026.10.0,
  Python Debugger 2026.6.0 and Ruff 2026.90.0. No global settings/extensions were changed;
  live Codex inference/authentication was not retested. No autorun service was added.

## J. Remaining defects, limitations and naming

No reproduced technical defect blocks the documented local synthetic MVP workflow.
One stale policy-parser documentation claim was corrected; application behavior was
unchanged. This scoped demo review is not a comprehensive Final MVP Audit.

| Category | Remaining consideration |
| --- | --- |
| Public release decisions | Provisional name has documented collisions; owner must select/confirm a public name and license before publication |
| Verification gaps | Fresh-machine cached bootstrap and OS/interpreter portability beyond the tested Windows pair |
| Documented trust boundary | Trusted small synthetic files, limited metadata secret screening, no authenticity/complete-coverage attestation |
| Filesystem/terminal limits | No fsync durability/network-filesystem guarantee or hostile-parent defense; crashes/failed cleanup can leave remnants; terminal failure may follow successful publication |
| Optional improvements | Broader synthetic fixtures, bounded input sizes, clearer diagnostics, eventual portability checks; none added automatically |
| Meaning of results | Literal/structure conformance and policy decisions, never truth/hallucination detection/live model quality |

The existing naming review records TrustBench collisions and GoldenDiff Lab as a
historical shortlist candidate. This milestone makes no fresh availability or legal
claim, performs no naming network search and renames no directory/package. Naming and
licensing are public-release gates, not defects in the local demo.

## K. Git status

`main` remains at **`private-checkpoint`**, with five local
checkpoint commits. The **7 modified and 4 new files** in section B are intentionally
unstaged/uncommitted. No remote, push, public repository, publication or changes to
other projects. All demonstration outputs, measurements and environments remain ignored.

## L. Recommended smallest Final MVP Audit

Separately authorize one focused review of the existing product:

1. Reproduce the documented setup/demo and isolated installed-package path; identify
   any environment or portability gap needed for the intended local audience.
2. Check contract/exit semantics, exact report provenance/determinism and input/output
   safety against the current implementation; fix only reproduced blocking defects.
3. Verify tests, lock/dependencies, source/wheel contents, docs and repository hygiene.
4. Record owner decisions on name/license and the conditions for any later publication.
5. Deliver an evidence-based go/no-go plus a short optional backlog; do not add metrics,
   services, CI, telemetry, a frontend or publication implicitly.

This is a recommendation only. The Final MVP Audit, rename, release preparation and
GitHub publication were **not started**. Stop after completed Milestone 3A.
