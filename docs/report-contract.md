# Report contract 1.0.0 and CLI (Milestone 2C)

The public command is now `fixturedelta`; the module is `fixturedelta_lab`.
The Markdown heading is `# FixtureDelta Lab synthetic evaluation`. JSON fields,
contract versions and legacy `trustbench-*-v1` fingerprint identifiers are unchanged.
The heading is not part of the JSON fingerprint. See [release verification](portfolio-release.md).

This adapter evaluates local, synthetic recorded responses through the existing
runner, comparator and gate. It does not call a model, execute recorded code, or
measure factual truth, hallucination, general safety, or statistical quality.

## Command and input snapshots

`fixturedelta check` and `python -m fixturedelta_lab check` share `cli.main(argv) -> int`.
Required options: `--dataset`, `--baseline`, `--candidate`, `--report-dir`.
Optional: `--policy`, `--baseline-id`, `--baseline-version`, `--candidate-id`,
`--candidate-version`. Long-option abbreviation is disabled. Help exits 0 without
evaluating inputs. Normal argparse duplicate-option behavior applies (last value wins).

The CLI parses the policy, reads the dataset once and each output file once, evaluates
both against the same dataset snapshot, compares the complete results, then renders
and publishes. All validation precedes output-directory creation. Sequential reads
are not a cross-file transaction; use stable input files. No input is modified.

Dataset and output files retain their strict schema-v1 formats in the
[evaluation contract](evaluation-contract.md). A dataset identifies its version,
synthetic origin, and ordered cases with IDs, language, category, prompt and typed
expectations. An output set identifies that dataset/version, its application
`candidate_version`, source statement, and exactly one text output per case ID.
Missing, duplicate, extra, or mismatched identities invalidate the run.
Output-set labels default to `baseline`/`1.0.0` and `candidate`/`1.0.0`; explicit ID
options require the existing lowercase ASCII ID grammar and versions require numeric
major.minor.patch. Those labels are independent of the application's recorded version.

## Policy JSON schema 1

Example: `tests/fixtures/policy-allow-v1.json`:

```json
{
  "schema_version": 1,
  "policy_id": "synthetic-allow",
  "policy_version": "1.0.0",
  "max_regressions": 2,
  "max_candidate_failures": 2,
  "min_candidate_pass_rate": {"numerator": 3, "denominator": 4}
}
```

The first four fields are required. The last two are optional; absent or null disables
the respective rule. Unknown fields, duplicate keys, invalid UTF-8/JSON, non-finite
numbers, unsupported schema versions, invalid identity/version labels, booleans and
negative/non-integer count limits are rejected. A rate must be null or an object
containing exactly integer `numerator` and positive integer `denominator`; its exact
value must lie in [0, 1]. Decimal floats, strings and booleans are invalid. Fractions
normalize: 6/8 and 3/4 yield identical policy fingerprints. Policy-file whitespace is
not hashed; the normalized policy values are. Omitted `--policy` selects the existing
`GatePolicy()` (strict zero regressions, other rules disabled).

All thresholds count evaluator checks. Rules are independent and inclusive; all must
pass. Improvements never offset regressions, including in mixed or already-failing
cases. An unchanged failure can pass the default regression-only policy; enable the
failure-count/rate rules to constrain it. See [gate semantics](gate-contract.md).

## Exit codes and diagnostics

| Code | Meaning | Reports from this invocation |
| --- | --- | --- |
| 0 | Valid gate passes (also normal help) | Complete pair, except help |
| 1 | Valid gate fails | Complete pair |
| 2 | Usage, missing/non-file input, invalid data/policy/metadata, incompatible evidence | None |
| 3 | Runtime/evaluator failure, file-access failure, existing output target, or failed publication | No newly published pair for evaluation/publication failures |

Input permission failures are runtime errors; known missing paths and directory
inputs are invalid input. Errors print a fixed code/action to stderr without raw
exception text, paths, labels or recorded responses. A successful publication prints
the gate decision, case/check/regression/improvement/failure counts, relative report
names and report SHA-256. Ctrl-C and argparse help keep their ordinary Python behavior.
A broken terminal after publication can yield a runtime failure with reports already
present; no transaction spans the filesystem and stdout. An unusable stderr can
prevent diagnostic delivery. These are terminal failures, not partial report pairs.

## Public JSON layout

`render_reports(comparison, policy) -> ReportBundle` validates/evaluates the gate once,
then produces immutable UTF-8 JSON and Markdown bytes. `ReportBundle` includes both
byte strings, `report_sha256`, and the validated `GateResult` used to render them.
The caller supplies trusted comparison evidence; rendering does not reread/evaluate
inputs or recompute transitions independently of the existing APIs.

The JSON object has exactly these top-level fields:

| Field | Content |
| --- | --- |
| `report_contract_version` | `"1.0.0"` |
| `report_fingerprint_version` | `"trustbench-report-v1"` |
| `provenance` | `comparison` (all ComparisonProvenance fields), `comparison_sha256`, `gate` (all GateProvenance fields), `gate_sha256` |
| `counts` | `cases` and `checks` transition counts; `cases_with_regressions`, `cases_with_improvements`, `mixed_cases` |
| `cases` | Ordered per-case outcomes and checks, described below |
| `policy` | All five GatePolicy fields, including null disabled rules and exact reduced rate |
| `gate` | `passed`, `total_checks`, `candidate_passes`, ordered `rules`, `regressions`, `candidate_failures` |
| `report_sha256` | Canonical payload fingerprint, excluding this field |

