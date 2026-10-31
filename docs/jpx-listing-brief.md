# JPX listing brief

`scripts/jpx_listing_brief.py` compares two saved JPX ETF listing snapshots by code and the canonical listing fields. It emits `brief.json` and `brief.md` with source URL, retrieval timestamps, and deterministic snapshot SHA-256 values.

Run:

```text
python scripts/jpx_listing_brief.py BEFORE.json AFTER.json --watchlist config/jpx-watchlist.json --out build/jpx-brief
```

Watchlists are versioned JSON and can match exact `values` or case-insensitive `contains` values for a record field. An empty `rules` list selects all records. Missing canonical fields fail instead of being inferred.

States are `ADDED`, `CHANGED`, `UNCHANGED`, and `REMOVED_FROM_CURRENT_SNAPSHOT`. The last state only means the code is absent from the later saved snapshot. It must not be presented as proof of delisting.

Service surface: generated briefs are intended for repository/Pages publication by the existing release path. CTA events, when a UI exposes them, use `jpx_brief_open` or `jpx_brief_source_open` and must include `schema_version: 1`, `watchlist_id`, and `synthetic: false`. Tests and fixtures must set `synthetic: true`; they are never counted as observed usage.
