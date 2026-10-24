# Architecture and engineering decisions

## Purpose and current boundary

FixtureDelta Lab is an offline comparison harness for two versions of an AI
application's recorded responses. It evaluates the supplied artifacts; it neither
runs a model nor reproduces the generation process. Milestone 1A implements only
domain contracts, strict local input loading/alignment, package structure, and tests.
Milestone 1B adds pure evaluators and a single-case adapter in `metrics/`, plus
project-local VS Code tasks/debugging. Milestone 1C adds single-run orchestration,
immutable byte-snapshot parsing, and reproducible provenance. Milestone 2A adds pure
baseline/candidate comparison and immutable comparison contracts. Milestone 2B adds
pure gate policy evaluation over comparisons. Milestone 2C connects these APIs through
an argparse CLI, a strict policy JSON parser and deterministic JSON/Markdown reports.
Existing evaluation/comparison/gate engines, domain contracts and released fixtures
remain unchanged; a new synthetic policy example is added.

## Dependency direction

```text
CLI
  -> runner -> datasets: snapshot parsing/alignment -> domain
            -> metrics: existing evaluate_case -> domain
            -> provenance: internal fingerprint encoding -> domain
  -> comparison -> domain + comparison_types + provenance
  -> policies -> datasets validators + gate_types
  -> reporting -> gates -> comparison_types + gate_types + provenance
               -> canonical provenance helpers + filesystem publication

comparison_types -> domain validators -> Python standard library only
gate_types -> comparison_types/domain validators -> Python standard library only
```

| Boundary | Responsibility | Must not own |
| --- | --- | --- |
| `domain.py` | Immutable validated types and local invariants | I/O, evaluation execution, presentation |
| `datasets.py` | Strict local JSON decoding; dataset/output coverage checks | Scoring or implicit data repair |
| `metrics/` | Pure output + expectation checks; `evaluate_case` attaches a matching case ID | File access, network, run orchestration, CLI exit |
| `runner.py` | Complete coverage, dataset-order dispatch, provenance capture, coded errors | Metric algorithms or report formatting |
| `provenance.py` | Exact-byte hashes and versioned internal run/comparison fingerprints | I/O, reports, CLI, evaluation algorithms |
| `comparison.py` | Evidence validation, compatible ID alignment and deterministic transitions | Loading files, reevaluation, gates, or hiding invalid runs |
| `comparison_types.py` | Immutable paired evidence, derived transitions/summaries/counts | I/O, evaluators, thresholds, policies |
| `gates.py` | Validate comparison evidence; enforce independent policy rules | Loading files, reevaluation, CLI exits, exports |
| `gate_types.py` | Immutable policies, rule outcomes, affected identities, gate result | I/O, evaluators, arbitrary policy languages |
| `policies.py` | Strict policy JSON decoding and exact rational thresholds | File I/O or gate decisions |
| `reporting.py` | Gate once; canonical projection, escaped Markdown, exclusive pair publication | Recomputing evaluator scores or adding timestamps |
| `cli.py` | Arguments, input snapshots, orchestration, sanitized diagnostics and exit codes | Domain business logic |

## Decisions

1. **Small standard-library domain.** Frozen, slotted dataclasses and enums provide
   explicit types without a runtime framework. Constructors validate important
   invariants; tuple fields keep nested data immutable. Direct invalid construction
   and invalid JSON input are both tested. A dedicated `ContractError` separates
   invalid input from failed expectations. This is not a generic schema engine.
2. **Readable JSON fixtures.** A single versioned document holds six cases, easily
   reviewed in Git. Each output set names the dataset/version it targets and its
   candidate version/source. Duplicate JSON keys, duplicate IDs, missing fields,
   unknown fields, and unsupported schemas fail rather than being guessed away.
   JSONL/streaming can be evaluated if real dataset size justifies it.
3. **One expectation family per case in v1.** Exact text, content rules, or a small
   JSON object shape. Required and forbidden rules may coexist. Result contracts
   allow multiple checks because a content evaluator may explain them separately.
   Avoid a plugin registry until real extensions need one.
4. **Python floor 3.12.** The installed 3.12.10 supports current language features
   and a conservative base interpreter. `requires-python >=3.12` is a compatibility
   intention; only interpreters actually tested in the milestone record are verified.
   Pin the local minor in `.python-version`; do not download another interpreter.
