import datetime as dt
import hashlib
import json
import tempfile
import unittest
from pathlib import Path

import fetch

ROOT = Path(__file__).resolve().parents[1]


class FakeProvider:
    name = "fixture"

    def __init__(self, fail_symbol=None):
        self.fail_symbol = fail_symbol
        self.calls = []

    def daily_prices(self, symbol, start, end):
        self.calls.append((symbol, start, end))
        if symbol == self.fail_symbol:
            raise RuntimeError("injected provider failure")
        return [
            {"date": "2026-01-02", "raw_close": 100.0},
            {"date": "2026-01-05", "raw_close": 101.5},
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


def snapshot():
    return fetch.build_snapshot(
        tickers=[ticker("AAA")],
        provider=FakeProvider(),
        start=dt.date(2026, 1, 1),
        end=dt.date(2026, 1, 31),
        retrieved_at=dt.datetime(2026, 2, 1, tzinfo=dt.timezone.utc),
        source_commit="abc123",
    )


class FetchSafetyTests(unittest.TestCase):
    def test_import_exposes_explicit_entrypoint(self):
        self.assertTrue(callable(fetch.main))
        self.assertEqual(fetch.DEFAULT_OUTPUT.parts[-3:], ("data", "prices", "current.json"))

    def test_explicit_period_and_timestamp_are_deterministic(self):
        first = snapshot()
        second = snapshot()
        self.assertEqual(first, second)
        self.assertEqual(first["schema_version"], "etf.daily-prices.v1")
        self.assertEqual(first["request"]["interval"], "1d")
        self.assertEqual(first["request"]["start"], "2026-01-01")
        self.assertEqual(first["request"]["end"], "2026-01-31")
        self.assertEqual(first["series"][0]["price_field_semantics"], "raw_close")
        self.assertEqual(len(first["snapshot_sha256"]), 64)
        fetch.verify_snapshot(first)

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
        payload = snapshot()
        with tempfile.TemporaryDirectory() as tmp:
            output = Path(tmp) / "nested" / "current.json"
            fetch.write_snapshot_atomic(payload, output)
            self.assertEqual(json.loads(output.read_text(encoding="utf-8")), payload)
            self.assertEqual(list(output.parent.glob("*.tmp")), [])

    def test_tampered_snapshot_is_rejected_before_publish(self):
        payload = snapshot()
        payload["series"][0]["records"][0]["raw_close"] = 999999.0
        with self.assertRaisesRegex(fetch.FetchError, "checksum mismatch"):
            fetch.verify_snapshot(payload)
        with tempfile.TemporaryDirectory() as tmp:
            output = Path(tmp) / "current.json"
            with self.assertRaisesRegex(fetch.FetchError, "checksum mismatch"):
                fetch.write_snapshot_atomic(payload, output)
            self.assertFalse(output.exists())

    def test_malformed_checksum_is_rejected(self):
        payload = snapshot()
        payload["snapshot_sha256"] = "not-a-sha256"
        with self.assertRaisesRegex(fetch.FetchError, "missing or malformed"):
            fetch.verify_snapshot(payload)

    def test_ticker_universe_is_json_and_explicitly_marks_unknown_metadata(self):
        tickers = fetch.load_universe()
        self.assertGreater(len(tickers), 0)
        self.assertEqual(len({item.symbol for item in tickers}), len(tickers))
        self.assertTrue(any(item.active_status == "unknown" for item in tickers))

    def test_root_python_has_no_retired_pickle_or_personal_path_acquisition(self):
        forbidden = ("C:\\Users\\", "pickle.load", "pickle.dump", ".to_pickle(")
        for path in sorted(ROOT.glob("*.py")):
            text = path.read_text(encoding="utf-8")
            for marker in forbidden:
                self.assertNotIn(marker, text, msg=f"retired acquisition marker in {path.name}: {marker}")

    def test_root_notebooks_are_not_byte_identical_aliases(self):
        by_digest = {}
        for path in sorted(ROOT.glob("*.ipynb")):
            digest = hashlib.sha256(path.read_bytes()).hexdigest()
            self.assertNotIn(
                digest,
                by_digest,
                msg=f"duplicate notebook alias: {by_digest.get(digest)} and {path.name}",
            )
            by_digest[digest] = path.name


if __name__ == "__main__":
    unittest.main()
