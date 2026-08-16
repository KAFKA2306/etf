#!/usr/bin/env python3
"""Discover official ARK holdings CSV links and store normalized daily snapshots."""
from __future__ import annotations

import argparse
import csv
import hashlib
import io
import json
import re
from datetime import datetime, timezone
from html import unescape
from pathlib import Path
from urllib.parse import urljoin
from urllib.request import Request, urlopen

BASE = "https://www.ark-funds.com"
FUNDS = ("ARKK", "ARKQ", "ARKW", "ARKG", "ARKF", "ARKX")


def fetch(url: str) -> bytes:
    request = Request(url, headers={"User-Agent": "ark-etf-holdings/1.0 github.com/KAFKA2306/etf"})
    with urlopen(request, timeout=60) as response:
        return response.read()


def discover_csv_url(ticker: str) -> tuple[str, str]:
    fund_url = f"{BASE}/funds/{ticker.lower()}"
    fund_html = fetch(fund_url).decode("utf-8", errors="replace")

    # Prefer an explicit official assets link when present in server-rendered HTML.
    matches = re.findall(r'https://assets\.ark-funds\.com/[^"\'<> ]+\.csv', fund_html, flags=re.I)
    if matches:
        return unescape(matches[0]), fund_url

    # ARK fund pages load document rows from an official internal endpoint.
    ids = re.findall(r"/api/fund/document-table/(\d+)", fund_html)
    for fund_id in dict.fromkeys(ids):
        table_url = f"{BASE}/api/fund/document-table/{fund_id}"
        table_html = fetch(table_url).decode("utf-8", errors="replace")
        links = re.findall(r'href=["\']([^"\']+\.csv[^"\']*)["\']', table_html, flags=re.I)
        if links:
            return urljoin(BASE, unescape(links[0])), table_url
    raise RuntimeError(f"official holdings CSV link not found for {ticker}")


def parse_csv(raw: bytes, ticker: str) -> tuple[str | None, list[dict[str, str]]]:
    text = raw.decode("utf-8-sig", errors="strict")
    reader = csv.DictReader(io.StringIO(text))
    rows = []
    as_of = None
    for raw_row in reader:
        row = {str(k or "").strip(): str(v or "").strip() for k, v in raw_row.items() if k is not None}
        if not any(row.values()):
            continue
        # ARK CSVs contain a footer/disclaimer; only keep rows that identify a fund/security.
        fund = row.get("fund") or row.get("Fund") or row.get("fund_name") or row.get("Fund Name")
        company = row.get("company") or row.get("Company") or row.get("company_name") or row.get("Company Name")
        if not fund and not company:
            continue
        date_value = row.get("date") or row.get("Date")
        if date_value and as_of is None:
            as_of = date_value
        row["fund_ticker"] = ticker
        rows.append(row)
    if not rows:
        raise ValueError(f"no holdings rows parsed for {ticker}")
    return as_of, rows


def collect(tickers: tuple[str, ...] = FUNDS) -> dict[str, object]:
    snapshots = []
    for ticker in tickers:
        csv_url, discovery_url = discover_csv_url(ticker)
        raw = fetch(csv_url)
        as_of, rows = parse_csv(raw, ticker)
        snapshots.append({
            "fund": ticker,
            "as_of": as_of,
            "retrieved_at": datetime.now(timezone.utc).isoformat(),
            "fund_page": f"{BASE}/funds/{ticker.lower()}",
            "discovery_url": discovery_url,
            "source_csv_url": csv_url,
            "source_sha256": hashlib.sha256(raw).hexdigest(),
            "row_count": len(rows),
            "holdings": rows,
        })
    return {"schema_version": 1, "publisher": "ARK ETF Trust", "snapshots": snapshots}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output-dir", type=Path, default=Path("data/ark-holdings"))
    args = parser.parse_args()
    payload = collect()
    args.output_dir.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    path = args.output_dir / f"ark-holdings-{stamp}.json"
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(path)


if __name__ == "__main__":
    main()
