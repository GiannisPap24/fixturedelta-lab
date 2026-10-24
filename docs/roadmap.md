# Milestone roadmap

Milestones 1A through 3A and the separately requested Final MVP Audit are complete.
The separately authorized portfolio release preparation is also complete. Stop here;
later development and publication need separate requests.
The entries below specify acceptance criteria, not further authorization.

| Milestone | Scope | Acceptance criteria |
| --- | --- | --- |
| **1A: foundation** | Packaging, contracts, strict loaders/alignment, synthetic fixtures, docs, local tooling | Offline contract tests pass; lint/format pass; lock is consistent; import and wheel/sdist verified; no evaluator execution or external services |
| **1B: deterministic evaluators (complete)** | Three pure families, single-case adapter, VS Code integration | Typed explained checks; literal Unicode/content and strict limited JSON; repeatability/immutability; targeted coverage; offline tasks/debugger; Python 3.12/3.14 compatibility |
| **1C: single-run execution (complete)** | Local input orchestration and result provenance | Exactly one result per dataset case in declared order; SHA-256 of actual evaluated bytes; missing/extra IDs and evaluator errors invalidate run; fixture oracle verified; no CLI or reports |
| **2A: baseline/candidate comparison (complete)** | Pair compatible runs; per-case/check changes | Two seeded case regressions and one improvement found; incompatible evidence rejected; check regressions visible in already-failing and mixed cases; deterministic immutable comparison; no gates, exports, or CLI |
| **2B: quality gates (complete)** | Explicit gate configuration over validated comparisons | Zero check regressions by default; optional failure-count and exact pass-rate rules; inclusive boundaries; mixed cases preserved; invalid evidence rejected; reproducible decisions |
| **2C: reports and CLI (complete)** | Canonical JSON/Markdown; commands and exit mapping | Byte-identical reports; Unicode/Markdown escaping; explicit error versus gate-failure exit codes; complete offline example |
| **3A: reproducible demo (complete)** | Real CLI scenarios, verified reports, portfolio guide and VS Code task | Strict failure and no-regression pass; invalid/output error distinction; console/module and Python 3.12/3.14 byte equality; unchanged fixture bytes; no runtime feature expansion |
| **Final audit and local release (complete)** | Confirmed corrections, FixtureDelta Lab naming, MIT, checked toolchain, portfolio docs | Reviewed local checkpoints; Python 3.12/3.14 and installed CLI verification; unchanged fingerprints; publication awaits separate authorization |
| **Optional later work** | Broader synthetic cases, multi-OS CI and resource quotas | Separately scoped acceptance criteria; no authorization to implement these here |

## Milestone 1B acceptance reference

Implement **only pure deterministic evaluators** for `ExactMatch`, `ContentRules`,
and `JsonObject`, taking a response string and a typed expectation and returning
explained `CheckResult` values with stable evaluator IDs/versions. Document each
evaluator's exact semantics from the contract. Use the existing six synthetic cases
plus focused edge cases. Do not add a runner, comparisons, gates, reports, CLI,
network access, framework, dashboard, or publication.

Specific acceptance checks:

1. Exact match distinguishes whitespace, punctuation, case, and composed/decomposed
   Greek accents; empty expected/actual strings behave explicitly.
2. Content checks test all required and forbidden phrases with deterministic reasons,
   including separate failing rules; no factual/hallucination claims.
3. JSON checks reject malformed documents, duplicate keys, root scalars, fences,
   non-finite/overflow numbers, missing/extra keys, and boolean-as-integer confusion.
4. No input mutation, filesystem reads, clock access, randomness, or network requests.
5. Offline tests and Ruff pass; contracts change only if justified and documented.

## Final MVP Audit

The [audit report](final-mvp-audit.md) records the reviewed command path, installed-package
isolation, deterministic reports, input/output safety, diagnostics, dependencies and builds.
The [release checklist](release-readiness.md) separates completed technical checks from
owner decisions and optional improvements. No algorithms, services, CI or remotes were added.

2C is complete: `fixturedelta check` uses the existing runner/comparison/gate APIs,
strict policy JSON, deterministic JSON/Markdown, and exclusive report publication.
Valid pass/fail exits are 0/1, invalid input/evidence/policy is 2, runtime/output failure
is 3. This supersedes the historical 2B proposal that grouped I/O failures under 2.
3A adds a repository demonstration wrapper/verifier and concise portfolio guide using
those same APIs. The six original synthetic cases remain immutable. Stop here: the
Final MVP Audit is checkpointed. See [portfolio release verification](portfolio-release.md)
for the approved rename, MIT licence, toolchain selection and local release checkpoint.