5. **Minimal development dependencies.** pytest provides focused parameterized
   validation tests; Ruff supplies lint and formatting. Coverage.py is development-only
   and measures the requested evaluator statement/branch coverage. `uv_build` is build-only,
   pinned to the installed uv backend version. No LLM frameworks, Pydantic,
   jsonschema, HTTP clients, database, or dashboard dependencies. Evaluate each
   addition against a concrete requirement in a later milestone.
6. **Project-local environment and editor configuration.** `.venv`, no global
   Python or Git changes, no PowerShell policy change. Existing Git repository
   reused; no remote added and no repository publication. Generated caches and
   build artifacts are ignored.
7. **Fail closed on incomplete evidence.** Missing outputs and incompatible
   datasets are input errors. An invalid response string can legitimately fail
   an expectation; an evaluator crash must invalidate the run, not become a
   pass/fail score. The runner validates all inputs before dispatch and returns only
   a complete `RunResult`; failures expose a stable code and optional case ID.
8. **Honest provenance.** The runner reads each file once, parses and hashes that
   immutable snapshot, and preserves dataset order. It reads the candidate version
   from the output file and requires output-set ID/version labels from the caller.
   The unchanged schema-v1 wire format has no output-set identity fields; filenames
   are never used as identities. Each check records its existing evaluator version.
   Contract version `1.1.0` identifies the additive orchestration contract; suite and
   evaluator versions remain `1.0.0`. Python's integer conversion limit is recorded
   because the existing JSON evaluator can depend on a stricter host limit.

## Implemented single-run flow

`run_evaluation(Path, Path, *, output_set_id, output_set_version)` reads two byte
snapshots and delegates to `evaluate_run(bytes, bytes, *, output_set_id,
output_set_version)`. Strict loaders validate both documents, then alignment checks
dataset identity/version and exact case coverage. A dictionary joins outputs by ID;
iteration follows dataset order. `evaluate_case` selects the existing evaluator
family. The runner verifies returned case/check IDs, versions, and check order before
building an immutable result. No partial result or error-as-score is returned.

`provenance.py` hashes raw inputs and an internal canonical projection of the full
result. It is not a reporting API. See the evaluation contract for the exact encoding.
Hashes exclude file paths, the clock, and the hash itself. Candidate versions are
caller-authored labels, not verified model identities. The source statement is bound
by the output-file digest; it is not copied into provenance. Old manual constructors
may omit new fields for compatibility and do not establish runner-complete evidence.

Files are read sequentially, not as an atomic filesystem transaction. A later edit
cannot alter captured snapshots; mismatched snapshots fail alignment. Keep input
files and interpreter settings stable during a run. No streaming or concurrency
framework is needed for these small local synthetic fixtures.

## Implemented comparison flow

`compare_runs(baseline, candidate)` accepts the existing `RunResult` contracts. It
revalidates nested shapes, rejects duplicate IDs and incomplete legacy provenance,
and recomputes each run fingerprint. It then requires matching dataset ID/version/hash,
evaluation contract, suite and integer-limit settings, case sets, and per-case
evaluator sets/versions. Supported evaluation contract is `1.1.0`. Each evaluator ID
must use one version throughout a run. No metric code or dataset loader is invoked.

Alignment uses IDs. Baseline case/check order is authoritative; normal runner outputs
carry dataset/evaluator order. A reordered candidate with a correctly recomputed
fingerprint is allowed. All pairs validate before comparison values are constructed.
Errors have stable codes and optional role/case context, with no partial result.

Every check retains both statuses and explanations. Case aggregate transitions use
all-checks-pass, while summaries expose any evaluator regression or improvement and
explicitly identify mixed cases. Counts are derived from immutable evidence. A mixed
case counts in both `cases_with_regressions` and `cases_with_improvements`; those
overlapping counts are not a partition. Quality decisions belong to the separate gate layer.

Comparison provenance records role-specific output-set/application labels, input/run
hashes, shared dataset/evaluation settings, and comparison contract version `1.0.0`.
The internal canonical fingerprint binds that provenance and every ordered paired
check. Run fingerprint encoding and evaluation behavior remain unchanged.

The comparison receives no dataset or source bytes. It can validate internal shape,
digest consistency, and agreement between runs, but cannot authenticate execution or
recover independently verified dataset coverage/order. Two identically truncated,
manually reconstructed and rehashed runs cannot be distinguished from complete runs
using these inputs alone. Use trusted runner outputs; fingerprints are not signatures.
Adding a dataset manifest/attestation would be a separate contract decision.

## Implemented gate flow

