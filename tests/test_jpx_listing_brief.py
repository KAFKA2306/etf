import json
import tempfile
import unittest
from pathlib import Path

from scripts.build_jpx_listing_brief import build_brief, render_markdown


def record(code, name, fee=None, active=False, index_name=None):
    return {
        "listing_date": "2026-01-01",
        "code": code,
        "fund_name": name,
        "index_name": index_name,
        "management_company": "Example Asset",
        "trading_unit": 1,
        "trust_fee_percent": fee,
        "indicative_nav": True,
        "active_etf": active,
    }


class JpxListingBriefTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.previous = self.root / "previous.json"
        self.current = self.root / "current.json"
        self.previous_manifest = self.root / "previous-manifest.json"
        self.current_manifest = self.root / "current-manifest.json"
        self.watchlists = self.root / "watchlists.json"
        self.previous.write_text(json.dumps({
            "source_url": "https://www.jpx.co.jp/example",
            "retrieved_at": "2026-01-01T00:00:00+09:00",
            "records": [record("100A", "Changed", 0.1), record("200A", "Removed", None), record("400A", "Stable", 0.4)],
        }), encoding="utf-8")
        self.current.write_text(json.dumps({
            "source_url": "https://www.jpx.co.jp/example",
            "retrieved_at": "2026-02-01T00:00:00+09:00",
            "records": [record("100A", "Changed", 0.2), record("300A", "Added", None), record("400A", "Stable", 0.4)],
        }), encoding="utf-8")
        self.previous_manifest.write_text('{"snapshot":"previous"}\n', encoding="utf-8")
        self.current_manifest.write_text('{"snapshot":"current"}\n', encoding="utf-8")
        self.watchlists.write_text(json.dumps({
            "schema_version": "etf.jpx-watchlists.v1",
            "watchlists": {
                "all": {"codes": [], "management_companies": [], "active_etf": None},
                "selected": {"codes": ["100A", "300A"], "management_companies": [], "active_etf": None},
            },
        }), encoding="utf-8")

    def tearDown(self):
        self.tmp.cleanup()

    def build(self, name="all"):
        return build_brief(self.previous, self.current, self.watchlists, name, self.previous_manifest, self.current_manifest)

    def test_classifies_all_four_states_without_inference(self):
        brief = self.build()
        changes = {item["code"]: item for item in brief["changes"]}
        self.assertEqual(changes["100A"]["status"], "CHANGED")
        self.assertEqual(changes["100A"]["changed_fields"], ["trust_fee_percent"])
        self.assertEqual(changes["200A"]["status"], "REMOVED_FROM_CURRENT_SNAPSHOT")
        self.assertIsNone(changes["200A"]["before"]["trust_fee_percent"])
        self.assertEqual(changes["300A"]["status"], "ADDED")
        self.assertIsNone(changes["300A"]["after"]["trust_fee_percent"])
        self.assertEqual(changes["400A"]["status"], "UNCHANGED")
        self.assertIn("does not assert delisting", brief["semantics"]["removed_from_current_snapshot"])

    def test_watchlist_is_config_only_and_provenance_is_complete(self):
        brief = self.build("selected")
        self.assertEqual([item["code"] for item in brief["changes"]], ["100A", "300A"])
        for side in ("previous", "current"):
            provenance = brief["provenance"][side]
            self.assertEqual(provenance["source_url"], "https://www.jpx.co.jp/example")
            self.assertEqual(len(provenance["snapshot_sha256"]), 64)
            self.assertEqual(len(provenance["manifest_sha256"]), 64)

    def test_output_is_deterministic_and_markdown_preserves_removal_semantics(self):
        first = self.build()
        second = self.build()
        self.assertEqual(json.dumps(first, sort_keys=True), json.dumps(second, sort_keys=True))
        markdown = render_markdown(first)
        self.assertIn("REMOVED_FROM_CURRENT_SNAPSHOT", markdown)
        self.assertIn("does not assert delisting", markdown)
        self.assertIn("Previous manifest SHA-256", markdown)


if __name__ == "__main__":
    unittest.main()
