#!/usr/bin/env python3
"""Fetch official ARK ETF holdings CSVs and store append-only normalized snapshots."""
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
    retrieved_at = datetime.now(timezone.utc).isoformat()
    snapshots = []
    for ticker in tickers:
        url, raw, rows, as_of = fetch_fund(ticker)
        if not as_of:
            raise RuntimeError(f"{ticker}: official CSV has no as-of date")
        for row in rows:
            row["fund_ticker"] = ticker
        snapshots.append(
            {
                "fund": ticker,
                "as_of": as_of,
                "retrieved_at": retrieved_at,
                "source_csv_url": url,
                "source_sha256": hashlib.sha256(raw).hexdigest(),
                "row_count": len(rows),
                "holdings": rows,
            }
        )
    return {"schema_version": 1, "publisher": "ARK ETF Trust", "snapshots": snapshots}


def parse_date(value: str) -> str:
    for fmt in ("%m/%d/%Y", "%Y-%m-%d"):
        try:
            return datetime.strptime(value, fmt).date().isoformat()
        except ValueError:
            pass
    raise ValueError(f"unsupported as-of date: {value!r}")


def snapshot_identity(payload: dict[str, object]) -> tuple[str, str]:
    snapshots = payload["snapshots"]
    dates = {parse_date(str(item["as_of"])) for item in snapshots}
    if len(dates) != 1:
        raise RuntimeError(f"fund as-of dates disagree: {sorted(dates)}")
    source_hashes = sorted(
        f'{item["fund"]}:{item["source_sha256"]}'
        for item in snapshots
    )
    fingerprint = hashlib.sha256("\n".join(source_hashes).encode()).hexdigest()[:16]
    return dates.pop(), fingerprint


def write_snapshot(payload: dict[str, object], output_dir: Path) -> Path:
    as_of, fingerprint = snapshot_identity(payload)
    path = output_dir / as_of / f"{fingerprint}.json"
    if path.exists():
        return path
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return path


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output-dir", type=Path, default=Path("data/ark-holdings"))
    args = parser.parse_args()
    print(write_snapshot(collect(), args.output_dir))


if __name__ == "__main__":
    main()
