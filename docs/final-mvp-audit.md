# Final MVP technical and security audit

> Historical verification record using the names and tools at that checkpoint.
> For current commands, names and licence, see [README](../README.md) and
> [portfolio release verification](portfolio-release.md).

Audit date: **2026-10-24**. Scope: this repository only, through Milestone 3A plus
the narrow corrections below. All fixture/probe data were synthetic. No LLM calls,
remote creation, push, deployment, publication or external source-code review occurred.

## A. Verdict

**Pass for the documented local, bounded-input MVP after corrections. Public release
remains pending owner decisions.** Three confirmed P1 findings were corrected:
quadratic work in the JSON depth precheck, an affected uv tool version, and ambiguous
Windows executable resolution. No P0 was confirmed. This is an engineering audit,
not certification, a penetration-test guarantee or evidence of production AI quality.

The initial source/contract/history review preceded audit implementation changes.
Further bounded probes and end-to-end verification reproduced the JSON and Windows
issues before their respective corrections. Findings below distinguish observed
defects from existing limitations and future work.

## B. Prioritized findings and evidence

| ID | Priority | Finding and evidence | Disposition |
| --- | --- | --- | --- |
| F01 | P1 | The old `metrics/json_structure.py::_check_depth` used an unanchored quoted-string regex. A synthetic quote followed by 30,000 escaped quotes (60,001 ASCII bytes) exceeded a five-second subprocess deadline; smaller probes grew disproportionately. This allows modest malformed recorded output to stall evaluation. | Corrected at `src/trustbench_ai/metrics/json_structure.py:19`. Two linear passes preserve the original lexical decisions. This is a reproduced resource defect, not a general performance benchmark. |
| F02 | P1 | Installed uv 0.13.3 and the old `pyproject.toml:26` requirement permitted a tool with an affected bundled CA store. OSV returned GHSA-hq85-5cpj-mr62 and its alias PYSEC-2026-4321; these describe one issue, fixed in 0.13.4. | Requirement raised to >=0.13.4,<0.14; backend pinned to 0.13.4 at `pyproject.toml:2`. Old uv is rejected. Patched project-local uv verified. |
| F03 | P1 | `scripts/demo.ps1:24` selected `.Source` from every `Get-Command uv -CommandType Application` result. With patched local uv and the existing global uv on PATH, PowerShell attempted to execute their combined path and failed before the demo. | Select the first executable, matching PATH priority. An isolated two-tool regression fails before the change and passes after it (`tests/test_demo.py:13`). |
| F04 | P2 | README setup and the VS Code opening instructions embedded this host's checkout path. | Replaced by a checkout placeholder/current-directory command (`README.md:60`, `docs/vscode.md:3`). Historical evidence remains historical. |
| F05 | P2 | Earlier shortlist searches had missed active GoldenDiff and TraceVerdict repositories. | Updated `docs/naming.md` with direct conflicts and a qualified alternative. No rename. |
| F06 | P3 | Whole-file reads and unrestricted total case/text sizes remain (`datasets.py:127`, `cli.py` input reader). The JSON depth/digit limits do not cap all memory/CPU use. | Documented bounded-local-input assumption. General upload quotas and OS isolation are future hardening, not implemented features. |

