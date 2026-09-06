from pathlib import Path


def test_ark_pages_source_action_uses_canonical_view_url():
    html = Path("docs/index.html").read_text(encoding="utf-8")

    assert "fund.source_csv_url" in html
    assert "ARK公式CSVを確認" in html
    assert 'target="_blank" rel="noopener noreferrer"' in html
    assert "公式CSV: unavailable" in html
