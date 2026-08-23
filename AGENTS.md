# Repository Agent Contract

## Mission

Own ETF evidence and user-facing ETF comparison work for this repository. Current high-value authorities include JPX official ETF listing snapshots, auditable daily price snapshots, and ARK official end-of-day holdings. Preserve raw observations separately from derived comparisons, theme mappings, rankings, and research conclusions.

## Canonical authority

- Use the repository's existing versioned snapshots, manifests, hashes, APIs, and workflows as the local source of truth.
- For new external facts prefer official sources where available. Do not treat trade notifications, secondary sites, or inferred values as end-of-day holdings facts.
- Keep `as_of`, `retrieved_at`, source URL, identity, units, and source hash when the owning dataset supports them.
- Do not copy another finance repository's canonical facts into a second authority; consume or link its versioned artifact instead.
- One responsibility gets one current implementation path. Remove retired aliases, duplicate artifacts, stale wrappers, and completed scaffolding when direct evidence shows they are no longer required.

## Autonomous execution

1. Read current `main`, README, open Issues/PRs, workflows, canonical snapshots/manifests, and public Pages/API before choosing work.
2. Resume the existing canonical workline for the same outcome before creating another dataset, workflow, or Issue.
3. Choose one executable outcome: verified ETF records, reproducible comparison/diff, a working public ETF task, a real blocker removal, or measurable simplification.
4. Prefer existing capability, deletion, consolidation, or replacement before adding code/dependencies/workflows.
5. Run the smallest relevant deterministic checks and use PR/exact-head CI when changing implementation.
6. Stop when the bounded outcome is verified. Do not extend a completed result into optional tooling or dashboard work.
7. Broad simplification Issues are iterative checkpoints, not one-shot cleanup tickets. Record each verified pass and keep the Issue open while material duplicate/stale surface remains or later re-audit is still useful.

Branch deletion is not a completion condition for repository work. Do not create cleanup-only work solely to remove branches, and do not report an otherwise verified implementation as blocked because branch deletion is unavailable to the current tool.

## Merge and release are separate

### PR merge conditions

A PR may merge when the repository-local change is reviewable and correct on the exact head revision: the bounded contract is satisfied, canonical data/provenance rules are preserved, relevant deterministic tests/audits pass, generated artifacts are reproducible when affected, and no unresolved review or correctness blocker remains.

Production deployment, a future trading-day observation, live external collection, public traffic, or other post-merge operating evidence is **not** a merge condition unless the PR specifically changes the release mechanism and that mechanism must be validated before merge.

### Product release conditions

Release is a separate post-merge decision. Call the product/data release complete only after the merged `main` revision is read back and every release surface in scope is actually verified, such as the published snapshot/API/Pages URL, deployment identity, fresh upstream collection, release artifact, and rollback path where applicable.

A merged PR does not prove a release. A release blocker does not retroactively make a correctly merged repository change a failure. Report merge evidence and release evidence separately.

## Boundaries

- Missing/null values stay missing; do not infer index names, holdings, prices, dates, or classifications.
- Theme exposure is derived data, not an ARK holdings fact.
- Do not execute trades, orders, transfers, or brokerage/account actions.
- A waiting requirement such as trading-day accumulation is not work until new source data exist.
- Never label an unobserved CI, deployment, or external-data layer as passed.
- Do not reintroduce personal absolute paths, pickle-based canonical datasets, import-time acquisition, or non-auditable partial price snapshots.

## Completion report

Report material Before -> After outcome, authoritative evidence/artifact, Issue/PR/commit and exact-head checks, then report `merged` and `released` separately with direct evidence for each. Include public read-back only when release is in scope, complexity/manual work removed, and the remaining verified blocker or next re-audit target.
