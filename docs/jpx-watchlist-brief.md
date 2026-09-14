# JPX ETF watchlist brief

`scripts/build_jpx_listing_brief.py` compares two saved JPX ETF snapshots without fetching or inferring data. It emits deterministic JSON plus Markdown and preserves the source URL, `retrieved_at`, snapshot SHA-256, and optional manifest SHA-256 for both sides.

The diff states are `ADDED`, `CHANGED`, `UNCHANGED`, and `REMOVED_FROM_CURRENT_SNAPSHOT`. The last state means only that a record disappeared from the newer saved snapshot; it must not be presented as proof of delisting. Missing source values remain missing.

Watchlists live in `config/jpx-watchlists.v1.json`, so codes, management companies, and `active_etf` can be changed without editing application code. An empty codes/companies array means that dimension is unrestricted.

Example:

```bash
python scripts/build_jpx_listing_brief.py \
  --previous path/to/previous.json \
  --current path/to/current.json \
  --watchlists config/jpx-watchlists.v1.json \
  --watchlist all \
  --previous-manifest path/to/previous-manifest.json \
  --current-manifest api/v1/manifest.json \
  --json-out out/jpx-brief.json \
  --markdown-out out/jpx-brief.md
```

Service CTA: “Generate this brief for my watchlist.” A consumer can record `brief_generated`, `brief_viewed`, or `cta_selected` using `docs/schemas/jpx-brief-event.v1.json`; the event contains no inferred listing facts.
