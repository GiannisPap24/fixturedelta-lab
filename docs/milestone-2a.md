# Milestone 2A verification

> Historical verification record using the names and tools at that checkpoint.
> For current commands, names and licence, see [README](../README.md) and
> [portfolio release verification](portfolio-release.md).

Verified locally on Windows on 2026-10-24. Scope: audit/checkpoint Milestone 1C,
then implement deterministic baseline/candidate comparison only. No gates, policy
thresholds, report exports, CLI, frontend, services, or later milestone was implemented.

## A. Milestone 1C checkpoint

- Commit: `private-checkpoint` on `main`.
- Message: `feat: add deterministic single-run evaluation and provenance`.
- Parent: `private-checkpoint` (foundation).
- Verified the exact 1C inventory: 10 modified and 3 new files. Reviewed source,
  tests, documentation, and configuration; no credentials, unexpected personal data,
  generated artifacts, environment files, or unintended source files were found.
- Verified ignore protection, repository root/branch/HEAD, empty staging area, no
  remote, and the existing approved repository-local author identity.
- Before committing: 287 offline tests passed; Ruff lint, Ruff formatting, lockfile,
  and Git whitespace checks passed.
- Staged only the reviewed 13 files. Verified the commit and clean working tree
  before any 2A implementation began. No push, publication, or remote creation.

## B. Exact 2A source inventory

Created:

1. `src/trustbench_ai/comparison_types.py` — immutable evidence, summaries, derived counts.
2. `tests/test_comparison.py` — 111 new deterministic comparison/contract tests.
3. `docs/milestone-2a.md` — this report.

Modified:

1. `src/trustbench_ai/comparison.py` — comparison engine, validation, alignment, coded errors.
2. `src/trustbench_ai/provenance.py` — comparison contract/fingerprint constants and hash helper.
3. `pyproject.toml` — adds comparison engine/types to targeted coverage.
4. `AGENTS.md` — current scope and stop-after-2A rule.
5. `README.md` — comparison example, semantics, provenance, boundaries, layout.
6. `docs/architecture.md` — comparison flow, dependencies, evidence trust boundary.
7. `docs/evaluation-contract.md` — comparison contract 1.0.0 and exact hashing/error rules.
8. `docs/roadmap.md` — completed 2A and proposed narrowly scoped 2B.
9. `docs/vscode.md` — comparison test/debug workflow and verification results.

The existing domain, dataset loaders, evaluator implementations, runner, all 287
previous tests, fixtures, `uv.lock`, and `.vscode/*` are unchanged. Verification
scripts/measurements under `artifacts/` and build outputs under `dist/` are ignored.
No new environment, repository, or workspace was created.

## C. Interface and result types

```python
from trustbench_ai.comparison import compare_runs, ComparisonError, ComparisonErrorCode

# Both arguments use the existing RunResult contract.
comparison = compare_runs(baseline, candidate)  # -> ComparisonResult
```

Types in `trustbench_ai.comparison_types`:

| Type | Contents |
| --- | --- |
| `CheckComparison` | Evaluator ID/version, both statuses and explanations; derived transition |
| `CaseComparison` | Case ID, ordered checks; derived statuses, aggregate transition, summary, check counts |
| `Transition` | Regression, improvement, unchanged pass, unchanged fail |
| `CaseSummary` | Those four values plus mixed |
| `TransitionCounts` | Four nonnegative counts and derived total |
| `RunReference` | Output-set ID/version, application version, output digest, run fingerprint |
| `ComparisonProvenance` | Explicit baseline/candidate references, shared compatibility metadata, contract version |
| `ComparisonResult` | Provenance, ordered cases, comparison fingerprint; derived totals |

All data values are frozen/slotted; nested collections are tuples. Counts and
classifications are derived rather than independently settable stored fields.
No reevaluation, input loading, input mutation, network, or model calls occur.

## D. Compatibility and alignment

