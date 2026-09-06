import unittest
from pathlib import Path


class PagesUiTest(unittest.TestCase):
    def test_ark_pages_source_action_uses_canonical_view_url(self):
        html = Path("docs/index.html").read_text(encoding="utf-8")

        self.assertIn("fund.source_csv_url", html)
        self.assertIn("ARK公式CSVを確認", html)
        self.assertIn('target="_blank" rel="noopener noreferrer"', html)
        self.assertIn("公式CSV: unavailable", html)

    def test_ark_pages_surfaces_canonical_daily_change_context(self):
        html = Path("docs/index.html").read_text(encoding="utf-8")
        workflow = Path(".github/workflows/pages.yml").read_text(encoding="utf-8")

        self.assertIn("./data/changes.json", html)
        self.assertIn("前回からの変更", html)
        self.assertIn("change?.additions?.length", html)
        self.assertIn("change?.removals?.length", html)
        self.assertIn("change?.weight_changes?.length", html)
        self.assertIn("changes.previous_as_of", html)
        self.assertIn("cp data/ark-views/changes.json docs/data/changes.json", workflow)


if __name__ == "__main__":
    unittest.main()
