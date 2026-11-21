#!/usr/bin/env python3
"""Publish one small, audited Parquet view from the canonical ARK JSON snapshots.

The raw append-only JSON remains authoritative. Parquet is a derived presentation/
analytics projection and never introduces inferred holdings.
"""
from __future__ import annotations

import argparse
from datetime import datetime
from decimal import Decimal, InvalidOperation
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
from tempfile import TemporaryDirectory

ROOT = Path(__file__).resolve().parents[1]
FUNDS = {"ARKK", "ARKQ", "ARKW", "ARKG", "ARKF", "ARKX"}
MAX_GIT_BLOB_BYTES = 1_000_000
MODEL_DIR = ROOT / "analytics/ark_parquet"
NAME = "holdings-latest.parquet"
MANIFEST = "holdings-latest.manifest.json"


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def snapshot_date(value: str) -> str:
    return datetime.strptime(value, "%m/%d/%Y").date().isoformat()


def select_current(root: Path) -> tuple[Path, dict]:
    """Use the latest as-of date, and the latest retrieval for corrected days."""
    candidates: list[tuple[str, str, Path, dict]] = []
    for path in sorted(root.glob("*/*.json")):
        data = json.loads(path.read_text(encoding="utf-8"))
        snapshots = data.get("snapshots", [])
        dates = {snapshot_date(str(s["as_of"])) for s in snapshots}
        if len(dates) != 1:
            raise ValueError(f"{path}: mixed or missing as_of")
        datestr = next(iter(dates))
        retrieved = max(str(s["retrieved_at"]) for s in snapshots)
        candidates.append((datestr, retrieved, path, data))
    if not candidates:
        raise ValueError("No canonical ARK snapshots available")
    _, _, path, payload = max(candidates, key=lambda item: item[:2])
    return path, payload


def numeric(value: object, *, percent: bool = False) -> Decimal:
    if not isinstance(value, str) or not value.strip():
        raise ValueError("missing numeric holding value")
    raw = value.strip().replace(",", "").replace("$", "")
    if percent:
        if not raw.endswith("%"):
            raise ValueError(f"invalid percentage: {value}")
        raw = raw[:-1]
    try:
        number = Decimal(raw)
    except InvalidOperation as exc:
        raise ValueError(f"invalid numeric value: {value}") from exc
    if not number.is_finite():
        raise ValueError("non-finite holding value")
    return number


def snapshot_rows(payload: dict) -> list[tuple]:
    snapshots = payload.get("snapshots", [])
    if {s.get("fund") for s in snapshots} != FUNDS or len(snapshots) != len(FUNDS):
        raise ValueError("latest ARK snapshot must contain six distinct funds")
    dates = {snapshot_date(str(s["as_of"])) for s in snapshots}
    if len(dates) != 1:
        raise ValueError("mixed as_of dates cannot be published")
    as_of = next(iter(dates))
    result = []
    for snap in sorted(snapshots, key=lambda s: s["fund"]):
        fund = snap["fund"]
        source_hash = str(snap.get("source_sha256", ""))
        source_url = str(snap.get("source_csv_url", ""))
        if not re.fullmatch(r"[0-9a-f]{64}", source_hash) or not source_url.startswith("https://"):
            raise ValueError(f"{fund}: incomplete provenance")
        seen = set()
        weight_total = Decimal(0)
        holdings = snap["holdings"]
        if len(holdings) != snap.get("row_count"):
            raise ValueError(f"{fund}: declared row count mismatch")
        for row in holdings:
            security = (row.get("cusip") or row.get("ticker") or row.get("company") or "").strip()
            company = (row.get("company") or "").strip()
            if not security or not company or security in seen:
                raise ValueError(f"{fund}: missing or duplicate holding identity")
            seen.add(security)
            weight = numeric(row.get("weight (%)"), percent=True)
            if not Decimal(0) <= weight <= Decimal(100):
                raise ValueError(f"{fund}: weight out of range")
            weight_total += weight
            shares = numeric(row.get("shares"))
            market_value = numeric(row.get("market value ($)"))
            if shares < 0 or market_value < 0 or shares != shares.to_integral_value():
                raise ValueError(f"{fund}: invalid holdings quantity/value")
            result.append((
                as_of, fund, security, (row.get("ticker") or "").strip(),
                company, int(shares), market_value, weight, source_hash, source_url,
            ))
        if not Decimal(95) <= weight_total <= Decimal(105):
            raise ValueError(f"{fund}: holdings weight audit failed ({weight_total})")
    return result


