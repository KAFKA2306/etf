#!/usr/bin/env python3
"""Discover official ARK holdings CSVs and store normalized daily snapshots."""
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
from urllib.error import HTTPError, URLError
from urllib.parse import urljoin
from urllib.request import Request, urlopen

BASE = "https://www.ark-funds.com"
FUNDS = ("ARKK", "ARKQ", "ARKW", "ARKG", "ARKF", "ARKX")
DOCUMENT_TABLE_IDS = range(1000, 1026)


def fetch(url: str) -> bytes:
    request = Request(url, headers={"User-Agent": "ark-etf-holdings/1.0 github.com/KAFKA2306/etf"})
    with urlopen(request, timeout=60) as response:
        return response.read()


def fund_value(row: dict[str, str]) -> str:
    return (
        row.get("fund")
        or row.get("Fund")
        or row.get("fund_name")
        or row.get("Fund Name")
        or ""
    ).strip().upper()


def parse_csv(raw: bytes, ticker: str | None = None) -> tuple[str | None, list[dict[str, str]]]:
    text = raw.decode("utf-8-sig", errors="strict")
    reader = csv.DictReader(io.StringIO(text))
    rows = []
    as_of = None
    for raw_row in reader:
        row = {str(k or "").strip(): str(v or "").strip() for k, v in raw_row.items() if k is not None}
        if not any(row.values()):
            continue
        fund = fund_value(row)
        company = row.get("company") or row.get("Company") or row.get("company_name") or row.get("Company Name")
        if not fund and not company:
            continue
        date_value = row.get("date") or row.get("Date")
        if date_value and as_of is None:
            as_of = date_value
        if ticker:
            row["fund_ticker"] = ticker
        rows.append(row)
    if not rows:
        raise ValueError("no holdings rows parsed")
    return as_of, rows


def identify_ticker(rows: list[dict[str, str]]) -> str | None:
    values = {fund_value(row) for row in rows if fund_value(row)}
    for ticker in FUNDS:
        if ticker in values:
            return ticker
    return None


def csv_links(table_html: str) -> list[str]:
    links = re.findall(r'href=["\']([^"\']+\.csv(?:\?[^"\']*)?)["\']', table_html, flags=re.I)
    return [urljoin(BASE, unescape(link)) for link in links]


def discover_csv_urls(targets: tuple[str, ...] = FUNDS) -> dict[str, tuple[str, str, bytes]]:
    """Probe ARK's official fund-document API and identify funds from CSV contents.

    The public fund pages return HTTP 403 to GitHub-hosted automation, while the
    official document-table endpoints are intended to serve fund materials. We do
    not assume a numeric ID maps to a ticker; the CSV itself must identify the fund.
    """
    wanted = set(targets)
    found: dict[str, tuple[str, str, bytes]] = {}
    for fund_id in DOCUMENT_TABLE_IDS:
        if wanted <= found.keys():
            break
        table_url = f"{BASE}/api/fund/document-table/{fund_id}"
        try:
            table_raw = fetch(table_url)
        except (HTTPError, URLError):
            continue
        table_html = table_raw.decode("utf-8", errors="replace")
        for csv_url in csv_links(table_html):
            try:
                raw = fetch(csv_url)
                _, rows = parse_csv(raw)
            except (HTTPError, URLError, UnicodeError, ValueError, csv.Error):
                continue
            ticker = identify_ticker(rows)
            if ticker in wanted and ticker not in found:
                found[ticker] = (csv_url, table_url, raw)
    missing = sorted(wanted - found.keys())
    if missing:
        raise RuntimeError(f"official holdings CSVs not discovered for: {missing}")
    return found


def collect(tickers: tuple[str, ...] = FUNDS) -> dict[str, object]:
    discovered = discover_csv_urls(tickers)
    snapshots = []
    for ticker in tickers:
        csv_url, discovery_url, raw = discovered[ticker]
        as_of, rows = parse_csv(raw, ticker)
        snapshots.append({
            "fund": ticker,
            "as_of": as_of,
            "retrieved_at": datetime.now(timezone.utc).isoformat(),
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
