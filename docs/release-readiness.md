# FixtureDelta Lab release readiness

Local release preparation date: **2026-10-24**. The owner approved FixtureDelta Lab,
repository name `fixturedelta-lab`, MIT and `Copyright (c) 2026 GiannisPap24`.
Local audit and release checkpoints are authorized. **Public publication is not.**
See [public release verification](public-release.md) for this sanitized candidate.
The [portfolio verification](portfolio-release.md) is a historical development record.

## Release checklist

- [x] Final product/distribution/module/command names applied consistently.
- [x] Official MIT text, owner-approved notice and package licence metadata.
- [x] Synthetic fixtures remain unchanged and clearly labelled.
- [x] README describes recorded-output checks without semantic or model-quality claims.
- [x] Patched project-local uv; version checks protect all uv-based VS Code tasks/demo.
- [x] Offline Python 3.12 and installed-wheel Python 3.14 tests, Ruff and coverage.
- [x] Locked sync, dependency compatibility, sdist/wheel and fresh isolated installation.
- [x] Actual CLI exits 0/1/2/3 and byte-identical cross-interpreter JSON/Markdown.
- [x] VS Code workspace configuration and task/debug-target commands verified.
- [x] Sanitized public tree, distribution review and generated-output exclusions.
- [x] One clean initial local commit; private development history excluded.
- [ ] Separate owner approval to create/push a public GitHub repository.
- [ ] At publication time, confirm the intended repository slug is available and
  re-review the exact public commit/tree and approved identity.

No remaining confirmed P0/P1 defect is reported within the bounded local MVP scope.
The only authorization blocker is publication approval. A new machine requires Python,
trusted patched uv and initial dependency downloads/cache; cross-OS validation is not claimed.

## Licence options and dependencies

The owner selected **MIT**, implemented in [LICENSE](../LICENSE) and in package metadata
(`license = "MIT"`, `license-files = ["LICENSE"]`). The text follows the
[official MIT licence](https://opensource.org/license/mit), with the exact approved notice.
Both built distributions carry the licence. No author email or unapproved holder was added.
The `Private :: Do Not Upload` classifier remains as a package-index upload safeguard;
GitHub publication and any future PyPI upload are separate decisions.

The repository's handwritten synthetic fixtures are covered by the same licence.
They are test inputs with deliberate differences, not imported benchmarks, private
responses or measured model outputs. No third-party dataset attribution was introduced.
The supplied ownership/licensing authorization is recorded; this is not an independent
legal chain-of-title determination.

The application has **zero runtime dependencies**. The existing development/build
licence inventory follows; dependency versions did not change during the rebrand.
Third-party tools retain their own licences. The wheel does not vendor those tools.
The ignored local uv copy retains its MIT and Apache licence files.

| Component | Audited version | Licence | Role |
| --- | --- | --- | --- |
| pytest | 9.1.1 | MIT | Tests |
| Ruff | 0.17.2 | MIT | Lint/format |
| Coverage.py | 7.17.0 | Apache-2.0; includes NOTICE | Coverage |
| colorama | 0.4.6 | BSD-3-Clause, verified licence text | pytest dependency on Windows |
| iniconfig | 2.3.1 | MIT | pytest dependency |
| packaging | 26.3 | Apache-2.0 OR BSD-2-Clause | pytest dependency |
| pluggy | 1.7.0 | MIT | pytest dependency |
| Pygments | 2.21.0 | BSD-2-Clause | pytest dependency |
| uv | 0.13.4 | MIT OR Apache-2.0 | Package/build tool, outside dependency lock |
| uv_build | 0.13.4 | MIT OR Apache-2.0 | Pinned build backend |

uv wheel licence files and [uv_build metadata](https://pypi.org/project/uv-build/0.13.4/)
support the tool/backend entries. This inventory does not relicense Python, Windows,
VS Code or extensions, or exhaustively inventory native dependencies embedded in tools.

## Proposed GitHub presentation

Repository: **GiannisPap24/fixturedelta-lab**.

Description: **Offline Python regression testing for recorded AI outputs, with deterministic
evaluators, quality gates and reproducible baseline/candidate reports.**

Topics: `python`, `ai-evaluation`, `regression-testing`, `quality-gates`,
`reproducibility`, `cli`, `pytest`, `synthetic-data`.

## Publication procedure — execute only after owner approval

1. Work only in the sanitized public staging repository. Verify its approved commit
   hash, clean worktree, `main` branch and exactly one root commit. Confirm that
   `git remote -v` and `git tag --list` are empty, the local Git identity is the
   approved GitHub noreply identity, and no alternate object store exists. Review
   README, licence and the exact tracked inventory. Keep `.tools`, environments,
   reports, builds and all private audit evidence out of Git. Never publish the
   original development repository or copy its `.git` directory into this one.
2. Confirm access to the owner account and that `GiannisPap24/fixturedelta-lab` is
   available. Create an **empty public repository** with the description above; do not
   initialize another README, licence or gitignore because this checkout already has them.
3. After that separately authorized creation, connect and push the reviewed branch:

   ```powershell
   git remote add origin https://github.com/GiannisPap24/fixturedelta-lab.git
   git push -u origin main
   ```

   Inspect `git remote -v` first; stop if an unexpected remote exists. Push only
   `main`; do not use a mirror push, force push, `--all` or `--tags`.
4. Set the proposed topics. Check the public README links, MIT detection, source tree,
   commit identity and synthetic-data explanation. No release tag or package-index
   upload is implied by this procedure; authorize those separately if wanted.

These instructions are a handoff, not publication authorization. No repository,
remote, tag, deployment or public release was created by this work.

## Optional future work and limits

Multi-OS CI, larger synthetic suites, total byte/case limits, fuzzing and signed
provenance are optional future improvements. The current implementation assumes
bounded local input and trusted filesystem parents. Fingerprints establish consistency,
not authenticity or truth. There is no live LLM benchmarking, semantic correctness
verification, comprehensive hallucination detection or production monitoring.
