import json
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from build_ark_views import build
from collect_ark_holdings import CANDIDATE_FILES, parse_csv, write_snapshot


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
                "holdings": [{
                    "fund": fund,
                    "company": "EXAMPLE INC",
                    "ticker": "EXM",
                    "cusip": "123",
                    "weight(%)": weights[index],
                }],
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

    def test_views_build_changes_and_overlap(self):
        with TemporaryDirectory() as tmp:
            root = Path(tmp) / "history"
            out = Path(tmp) / "views"
            write_snapshot(payload(as_of="08/17/2026", suffix="a"), root)
            write_snapshot(payload(as_of="08/18/2026", suffix="b", weights=("1.5", "2.0")), root)
            build(root, out)
            latest = json.loads((out / "latest.json").read_text())
            changes = json.loads((out / "changes.json").read_text())
            overlap = json.loads((out / "overlap.json").read_text())
            self.assertEqual(latest["snapshot_count"], 2)
            self.assertEqual(changes["funds"]["ARKK"]["weight_changes"][0]["weight"], 1.5)
            self.assertEqual(overlap["shared_holdings"][0]["fund_count"], 2)


if __name__ == "__main__":
    unittest.main()
