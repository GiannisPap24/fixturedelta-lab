# Milestone 1C verification

> Historical verification record using the names and tools at that checkpoint.
> For current commands, names and licence, see [README](../README.md) and
> [portfolio release verification](portfolio-release.md).

Verified locally on Windows on 2026-10-24. Scope: initial foundation checkpoint,
single-run evaluation orchestration, and reproducible provenance. No later milestone
was implemented.

## A. Foundation checkpoint

- Commit: `private-checkpoint` on `main`.
- Message: `feat: establish deterministic AI evaluation foundation`.
- Approved author identity configured only in this repository.
- All 38 foundation files were reviewed for secrets, personal data, caches,
  environments, generated artifacts, and unintended files. No credential findings.
- Ignore checks covered `.env`, `.env.local`, both environment patterns, artifacts,
  distributions, Python caches, pytest caches, and Ruff caches.
- Foundation verification before committing: 186 tests passed; Ruff lint/format and
  offline lock checks passed. The commit contained no 1C changes.
- The initial commit and clean working tree were verified before beginning 1C.
  No remote exists; no GitHub repository, publication, or push was created.

## B. Exact 1C project files

Created:

1. `src/trustbench_ai/provenance.py` — version constants and canonical fingerprint helpers.
2. `tests/test_runner.py` — 101 offline integration and provenance tests.
3. `docs/milestone-1c.md` — this report.

Modified:

1. `src/trustbench_ai/runner.py` — replaces placeholder with snapshot/file runner and coded errors.
2. `src/trustbench_ai/datasets.py` — shared strict byte parsers, single-read file wrappers,
   and conversion/recursion error translation.
3. `src/trustbench_ai/domain.py` — additive, keyword-only provenance and result digest fields.
4. `pyproject.toml` — extends targeted coverage and updates ignored coverage output paths.
5. `AGENTS.md` — current scope and stopping point.
6. `README.md` — single-run example, provenance, scope, and module layout.
7. `docs/architecture.md` — implemented boundaries, data flow, and reproducibility decisions.
8. `docs/evaluation-contract.md` — contract 1.1.0, hashing, interface, errors, compatibility.
9. `docs/roadmap.md` — completed 1C and narrow 2A comparison proposal.
10. `docs/vscode.md` — runner debugging, coverage, and verification record.

Existing evaluators, all original tests, all fixtures, `uv.lock`, and `.vscode/*`
are unchanged from the checkpoint. Comparison, reporting, and CLI remain placeholders.
Ignored verification scripts, measurements, and build outputs remain under
`artifacts/` and `dist/`; neither environment is a source change.

## C. Runner interface

```python
from trustbench_ai.runner import evaluate_run, run_evaluation, RunError, RunErrorCode

run_evaluation(dataset_path: Path, outputs_path: Path, *,
               output_set_id: str, output_set_version: str) -> RunResult
evaluate_run(dataset_bytes: bytes, outputs_bytes: bytes, *,
             output_set_id: str, output_set_version: str) -> RunResult
```

The file wrapper reads each file once and passes those immutable snapshots to the
byte interface. Output-set ID/version are required caller assertions because the
unchanged schema-v1 documents do not contain them. Candidate/application version is
read from the output file. The README contains an executable fixture example.

## D. Evaluation and provenance semantics

Both inputs must fully validate and align before evaluation starts. Dataset ID/version
and exact unique case coverage must match. Outputs are joined by ID; results follow
dataset order. The runner calls the existing `evaluate_case` adapter and validates
its returned case/check IDs, check order, and evaluator versions. Every successful
return contains a complete immutable run. Failed checks remain legitimate evidence;
invalid inputs and evaluator crashes produce coded errors with no partial results.

Provenance records dataset ID/version and raw SHA-256, raw output SHA-256, supplied
output-set ID/version, candidate version, suite version, evaluation contract version,
and Python integer conversion limit. Each check retains its evaluator ID/version.
Contract version is `1.1.0`; schema stays integer `1`; suite/evaluators stay `1.0.0`.
The additive fields preserve existing domain constructor calls. Legacy manually
constructed values may omit them and do not establish complete runner evidence.