`evaluate_gate(comparison, policy)` first revalidates the policy, then exact nested
comparison types, nonempty evidence, unique IDs, consistent evaluator versions,
supported evaluation/comparison contract versions, and the comparison fingerprint.
Only then does it count individual evaluator regressions and candidate failures.
It never calls `compare_runs`, reads datasets, or invokes evaluators. All rules run
independently in fixed order; no short circuit hides another rule's outcome.

The default policy enforces zero check regressions. Optional candidate failure-count
and minimum pass-rate limits are explicit. Exact `Fraction` arithmetic compares the
number of passing candidate checks against all paired checks, preserving mixed-case
regressions. Results retain ordered affected case/evaluator IDs and observed/permitted
values, with derived pass/fail and explanations. A failed rule is normal evidence;
an invalid policy or comparison raises a coded exception without a partial result.

Policy and gate hashes extend the existing `provenance.py` canonical JSON encoding.
Rationals encode as reduced integer numerator/denominator pairs. The gate binds its
comparison fingerprint, policy identity/version/hash, contract version, all rule
outcomes/explanations, affected IDs, and totals. No timestamp, new runtime setting,
environment variable, or machine path is read. Existing run/comparison hashes remain
unchanged. See the [gate contract](gate-contract.md) for the exact projections.

Comparison fingerprints still establish consistency rather than authenticity. The
gate cannot verify referenced run fingerprints against source data or recover missing
coverage when evidence has been deliberately rebuilt and rehashed. Use trusted
comparison results. Caller-supplied policy labels are assertions, with the policy
hash distinguishing configurations even if labels were mistakenly reused.

## Implemented CLI and reporting flow

The CLI reads one dataset snapshot and two recorded-output snapshots. It delegates
runs, pairing, and rules to the existing APIs. The strict policy parser accepts a
versioned JSON object with integer counts and exact integer-ratio rates. Reports
preserve dataset/baseline case and evaluator order. They sort JSON object keys, retain
Unicode, and use UTF-8/LF with a final newline. The report digest binds a versioned
canonical projection including provenance, statuses, all policy/rule values and counts.
No timestamps, random IDs, machine paths or fabricated performance fields are added.

The renderer excludes recorded responses, prompts and evaluator explanations that can
contain text previews. Metadata is screened for recognizable paths/credentials and
escaped for Markdown. Callers must still use non-confidential labels; screening is not
a general secret detector. Source hashes transitively bind omitted raw evidence.

Publication exclusively reserves a new output directory, writes both files under
`.pending`, and renames the completed pair to `reports/`. Existing targets are refused.
Failure cleanup touches only known owned paths; no recursive deletion is used.
Staging remnants are never reported as success. Trusted local parent directories are
required; this is not a hostile-filesystem or crash-durability guarantee.

Valid pass/fail maps to 0/1; invalid input/evidence/policy to 2; runtime/output failures
to 3. See the [report contract](report-contract.md) for the precise schemas, canonical
hash recipe, output paths, terminal failure boundary and confidentiality limitations.
Run/comparison/gate hashing encodings and semantics remain unchanged.

## Risks and follow-up

- A six-case synthetic suite proves plumbing only. It does not estimate real-world
  model quality, hallucination rates, or multilingual generalization.
- Literal Unicode matching is sensitive to accents, normalization, case, punctuation,
  and whitespace. 1B tests cover these distinctions; no normalization is applied.
- The JSON object specification is intentionally shallow. It cannot express nested
  schemas, array item constraints, or semantic relationships. Revisit a dependency
  only when those requirements appear.
- Fully loaded JSON assumes trusted, small local artifacts. The response evaluator
  caps nesting at 64 containers and integer tokens at 4300 digits for consistent
  behavior across Python 3.12/3.14. This does not change dataset/output metadata
  loaders or constitute comprehensive untrusted-input hardening. File-size limits
  and total diagnostic-size limits remain future work.
- Runtime validation does not replace static type checking. A type checker and
  a multi-OS/interpreter CI matrix are future decisions; do not claim them today.
- Offline setup still needs pre-cached development packages and a matching build
  backend. The lockfile is not a vendored toolchain or a promise of offline bootstrap.
- The owner selected FixtureDelta Lab and MIT. The Python distribution is
  `fixturedelta-lab`, module is `fixturedelta_lab`, and command is `fixturedelta`.
  Legacy fingerprint namespaces are immutable format identifiers, not product branding.
- Retain the private-upload classifier: PyPI publication is not authorized.
  GitHub publication also awaits separate approval. See [release readiness](release-readiness.md).
