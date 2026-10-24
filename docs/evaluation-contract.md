# Evaluation contract 1.1.0 (schema v1)

Status: dataset/output parsing, alignment, and Python types are implemented in 1A.
1B implements the three deterministic evaluator families and a single-case adapter.
1C implements single-run orchestration and reproducible provenance. 2A adds the
separate comparison contract 1.0.0 below. 2B adds [gate contract 1.0.0](gate-contract.md).
2C adds the [CLI and report contract](report-contract.md); evaluation/comparison semantics are unchanged.
The wire schemas, fixtures, and evaluator
behavior are unchanged. New domain fields are additive and keyword-only.

## Input documents

Files are UTF-8 JSON without a BOM. The document root is an object. Unknown and
missing fields, duplicate object keys at any depth, nonstandard `NaN`/`Infinity`
constants, wrong types, and unsupported schema versions are errors. No type coercion
or silent normalization occurs. File I/O failures remain `OSError` subclasses;
malformed input raises `ContractError`. Byte parsers also reject parser recursion and
integer conversion limits as `ContractError`. Original text in strings is preserved.
The runner wraps these errors in the stable codes below; direct loaders retain their
original exception interface.

Every document requires integer `schema_version: 1` (not `true` or `1.0`). This
versions the wire format, separately from dataset content and evaluator behavior.

### Golden dataset

Required root fields: `schema_version`, `dataset_id`, `dataset_version`, `origin`,
`cases`. `origin` must be `synthetic`. A dataset has at least one case.

| Case field | Rule |
| --- | --- |
| `case_id` | Unique stable lowercase ASCII identifier; never reuse for a different task |
| `category` | Lowercase ASCII identifier for future slices |
| `language` | `en` or `el` in schema v1; extension requires an explicit contract change |
| `prompt` | Nonblank reference task text; never sent to a model by this harness |
| `expectation` | Exactly one of the discriminated objects below |

Identifiers match `[a-z][a-z0-9]*(?:[._-][a-z0-9]+)*`. Dataset versions use
`major.minor.patch` with nonnegative integers and no leading zeroes. Before release,
1A fixtures are draft; once released, do not edit a version in place. Fixes, new
cases, and expectation changes need a new content version. Preserve an ID only
while it represents the same task. Dataset identity plus hash protects comparisons
even if a version is accidentally reused.

### Expectations and implemented evaluator semantics

```json
{"kind": "exact_match", "expected": "Έτοιμο"}
```

`expected` is a string, including possibly empty. Evaluation is exact
Unicode code-point equality: no trimming, case folding, accent removal, or NFC/NFD
normalization. A normalization option would need explicit configuration and a new
evaluator behavior version.

```json
{"kind": "content_rules", "required": ["blue triangle"], "forbidden": ["red square"]}
```

Both arrays are required; each may be empty but not both. Strings must be nonblank
and unique within each array. A required string containing a forbidden string is
contradictory and rejected. Checks use case-sensitive literal substrings,
not regexes, whole words, or semantic similarity. All required strings must occur;
no forbidden string may occur. These checks cannot establish truth or detect
hallucination. Failure explanations identify the violated rule.

```json
{"kind": "json_object", "required_fields": {"label": "string", "count": "integer"}, "allow_extra_fields": false}
```

`required_fields` maps nonblank keys to `string`, `integer`, `number`, `boolean`,
`object`, `array`, or `null`. The map may be empty to request an empty object (or any
object if extras are allowed). `allow_extra_fields` is an actual boolean. The
evaluator parses the entire response as strict JSON, rejecting duplicate keys and
non-finite values (including overflow such as `1e999`), and require a root object.
No Markdown fence stripping or substring extraction. All declared fields must exist;
extra fields pass only when explicitly allowed.

