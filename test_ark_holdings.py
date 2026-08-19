import json
import unittest
from datetime import date, timedelta
from pathlib import Path
from tempfile import TemporaryDirectory

from build_ark_views import FUNDS, REQUIRED_TRADING_DAYS, build, build_readiness
from collect_ark_holdings import CANDIDATE_FILES, audit_rows, parse_csv, write_snapshot


def payload(as_of="08/17/2026", suffix="a", weights=("1.0", "2.0")):
    snapshots = []
    for index, fund in enumerate(("ARKK", "ARKQ")):
        snapshots.append(
            {
                "fund": fund,
                "as_of": as_of,
                "retrieved_at": "2026-08-17T10:00:00+00:00",
                "source_csv_url": f"https://example.test/{fund}.csv",
                "source_sha256": (suffix + fund).ljust(64, "0"),
                "row_count": 1,
                "holdings": [
                    {
                        "fund": fund,
                        "company": "EXAMPLE INC",
                        "ticker": "EXM",
                        "cusip": "123",
                        "weight(%)": weights[index],
                    }
                ],
            }
        )
    return {"schema_version": 1, "publisher": "ARK ETF Trust", "snapshots": snapshots}


def complete_payload(as_of: str, suffix: str) -> dict:
    snapshots = []
    for index, fund in enumerate(FUNDS):
        snapshots.append(
            {
                "fund": fund,
                "as_of": as_of,
                "retrieved_at": f"{as_of}T10:00:00+00:00",
                "source_csv_url": f"https://example.test/{fund}.csv",
                "source_sha256": (suffix + fund).ljust(64, "0")[:64],
                "row_count": 1,
                "holdings": [
                    {
                        "fund": fund,
                        "company": f"EXAMPLE {index}",
                        "ticker": f"EX{index}",
                        "cusip": f"CUSIP{index}",
                        "weight(%)": "100.0",
                    }
                ],
            }
        )
    return {"schema_version": 1, "publisher": "ARK ETF Trust", "snapshots": snapshots}


class ArkHoldingsTest(unittest.TestCase):
    def test_parse_csv_keeps_holdings_and_drops_footer(self):
        raw = b"date,fund,company,ticker,cusip,shares,market value($),weight(%)\n08/17/2026,ARKK,EXAMPLE INC,EXM,123,100,1000,1.2\n,,,,,,,\nThe principal risks,,,,,,,\n"
        as_of, rows = parse_csv(raw, "ARKK")
        self.assertEqual(as_of, "08/17/2026")
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["company"], "EXAMPLE INC")
        self.assertEqual(rows[0]["fund_ticker"], "ARKK")

    def test_audit_rows_checks_identity_duplicates_and_weight_total(self):
        rows = [
            {"cusip": "111", "weight (%)": "60.0%"},
            {"cusip": "222", "weight (%)": "40.0%"},
        ]
        self.assertEqual(audit_rows(rows, "ARKK"), {"row_count": 2, "weight_total": 100.0})

        with self.assertRaisesRegex(ValueError, "duplicate security identity"):
            audit_rows([rows[0], rows[0]], "ARKK")
        with self.assertRaisesRegex(ValueError, "no weight"):
            audit_rows([{"cusip": "333"}], "ARKK")
        with self.assertRaisesRegex(ValueError, "expected about 100"):
            audit_rows([{"cusip": "333", "weight (%)": "75%"}], "ARKK")

    def test_arkx_uses_current_fund_name(self):
        self.assertEqual(
            CANDIDATE_FILES["ARKX"],
            ("ARK_SPACE_&_DEFENSE_INNOVATION_ETF_ARKX_HOLDINGS.csv",),
        )

    def test_snapshot_path_is_append_only_and_content_addressed(self):
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            first = write_snapshot(payload(), root)
            second = write_snapshot(payload(), root)
            changed = write_snapshot(payload(suffix="b"), root)
            self.assertEqual(first, second)
            self.assertNotEqual(first, changed)
            self.assertEqual(first.parent.name, "2026-08-17")
            self.assertTrue(first.exists() and changed.exists())

    def test_views_build_changes_overlap_audit_and_readiness(self):
        with TemporaryDirectory() as tmp:
            root = Path(tmp) / "history"
            out = Path(tmp) / "views"
            write_snapshot(payload(as_of="08/17/2026", suffix="a"), root)
            write_snapshot(payload(as_of="08/18/2026", suffix="b", weights=("1.5", "2.0")), root)
            build(root, out)
            latest = json.loads((out / "latest.json").read_text())
            changes = json.loads((out / "changes.json").read_text())
            overlap = json.loads((out / "overlap.json").read_text())
            readiness = json.loads((out / "readiness.json").read_text())
            self.assertEqual(latest["snapshot_count"], 2)
            self.assertEqual(
                latest["funds"]["ARKK"]["audit"],
                {
                    "weight_total": 1.5,
                    "duplicate_identity_count": 0,
                    "missing_identity_count": 0,
                    "missing_weight_count": 0,
                },
            )
            self.assertEqual(changes["funds"]["ARKK"]["weight_changes"][0]["weight"], 1.5)
            self.assertEqual(overlap["shared_holdings"][0]["fund_count"], 2)
            self.assertEqual(overlap["matrix"]["ARKK"]["ARKQ"], 1)
            self.assertEqual(overlap["matrix"]["ARKQ"]["ARKK"], 1)
            self.assertEqual(overlap["matrix"]["ARKK"]["ARKK"], 1)
            self.assertEqual(overlap["matrix"]["ARKK"]["ARKX"], 0)
            self.assertFalse(readiness["complete"])
            self.assertEqual(readiness["observed_trading_days"], 2)
            self.assertEqual(readiness["remaining_trading_days"], 58)
            self.assertFalse(readiness["checks"]["all_daily_sets_have_six_funds"])

    def test_readiness_completes_only_after_60_clean_six_fund_days(self):
        start = date(2026, 1, 2)
        history = []
        for offset in range(REQUIRED_TRADING_DAYS):
            day = start + timedelta(days=offset)
            history.append(complete_payload(day.isoformat(), f"{offset:02d}"))
        readiness = build_readiness(history)
        self.assertTrue(readiness["complete"])
        self.assertEqual(readiness["observed_trading_days"], REQUIRED_TRADING_DAYS)
        self.assertEqual(readiness["remaining_trading_days"], 0)
        self.assertEqual(readiness["complete_daily_sets"], REQUIRED_TRADING_DAYS)
        self.assertTrue(all(readiness["checks"].values()))

    def test_readiness_fails_closed_on_missing_provenance(self):
        history = [complete_payload("2026-01-02", "a")]
        history[0]["snapshots"][0]["source_sha256"] = ""
        readiness = build_readiness(history)
        self.assertFalse(readiness["complete"])
        self.assertFalse(readiness["checks"]["all_snapshots_have_provenance"])

    def test_views_order_snapshots_across_year_boundary(self):
        with TemporaryDirectory() as tmp:
            root = Path(tmp) / "history"
            out = Path(tmp) / "views"
            write_snapshot(payload(as_of="12/31/2026", suffix="a"), root)
            write_snapshot(payload(as_of="01/04/2027", suffix="b"), root)
            build(root, out)
            latest = json.loads((out / "latest.json").read_text())
            changes = json.loads((out / "changes.json").read_text())
            self.assertEqual(latest["as_of"], "01/04/2027")
            self.assertEqual(changes["previous_as_of"], "12/31/2026")


if __name__ == "__main__":
    unittest.main()
