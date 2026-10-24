# Milestone 2C verification

> Historical verification record using the names and tools at that checkpoint.
> For current commands, names and licence, see [README](../README.md) and
> [portfolio release verification](portfolio-release.md).

Verified locally on Windows on 2026-10-24. Scope: audited local 2B checkpoint,
then a minimal offline CLI and deterministic JSON/Markdown reports. Stop after 2C.
No release preparation, remote, deployment, model API, telemetry or publication.

## A. Milestone 2B checkpoint

- Branch: `main`.
- Commit: **`private-checkpoint`**.
- Message: `feat: add deterministic AI quality gates`.
- Parent: `private-checkpoint` (2A checkpoint).
- Audited exactly the expected 8 modified and 5 new 2B files, contracts, implementation,
  fixture protection and ignore rules. No unexpected artifacts, credentials or private
  data were found in the reviewed checkpoint candidates.
- Verified existing approved repository-local Git identity, branch/HEAD, staging state,
  untracked inventory and absence of remotes. No global Git settings were changed.
- Before committing: all **529** existing tests, Ruff lint/format, offline lock check
  and Git whitespace checks passed. Staged only the reviewed 13 files.
- Verified the checkpoint and a clean tree **before starting 2C**. No push occurred.

## B. Exact Milestone 2C inventory

Created (8):

1. `src/trustbench_ai/__main__.py` — module entry point.
2. `src/trustbench_ai/policies.py` — strict schema-v1 policy JSON parser.
3. `tests/test_cli.py` — 35 CLI/workflow/process tests.
4. `tests/test_policies.py` — 37 policy parsing tests.
5. `tests/test_reporting.py` — 20 report/rendering/publication tests.
6. `tests/fixtures/policy-allow-v1.json` — explicit synthetic passing-policy example.
7. `docs/report-contract.md` — CLI, policy/report schemas, hashing and output boundaries.
8. `docs/milestone-2c.md` — this A–L completion report.

Modified (12):

1. `src/trustbench_ai/cli.py` — replace placeholder with argparse orchestration/errors.
2. `src/trustbench_ai/reporting.py` — replace placeholder with deterministic report pair.
3. `pyproject.toml` — console script and expanded targeted coverage; no dependency changes.
4. `.vscode/tasks.json` — prompted synthetic CLI demo, expected exit 1.
5. `.vscode/launch.json` — CLI debug target with arguments and new-directory prompt.
6. `AGENTS.md` — authorized 2C scope and stop/uncommitted boundary.
7. `README.md` — commands, exits, output paths and current status.
8. `docs/architecture.md` — implemented CLI/report flow and publication boundary.
9. `docs/evaluation-contract.md` — current adapter references and corrected exit mapping.
10. `docs/gate-contract.md` — current adapter reference; pure gate semantics unchanged.
11. `docs/roadmap.md` — completed 2C, separately authorized next review.
12. `docs/vscode.md` — CLI task/debug usage and verified results.

All 529 previous tests and their fixtures are unchanged. Existing evaluator, loader,
runner, comparison, gate and fingerprint implementations/types are unchanged.
`uv.lock`, `.gitignore`, workspace settings and extension recommendations are unchanged.
Generated reports, verification helpers and measurements under `artifacts/`, builds
under `dist/`, and the two existing environments remain ignored. No new environment,
repository or copy of the project was created.

## C. CLI interface and commands

Primary entry points: `trustbench check` and `python -m trustbench_ai check`.
Required: `--dataset`, `--baseline`, `--candidate`, `--report-dir`.
Optional: `--policy`, output-set `--baseline-id`/`--candidate-id`, and respective
`--baseline-version`/`--candidate-version`. The defaults label sets `baseline` and
`candidate`, both `1.0.0`; application versions are read from the recorded files.

```powershell
uv run --locked --offline trustbench check --dataset tests/fixtures/golden-v1.0.0.json --baseline tests/fixtures/baseline-v1.json --candidate tests/fixtures/candidate-v2.json --report-dir artifacts/check-strict-01
uv run --locked --offline trustbench check --dataset tests/fixtures/golden-v1.0.0.json --baseline tests/fixtures/baseline-v1.json --candidate tests/fixtures/candidate-v2.json --policy tests/fixtures/policy-allow-v1.json --report-dir artifacts/check-allowed-01
uv run --locked --offline python -m trustbench_ai check --help
```

