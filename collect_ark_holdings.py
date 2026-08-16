#!/usr/bin/env python3
"""Fetch official ARK ETF holdings CSVs and store normalized snapshots."""
from __future__ import annotations

import argparse
import csv
import hashlib
import io
import json
from datetime import datetime, timezone
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

ASSET_BASE = "https://assets.ark-funds.com/fund-documents/funds-etf-csv"
FUNDS = ("ARKK", "ARKQ", "ARKW", "ARKG", "ARKF", "ARKX")
CANDIDATE_FILES = {
    "ARKK": ("ARK_INNOVATION_ETF_ARKK_HOLDINGS.csv",),
    "ARKQ": ("ARK_AUTONOMOUS_TECH._&_ROBOTICS_ETF_ARKQ_HOLDINGS.csv",),
    "ARKW": ("ARK_NEXT_GENERATION_INTERNET_ETF_ARKW_HOLDINGS.csv",),
    "ARKG": ("ARK_GENOMIC_REVOLUTION_ETF_ARKG_HOLDINGS.csv",),
    "ARKF": ("ARK_BLOCKCHAIN_&_FINTECH_INNOVATION_ETF_ARKF_HOLDINGS.csv",),
    "ARKX": ("ARK_SPACE_&_DEFENSE_INNOVATION_ETF_ARKX_HOLDINGS.csv",),
}


def fetch(url: str) -> bytes:
    request = Request(
        url,
        headers={"User-Agent": "ark-etf-holdings/1.0 github.com/KAFKA2306/etf"},
    )
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
        row = {
            str(k or "").strip(): str(v or "").strip()
            for k, v in raw_row.items()
            if k is not None
        }
        if not any(row.values()):
            continue
        fund = fund_value(row)
        company = (
            row.get("company")
            or row.get("Company")
            or row.get("company_name")
            or row.get("Company Name")
        )
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


def source_url(filename: str) -> str:
    return f"{ASSET_BASE}/{filename}"


def fetch_fund(ticker: str) -> tuple[str, bytes, list[dict[str, str]], str | None]:
    errors: list[str] = []
    for filename in CANDIDATE_FILES[ticker]:
        url = source_url(filename)
        try:
            raw = fetch(url)
            as_of, rows = parse_csv(raw)
        except (HTTPError, URLError, UnicodeError, ValueError, csv.Error) as exc:
            errors.append(f"{url}: {exc}")
            continue
        identified = identify_ticker(rows)
        if identified != ticker:
            errors.append(f"{url}: CSV identified as {identified!r}, expected {ticker}")
            continue
        return url, raw, rows, as_of
    raise RuntimeError(f"no verified official holdings CSV for {ticker}: {'; '.join(errors)}")


def collect(tickers: tuple[str, ...] = FUNDS) -> dict[str, object]:
    snapshots = []
    for ticker in tickers:
        url, raw, rows, as_of = fetch_fund(ticker)
        for row in rows:
            row["fund_ticker"] = ticker
        snapshots.append(
            {
                "fund": ticker,
                "as_of": as_of,
                "retrieved_at": datetime.now(timezone.utc).isoformat(),
                "source_csv_url": url,
                "source_sha256": hashlib.sha256(raw).hexdigest(),
                "row_count": len(rows),
                "holdings": rows,
            }
        )
    return {"schema_version": 1, "publisher": "ARK ETF Trust", "snapshots": snapshots}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output-dir", type=Path, default=Path("data/ark-holdings"))
    args = parser.parse_args()
    payload = collect()
    args.output_dir.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    path = args.output_dir / f"ark-holdings-{stamp}.json"
    path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print(path)


if __name__ == "__main__":
    main()