Input digests hash the exact bytes parsed. Result digests hash canonical ASCII JSON
of `fingerprint_version`, all provenance fields, and ordered case/check fields,
including explanations. Encoding uses sorted object keys, compact separators,
ASCII escapes, no non-finite numbers, and no final newline. Fingerprint version is
`trustbench-run-v1`; the digest itself and derived case status are excluded. The
[evaluation contract](evaluation-contract.md#fingerprints) specifies the full encoding.
No timestamps, local paths, machine usernames, token counts, cost, or latency are added.

Stable error codes: `DATASET_READ_ERROR`, `OUTPUTS_READ_ERROR`, `DATASET_INVALID`,
`OUTPUTS_INVALID`, `ALIGNMENT_INVALID`, `PROVENANCE_INVALID`, `EVALUATOR_ERROR`,
`RESULT_INVALID`. Causes remain available for debugging; evaluator errors identify
the affected case. User interrupts are allowed to propagate.

## E. Verification results

| Check | Result |
| --- | --- |
| Complete offline pytest suite | **287 passed**: original 186 plus 101 new runner tests |
| Existing tests preserved | 40 dataset + 23 domain + 123 evaluator tests unchanged |
| Targeted statement/branch coverage | **100%**, 308 statements and 86 branches, zero misses |
| Coverage scope | `datasets`, `metrics`, `provenance`, `runner`; not a whole-package claim |
| Ruff lint | Passed |
| Ruff format check | Passed, 27 Python files formatted |
| `uv lock --check --offline` | Passed; 9 resolved packages; lockfile unchanged |
| `uv pip check` | Passed in both existing environments |
| Runtime dependencies | None; no dependencies added |
| `uv build --offline` | Source distribution and wheel built; wheel built from sdist |
| Distribution contents | Runner, provenance, and typing marker in wheel; tests/docs in sdist; no environments/caches/artifacts |
| Git whitespace check | `git diff --check` passed |

Tests cover all evaluator families, single/multiple cases, mixed Greek/English,
non-normalization, dataset/output ordering, duplicates, missing/extra identities,
version/schema mismatches, invalid configurations, malformed/deep input, read failures,
passing/failing checks together, immutability, repeatability, hash sensitivity and
independent hash oracles, file replacement after a read, evaluator crashes mid-run,
inconsistent adapter returns, and retry after failure. The existing socket/DNS test
guard remains enabled. No external LLM or paid API calls were made.

## F. Python compatibility

- Existing `.venv`: Python **3.12.10**, 287 tests passed with editable source.
- Existing `.venv-package`: Python **3.14.4**, 287 tests passed against the reinstalled
  wheel using `-I` and pytest importlib mode. Import origin was independently checked
  to be that environment's `site-packages`, not `src/`.
- Full baseline run equality was verified across both interpreters with the same
  bytes, output labels, and default integer limit of 4300.
- Baseline result digest with ID `synthetic-baseline` and version `1.0.0`:
  `e858e67db4a8bde10009b0220555aa17b76d45d43af5d34f67f76d5383fd016b`.
- No interpreter download, new environment, or second repository was created.
  Other Python versions and operating systems were not verified.

## G. VS Code

The existing workspace configuration remains unchanged. Discovery using its selected
interpreter and configured pytest arguments found all 287 tests, including 101 runner
tests. Every executable task's exact command passed. The existing evaluator debug
target passed 123 tests; the current-file target passed all 101 runner tests.

The installed debug adapter launched the runner suite, stopped at an actual breakpoint
in `runner.py:76`, returned the expected stack frame, resumed, and exited successfully.
Verification used stdio/internal console; saved configurations retain integrated-terminal
routing. Interactive task-menu/F5 clicks were not automated.

The extension CLI still lists official `openai.chatgpt@26.1021.22027`, Python, Python
Debugger, and Ruff. No extension or global/editor settings were changed. The earlier
1B sidebar/UI observation remains historical; live Codex inference/authentication
was not retested or needed for 1C.

## H. Limitations and risks

- Six synthetic cases establish harness behavior, not real model quality or truth.
- Output-set labels are caller assertions. Hashes establish byte identity, not
  authenticity; formatting-only edits intentionally produce different fingerprints.
- Manual dataclass construction/replacement validates shape, not fingerprint
  correctness or proof of execution. Future comparison must validate complete evidence.
- Files are captured sequentially, not as one atomic filesystem transaction. Inputs
  and interpreter settings should remain stable during a run. Raw snapshots are kept
  in memory; comprehensive size limits, streaming, and untrusted-input hardening are
  not implemented.
- Stricter host integer limits can affect the existing JSON evaluator, so that setting
  is recorded. No interpreter limits are changed by production code.
- Chained diagnostic exceptions can contain paths/input details. Synthetic labels
  and source statements are required; this is not a secret-redaction system.
- No comparisons, quality gates, exported evaluation reports, CLI, CI matrix, deployment,
  or publication. Internal fingerprint JSON is not a public report serialization format.

## I. Git status

`main` still points to the initial foundation commit. All 1C work is intentionally
uncommitted and unstaged: **10 modified tracked files and 3 new untracked project
files**, exactly those listed in section B. Generated artifacts and environments are
ignored. No remote exists and no push was performed.

## J. Recommended Milestone 2A

Implement only pure baseline/candidate regression comparison over complete immutable
runs. Validate fingerprints and matching dataset identity/version/hash, contract/suite
versions, integer limits, case coverage, and evaluator IDs/versions. Join by stable
IDs; classify case and check transitions, including regressions in already-failing
cases. Verify the fixture oracle of two case regressions and one improvement. Return
typed immutable comparison data and deterministic counts. Defer gates, report exports,
CLI, category/language slices, external services, and publication to separate requests.