JSON types: `integer` is an integer token decoded to Python `int`, excluding
`bool`; `number` accepts finite `int` or `float`, excluding `bool`; `boolean` requires
`bool`. `2.0` does not satisfy `integer` in this deliberately lexical contract.
`object`/`array` validate only the field's container type; their nested content has no
schema constraints, but must still be valid finite JSON. `null` requires JSON null.
This is a small object contract, not an implementation of JSON Schema.

The first evaluator version supports **64 nested containers** (root counts as one)
and **4300 decimal digits per integer token**, excluding the sign. A lexical depth
check ignores delimiters inside quoted strings, including escaped quotes. These
explicit evaluator resource bounds were added in 1B because Python 3.12 and 3.14
have different built-in JSON nesting limits. They do not change the 1A metadata
loaders or dataclass shapes. Exceeding either bound produces `JSON_INVALID`.
Float values use Python's finite binary floating-point representation, including
ordinary rounding/underflow; numeric precision validation is outside this contract.
The harness does not change interpreter limits: a host configured with a stricter
integer conversion limit produces a stable parser-limit failure. Reproducibility
requires the documented interpreter configuration as well as identical inputs.

The final audit replaced repeated regular-expression suffix scans with two linear
passes that preserve the same lexical depth decisions, including malformed strings.
This resource fix does not change evaluator IDs, versions, results or fingerprints.
The CLI still reads complete input files into memory; there is no total-byte, case-count,
CPU or memory quota. Use bounded local inputs. The depth/digit limits do not make this
MVP a service for arbitrary hostile uploads.

### Python evaluator interface (1B)

| Function | Return value | Evaluator ID(s), version |
| --- | --- | --- |
| `evaluate_exact_match(output: str, expectation: ExactMatch)` | `CheckResult` | `exact-match`, `1.0.0` |
| `evaluate_content_rules(output: str, expectation: ContentRules)` | `tuple[CheckResult, ...]` | `required-content`, `forbidden-content`, `1.0.0` |
| `evaluate_json_object(output: str, expectation: JsonObject)` | `CheckResult` | `json-object`, `1.0.0` |
| `evaluate_case(case: Case, output: RecordedOutput)` | `CaseResult` | Dispatches one of the above families |

Import these functions from `fixturedelta_lab.metrics`. The case adapter requires equal
case IDs and performs no file I/O, iteration over datasets, run creation, or hashing.
Direct family calls do not attach case IDs; use the adapter when case identity is needed.
Wrong argument/configuration types raise `ContractError`; omitted Python arguments
raise `TypeError`. Construct validated expectation dataclasses or use the strict
dataset loader; dictionaries and arbitrary schema definitions are not accepted.

Required-content is emitted first, then forbidden-content, omitting empty groups.
Each group explanation lists every rule, its 1-based index, pass/fail status, and
presence/absence in declared order. JSON checks list required fields in declared
order and extra keys in sorted Unicode order. All functions preserve inputs and
return immutable results. No clock, randomness, network, or model execution is used.

Explanations start with stable codes: `EXACT_MATCH`, `EXACT_MISMATCH`,
`REQUIRED_CONTENT`, `FORBIDDEN_CONTENT`, `JSON_INVALID`, `JSON_ROOT_TYPE`,
`JSON_OBJECT_MATCH`, or `JSON_OBJECT_MISMATCH`. JSON field details distinguish
`MISSING_FIELD`, `FIELD_TYPE`, `FIELD_OK`, `EXTRA_FIELDS`, and `EXTRA_FIELDS_ALLOWED`.
Exact mismatch includes the zero-based first differing code-point offset, including
end-of-string. Text/key previews escape Unicode/control characters and truncate at
80 code points; JSON values are described by type rather than echoed. Previews are
not a secret-redaction system; use synthetic, non-confidential inputs only.
Malformed response JSON is a failed check, not an invalid evaluator configuration.

### Recorded output sets

Required root fields: `schema_version`, `dataset_id`, `dataset_version`,
`candidate_version`, `source`, and `outputs`.

