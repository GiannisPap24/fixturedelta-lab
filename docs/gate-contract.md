# Gate contract 1.0.0 (Milestone 2B)

This is a Python-only policy and result contract. It implements no CLI, report export,
network access, model execution, or reevaluation. Existing evaluation contract 1.1.0
and comparison contract 1.0.0 are unchanged.

## Policy interface

```python
from fractions import Fraction
from fixturedelta_lab.gate_types import GatePolicy
from fixturedelta_lab.gates import evaluate_gate

policy = GatePolicy()  # strict zero evaluator-check regressions
# Optional additional constraints, explicitly configured:
policy = GatePolicy(
    policy_id="release-review",
    policy_version="1.0.0",
    max_regressions=0,
    max_candidate_failures=2,
    min_candidate_pass_rate=Fraction(3, 4),
)
# result = evaluate_gate(comparison, policy)
```

`GatePolicy` is a frozen, slotted dataclass. Its complete supported fields:

| Field | Default | Validation |
| --- | --- | --- |
| `policy_id` | `strict-regression` | Existing lowercase ASCII identifier grammar |
| `policy_version` | `1.0.0` | Existing major.minor.patch grammar |
| `max_regressions` | `0` | Actual nonnegative int, not bool |
| `max_candidate_failures` | `None` | Disabled, or actual nonnegative int |
| `min_candidate_pass_rate` | `None` | Disabled, or exact `fractions.Fraction` in [0, 1] |

No coercion from dictionaries, strings, floats, booleans, or integer rate arguments.
For a decimal threshold use `Fraction("0.75")`; for a ratio use `Fraction(3, 4)`.
Fraction values are reduced canonically, so 6/8 and 3/4 are the same policy value.
Constructing a Fraction from a float captures that float's binary value; callers
should use integer ratios or decimal strings when specifying intended exact limits.
Non-finite numeric inputs cannot be valid fractions. Unknown keyword fields raise
Python `TypeError`; invalid supported values raise `ContractError`. Configuration-file
parsing belongs to the [2C adapter](report-contract.md), which provides strict policy
JSON parsing. No policy language is evaluated. Supplied policy identity/version are
caller assertions; changed policies should receive a new version, and the hash detects
reused labels.

The three rules are upper bounds on regressions/failures and a lower bound on passes.
All individually valid combinations are jointly satisfiable by an all-passing,
zero-regression candidate. Different failure-count/pass-rate limits may be redundant
or differ in strictness; that is not a conflict. Both are enforced independently.
No duplicate rule configuration, alternate denominator, weighting, or override fields
are supported, so conflicting alternate settings are rejected as unknown fields.

## Units and decisions

Every unit is an individual `(case_id, evaluator_id)` check, not a case. The same
evaluator used in different cases counts once per case. Every check has equal weight.
Stable order is comparison case order followed by check order within each case.

| Rule ID | Observation | Pass condition |
| --- | --- | --- |
| `max-regressions` | Checks with baseline pass and candidate fail | observed ≤ configured maximum |
| `max-candidate-failures` | All failing candidate checks, including unchanged failures | observed ≤ configured maximum |
| `min-candidate-pass-rate` | Passing candidate checks / all compared checks | observed ≥ configured minimum |

Rules execute in table order, omitting disabled optional rules. All configured rules
are evaluated; the gate passes only if every rule passes. No improvement is subtracted
from a regression count. A mixed case or a case that was already failing can therefore
cause a gate failure even when aggregate case-regression count is zero. No case-level
summary substitutes for the underlying check statuses.

The denominator is the total number of paired evaluator checks across every case.
Empty comparisons/cases are invalid, so it cannot be zero. Ratios use exact Fraction
arithmetic, never floating-point tolerance or rounded percentages. GateResult retains
raw `candidate_passes` and `total_checks` as well as the reduced observed fraction.
The six-case fixture has eight checks: six candidate passes and two failures, yielding
3/4, rather than the case-level rate 4/6. Its two regressions fail the default policy,
despite one improvement. The default policy alone can pass a candidate with unchanged
failures; enable the optional rules to constrain those failures.

## Evidence validation and errors

`evaluate_gate(comparison: ComparisonResult, policy: GatePolicy) -> GateResult` first
revalidates the exact policy type and fields. It then validates exact comparison,
provenance, run-reference, case, and check types; nested invariants; nonempty tuples;
unique case/check identities; valid strict boolean statuses; and consistent evaluator
versions across cases. Supported comparison/evaluation contracts are 1.0.0/1.1.0.
Finally it recomputes the comparison fingerprint using the unchanged 2A encoding.
Only after all validation succeeds does it count checks or produce any rule outcomes.

