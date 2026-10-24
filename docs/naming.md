# Naming decision and collision research

Research date: **2026-10-24**. This is a public-web collision screen, not a name
reservation, exhaustive registry search, or legal clearance. No repositories or
packages were created. No external code or cases were imported.

The owner selected **FixtureDelta Lab**, repository `fixturedelta-lab`, command
`fixturedelta` and Python package `fixturedelta_lab`. The existing Windows checkout
folder stays in place. The research below records the basis for that decision.

## Confirmed TrustBench collisions

| Existing use | Primary source | Relevance |
| --- | --- | --- |
| AI support-agent evaluation harness named TrustBench | [Umarfarook1/trustbench](https://github.com/Umarfarook1/trustbench) | Particularly close domain: versioned golden set and regression evaluation |
| TrustBench AI evaluation product | [TrustBench](https://www.trustbench.net/en) | Same name in output-quality evaluation |
| TrustBench evaluation and benchmarking platform | [TrustModel](https://trustmodel.ai/trustbench) | Same name in model evaluation |
| TrustBench attested evaluations | [Divinci SDK](https://sdk.divinci.ai/server/trustbench/) | Same name for benchmark result provenance |
| Machine-learning trustworthiness benchmark | [epicosy/TrustBench](https://github.com/epicosy/TrustBench) | Existing repository and Python namespace |

These sources establish name use; their product or quality claims were not evaluated.
The former working names were replaced in active commands, imports and documentation.
Historical records and immutable fingerprint namespaces intentionally retain them.

## Shortlist

1. **FixtureDelta Lab** — recommended after the final audit. Describes versioned
   test fixtures and baseline/candidate changes without promising AI trustworthiness.
   GitHub's public repository search returned zero names containing `fixturedelta`
   or `fixturedelta-lab`; neither query reported incomplete results. Quoted public-web
   searches for "FixtureDelta" and "FixtureDelta Lab" surfaced no clear project match.
2. **GoldenDiff Lab** — descriptive, but the audit found
   [dkej123/goldendiff](https://github.com/dkej123/goldendiff). The exact hyphenated
   `goldendiff-lab` GitHub name search returned zero matches, but the base-name
   collision weakens distinctiveness. This supersedes the earlier recommendation.
3. **TraceVerdict** — avoid: the current screen found
   [weaqaq/traceverdict](https://github.com/weaqaq/traceverdict), described as an
   auditable state-regression evaluator for coding agents, and
   [ANZA24k/TraceVerdict](https://github.com/ANZA24k/TraceVerdict).
4. **CaseDelta Lab** — descriptive fallback, but less distinctive: searches found
   the existing [CaseDelta AI paralegal](https://casedelta.com/). Prefer another name.

Other screened names were less suitable: EvalLedger already appears in evaluation
provenance projects ([GitHub topic listing](https://github.com/topics/research-infrastructure?l=python&o=desc&s=forks)),
and Caseharbor is used by an existing [operations platform](https://thecaseharbor.com/legal/terms.php).

No clear search result does **not** establish availability. Before a public rename,
check the exact intended GitHub repository/organization, PyPI normalized package
name, and any desired domain, then review any relevant trademark concerns. Those
availability checks remain publication-time diligence. The owner choice is now approved
and the local package/command rebrand is complete. This research is a portfolio naming
judgment, not trademark advice. Search results are dated and can change.