`candidate_version` is a nonblank application/response-set version label, not
necessarily a model name. `source` is a nonblank provenance statement. The example
files explicitly say `synthetic-handwritten; not generated by an AI model`.
There is no implicit baseline/candidate role: the caller will choose roles.

Each output record has exactly `case_id` and `output`. Output must be a string and
may be empty, contain Unicode, or contain invalid JSON: response content is evidence
to evaluate, not input metadata to repair. Output sets must be nonempty with unique
case IDs. `validate_alignment` requires exact dataset ID/version and case-ID coverage;
order may differ. Missing/extra IDs are input errors, never silently skipped.

The loader and alignment function are separate: loading an output set does not
establish that it matches a particular dataset. Always call alignment before evaluation.

## Result contracts (Python only)

- `CheckResult`: evaluator ID, evaluator version, strict boolean `passed`, nonblank
  human explanation. Failed checks still need explanations. No fabricated scores.
- `CaseResult`: case ID, nonempty tuple of checks with unique evaluator IDs. Its
  `passed` property is derived as all checks passing; callers cannot set an inconsistent
  aggregate boolean.
- `RunProvenance`: dataset ID/version, dataset/output SHA-256 digests, candidate
  version, and evaluator suite version. 1C adds output-set ID/version, evaluation
  contract version, and Python integer conversion limit. These additions are either
  all supplied or all omitted for compatibility with the original constructors.
  Digests must be 64 lowercase hex characters.
- `RunResult`: provenance and nonempty results with unique case IDs; 1C adds optional
  keyword-only `result_sha256`. The runner always supplies it and all provenance fields.

These types validate internal structure only. They do not calculate hashes, prove
that checks ran, enforce full dataset coverage without a dataset, or serialize reports.
The runner must verify coverage and construct provenance from the actual evaluated
bytes. Suite version identifies the evaluator implementation/configuration; each
check also records its specific evaluator version. Package version is independent.
There are no result timestamps, token counts, latency values, or cost fields in v1.
Adding operational metrics requires values, units, source/method, and whether they
were supplied or measured. Missing metrics remain absent, never zero by default.

## Single-run interface (1C)

Import from `fixturedelta_lab.runner`:

```python
run_evaluation(dataset_path: Path, outputs_path: Path, *,
               output_set_id: str, output_set_version: str) -> RunResult
evaluate_run(dataset_bytes: bytes, outputs_bytes: bytes, *,
             output_set_id: str, output_set_version: str) -> RunResult
```

Both return exactly one case result per dataset case, in dataset order. Outputs are
joined by stable case ID, independent of their file order. Check order and evaluator
IDs/versions are those emitted by the existing adapter. All input and provenance
validation finishes before evaluation. A false check is a legitimate evaluated
failure, including malformed JSON inside a recorded response string. An invalid
dataset expectation or evaluator exception invalidates the entire run.

Schema-v1 output files have no output-set ID/version, so the caller must supply them:
ID uses the existing lowercase ASCII identifier grammar; version is `major.minor.patch`.
These are explicit assertions, not inferred from filenames or candidate labels.
Candidate/application version comes directly from the output document. The source
statement is covered by the file hash, but is not copied into provenance. Use only
synthetic, non-confidential metadata; labels are not a redaction or authenticity system.
`parse_dataset(bytes)` and `parse_outputs(bytes)` in `datasets` expose the same strict
parsing used by the file loaders. Mutable bytearrays and non-byte input are rejected.

### Fingerprints

- `dataset_sha256` and `outputs_sha256`: lowercase SHA-256 of the exact byte snapshot
  parsed. Each file is read once. No BOM removal, newline conversion, whitespace
  removal, JSON rewriting, or Unicode normalization precedes hashing.