Use a fresh output directory per run. No overwrite flag exists. Both commands connect
the original evaluator/runner/comparison/gate APIs; no scoring logic is duplicated.
The dataset snapshot is shared by both evaluations. Inputs are never modified.

## D. JSON and Markdown contracts

Report contract **1.0.0**, fingerprint version **trustbench-report-v1**. JSON records
shared dataset/evaluator/runtime contracts, baseline/candidate references and hashes,
ordered case/check statuses, aggregate/check transition counts, mixed-case evidence,
normalized policy and fingerprint, independent rule outcomes, affected identities,
overall decision and report digest. Every check is retained.

Public JSON uses sorted object keys, two-space indentation, literal Unicode, UTF-8
without BOM, LF and a final newline. Markdown summarizes outcomes, all transitions,
rules/explanations, raw candidate check counts and provenance. Dynamic punctuation
and controls are numeric entities, preserving Greek while preventing Markdown/HTML
structure injection. Both omit raw outputs, prompts, source statements and evaluator
text previews. See [full contract and examples](report-contract.md).

Publication reserves a new directory, stages both files in `.pending/`, closes them,
then renames the pair to `reports/`. Existing targets are refused, including empty
directories. Output paths are `<report-dir>/reports/report.json` and `report.md`.
Write/rename failures never produce a success summary; tested rollback touches only
known owned paths. Cleanup failure may leave staging remnants, never a published pair.

## E. Exit behavior

| Exit | Meaning |
| --- | --- |
| 0 | Valid gate passes; complete report pair published (also normal help without reports) |
| 1 | Valid gate fails; complete report pair published |
| 2 | Invalid usage, missing/non-file input, malformed policy/data/metadata or incompatible evidence |
| 3 | Runtime/evaluator/file-access failure or failed output publication, including existing targets |

Expected errors contain fixed actionable codes/messages, no raw exception text or
tracebacks. Directory input is classified as invalid on Windows too. Both all-pass
configured policy and strict seeded failure were verified in-process, as subprocesses
and through the installed console. Actual console tests also verified codes 2/3/help.
Improvements do not cancel unrelated regressions. This supersedes the historical 2B
proposal to group I/O failures under exit 2.

## F. Deterministic provenance

The report digest hashes its entire JSON payload except `report_sha256`, using sorted,
compact ASCII JSON, no trailing newline, UTF-8 and SHA-256. A separate independent
test recomputes it. It includes the fingerprint-version field and binds all exported
provenance, policy, counts and outcomes; it is not a digest of Markdown bytes.
Fractions use reduced integer numerator/denominator pairs. The original upstream
fingerprint encodings remain unchanged and bind the omitted response evidence.

Identical source bytes, labels, supported evaluator/contracts, normalized policy and
recorded integer limit produce identical report bytes. Input/output paths and clocks
do not enter the report. Moving inputs preserves bytes; source formatting edits affect
the exact-byte hashes. Strict and permissive report pairs matched byte for byte across
Python 3.12/3.14. Hash consistency is not authenticity, proof of coverage or truth.

## G. Python test results

| Existing environment | Result |
| --- | --- |
| `.venv`, Python 3.12.10 | **621 passed** |
| `.venv-package`, Python 3.14.4, installed wheel | **621 passed** |

92 new tests preserve all 529 original tests. Coverage includes all three evaluator
families, Greek/English, exact counts, mixed cases, policy independence, missing and
duplicate IDs, dataset/evaluator-version mismatches, stable bytes/hash oracle,
Markdown injection, confidential preview exclusion, inert recorded code, input
immutability, exclusive outputs and simulated staging/write/rename/cleanup failures.

Existing socket/DNS guards remain active. Guarded CLI subprocess tests install their
own guard before importing the application; true module/console invocations also
verify the offline implementation. This is not an OS network sandbox. No model API
or external network request was used. Wheel tests run with `-I` and importlib mode;
an isolated import probe confirmed the 3.14 `site-packages` origin.

## H. Quality and packaging

| Check | Result |
| --- | --- |
| Targeted statement/branch coverage | **100%**, 933 statements, 258 branches, zero misses |
| CLI | 72 statements, 6 branches; zero misses |
| Policy parser | 20 statements, 6 branches; zero misses |
| Reports | 76 statements, 26 branches; zero misses |
| Ruff lint/format | Passed (43 files checked by formatter) |
| Offline lock check | Passed; 9 packages, lock unchanged |
| Installed dependency compatibility | Passed in both existing environments |
| Runtime dependencies | None; no dependency additions |
| Build | Source distribution and wheel built offline; wheel built from sdist |
| Installed console | Isolated working directory, no PYTHONPATH/source injection; exits 0/1/2/3/help verified |
| Git whitespace | Passed |

