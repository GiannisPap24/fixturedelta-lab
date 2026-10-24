# Milestone 2B verification

> Historical verification record using the names and tools at that checkpoint.
> For current commands, names and licence, see [README](../README.md) and
> [portfolio release verification](portfolio-release.md).

Verified locally on Windows on 2026-10-24. Scope: audit/checkpoint Milestone 2A,
then implement deterministic quality gates only. No CLI, JSON/Markdown report exports,
AI integration, deployment, publication, or later milestone was implemented.

## A. Milestone 2A checkpoint

- Commit: `private-checkpoint` on `main`.
- Message: `feat: add deterministic AI regression comparison`.
- Parent: `private-checkpoint` (1C checkpoint).
- Audited exactly 9 modified and 3 new files from 2A. Read implementation, tests,
  configuration, milestone report, and contracts; no credential/private-data findings,
  generated files, or unexpected project source were found.
- Verified repository root, HEAD, branch, empty staging area, approved repository-local
  noreply identity, ignore protection, and absence of remotes.
- Before committing: 398 offline tests passed; Ruff lint/format, offline lock, and
  Git whitespace checks passed. Staged only the reviewed 12 files.
- Verified the new commit and a clean tree before beginning 2B. No push or remote creation.

## B. Exact 2B file inventory

Created:

1. `src/trustbench_ai/gate_types.py` — immutable policies, rule observations, affected IDs, results.
2. `src/trustbench_ai/gates.py` — comparison/policy validation and independent gate evaluation.
3. `tests/test_gates.py` — 131 new offline tests.
4. `docs/gate-contract.md` — detailed policy, arithmetic, error, and fingerprint contract.
5. `docs/milestone-2b.md` — this verification report.

Modified:

1. `src/trustbench_ai/provenance.py` — gate/policy versions and canonical hash helpers.
2. `pyproject.toml` — adds gate engine/types to targeted coverage.
3. `AGENTS.md` — stop-after-2B scope.
4. `README.md` — policy examples, decisions, interfaces, and boundaries.
5. `docs/architecture.md` — gate flow, dependencies, provenance, and trust boundary.
6. `docs/evaluation-contract.md` — links gate contract and updates implementation status.
7. `docs/roadmap.md` — completed 2B and proposed CLI/report scope for 2C.
8. `docs/vscode.md` — gate discovery/debugging workflow and results.

All 398 prior tests, fixtures, existing evaluation/comparison engines and types,
runner, dataset loaders, `uv.lock`, and `.vscode/*` are unchanged. Verification helpers
and measurements under `artifacts/`, distributions under `dist/`, and the existing
environments are ignored. No second workspace/repository or new environment was created.

## C. Public interfaces

`GatePolicy` in `trustbench_ai.gate_types`:

- `policy_id="strict-regression"`, `policy_version="1.0.0"`.
- `max_regressions: int = 0`.
- `max_candidate_failures: int | None = None`.
- `min_candidate_pass_rate: Fraction | None = None`.

`evaluate_gate(comparison: ComparisonResult, policy: GatePolicy) -> GateResult`
in `trustbench_ai.gates`. There is no implicit policy argument: pass `GatePolicy()`
to select the strict defaults explicitly. Additional rules are disabled unless supplied.

Policy/results are immutable frozen/slotted dataclasses. `GateRuleResult` exposes
stable rule ID, observed/permitted values, and derived pass/fail and explanation.
`CheckIdentity` preserves case ID, evaluator ID, and evaluator version. `GateResult`
includes provenance, ordered rules/regressions/candidate failures, raw check totals,
result digest, and derived overall `.passed`. It validates count/observation agreement.

## D. Decisions and errors

All counts are evaluator-check counts. Rules execute independently, in fixed order:
maximum regressions, optional maximum candidate failures, optional minimum candidate
pass rate. Limits are inclusive. Overall pass requires every configured rule to pass.
An improvement never offsets a regression, including within mixed or already-failing
cases. The synthetic fixture has two regressions and one improvement and correctly
returns a legitimate failed gate under defaults.

Pass rate is passing candidate checks divided by all paired checks: the fixture has
6/8 = 3/4. `Fraction` comparisons preserve exact boundaries without tolerances or
rounded percentages. Float/string/bool rate values and bool/negative/malformed counts
are rejected. Fraction ratios normalize, so 6/8 and 3/4 have the same policy hash.
Unknown constructor keywords raise TypeError. All individually valid rules are jointly
satisfiable by an all-pass candidate; differing count/rate strictness is not a conflict.

Comparison structure, completeness, unique IDs, evaluator-version consistency,
supported contracts, and fingerprint are checked before rules. Policy fields are
revalidated before comparison evidence. Invalid input raises `GateError`, with one of:
`INVALID_POLICY`, `INVALID_COMPARISON`, `INCOMPATIBLE_COMPARISON`, or
`COMPARISON_FINGERPRINT_MISMATCH`. It never becomes an ordinary gate failure or
partial result. Construction errors use `ContractError` or Python signature errors.

A legitimate rule failure returns `passed=False` without an exception/process exit;
tests assert that outcome successfully. Each rule explains its observation, bound,
and corrective action. Regression and candidate-failure IDs are retained even when
permitted. Default zero regressions can pass unchanged candidate failures; the optional
failure/rate rules constrain those explicitly.

## E. Provenance and hashing

Gate contract: `1.0.0`. Supported comparison/evaluation contracts: `1.0.0`/`1.1.0`.
Gate provenance records comparison fingerprint/contract, policy ID/version/hash,
and gate contract version. The comparison fingerprint serves as comparison identity.

