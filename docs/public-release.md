# Sanitized public release verification

Date: **2026-10-24**. This is a local release candidate. Public GitHub creation and
publication require separate owner approval. No remote, push or release tag was
created during this preparation.

## Snapshot and privacy boundary

The public repository begins with one new root commit, titled
`feat: initial public release of FixtureDelta Lab`. Its parentless history contains
only the sanitized release snapshot. No original Git objects, refs, tags, reflogs,
alternate object stores, virtual environments, private audit evidence, local tools,
caches or generated reports were transferred into the public Git tree.

The private development repository and all of its existing files/history remain
unchanged. This public tree preserves the approved implementation, synthetic data,
licence and project configuration. Historical milestone documents describe earlier
development states; their reported test counts and former product names are retained
as historical evidence, not current release instructions or reachable public commits.

The initial allowlist contained 67 source files. This verification document is the
only additional public file, giving **68 reviewed tracked files**. No binary or
symlink is included. The exact inventory is listed below.

## Intentional documentation changes

- `AGENTS.md`: replace the machine-specific browser-skill location with discovery
  of the skill in the current session.
- `docs/milestone-1a.md` and `docs/milestone-1b.md`: replace real checkout/interpreter
  locations with portable descriptions; remove unnecessary unrelated-environment
  inventory from the historical 1A record.
- Historical milestone/audit documents: omit private development commit identifiers.
  Their technical observations remain historical records.
- `docs/portfolio-release.md`: explicitly mark the old release/history assessment as
  historical and point to this public verification record.
- `README.md`: clarify report locations and synthetic-origin limitations; describe
  the sanitized snapshot and link to current verification.
- `docs/release-readiness.md`: replace the old publication handoff with a procedure
  restricted to this clean public repository.

No application code, test, synthetic fixture, dependency lock or packaging manifest
changed. No regression test was needed for these documentation-only corrections.
The five legacy fingerprint namespace constants remain unchanged, preserving report
compatibility. Synthetic rejection tests intentionally contain fictional paths and
credential-shaped markers; these are not real credentials or machine locations.

## Verified behavior and quality

| Check | Result |
| --- | --- |
| Python 3.12.10 complete suite | 632 passed |
| Python 3.14.4 installed-wheel suite | 632 passed, isolated Python mode, working directory outside the source root |
| Targeted coverage | 949/949 statements and 268/268 branches across 15 configured modules; 100% |
| Ruff lint and formatting | Pass; all 30 allowlisted Python source/test/script files |
| Patched uv | Project-local 0.13.4; wrapper validates >=0.13.4,<0.14 |
| Dependencies | Locked sync/check; hash-checked development install; compatibility checks pass |
| Packaging | Source distribution and wheel built with pinned uv_build 0.13.4 |
| Fresh wheel environments | Python 3.12 and 3.14; no runtime dependency install; imports verified in site-packages |
| Installed entry points | Console and `python -m fixturedelta_lab`, help and exits 0/1/2/3 verified |
| README Python example and relative links | Executed on both interpreters; documentation file/fragment links checked |
| Synthetic demo | Python 3.12, Python 3.14 wheel and PowerShell wrapper pass |
| Determinism | JSON and Markdown bytes identical across interpreters and entry points |
| VS Code | Workspace-relative settings, manual tasks and debug-target commands verified |

One Python 3.14 development wheel was absent from the local cache during setup and
was downloaded with the hashes exported from the unchanged lockfile. Tests, builds,
application execution and subsequent dependency checks ran offline. Reproducibility
on a host with a populated cache is verified; an empty-cache offline bootstrap is
not claimed. No global interpreter, tool, editor or security configuration changed.

The source archive includes the reviewed source files plus generated package metadata.
Its backend-formatted `pyproject.toml` is semantically identical to the source; the
generated `pyproject.toml.orig` matches the original manifest bytes. Wheel package
files match the source, RECORD hashes/sizes are verified, MIT text is included and
there are no runtime `Requires-Dist` entries. No environment, scanner, generated
report or private development history appears in either distribution.

## Synthetic comparison results

| Scenario | Cases / checks | Regressions | Improvements | Candidate passes | Exit |
| --- | --- | --- | --- | --- | --- |
| Baseline vs candidate, strict policy | 6 / 8 | 2 | 1 | 6/8 | 1 |
| Baseline vs baseline, strict policy | 6 / 8 | 0 | 0 | 7/8 | 0 |
| Baseline vs candidate, explicit allow policy | 6 / 8 | 2 | 1 | 6/8 | 0 |
| Malformed/incompatible input | No valid report | — | — | — | 2 |
| Occupied report directory | Existing bytes preserved | — | — | — | 3 |