def build(source_dir: Path, output_dir: Path, *, force: bool = False) -> dict:
    import duckdb  # CI's pinned existing requirements; tests can import without deps.

    source_path, payload = select_current(source_dir)
    rows = snapshot_rows(payload)
    source_hash = digest(source_path)
    output_dir.mkdir(parents=True, exist_ok=True)
    target = output_dir / NAME
    metadata = output_dir / MANIFEST
    if target.is_file() and metadata.is_file() and not force:
        previous = json.loads(metadata.read_text(encoding="utf-8"))
        if (previous.get("source_snapshot_sha256") == source_hash
                and previous.get("parquet_sha256") == digest(target)
                and previous.get("record_count") == len(rows)):
            return previous  # No fresh binary, no duplicate Git commit.

    # A single temporary DB. dbt owns SQL/typing and Parquet materialization.
    pending = output_dir / (NAME + ".next")
    if pending.exists():
        pending.unlink()
    try:
        with TemporaryDirectory(prefix="ark-parquet-") as temp:
            scratch = Path(temp)
            database = scratch / "dbt.duckdb"
            with duckdb.connect(str(database)) as db:
                db.execute("create schema raw")
                db.execute("""create table raw.holdings (
                    as_of date, fund varchar, security varchar, ticker varchar,
                    company varchar, shares bigint, market_value_usd decimal(20,2),
                    weight_pct decimal(9,4), source_sha256 varchar, source_csv_url varchar
                )""")
                db.executemany(
                    "insert into raw.holdings values (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                    rows,
                )
            env = {
                **os.environ,
                "ARK_PARQUET_DB": str(database),
                "ARK_PARQUET_OUT": str(pending),
                "DBT_SEND_ANONYMOUS_USAGE_STATS": "false",
            }
            subprocess.run([
                "dbt", "--no-use-colors", "--log-path", str(scratch / "logs"),
                "build", "--project-dir", str(MODEL_DIR),
                "--profiles-dir", str(MODEL_DIR),
                "--target-path", str(scratch / "target"),
                "--select", "ark_holdings_latest",
            ], check=True, cwd=str(ROOT), env=env)
            with duckdb.connect() as db:
                count, distinct_count, min_date, max_date = db.execute(
                    f"""select count(*), count(distinct fund || ':' || security),
                        min(as_of), max(as_of) from read_parquet('{pending.as_posix()}')"""
                ).fetchone()
            if count != len(rows) or distinct_count != count or min_date != max_date:
                raise ValueError("Parquet does not match validated input")
            if pending.stat().st_size > MAX_GIT_BLOB_BYTES:
                raise ValueError("Parquet too large for efficient Git history; use Releases/object storage")
            if pending.stat().st_size < 8 or pending.read_bytes()[:4] != b"PAR1":
                raise ValueError("Invalid Parquet magic")
        # Commit metadata and binary only after all independent checks succeed.
        os.replace(pending, target)
    finally:
        if pending.exists():
            pending.unlink()
    manifest = {
        "schema_version": "ark-holdings-parquet.v1",
        "kind": "derived-not-authoritative",
        "as_of": rows[0][0],
        "record_count": len(rows),
        "fund_count": len(FUNDS),
        "source_snapshot": str(source_path.relative_to(ROOT)) if source_path.is_relative_to(ROOT) else str(source_path),
        "source_snapshot_sha256": source_hash,
        "parquet": NAME,
        "parquet_bytes": target.stat().st_size,
        "parquet_sha256": digest(target),
        "compression": "zstd",
        "source_funds": [
            {"fund": snap["fund"], "source_csv_url": snap["source_csv_url"],
             "source_sha256": snap["source_sha256"]}
            for snap in sorted(payload["snapshots"], key=lambda s: s["fund"])
        ],
    }
    metadata.write_text(
        json.dumps(manifest, ensure_ascii=False, sort_keys=True, indent=2) + "\n",
        encoding="utf-8",
    )
    return manifest


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input-dir", type=Path, default=ROOT / "data/ark-holdings")
    parser.add_argument("--output-dir", type=Path, default=ROOT / "data/ark-views")
    parser.add_argument("--force", action="store_true")
    args = parser.parse_args()
    print(json.dumps(build(args.input_dir, args.output_dir, force=args.force), indent=2))


if __name__ == "__main__":
    main()