`GateError` exposes a stable string-enum `.code`:

| Code | Correction |
| --- | --- |
| `INVALID_POLICY` | Supply a validated GatePolicy; inspect chained constructor/shape cause |
| `INVALID_COMPARISON` | Recreate complete typed comparison evidence; inspect chained cause |
| `INCOMPATIBLE_COMPARISON` | Use supported comparison 1.0.0 and evaluation 1.1.0 contracts |
| `COMPARISON_FINGERPRINT_MISMATCH` | Recreate the comparison; its evidence differs from its hash |

Invalid evidence/policy raises, with no partial GateResult. Legitimate rule failures
return a normal GateResult with `passed=False`; they do not raise, terminate a process,
or fail pytest. The API does not catch user interrupts or arbitrary system failures.
Incorrect Python call signatures remain ordinary `TypeError` exceptions.

## Immutable results

`GateResult` has `provenance`, ordered `rules`, ordered `regressions` and
`candidate_failures`, raw `total_checks` and `candidate_passes`, and `result_sha256`.
Its `.passed` property derives from all rule outcomes. Each affected `CheckIdentity`
contains `case_id`, `evaluator_id`, and `evaluator_version`. Regressions are also
candidate failures. These identities remain available even when a configured rule
permits them. Failure identities are present even if optional failure/rate rules are
disabled; they also identify checks that can improve a failing pass-rate rule.

Each `GateRuleResult` stores `rule_id`, `observed`, and `permitted`. Count values are
ints; rate values are Fractions. `.passed` and `.explanation` are deterministic derived
properties. Explanations name the rule, pass/fail, observation, permitted bound, and
corrective action. GateResult construction checks count/identity/observation agreement
and rule order. All new types are frozen/slotted and nested collections are tuples.

## Provenance and canonical fingerprints

GateProvenance records `comparison_sha256` (the comparison identity),
`comparison_contract_version`, `policy_id`, `policy_version`, `policy_sha256`, and
`gate_contract_version`. Gate evaluation contract is `1.0.0`. New helpers extend the
existing `provenance.py`; run/comparison encodings remain unchanged.

Every hash uses SHA-256 of `json.dumps(sort_keys=True, ensure_ascii=True,
separators=(",", ":"), allow_nan=False)` encoded as ASCII, without BOM or final newline.
Fractions encode as objects with integer `numerator` and positive `denominator`, in
their reduced form. Optional disabled fields encode as null. Arrays preserve order.

- Policy payload has exactly `fingerprint_version: "trustbench-gate-policy-v1"` and
  `policy`, containing every GatePolicy field. The rate is converted to the rational
  object described above. Identity/version changes therefore affect the policy hash.
- Gate payload has exactly `fingerprint_version: "trustbench-gate-v1"`, `provenance`,
  `rules`, `regressions`, `candidate_failures`, `total_checks`, `candidate_passes`, and
  `passed`. Provenance contains every GateProvenance field. Each rule includes `rule_id`,
  encoded `observed`, encoded `permitted`, derived `passed`, and derived `explanation`.
  Each affected check includes all CheckIdentity fields. The gate digest itself is
  excluded. Unlike comparison hashes, this projection includes derived rule explanations
  and outcomes explicitly; changes to their wording change the digest.

No machine paths, timestamps, environment reads, secrets, or random identifiers are
added. The comparison hash transitively binds evaluation metadata already recorded
upstream. Identical validated comparison and policy values yield identical results
and hashes. Encoding changes need a fingerprint-version change; semantic changes
need a contract-version change. Manual dataclass replacement does not recompute or
authenticate hashes. Internal canonical JSON is not an export format or API.

## Limits and future adapters

Fingerprint validation establishes internal consistency, not authenticity, original
coverage, or proof that evaluation occurred. The gate does not possess original runs,
datasets, or output bytes, and cannot independently validate referenced run digests.
Deliberately rebuilt/rehashed incomplete evidence remains outside this trust boundary.
Use trusted output from the existing runner and comparator. Policies measure literal
synthetic conformance only, not truth, safety, model quality, or statistical significance.

The separately implemented [2C CLI/report adapter](report-contract.md) maps a valid
gate pass to exit 0, valid gate fail to 1, invalid policy/evidence/input to 2, and
runtime/file-access/report-output failures to 3. It preserves exact rates, mixed-case
regressions, provenance and independent rule evidence. These exits and public reports
belong to the adapter; this Python gate API remains pure and unchanged.