Comparison provenance includes dataset ID/version/raw SHA-256, evaluation/comparison
contract versions, evaluator suite version, recorded Python integer limit and baseline/
candidate references. Each reference includes output-set ID/version, application
version, raw output-file SHA-256 and run SHA-256. Gate provenance includes comparison
SHA-256/contract, policy ID/version/SHA-256 and gate contract version. Exact nested
fields are the existing versioned dataclasses documented in the evaluation/gate contracts.

Both transition count objects contain `regressions`, `improvements`, `unchanged_passes`,
`unchanged_failures`, `total`. Case counts use aggregate all-checks-pass transitions;
check counts count every paired evaluator independently. Overlapping case-with-change
counts are not a partition. A mixed case contributes to both affected-case counts.

Each case contains `case_id`, `baseline_passed`, `candidate_passed`, aggregate
`transition`, `summary` (including `mixed`), and `checks`. Each check contains
`evaluator_id`, `evaluator_version`, both passed booleans and `transition`. Ordering
follows the baseline comparison: dataset case order and evaluator check order, never
alphabetical sorting. All checks are included, even unchanged passes/failures.

Gate rules contain `rule_id`, `observed`, `permitted`, `passed`, `explanation`, in the
existing fixed order. Values are integer counts or reduced `{numerator, denominator}`
objects. Affected check lists contain case ID, evaluator ID and evaluator version.
Explanations are controlled gate messages; evaluator explanations are excluded because
they can contain response previews. Raw responses, prompts and source statements are
also excluded. Upstream hashes still bind the omitted evidence.

JSON is sorted by object key, two-space indented, `ensure_ascii=False`, `allow_nan=False`,
UTF-8 without BOM, LF and one trailing newline. Greek/English strings are preserved
without normalization. Arrays retain declared order. No clock, random ID, input/output
path, environment variable or host-specific location enters the payload.

## Fingerprints and repeatability

To verify the report digest, remove only the top-level `report_sha256`, encode the
remaining object with `json.dumps(sort_keys=True, ensure_ascii=True, allow_nan=False,
separators=(",", ":"))`, UTF-8, no newline, and compute lowercase SHA-256. The
`trustbench-report-v1` field provides domain/version separation. This compact internal
encoding differs intentionally from the readable public JSON. The digest binds all
projected statuses, provenance, policy and gate values, not the Markdown byte stream.

Identical source bytes, labels, supported evaluator/contract versions, normalized
policy and recorded integer setting yield byte-identical JSON and Markdown across
the tested Python 3.12/3.14 Windows environments. Paths do not affect identity.
Formatting-only source edits change raw input hashes and therefore report identity.
Reports can preserve Greek in application labels without exposing raw Greek responses.
Renderer/encoding changes require report-contract/fingerprint review and versioning.
The old run/comparison/policy/gate encodings are unchanged. These are consistency
digests, not signatures or proof of original execution, complete coverage or truth.

## Markdown

The Markdown includes gate decision, dataset and baseline/candidate labels, case/check
transition counts, mixed-case count, all per-case/evaluator transitions, all policy
rule outcomes with explanatory text, raw candidate passing-check counts, contract/
suite/runtime settings, and dataset/output/run/comparison/policy/gate/report hashes.

The seeded example shows:

```text
Gate: FAIL
Cases: 2 regressions, 1 improvement, 3 unchanged passes, 0 unchanged failures (6 total)
Checks: 2 regressions, 1 improvement, 5 unchanged passes, 0 unchanged failures (8 total)
Candidate passes: 6/8
max-regressions: observed 2, permitted 0, FAIL
```

Every dynamic value escapes ASCII punctuation and ASCII controls (including line
breaks and DEL) as decimal numeric HTML entities. For example, a label `Έτοιμο | <x>`
becomes `Έτοιμο &#124; &#60;x&#62;`. This prevents table, heading, link and raw HTML
injection in Markdown; Unicode letters remain literal. Static structure is authored
by the renderer. JSON strings are data, not HTML; consumers must escape them for their
own output context rather than injecting them directly into a webpage.

## Publication and confidentiality boundaries

`write_reports(directory, bundle)` accepts an already-rendered bundle. It creates any
missing parents, exclusively reserves the selected **new** directory, writes both
files in its `.pending/` subdirectory using exclusive binary creates, closes both,
then renames that directory to `reports/`. The published paths are
`<report-dir>/reports/report.json` and `<report-dir>/reports/report.md`. Existing
directories (even empty), files and symlinks at the chosen target are refused; there
is no overwrite option. No successful completion is printed until publication returns.

On an ordinary filesystem error, cleanup attempts only the two known staging files
and owned staging/target directories. It never recursively deletes. Cleanup failure
or process termination can leave `.pending/` or empty parent directories; these are
not published reports. Do not interpret `.pending` as successful output. A subsequent
run needs a fresh target. This uses a same-filesystem directory rename, not an fsync
durability guarantee, portable network-filesystem transaction, or protection against
hostile concurrent mutation of parent directories. Use trusted local locations.

Use ignored `artifacts/` for generated reports. Other caller-selected locations need
their own Git-ignore policy. No files are auto-committed. The application never
executes or interprets recorded text as code. It fully loads small local input files;
there are no new file-size/resource limits or hostile-data sandbox guarantees.

The CLI does not export machine paths, raw output, prompts, source statements, or
evaluator previews. It rejects recognizable absolute paths, common token/private-key
forms, credential assignments and lone surrogates in exported metadata before writing.
This is deliberately limited detection, not universal secret discovery/redaction.
Use non-confidential synthetic application labels; arbitrary user-authored metadata
cannot be certified secret-free. Hashes may also reveal equality of source artifacts.
No external services, network clients, paid API calls, telemetry or model judges exist.
