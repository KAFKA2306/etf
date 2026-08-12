import datetime as dt
import json
import tempfile
import unittest
from pathlib import Path

import fetch


class FakeProvider:
    name = "fixture"

    def __init__(self, fail_symbol=None):
        self.fail_symbol = fail_symbol
        self.calls = []

    def weekly_prices(self, symbol, start, end):
        self.calls.append((symbol, start, end))
        if symbol == self.fail_symbol:
            raise RuntimeError("injected provider failure")
        return [
            {"date": "2026-01-02", "raw_close": 100.0},
            {"date": "2026-01-09", "raw_close": 101.5},
        ]


def ticker(symbol):
    return fetch.Ticker(
        symbol=symbol,
        exchange=None,
        currency=None,
        fund_name=None,
        active_status="unknown",
        source_url="https://example.invalid/source",
        verified_at=None,
    )


class FetchSafetyTests(unittest.TestCase):
    def test_import_has_no_network_or_file_side_effect_entrypoint(self):
        self.assertTrue(callable(fetch.main))
        self.assertFalse(fetch.DEFAULT_OUTPUT.exists())

    def test_explicit_period_and_timestamp_are_deterministic(self):
        kwargs = dict(
            tickers=[ticker("AAA")],
            provider=FakeProvider(),
            start=dt.date(2026, 1, 1),
            end=dt.date(2026, 1, 31),
            retrieved_at=dt.datetime(2026, 2, 1, tzinfo=dt.timezone.utc),
            source_commit="abc123",
        )
        first = fetch.build_snapshot(**kwargs)
        second = fetch.build_snapshot(**kwargs)
        self.assertEqual(first, second)
        self.assertEqual(first["request"]["start"], "2026-01-01")
        self.assertEqual(first["request"]["end"], "2026-01-31")
        self.assertEqual(first["series"][0]["price_field_semantics"], "raw_close")
        self.assertEqual(len(first["snapshot_sha256"]), 64)

    def test_partial_provider_failure_is_fail_closed(self):
        with self.assertRaisesRegex(fetch.FetchError, "partial fetch rejected"):
            fetch.build_snapshot(
                [ticker("AAA"), ticker("BAD")],
                FakeProvider(fail_symbol="BAD"),
                start=dt.date(2026, 1, 1),
                end=dt.date(2026, 1, 31),
                retrieved_at=dt.datetime(2026, 2, 1, tzinfo=dt.timezone.utc),
                source_commit=None,
            )

    def test_atomic_writer_replaces_complete_json(self):
        payload = {"schema_version": fetch.SCHEMA_VERSION, "series": [], "snapshot_sha256": "0" * 64}
        with tempfile.TemporaryDirectory() as tmp:
            output = Path(tmp) / "nested" / "current.json"
            fetch.write_snapshot_atomic(payload, output)
            self.assertEqual(json.loads(output.read_text(encoding="utf-8")), payload)
            self.assertEqual(list(output.parent.glob("*.tmp")), [])

    def test_ticker_universe_is_json_and_explicitly_marks_unknown_metadata(self):
        tickers = fetch.load_universe()
        self.assertGreater(len(tickers), 0)
        self.assertEqual(len({item.symbol for item in tickers}), len(tickers))
        self.assertTrue(any(item.active_status == "unknown" for item in tickers))


if __name__ == "__main__":
    unittest.main()