The passing strict comparison retains one unchanged failure. Improvements do not
cancel regressions. Invalid input is never treated as an ordinary failed quality gate.

Canonical report fingerprints remain:

```text
fail: 08b2702208de2ac7caf0f38152939f4a7f907113f9e7444aa4954582c156b10e
pass: 5d69da236056a383b4f6e1c0906cac9c6d794e0851470bb091f8cef717f8a638
```

These are evidence consistency digests, not signatures or proof of AI correctness.

## Security review and remaining limitations

Gitleaks 8.30.1 and contextual privacy checks cover the allowlisted source, complete
new Git history, staged content and both distribution archives. The reviewed tree
has no confirmed P0/P1 issue or unintended personal/machine-path disclosure. Only
handwritten synthetic evaluation data is intended for release. A clean scan is not
a guarantee that all possible secrets or vulnerabilities have been found.

The existing trusted-local-input boundary remains: no total file-size/case-count
quota, no adversarial filesystem-parent protection, no crash-durability guarantee,
and no authenticity signatures. JSON depth/digit limits, schema validation, Markdown
escaping, exclusive output creation and raw-text report omission remain intact.
Metadata screening is heuristic, so callers must still use nonconfidential labels.
Recorded responses are never executed. The application has no network client or
telemetry; pytest socket guards are not an operating-system network sandbox.

Validation covers Windows and the two stated Python versions. Current editor checks
exercise saved configuration/commands, not interactive F5/task-menu clicks. Historical
debug-adapter observations are explicitly historical. No live model benchmarks,
factuality/safety guarantee, multilingual generalization or cross-OS CI is claimed.

MIT: **Copyright (c) 2026 GiannisPap24**. Development/build tools retain their own
licences. Package-index upload remains disabled by the private-upload classifier.

See the [publication procedure](release-readiness.md#publication-procedure--execute-only-after-owner-approval)
for the separately authorized handoff. Publish only the reviewed clean repository;
never upload a ZIP of the working directory or its ignored verification evidence.

## Public file inventory

```text
.gitattributes
.gitignore
.python-version
.vscode/extensions.json
.vscode/launch.json
.vscode/settings.json
.vscode/tasks.json
AGENTS.md
LICENSE
README.md
docs/architecture.md
docs/demo.md
docs/evaluation-contract.md
docs/final-mvp-audit.md
docs/gate-contract.md
docs/milestone-1a.md
docs/milestone-1b.md
docs/milestone-1c.md
docs/milestone-2a.md
docs/milestone-2b.md
docs/milestone-2c.md
docs/milestone-3a.md
docs/naming.md
docs/portfolio-release.md
docs/public-release.md
docs/release-readiness.md
docs/report-contract.md
docs/roadmap.md
docs/vscode.md
pyproject.toml
scripts/demo.ps1
scripts/demo.py
scripts/uv.ps1
src/fixturedelta_lab/__init__.py
src/fixturedelta_lab/__main__.py
src/fixturedelta_lab/cli.py
src/fixturedelta_lab/comparison.py
src/fixturedelta_lab/comparison_types.py
src/fixturedelta_lab/datasets.py
src/fixturedelta_lab/domain.py
src/fixturedelta_lab/gate_types.py
src/fixturedelta_lab/gates.py
src/fixturedelta_lab/metrics/__init__.py
src/fixturedelta_lab/metrics/_common.py
src/fixturedelta_lab/metrics/content.py
src/fixturedelta_lab/metrics/exact.py
src/fixturedelta_lab/metrics/json_structure.py
src/fixturedelta_lab/policies.py
src/fixturedelta_lab/provenance.py
src/fixturedelta_lab/py.typed
src/fixturedelta_lab/reporting.py
src/fixturedelta_lab/runner.py
tests/conftest.py
tests/fixtures/baseline-v1.json
tests/fixtures/candidate-v2.json
tests/fixtures/golden-v1.0.0.json
tests/fixtures/policy-allow-v1.json
tests/test_cli.py
tests/test_comparison.py
tests/test_datasets.py
tests/test_demo.py
tests/test_domain.py
tests/test_gates.py
tests/test_metrics.py
tests/test_policies.py
tests/test_reporting.py
tests/test_runner.py
uv.lock
```