F02 affects online dependency retrieval, not offline evaluator execution. The upstream
advisory identifies uv <0.13.4 and the bundled certificate-store change; its severity
label is High, while the OSV/GitHub database record used Critical. This report's P1
classification reflects this project's development-tool exposure, not a new CVSS score.
[Upstream uv advisory](https://github.com/astral-sh/uv/security/advisories/GHSA-hq85-5cpj-mr62).

## C. Corrective actions and regression evidence

- **JSON precheck:** precompute quoted span ends from right to left, then count
  delimiters from left to right. This avoids retrying every suffix of an unterminated
  string. The original lexical behavior is retained even for malformed strings,
  including backslash/newline handling. A compatibility regression compares depth
  decisions against the old regex over **37,449** short inputs; another bounds a
  400,001-byte malformed input in an isolated subprocess (`tests/test_metrics.py:228`
  and `:256`). Existing depth, integer, escaped-delimiter and fixture tests pass.
- **Toolchain:** patched uv was downloaded from PyPI using Python HTTPS, with the
  wheel's SHA-256 checked against PyPI metadata, and extracted under ignored
  `artifacts/audit-tools/`. No global tool was upgraded. An actual old-tool invocation
  fails the new requirement; patched lock/sync/build invocations pass. The matching
  backend bump keeps bundled offline builds possible. The dependency lock is unchanged.
- **Windows wrapper:** first-match resolution is covered using two synthetic tool
  stubs in an isolated temporary project, then verified with both real uv copies on
  PATH and the real demo. No execution policy or global settings were changed.
- **Documentation:** portable setup, current stopping point, collision research,
  resource limitations and release/ownership decisions are now explicit.

No evaluator type, API, contract version, fixture, output schema or fingerprint
algorithm changed. The lexical resource fix preserves outcomes/explanations, so
evaluator and suite versions remain unchanged. The accepted demo hashes below match
the 3A checkpoint. No tests were weakened to obtain a pass.

## D. Exact audit file inventory

Modified (10):

1. `AGENTS.md` — recognize the separately authorized audit and its stopping point.
2. `README.md` — audited status, portable setup, patched tool prerequisite and links.
3. `docs/evaluation-contract.md` — linear precheck and remaining resource boundary.
4. `docs/naming.md` — updated collision evidence and recommendation.
5. `docs/roadmap.md` — audit completion; release still separate.
6. `docs/vscode.md` — portable opening instructions.
7. `pyproject.toml` — patched uv requirement and matching backend pin.
8. `scripts/demo.ps1` — deterministic first executable selection.
9. `src/trustbench_ai/metrics/json_structure.py` — linear compatible depth scan.
10. `tests/test_metrics.py` — two JSON regressions.

Created (3):

1. `tests/test_demo.py` — Windows executable-resolution regression.
2. `docs/final-mvp-audit.md` — this A–M technical/security report.
3. `docs/release-readiness.md` — release checklist, licence inventory and owner decisions.

Ignored local evidence includes `artifacts/audit-research/`, `artifacts/audit-tools/`,
`artifacts/audit-verification-final/`, `artifacts/verify_final_audit.py`, coverage output,
temporary probes, updated environments and `dist/`. These are not release-source files
or staged changes. The three original demonstration input files remain byte-identical.

## E. Git checkpoint

Milestone 3A was reviewed, verified and committed **before** audit corrections:

- Branch: `main`.
- Commit: `private-checkpoint`.
- Subject: `feat: add reproducible AI evaluation demo`.
- Parent: `private-checkpoint`.
- Identity: approved repository-local `GiannisPap24` / GitHub noreply identity.
- Inventory: exactly seven modified and four new 3A files; working tree clean after commit.
- Before checkpoint: 621 tests, Ruff lint/format, offline lock check and diff check passed.

HEAD still points at that checkpoint. The 13 audit files are **uncommitted and unstaged**.
There are six reachable commits, no configured Git remote, and no publication.

## F. Current test results

| Environment | Execution | Result |
| --- | --- | --- |
| Python 3.12.10, editable project | Complete offline suite; also run with branch coverage | **624 passed** |
| Python 3.14.4, rebuilt installed wheel in `.venv-package` | `python -I -m pytest`, cwd outside source root, explicit repository test/config paths | **624 passed** |
| Python 3.14.4, new isolated environment under artifacts | Offline wheel install with no dependencies; import origin asserted under that environment's site-packages; actual console/module CLI | Pass |

The increase from 621 is three focused tests, not more synthetic benchmark cases.
The new launcher test is Windows-specific and explicitly skips if its platform or
Windows PowerShell is absent. Both audited Windows interpreters ran it successfully.
Tests contain in-process network guards; this is not an OS network sandbox. Tests
and fixtures are read from the checkout; the 3.14 application is imported from the
installed wheel with no source-path injection.

## G. Quality, dependencies and packaging

- Ruff 0.17.2 lint and format: **pass**, 47 Python files formatted.
- Targeted Coverage.py 7.17.0: **949/949 statements and 268/268 branches**, zero
  missing statements/partial branches. Targets are the 15 configured evaluator,
  loader, runner, comparison/gate, provenance, policy, reporting and CLI modules.
  This is not whole-repository coverage; domain contracts, demo scripts and entry
  point coverage are not included in that percentage.
- uv 0.13.4: `lock --check --offline`, `sync --locked --offline --no-python-downloads`
  and dependency compatibility checks pass. Nine project/dev packages resolve;
  no runtime dependencies. `uv.lock` did not need regeneration.
- `uv build --offline`: sdist and wheel built with pinned uv_build 0.13.4. The wheel
  was reinstalled for 3.14 tests, and installed without dependencies into a genuinely
  new isolated 3.14 environment. Package metadata/contents were inspected.
- VS Code: workspace JSON/interpreter/Ruff paths, nonautomatic tasks, every task
  command and all three debug targets pass with patched uv on the process PATH.
  The installed debug adapter stopped at `cli.py:79`, supplied a stack, continued
  and exited 1 with the expected report pair. This was a DAP session, not a claim
  of manually clicking F5 in the editor. No extensions were installed or changed.

The verification used `artifacts/audit-tools/uv.exe` by prepending its directory to
the child-process PATH. The older global uv 0.13.3 remains installed. An ordinary
terminal/editor must resolve a compatible patched uv before using the updated
project. No persistent PATH, global tool or editor configuration was changed.

## H. Security and reproducibility

### Reviewed behavior

Strict schema/type/duplicate-key validation, literal Unicode and whitespace behavior,
finite JSON numeric rules, boolean/integer distinctions, complete case alignment and
dataset ordering are covered by existing tests and source inspection. Comparison
validates identities, hashes, versions, coverage and evaluator compatibility before
pairing by ID. Mixed cases preserve individual regressions; improvements do not
offset them. Gate thresholds are inclusive, independent and use exact rational
pass rates over individual checks. Invalid evidence does not become a failed gate.

CLI exits distinguish pass (0), policy failure (1), invalid input/evidence (2), and
runtime/output failure (3). Expected diagnostics omit raw paths and exception text.
Recorded outputs are parsed/evaluated as data: no eval, shell execution, unsafe
deserialization, networking or telemetry exists in application code.

Report metadata is screened for recognizable secrets/paths and unsafe Unicode;
this is a heuristic, not general redaction. Raw prompts, response text, source labels
and evaluator previews are omitted from exported reports. Callers must still use
nonconfidential labels. Markdown escaping protects table/HTML/link structure
(`reporting.py:30`, `:49`). JSON and Markdown rendering use deterministic ordering.

`reporting.py:216` exclusively creates a fresh target, stages both report files and
publishes the pair by rename. Existing paths, including existing symlink targets,
are refused. Expected write failures do not publish a successful partial pair;
tests cover collision/failure cleanup. It assumes trusted local parent directories:
it is not hardened against an adversary concurrently swapping parents, power loss
or exotic network filesystem semantics. The demo only declares success after its
report assertions and verification manifest; a failed later scenario can leave
earlier complete report pairs, which is documented behavior.

Input byte hashes and canonical evidence fingerprints are repeatable consistency
checks, not signatures or proof that a caller supplied authentic/complete historical
evidence. Files are read whole; large-input quotas and process isolation remain
outside this CLI. The JSON fix removes the reproduced suffix-rescan defect without
claiming immunity to all resource exhaustion.

### Privacy/history and advisories

All **107 distinct reachable historical file blobs across six commits** were scanned
for credential/private-key patterns, email addresses and local home paths, alongside
tracked-file review. The two credential hits are explicit synthetic rejection cases
in `tests/test_reporting.py:136`/`:137`. No actual credential or confidential dataset
was identified. Commit author/committer fields all use the approved noreply identity.
Historical docs and AGENTS contain generic local paths; tests contain intentional
path examples. No history rewrite or unrelated-project inspection occurred.

This was pattern-based review of reachable history, not an exhaustive forensic audit
of unreachable objects/reflogs or proof that all secrets/vulnerabilities are absent.
Ignored outputs/environments/builds are excluded from Git. The chosen public identity
and historical machine details still deserve owner review before publication.

OSV was queried by exact public package/version for eight locked third-party Python
development dependencies, uv and uv_build. Only uv 0.13.3 returned the advisory above.
Requerying uv and uv_build 0.13.4 returned no entries; the other eight queries also
returned no entries. No pagination was indicated. This is a dated database result,
not proof of safety; it does not cover all native tool internals, Python/OS/editor
components or future disclosures. [OSV API documentation](https://google.github.io/osv.dev/api/).

Read-only web/GitHub/PyPI/OSV research and the patched tool download used the network.
Offline application/demo/test verification did not call a model or remote service.
The security-best-practices skill supplied the review/report workflow; its bundled
Python references target web frameworks, so no framework-specific guidance was
applied to this standard-library CLI.

### Actual rerun of the demo

The real PowerShell wrapper on 3.12 and the demo verifier with the installed 3.14
wheel each invoked seven CLI scenarios. Both console and module entry points ran
the fail/pass cases; malformed input, incompatible dataset version and occupied
output directory exercised exits 2/2/3. The fresh isolated wheel independently
matched the successful report bytes through both entry points.

| Scenario | Cases/checks | Check transitions | Candidate passes | Gate/exit |
| --- | --- | --- | --- | --- |
| Baseline vs candidate | 6 / 8 | 2 regressions, 1 improvement, 5 unchanged passes | 6/8 | Strict FAIL / 1 |
| Baseline vs baseline | 6 / 8 | 0 regressions/improvements, 7 unchanged passes, 1 unchanged failure | 7/8 | Strict PASS / 0 |

The second result passes the no-regression policy despite an existing failed check;
it does not claim every response is correct. Input bytes stayed unchanged. JSON and
Markdown bytes matched across Python versions and entry points. Report fingerprints:

```text
fail: 08b2702208de2ac7caf0f38152939f4a7f907113f9e7444aa4954582c156b10e
pass: 5d69da236056a383b4f6e1c0906cac9c6d794e0851470bb091f8cef717f8a638
```

Current logs/manifests live under ignored `artifacts/audit-verification-final/`.
Earlier milestone reports are historical evidence, not substituted for these reruns.

## I. Portfolio README assessment

The README presents the concrete regression-testing problem, deterministic versus
semantic limits, all three evaluator families, comparisons, configurable gates,
CLI exit codes, reports, actual demo results, architecture, setup/testing and limits.
It makes no hallucination-detection or general-correctness guarantee. The two-minute
demo and honest synthetic provenance are useful portfolio evidence. Changes were
limited to status, tool prerequisites, portable paths, current report links and the
revised name recommendation; no marketing claims or fabricated measurements added.

## J. Naming recommendation

Recommend **FixtureDelta Lab**, subject to owner selection and a fresh availability
check before release. Current GitHub name queries for `fixturedelta` and
`fixturedelta-lab` returned zero matches with incomplete-results false; quoted public
web searches surfaced no clear project match. That is limited collision evidence,
not trademark, domain, organization or PyPI availability clearance.

GoldenDiff Lab is weaker because [dkej123/goldendiff](https://github.com/dkej123/goldendiff)
already exists; TraceVerdict has a closely related
[coding-agent regression project](https://github.com/weaqaq/traceverdict).
TrustBench has direct evaluation-domain conflicts. See [naming research](naming.md).
No directory/package/command/import was renamed.

## K. Licence and attribution recommendation

Recommend **MIT** for the small educational portfolio, with Apache-2.0 as the
alternative if the owner prioritizes an explicit patent grant. The
[release checklist](release-readiness.md#licence-options-and-dependencies) records
official licence sources, development/build dependency licences and attribution
considerations. No licence was selected or written. The owner must approve the
public holder wording and confirm rights to publish code and synthetic fixtures.

## L. Publication readiness and owner decisions

Technical checks pass within the stated Windows/local-input scope. Public release
is pending: name, licence, copyright-holder wording/rights confirmation, acceptance
of the public identity/history, review/commit of audit changes, and explicit permission
for remote creation/push. Ensure the terminal/editor uses patched uv. No CI or
cross-OS claim is made; those are optional future improvements for this MVP.

Proposed description/topics and a blocker-versus-optional checklist are in
[release readiness](release-readiness.md). No LICENSE, remote, tag or release was created.

## M. Recommended release procedure

After the owner decisions, apply any approved rename/licence in a separate reviewed
change. Re-run the documented quality/install/demo checks, review the staged diff
and history, and commit only with authorization. Create/push to the owner-selected
repository only after separate publication authorization; then verify public
README/licence rendering. Keep generated evidence out of Git. Package-index
publication is a distinct optional action. **Stop after this audit.**
