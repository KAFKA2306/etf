from __future__ import annotations

import csv
import hashlib
import json
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "data/official/jpx-etf-new-listings-2026.json"
OUT = ROOT / "api/v1"


def canonical_bytes(value: object) -> bytes:
    return (json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")) + "\n").encode()


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def build() -> dict[str, object]:
    source = json.loads(SOURCE.read_text(encoding="utf-8"))
    records = source["records"]
    if source["selection"]["record_count"] != len(records):
        raise ValueError("source record_count mismatch")
    codes = [row["code"] for row in records]
    if len(codes) != len(set(codes)):
        raise ValueError("duplicate ETF code")
    if records != sorted(records, key=lambda row: (row["listing_date"], row["code"])):
        raise ValueError("records must be sorted by listing_date and code")

    OUT.mkdir(parents=True, exist_ok=True)
    listings = {
        "schema_version": "1.0.0",
        "publisher": source["publisher"],
        "source_url": source["source_url"],
        "retrieved_at": source["retrieved_at"],
        "count": len(records),
        "records": records,
    }
    (OUT / "listings.json").write_bytes(canonical_bytes(listings))

    fields = [
        "listing_date", "code", "fund_name", "index_name", "management_company",
        "trading_unit", "trust_fee_percent", "indicative_nav", "active_etf",
    ]
    with (OUT / "listings.csv").open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerows(records)

    facets = {
        "management_company": dict(sorted(Counter(row["management_company"] for row in records).items())),
        "listing_month": dict(sorted(Counter(row["listing_date"][:7] for row in records).items())),
        "active_etf": {"false": sum(not row["active_etf"] for row in records), "true": sum(row["active_etf"] for row in records)},
        "indicative_nav": {"false": sum(not row["indicative_nav"] for row in records), "true": sum(row["indicative_nav"] for row in records)},
    }
    (OUT / "facets.json").write_bytes(canonical_bytes(facets))

    distributions = {}
    for name in ("listings.json", "listings.csv", "facets.json"):
        path = OUT / name
        distributions[name] = {"bytes": path.stat().st_size, "sha256": sha256(path)}
    manifest = {
        "schema_version": "1.0.0",
        "dataset": source["dataset"],
        "publisher": source["publisher"],
        "source_url": source["source_url"],
        "retrieved_at": source["retrieved_at"],
        "record_count": len(records),
        "first_listing_date": records[0]["listing_date"],
        "last_listing_date": records[-1]["listing_date"],
        "source_sha256": sha256(SOURCE),
        "cache_control_seconds": 3600,
        "rights": source["rights"],
        "distributions": distributions,
    }
    (OUT / "manifest.json").write_bytes(canonical_bytes(manifest))
    return manifest


if __name__ == "__main__":
    print(json.dumps(build(), ensure_ascii=False, indent=2))
