from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import os
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Protocol

ROOT = Path(__file__).resolve().parent
DEFAULT_UNIVERSE = ROOT / "data" / "ticker-universe.json"
DEFAULT_OUTPUT = ROOT / "data" / "prices" / "current.json"
SCHEMA_VERSION = "etf.daily-prices.v1"


class FetchError(RuntimeError):
    """Raised when a complete, auditable price snapshot cannot be produced."""


class Provider(Protocol):
    name: str

    def daily_prices(self, symbol: str, start: dt.date, end: dt.date) -> list[dict[str, Any]]: ...


@dataclass(frozen=True)
class Ticker:
    symbol: str
    exchange: str
    currency: str
    fund_name: str
    active_status: str
    source_url: str
    verified_at: str


class YFinanceProvider:
    name = "yfinance"

    def daily_prices(self, symbol: str, start: dt.date, end: dt.date) -> list[dict[str, Any]]:
        try:
            import yfinance as yf  # type: ignore
        except ImportError as exc:
            raise FetchError("live fetch requires yfinance; install the project dependencies first") from exc
        frame = yf.download(
            symbol,
            start=start.isoformat(),
            end=(end + dt.timedelta(days=1)).isoformat(),
            interval="1d",
            auto_adjust=False,
            actions=False,
            progress=False,
        )
        if frame.empty:
            raise FetchError(f"provider returned no daily rows for {symbol}")
        close = frame["Close"]
        if getattr(close, "ndim", 1) != 1:
            if symbol in getattr(close, "columns", []):
                close = close[symbol]
            else:
                raise FetchError(f"ambiguous Close field for {symbol}")
        records: list[dict[str, Any]] = []
        for index, value in close.items():
            if value is None or value != value:
                raise FetchError(f"null/NaN raw close for {symbol} at {index}")
            date_value = index.date() if hasattr(index, "date") else dt.date.fromisoformat(str(index)[:10])
            if date_value < start or date_value > end:
                continue
            records.append({"date": date_value.isoformat(), "raw_close": float(value)})
        if not records:
            raise FetchError(f"no rows remained inside requested range for {symbol}")
        dates = [row["date"] for row in records]
        if len(dates) != len(set(dates)):
            raise FetchError(f"duplicate daily dates for {symbol}")
        return records


def load_universe(path: Path = DEFAULT_UNIVERSE) -> list[Ticker]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if payload.get("schema_version") != "etf.ticker-universe.v1":
        raise FetchError("unsupported ticker universe schema")
    rows = payload.get("tickers")
    if not isinstance(rows, list) or not rows:
        raise FetchError("ticker universe must contain at least one ticker")
    tickers = [Ticker(**row) for row in rows]
    symbols = [row.symbol for row in tickers]
    if len(symbols) != len(set(symbols)):
        raise FetchError("ticker universe contains duplicate symbols")
    return tickers


def _snapshot_digest(payload: dict[str, Any]) -> str:
    unsigned = {key: value for key, value in payload.items() if key != "snapshot_sha256"}
    canonical = json.dumps(unsigned, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(canonical).hexdigest()


def verify_snapshot(payload: dict[str, Any]) -> None:
    """Fail closed when a snapshot is malformed or its signed content drifted."""
    if payload.get("schema_version") != SCHEMA_VERSION:
        raise FetchError("unsupported price snapshot schema")
    expected = payload.get("snapshot_sha256")
    if not isinstance(expected, str) or len(expected) != 64:
        raise FetchError("snapshot_sha256 is missing or malformed")
    actual = _snapshot_digest(payload)
    if actual != expected:
        raise FetchError("snapshot checksum mismatch; refusing to publish tampered content")


def build_snapshot(
    tickers: list[Ticker],
    provider: Provider,
    *,
    start: dt.date,
    end: dt.date,
    retrieved_at: dt.datetime,
    source_commit: str | None,
) -> dict[str, Any]:
    if end < start:
        raise FetchError("end date must be on or after start date")
    series: list[dict[str, Any]] = []
    failures: list[dict[str, str]] = []
    for ticker in tickers:
        try:
            records = provider.daily_prices(ticker.symbol, start, end)
        except Exception as exc:
            failures.append({"symbol": ticker.symbol, "reason": f"{type(exc).__name__}: {exc}"})
            continue
        series.append(
            {
                "symbol": ticker.symbol,
                "exchange": ticker.exchange,
                "currency": ticker.currency,
                "price_field_semantics": "raw_close",
                "requested_start": start.isoformat(),
                "requested_end": end.isoformat(),
                "actual_start": records[0]["date"],
                "actual_end": records[-1]["date"],
                "row_count": len(records),
                "records": records,
            }
        )
    if failures:
        detail = "; ".join(f"{row['symbol']}: {row['reason']}" for row in failures)
        raise FetchError("partial fetch rejected; current snapshot was not replaced: " + detail)
    payload: dict[str, Any] = {
        "schema_version": SCHEMA_VERSION,
        "provider": provider.name,
        "request": {"interval": "1d", "start": start.isoformat(), "end": end.isoformat()},
        "retrieved_at": retrieved_at.astimezone(dt.timezone.utc).isoformat(),
        "timezone": "UTC",
        "source_commit": source_commit,
        "series": series,
    }
    payload["snapshot_sha256"] = _snapshot_digest(payload)
    return payload


def write_snapshot_atomic(payload: dict[str, Any], output: Path) -> None:
    verify_snapshot(payload)
    output.parent.mkdir(parents=True, exist_ok=True)
    text = json.dumps(payload, ensure_ascii=False, sort_keys=True, indent=2) + "\n"
    fd, temp_name = tempfile.mkstemp(prefix=output.name + ".", suffix=".tmp", dir=output.parent)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            handle.write(text)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temp_name, output)
    except BaseException:
        try:
            os.unlink(temp_name)
        except FileNotFoundError:
            pass
        raise


def parser() -> argparse.ArgumentParser:
    result = argparse.ArgumentParser(description="Fetch an explicit, fail-closed ETF daily raw-close snapshot")
    result.add_argument("--start", type=dt.date.fromisoformat, required=True)
    result.add_argument("--end", type=dt.date.fromisoformat, required=True)
    result.add_argument("--universe", type=Path, default=DEFAULT_UNIVERSE)
    result.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    result.add_argument("--retrieved-at", type=dt.datetime.fromisoformat, help="Explicit retrieval timestamp for reproducible fixtures")
    return result


def main(argv: list[str] | None = None) -> int:
    args = parser().parse_args(argv)
    retrieved_at = args.retrieved_at or dt.datetime.now(dt.timezone.utc)
    if retrieved_at.tzinfo is None:
        raise FetchError("--retrieved-at must include a timezone offset")
    snapshot = build_snapshot(
        load_universe(args.universe),
        YFinanceProvider(),
        start=args.start,
        end=args.end,
        retrieved_at=retrieved_at,
        source_commit=os.environ.get("GITHUB_SHA"),
    )
    write_snapshot_atomic(snapshot, args.output)
    print(f"wrote {len(snapshot['series'])} complete series to {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