Coverage targets the existing evaluation/comparison/gate modules plus policy parser,
CLI and reports; this is not a whole-package coverage claim. Local distributions use
the existing provisional name/version and private publication classifier. No release
version bump, remote upload, CI or release preparation occurred.

## I. VS Code verification

The existing `.venv`, settings, pytest discovery and Ruff integration were retained.
Configured discovery found all 621 tests. Every saved executable task command returned
its expected status; the new demo's valid gate failure is exit 1, all quality/test/lock
tasks exit 0. The aggregate Ruff task's dependency order was checked. All three debug
argument lists ran: 123 evaluator tests, 35 CLI tests, and the synthetic CLI workflow.

The installed Python Debugger adapter stopped at **`cli.py:79`**, on the call to
`compare_runs`, returned the expected stack frame, continued, published the pair and
exited 1. Verification used stdio/internal console. Saved launches use integrated
terminal; interactive menu/prompt clicks and F5 terminal routing were not automated.
No auto-run services were added.

The extension CLI confirmed official `openai.chatgpt@26.1021.22027`, Python 2026.10.0,
Python Debugger 2026.6.0 and Ruff 2026.90.0. No extensions/global settings changed.
Live Codex inference/authentication was not retested; earlier workspace integration
is preserved. No browser/frontend task was required.

## J. Synthetic example

```text
Gate FAIL | cases=6 checks=8 regressions=2 improvements=1 candidate_failures=2
Reports published: reports/report.json and reports/report.md
Report SHA-256: 08b2702208de2ac7caf0f38152939f4a7f907113f9e7444aa4954582c156b10e
```

Regressions: `en-label-001` exact match and `en-json-001` JSON structure.
Improvement: `el-rules-001` required-content check. Three aggregate cases and five
checks remain passing. Candidate passes 6/8 checks. Strict policy fails, exit 1.

The explicit example policy permits 2 regressions, 2 failures and minimum rate 3/4;
all three rules pass, exit 0. Its report SHA-256 is
`c45bc33bc931f3aa535889109f677637b2bcaa9ba75ceacaec077aaccc092053`.
These digests use default output-set labels/versions and recorded integer limit 4300.
They describe handwritten synthetic fixtures, not measured AI model performance.

## K. Limitations and security considerations

- Synthetic literal/structure conformance only; no truth, hallucination, safety,
  statistical significance or live-model benchmarking claims.
- Raw output/prompts/source/evaluator previews are omitted. Exported metadata is
  screened for recognizable paths/credentials and invalid surrogates. This is limited
  detection, not a guarantee that arbitrary caller-authored text contains no secret.
  Use non-confidential labels; hashes also reveal equality of source artifacts.
- Report fingerprints establish internal consistency, not execution/authenticity or
  independent dataset completeness. The CLI builds evidence through trusted APIs;
  public rendering still assumes trusted comparison construction.
- Counts are check-level and unweighted. No new algorithms, slicing, remote inputs,
  model judges, schema-import framework or report re-import validator was added.
- Input files are fully read, sequentially. No new broad resource caps, static type
  checker, hostile-input sandbox or multi-OS test matrix is claimed.
- Exclusive publication assumes trusted local parent directories. It is not a
  network-filesystem transaction, fsync durability guarantee or defense against
  hostile concurrent filesystem changes. Crashes/failed cleanup can leave `.pending`
  or empty parents. Existing targets remain protected and require a fresh directory.
- Filesystem and stdout cannot commit atomically: terminal failure after publication
  may leave a complete pair while reporting a runtime error. An unusable stderr may
  prevent diagnostics. No partial report pair is advertised as successful.
- `artifacts/` is ignored; callers choosing another location manage its ignore policy.
  Fresh offline setup still needs cached tooling. Name/license decisions remain open.

## L. Git state and next milestone

`main` remains at **`private-checkpoint`** with four local
checkpoint commits. The **12 modified and 8 new 2C files** above are intentionally
unstaged and uncommitted. No remote, push, publication or changes to other projects.

Recommended next request: a separately scoped release-readiness review covering
portability/bootstrap, broader synthetic coverage, resource limits, confidentiality,
documentation and owner-selected naming/licensing. That review and any later feature
or release work were **not started**. Stop after this completed 2C implementation.