The comparator revalidates exact existing run-domain types and every nested value,
including evidence made through bypassed constructors. It rejects malformed/empty
structures, duplicates, incomplete legacy provenance, and stale fingerprints.
Each run fingerprint is recomputed with the unchanged 1C encoding.

Both runs must match dataset ID/version/content hash, evaluation contract, suite,
integer conversion limit, case-ID sets, and per-case evaluator-ID/version sets.
Only evaluation contract `1.1.0` is supported. A given evaluator ID must have one
version throughout a run. Application/output labels, versions, and hashes can differ.

Roles come from argument position. Results align by IDs and preserve baseline
case/check order, which is dataset/evaluator order for runner outputs. Candidate
ordering may differ when its own fingerprint covers that order. Every pair validates
before a comparison is built. No invalid input returns partial comparisons.

Errors expose stable `ComparisonErrorCode`, optional role, and optional case ID.
Codes distinguish invalid types/structures, omitted provenance, stale fingerprints,
unsupported/mismatching contracts, dataset/suite/runtime incompatibility, duplicate
cases/evaluators, coverage mismatches, and evaluator-version incompatibility. The
[contract](evaluation-contract.md#comparison-errors) lists every code and correction.

## E. Regression, improvement, and mixed semantics

Pass→fail is a regression; fail→pass is an improvement. Equal statuses are unchanged
pass or unchanged fail. This classification applies independently to each evaluator.
Case aggregate transitions use all-checks-pass on each side.

Case summaries expose any check regression or improvement; both together produce
`mixed`. A regression within an already-failing case remains a regression summary,
even though its aggregate transition is unchanged fail. A mixed case contributes to
both `cases_with_regressions` and `cases_with_improvements`; these counts overlap.
There is no net score or quality decision.

`case_counts` counts aggregate case transitions; `check_counts` counts evaluator
transitions. Each case also has `check_counts`; `mixed_case_count` counts mixed
summaries. The original six-case fixture oracle produces:

| Unit | Regressions | Improvements | Unchanged pass | Unchanged fail | Total |
| --- | --- | --- | --- | --- | --- |
| Cases | 2 | 1 | 3 | 0 | 6 |
| Checks | 2 | 1 | 5 | 0 | 8 |

Regressions: `en-label-001`, `en-json-001`. Improvement: `el-rules-001`.
Additional tests exercise mixed outcomes using the actual content evaluator.
These are synthetic conformance results, not real-model quality measurements.

## F. Provenance and fingerprint rules

Comparison contract version: `1.0.0`; fingerprint version: `trustbench-comparison-v1`.
Shared provenance includes dataset ID/version/hash, evaluation contract, suite, and
recorded integer limit. Explicit baseline/candidate references retain output-set
ID/version, application version, output-byte hash, and run fingerprint. Paired checks
retain evaluator identities/versions and both explanations.

SHA-256 covers a canonical JSON object with `fingerprint_version`, `provenance`,
and `cases`. Encode every stored provenance and case/check field using sorted object
keys, ASCII escapes, compact comma/colon separators, non-finite values disallowed,
ASCII bytes, no BOM/final newline. Preserve baseline array order. Exclude the digest
itself and all derived properties. Contract version binds derivation semantics.
There is no timestamp, path, new host-setting read, or machine identity. The recorded
integer limit is copied from run evidence because it affects evaluation behavior.
Internal hashing is not a JSON/Markdown export feature.

The fixture comparison with labels `baseline`/`1.0.0` and `candidate`/`2.0.0`, and
integer limit 4300, has fingerprint:
`3e556c80b350085ff53c6d2ac06c2e6ee2d566334c25187a4c0ce9752049db8e`.

## G. Python compatibility

- Existing `.venv`, Python **3.12.10**: **398 tests passed**.
- Existing `.venv-package`, Python **3.14.4**: **398 installed-wheel tests passed**
  with `-I` and pytest importlib mode. Import origin independently confirmed as that
  environment's `site-packages`, not the source checkout.
- All 287 original tests preserved; 111 new comparison tests added.
- Full comparison evidence, derived case/check counts, and fingerprint matched
  exactly across both interpreters using the same fixtures and labels.
- No new interpreter/environment was created or downloaded. Other OS/interpreter
  versions were not verified.

## H. Quality and packaging verification

| Check | Result |
| --- | --- |
| Complete offline pytest suite | 398 passed |
| Targeted statement and branch coverage | **100%**, 560 statements, 154 branches, zero misses |
| Comparison engine coverage | 97 statements, 44 branches, zero misses |
| Comparison value types coverage | 148 statements, 24 branches, zero misses |
| Coverage scope | Loaders, evaluators, runner, provenance, comparison engine/types; not whole-package |
| Ruff lint and formatting | Passed; 30 Python files formatted at verification |
| Offline lock check | Passed; 9 resolved packages; lockfile unchanged |
| Dependency compatibility | `uv pip check` passed in both existing environments |
| Runtime/development dependencies | None added; runtime dependencies remain empty |
| Source distribution and wheel | Built offline; wheel built from sdist |
| Git whitespace check | Passed |

Tests cover all transitions, identical runs with legitimate failures, actual mixed
content checks, simultaneous improvements/regressions, Greek/English evidence,
compatibility failures, duplicates and bypassed constructors, empty/malformed nested
results, late-case failure without partial success, input/result immutability, ID
alignment/order, metadata/explanation/hash sensitivity, independent hash oracle,
per-case/total counts, and no I/O/reevaluation. The socket/DNS test guard remains active.

## I. VS Code readiness

Configured pytest discovery found 398 tests including all 111 comparison tests.
Every executable saved task command passed. Existing debug target arguments passed:
123 evaluator tests and 111 comparison tests using the current-file configuration.
The installed debug adapter stopped at a real breakpoint at `comparison.py:145`,
returned the expected stack frame, resumed, and exited successfully.

This used the existing configuration via stdio/internal console. Interactive F5
terminal routing/task-menu clicks were not automated. Saved configurations remain
unchanged. The extension CLI confirmed Python, Python Debugger, Ruff, and official
`openai.chatgpt@26.1021.22027`. No extension/global-setting changes or live Codex
inference/authentication verification occurred.

## J. Remaining limitations

- Run fingerprints establish consistency, not execution authenticity. With only two
  run objects, the comparator cannot independently verify original dataset coverage,
  ordering, or hashes against source bytes. Identically truncated, manually rebuilt
  and rehashed runs cannot be detected. Use trusted runner outputs.
- Only evaluation contract 1.1.0 is supported; no migration or report import exists.
- Manually replacing comparison values does not recompute their fingerprint.
- Exact-byte source formatting/reordering changes run and comparison identities even
  when paired outcomes are unchanged. Explanation-only changes affect fingerprints
  but do not create a status regression.
- Small local synthetic evidence only; no quality claims, category/language slices,
  static type-checking claim, multi-OS matrix, or comprehensive hostile-data hardening.
- Counts have distinct meanings: aggregate case transitions alone cannot reveal every
  evaluator regression. Mixed summaries/check counts must remain visible in future gates.

## K. Final Git status and next scope

`main` remains at `private-checkpoint` with two local commits.
2A has **9 modified tracked files and 3 new untracked source/documentation files**,
exactly section B, all unstaged and uncommitted. Generated verification/build outputs
remain ignored. No remote exists and no push/publication was performed.

Recommended **2B only**: pure quality-gate decisions over validated comparison evidence,
with explicitly specified versioned policies and thresholds, fingerprint verification,
exact boundary tests, and immutable explanations. Define treatment of mixed cases and
regressions inside already-failing cases so improvements cannot hide them. Keep invalid
evidence distinct from a valid failed gate. Defer CLI, exports, dashboards, services,
and publication. Stop after 2A; this report does not authorize or implement 2B.
