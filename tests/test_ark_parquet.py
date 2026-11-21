"""Source validation tests without a database or network connection."""
from __future__ import annotations

from copy import deepcopy
from decimal import Decimal
from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from build_ark_parquet import FUNDS, numeric, snapshot_rows, snapshot_date  # noqa: E402


class ParquetInputTest(unittest.TestCase):
    def sample(self):
        return {"snapshots": [
            {
                "fund": fund, "as_of": "11/20/2026",
                "source_sha256": "a" * 64,
                "source_csv_url": "https://example.org/a.csv",
                "row_count": 1,
                "holdings": [{
                    "cusip": f"ID-{fund}", "ticker": "", "company": "TEST HOLDING",
                    "shares": "1,000", "market value ($)": "$12,300.20",
                    "weight (%)": "100.00%",
                }],
            }
            for fund in sorted(FUNDS)
        ]}

    def test_missing_ticker_stays_blank_not_fabricated(self):
        rows = snapshot_rows(self.sample())
        self.assertEqual(len(rows), 6)
        self.assertEqual(rows[0][3], "")
        self.assertEqual(rows[0][6], Decimal("12300.20"))
        self.assertEqual(rows[0][7], Decimal("100.00"))

    def test_as_of_mismatch_is_rejected(self):
        payload = self.sample()
        payload["snapshots"][0]["as_of"] = "11/19/2026"
        with self.assertRaisesRegex(ValueError, "mixed as_of"):
            snapshot_rows(payload)

    def test_duplicate_security_is_rejected(self):
        payload = self.sample()
        row = deepcopy(payload["snapshots"][0]["holdings"][0])
        payload["snapshots"][0]["holdings"].append(row)
        payload["snapshots"][0]["row_count"] = 2
        with self.assertRaisesRegex(ValueError, "duplicate holding identity"):
            snapshot_rows(payload)

    def test_missing_numeric_not_zero(self):
        payload = self.sample()
        payload["snapshots"][0]["holdings"][0]["weight (%)"] = ""
        with self.assertRaisesRegex(ValueError, "missing numeric"):
            snapshot_rows(payload)

    def test_nonfinite_and_invalid_date_are_rejected(self):
        with self.assertRaisesRegex(ValueError, "non-finite"):
            numeric("NaN")
        with self.assertRaises(ValueError):
            snapshot_date("2026-11-20")


if __name__ == "__main__":
    unittest.main()