- `result_sha256`: SHA-256 of canonical JSON containing exactly `fingerprint_version`,
  `provenance`, and `results`. Fingerprint version is `trustbench-run-v1`.
  Provenance contains all dataclass fields, including `python_integer_limit`; results
  are an array of `{case_id, checks}` with each check's `evaluator_id`,
  `evaluator_version`, `passed`, and `explanation`. Derived case status is excluded.
  The result digest itself is excluded. Python's `json.dumps` uses `sort_keys=True`,
  `ensure_ascii=True`, `separators=(",", ":")`, and `allow_nan=False`. Encode the
  resulting string as ASCII, with no BOM or final newline. Arrays retain dataset
  and evaluator check order. The encoding includes every explanation byte after
  JSON escaping; changing explanation wording changes the fingerprint.
- Contract version is `1.1.0`, suite version is `1.0.0`, and each evaluator retains
  `1.0.0`. The input wire schema remains integer `1`. Any later fingerprint encoding
  change must use a new fingerprint version. Package version is independent.

Exact-byte input digests deliberately change after formatting-only edits or output
reordering even when checks are identical. Identical bytes, labels, evaluator behavior,
and integer conversion settings yield equal runs and digests across the tested Python
versions. No timestamp, random ID, absolute path, platform username, or operational
metric is added. These hashes identify artifacts, not authenticity or model quality.
Manually constructing or replacing a dataclass does not recompute or verify a digest;
use the runner for complete evaluated evidence. No public report format is introduced.

### Run errors

`RunError.code` is a `RunErrorCode` string enum. `case_id` is populated only for
evaluator/result errors. There is no partial `RunResult` or partial-result attribute.
Messages give a corrective action. Parser, I/O, and evaluator exceptions are chained
as `__cause__` for detailed diagnostics; those causes can include input details/paths
and should not be treated as sanitized reports. Error precedence is file reads,
dataset validation, output validation, alignment, provenance, then ordered evaluation.
Incorrect Python call signatures/path argument types remain ordinary Python errors;
`KeyboardInterrupt`/`SystemExit` are not swallowed.

| Code | Meaning / corrective action |
| --- | --- |
| `DATASET_READ_ERROR` | Dataset cannot be read; check existence and permissions |
| `OUTPUTS_READ_ERROR` | Output file cannot be read; check existence and permissions |
| `DATASET_INVALID` | Correct malformed/empty dataset, duplicate IDs, or invalid expectations |
| `OUTPUTS_INVALID` | Correct malformed/empty output metadata or duplicate output IDs |
| `ALIGNMENT_INVALID` | Match dataset ID/version and provide exact case coverage |
| `PROVENANCE_INVALID` | Supply valid output-set ID and semantic version labels |
| `EVALUATOR_ERROR` | Evaluator raised; inspect cause, fix it, rerun the entire evaluation |
| `RESULT_INVALID` | Adapter returned inconsistent case/check IDs, order, or versions |

The runner performs no scoring, thresholds, model calls, comparison, report writing,
or filesystem mutation. Its byte interface also performs no file reads.

## Comparison contract 1.0.0 (2A)

`fixturedelta_lab.comparison.compare_runs(baseline: RunResult, candidate: RunResult)
-> ComparisonResult` performs no I/O or reevaluation. Argument position assigns the
roles; labels are not interpreted. Result types live in `fixturedelta_lab.comparison_types`.
All comparison dataclasses are frozen/slotted and nested collections are tuples.

### Evidence validation and alignment

The comparator accepts exact `RunResult`, `RunProvenance`, `CaseResult`, and
`CheckResult` types, not dictionaries or subclasses. It revalidates nested shapes
even when constructors were bypassed. Runs/cases must be nonempty; statuses are actual
booleans; IDs are valid and unique. Provenance must contain the complete 1C fields
and a valid run fingerprint, recomputed with the existing `trustbench-run-v1` encoding.
Legacy constructors with omitted provenance/digest cannot be compared.

Both runs must have identical dataset ID/version/SHA-256, evaluation contract,
evaluator suite, and Python integer conversion limit. Evaluation contract `1.1.0`
is currently supported. Case-ID sets must match, as must evaluator-ID sets within
each case. Versions must match for every paired evaluator; an evaluator ID must use
one version throughout each run. Labels for application/output sets, output versions,
and output-byte hashes may differ, and may also be identical.

