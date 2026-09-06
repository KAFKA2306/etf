import unittest
from pathlib import Path


class PagesUiTest(unittest.TestCase):
    def test_ark_pages_source_action_uses_canonical_view_url(self):
        html = Path("docs/index.html").read_text(encoding="utf-8")

        self.assertIn("fund.source_csv_url", html)
        self.assertIn("ARK公式CSVを確認", html)
        self.assertIn('target="_blank" rel="noopener noreferrer"', html)
        self.assertIn("公式CSV: unavailable", html)


if __name__ == "__main__":
    unittest.main()
