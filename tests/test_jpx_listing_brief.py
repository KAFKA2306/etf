import json
import tempfile
import unittest
from pathlib import Path

from scripts.build_jpx_listing_brief import build_brief, render_markdown


FIXTURES = Path(__file__).parent / "fixtures" / "jpx_listing_brief"
WATCHLISTS = Path(__file__).parents[1] / "config" / "jpx-watchlists.v1.json"


class JpxListingBriefTests(unittest.TestCase):
    def build(self, name="all", watchlists=WATCHLISTS):
        return build_brief(
            FIXTURES / "previous.json",
            FIXTURES / "current.json",
            watchlists,
            name,
            FIXTURES / "previous-manifest.json",
            FIXTURES / "current-manifest.json",
        )

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
        config = json.loads(WATCHLISTS.read_text(encoding="utf-8"))
        config["watchlists"]["selected"] = {
            "codes": ["100A", "300A"],
            "management_companies": [],
            "active_etf": None,
        }
        with tempfile.TemporaryDirectory() as tmp:
            temp_config = Path(tmp) / "watchlists.json"
            temp_config.write_text(json.dumps(config), encoding="utf-8")
            brief = self.build("selected", temp_config)
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
