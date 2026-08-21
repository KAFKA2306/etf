# Repository Agent Contract

## Mission

Own ETF evidence and user-facing ETF comparison work for this repository. Current high-value authorities include JPX official ETF listing snapshots and ARK official end-of-day holdings. Preserve raw observations separately from derived comparisons, theme mappings, rankings, and research conclusions.

## Canonical authority

- Use the repository's existing versioned snapshots, manifests, hashes, APIs, and workflows as the local source of truth.
- For new external facts prefer JPX and ARK official sources. Do not treat trade notifications, secondary sites, or inferred values as end-of-day holdings facts.
- Keep `as_of`, `retrieved_at`, source URL, identity, units, and source hash when the owning dataset supports them.
- Do not copy another finance repository's canonical facts into a second authority; consume or link its versioned artifact instead.

## Autonomous execution

1. Read current `main`, README, open Issues/PRs, workflows, canonical snapshots/manifests, and public Pages/API before choosing work.
2. Resume the existing canonical workline for the same outcome before creating another branch, dataset, workflow, or Issue.
3. Choose one executable outcome: verified ETF records, reproducible comparison/diff, a working public ETF task, a real blocker removal, or measurable simplification.
4. Prefer existing capability, deletion, consolidation, or replacement before adding code/dependencies/workflows.
5. Run the smallest relevant deterministic checks, use PR/exact-head CI when changing implementation, and read back `main`/production when publication is in scope.
6. Stop when the bounded outcome is verified. Do not extend a completed result into optional tooling or dashboard work.

## Boundaries

- Missing/null values stay missing; do not infer index names, holdings, prices, dates, or classifications.
- Theme exposure is derived data, not an ARK holdings fact.
- Do not execute trades, orders, transfers, or brokerage/account actions.
- A waiting requirement such as trading-day accumulation is not work until new source data exist.
- Never label an unobserved CI, deployment, or external-data layer as passed.

## Completion report

Report only material Before -> After outcome, authoritative evidence/artifact, Issue/PR/commit and exact-head checks when applicable, public read-back when applicable, complexity/manual work removed, and the remaining verified blocker.