Join by case and evaluator ID, never row position. Return cases/checks in baseline
order, which is dataset/evaluator order for runner-generated evidence. Candidate
ordering may differ if its fingerprint correctly covers that order. A reordered
input changes its run identity and therefore the comparison fingerprint even if
aligned outcomes are unchanged. All pairs validate before comparison construction.

No source dataset is supplied to comparison. It cannot independently confirm original
coverage/order, authenticate execution, or detect two identically truncated/rebuilt
and rehashed runs. Use trusted runner output. Hashes detect inconsistent evidence,
not deliberate forgery. Evaluator identities are matched exactly; comparison does
not execute or semantically verify their implementations.

### Transitions, summaries, and counts

Every `CheckComparison` stores evaluator ID/version, both boolean statuses, and both
original explanations. Its derived `transition` uses the table below. A
`CaseComparison` contains a case ID and these ordered checks. Its `baseline_passed`
and `candidate_passed` each mean all checks passed; its aggregate `transition` uses
those two booleans with the same table:

| Baseline | Candidate | Classification |
| --- | --- | --- |
| pass | fail | regression |
| fail | pass | improvement |
| pass | pass | unchanged pass |
| fail | fail | unchanged fail |

Case `summary` considers the individual check transitions:

- At least one regression and at least one improvement: `mixed`.
- Any regression without an improvement: `regression`.
- Any improvement without a regression: `improvement`.
- Otherwise: `unchanged_pass` or `unchanged_fail` from aggregate status.

For example, required-content pass→fail and forbidden-content fail→pass produce a
mixed summary, one check regression, one check improvement, and an aggregate
unchanged-fail transition. Pass→fail beside another unchanged failing check produces
a regression summary even though the aggregate case stays failed. No net score or
offsetting of improvements against regressions exists.

`TransitionCounts` has `regressions`, `improvements`, `unchanged_passes`,
`unchanged_failures`, and derived `total`. `CaseComparison.check_counts` counts checks.
`ComparisonResult.case_counts` counts aggregate case transitions; its `check_counts`
counts all check transitions. `cases_with_regressions` and `cases_with_improvements`
include mixed cases and are intentionally overlapping. `mixed_case_count` counts
mixed summaries. Counts and transitions are computed properties; callers cannot
provide inconsistent stored aggregates. A valid comparison with regressions returns
normally; there is no quality-gate decision or comparison-level pass flag.

### Comparison provenance and fingerprint

`ComparisonResult` stores `provenance`, ordered `cases`, and `comparison_sha256`.
`ComparisonProvenance` records shared dataset ID/version/SHA-256, evaluation contract,
suite, integer limit, and comparison contract version `1.0.0`. Its explicit `baseline`
and `candidate` `RunReference` values each contain output-set ID/version, application
version (`candidate_version` from the corresponding run), output-byte SHA-256, and
`run_sha256`. The run fingerprint is the run identity; no random IDs are introduced.
Paired evaluator IDs/versions remain in every compared check.

Comparison SHA-256 covers an internal JSON object with exactly `fingerprint_version`,
`provenance`, and `cases`. Fingerprint version is `trustbench-comparison-v1`. Provenance
and case/check arrays contain every dataclass field listed above, including both
explanations. Use `json.dumps(sort_keys=True, ensure_ascii=True, separators=(",", ":"),
allow_nan=False)`, encode as ASCII, with no BOM or trailing newline. Preserve baseline
case/check array order. Exclude the comparison digest itself and all derived
properties (transitions, summaries, statuses at case level, and counts). Their
semantics are bound by the comparison contract version. Changes to the encoding
require a new fingerprint version; changes to semantics require a contract version.