The existing `provenance.py` provides canonical compact, sorted-key ASCII JSON and
SHA-256 with no BOM/newline, non-finite values, clocks, paths, random IDs, or environment
reads. Fractions encode as reduced integer numerator/denominator objects.

- Policy fingerprint version `trustbench-gate-policy-v1`: binds all fields, including
  null disabled rules and caller identity/version.
- Gate fingerprint version `trustbench-gate-v1`: binds provenance, every ordered rule's
  observed/permitted values, passed status and explanation, affected identities,
  total/passing check counts, and overall pass. Excludes the result hash itself.
- Existing run/comparison fingerprint formats and behavior are unchanged.

Full projections are specified in [gate contract](gate-contract.md). These are internal
hash encodings, not public report exports. For the original comparison labeled
`baseline`/`1.0.0` and `candidate`/`2.0.0` with integer limit 4300:

- Strict policy fingerprint:
  `6fc2ed470ab50aa0ef663409b8b217444afd3157434ccd9e0b026400140d2336`.
- Strict failed-gate fingerprint:
  `c667692b61e45fb1491150d811a26eab569e1aebedc6509e391501067d5c01ea`.

## F. Python verification

| Environment | Executed suite |
| --- | --- |
| Existing `.venv`, Python 3.12.10 | **529 passed** |
| Existing `.venv-package`, Python 3.14.4 installed wheel | **529 passed** |

The original 398 tests are preserved; 131 gate tests were added. Wheel tests used `-I`
and pytest importlib mode. Import origin independently confirmed `site-packages` in
the 3.14 environment. Full gate evidence, rational values, rule statuses/explanations,
and fingerprints matched across both interpreters for strict-failing and explicitly
permitted-passing policies. No interpreter was downloaded or environment created.

## G. Coverage, dependencies, and packaging

| Check | Result |
| --- | --- |
| Targeted statement/branch coverage | **100%**, 765 statements, 220 branches, zero misses |
| Gate engine | 73 statements, 34 branches, zero misses |
| Gate types | 115 statements, 30 branches, zero misses |
| Coverage scope | Loaders, evaluators, runner, comparison/gate engines and types, provenance; not whole-package |
| Ruff lint and format | Passed, including new Python examples in Markdown |
| `uv lock --check --offline` | Passed; 9 resolved packages; lockfile unchanged |
| `uv pip check` | Passed in both existing environments |
| Dependencies | None added; no runtime dependencies |
| `uv build --offline` | Source distribution and wheel built; wheel built from sdist |
| Git whitespace | `git diff --check` passed |

Tests include default zero/one/two-regression outcomes, permitted thresholds,
candidate failure limits, exact/rational rate boundaries, all-pass/all-fail candidates,
mixed Greek/English content checks, multiple checks per case, rule independence/order,
invalid numeric/policy fields, malformed/duplicate/subclass/stale/incompatible evidence,
immutable inputs/results, no I/O/reevaluation, repeated results, hash sensitivity,
and independent policy/gate hash oracles. Existing socket/DNS blocking remains active.

## H. VS Code readiness

The configured Python 3.12.10 interpreter and pytest arguments discovered all 529 tests,
including 131 gate tests. Every executable saved task command passed. Both debug
target argument lists passed: 123 evaluator tests and 131 gate tests via the existing
current-file configuration. Saved `.vscode` files are unchanged.

The installed adapter stopped at a real `evaluate_gate` breakpoint at `gates.py:105`,
returned the expected stack frame, continued, and exited successfully. Verification
used stdio/internal console; interactive F5 terminal routing/task-menu clicks were not
automated. The extension CLI confirmed Python, Python Debugger, Ruff, and official
`openai.chatgpt@26.1021.22027`. No extensions/global settings changed. Live Codex
inference/authentication was not retested; existing integration was preserved.

## I. Limitations and risks

- Hash consistency does not prove original coverage, execution, or authenticity. The
  gate receives no original runs/dataset/output bytes and cannot verify run references
  against those sources. Deliberately reconstructed/rehashed incomplete evidence is
  outside this trust boundary; use trusted runner/comparator results.
- Counts are check-level. Cases with more checks contribute more to rate denominators;
  no weighting, category/language slices, or case-level threshold variants exist.
- Policy labels are caller assertions. Changed settings should have a new version;
  hashes distinguish content even when labels are reused. Manual dataclass replacement
  does not recompute fingerprints.
- Use integer ratios/decimal strings when constructing Fraction thresholds; constructing
  Fraction from a float preserves that float's binary value.
- No comprehensive resource caps or hostile-data hardening, static type-checking claim,
  or OS/interpreter matrix beyond the two tested Windows interpreters.
- Synthetic conformance only: no truth, safety, model-quality, or statistical claims.
- No CLI exit behavior, file exports, external AI, deployment, or publication.

## J. Git status

`main` remains at `private-checkpoint` with three local checkpoint
commits. 2B changes are intentionally unstaged and uncommitted: **8 modified tracked
files and 5 new files**, exactly section B. Generated artifacts and environments remain
ignored. No remote exists; no push or publication occurred.

## K. Recommended Milestone 2C

Implement only a thin local CLI and deterministic JSON/Markdown reporting over the
existing APIs. Specify a public report schema, exact policy input representation,
Unicode/Markdown escaping, stable ordering/provenance, and write-error behavior.
Map valid pass to exit 0, valid gate failure to 1, and invalid policy/evidence/input or
I/O errors to 2. Verify subprocess codes and repeated byte-identical output with the
synthetic fixtures. Preserve check-level and mixed-case evidence. Do not add services,
dashboards, deployment, or publication. Stop after 2B; 2C is not implemented or started.