The helper `comparison_sha256(provenance, cases)` in `provenance` computes this digest.
The runner's hashing strategy and evaluation contract are unchanged. Comparison adds
no wall-clock values, filesystem paths, machine identity, or host configuration reads;
it copies only the behavior-relevant integer limit already recorded in the runs.
This internal encoding is not a JSON/Markdown export API. Manually replacing a
comparison dataclass does not recalculate its fingerprint; use `compare_runs` for
validated evidence and consistent hashes.

### Comparison errors

`ComparisonError` exposes `code: ComparisonErrorCode`, optional `role` (`baseline`
or `candidate` when validating one run), and optional `case_id`. Messages describe
corrective action; structural errors chain the validation cause. No partial comparison
is attached. Validation order is baseline structure/completeness/digest, candidate
structure/completeness/digest, shared metadata compatibility, supported contract,
case coverage, then evaluator coverage/versions in baseline order. Within a run,
duplicate cases/checks and inconsistent evaluator versions have their own codes.

| Code | Meaning / correction |
| --- | --- |
| `INVALID_RUN_TYPE` | Supply the existing typed RunResult |
| `INVALID_RESULT_STRUCTURE` | Recreate valid nonempty immutable evidence; inspect chained cause |
| `INCOMPLETE_PROVENANCE` | Reevaluate to populate omitted legacy provenance/digest |
| `RUN_FINGERPRINT_MISMATCH` | Recreate evidence from recorded inputs; stored hash does not match |
| `UNSUPPORTED_EVALUATION_CONTRACT` | This comparator supports evaluation contract 1.1.0 |
| `DATASET_MISMATCH` | Use identical dataset identity/version/bytes |
| `EVALUATION_CONTRACT_MISMATCH` | Reevaluate under one evaluation contract |
| `EVALUATOR_SUITE_MISMATCH` | Reevaluate under one evaluator suite version |
| `RUNTIME_SETTINGS_MISMATCH` | Match the recorded integer conversion limits |
| `DUPLICATE_CASE_ID` | Supply exactly one result per case ID |
| `CASE_ID_MISMATCH` | Match case coverage; message lists missing/unexpected IDs relative to baseline |
| `DUPLICATE_EVALUATOR_ID` | Supply exactly one check per evaluator ID within each case |
| `EVALUATOR_ID_MISMATCH` | Match evaluator coverage for the identified case |
| `EVALUATOR_VERSION_MISMATCH` | Use consistent evaluator versions within and across runs |

Legitimate failed checks and regressions/improvements are result values, never these
errors. Invalid evidence never becomes an ordinary regression.

## Implemented gates and report adapter

2B implements `evaluate_gate(comparison, policy)` with strict zero check regressions
by default, optional maximum candidate check failures, and optional exact minimum
candidate check pass rate. Rules are independent; mixed cases and regressions within
already-failing cases remain visible. See [gate contract](gate-contract.md) for
precise denominators, policy validation, error codes, and provenance. Category/language
slices remain unimplemented. 2C exports complete comparison/gate reports.

Implemented CLI codes: `0` valid gate pass; `1` valid gate failure; `2` invalid
input/configuration or incompatible evidence; `3` runtime, file-access or report-output
failure. Contract failure and an evaluated response failing a check remain distinct.
The [2C report contract](report-contract.md) specifies policy files, serialization,
output publication and precise error boundaries. The pure gate API has no process exit.

## Synthetic fixture intent

| Case | Baseline intent | Candidate intent |
| --- | --- | --- |
| `en-label-001` | pass | fail: extra punctuation |
| `el-label-001` | pass | pass |
| `en-rules-001` | pass | pass |
| `el-rules-001` | fail: missing required phrase | pass |
| `en-json-001` | pass | fail: boolean where integer required |
| `el-json-001` | pass | pass |

This table originated as the handwritten 1A test oracle. The 1B single-case tests
now verify every listed outcome against both fixture sets. These are synthetic
test results, not model measurements. The 2A comparison tests verify two case/check
regressions (`en-label-001`, `en-json-001`), one improvement (`el-rules-001`), and
three unchanged passing cases. The 2C CLI exports this evidence in JSON and Markdown.
