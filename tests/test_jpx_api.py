import csv
import hashlib
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import scripts.build_jpx_api as api


class JpxApiTest(unittest.TestCase):
    def test_build_distribution(self):
        with tempfile.TemporaryDirectory() as tmp:
            with patch.object(api, "OUT", Path(tmp)):
                manifest = api.build()
                listings = json.loads((Path(tmp) / "listings.json").read_text(encoding="utf-8"))
                with (Path(tmp) / "listings.csv").open(encoding="utf-8", newline="") as handle:
                    csv_rows = list(csv.DictReader(handle))
                self.assertEqual(7, manifest["record_count"])
                self.assertEqual(7, listings["count"])
                self.assertEqual(7, len(csv_rows))
                self.assertEqual("600A", listings["records"][0]["code"])
                self.assertEqual("613A", listings["records"][-1]["code"])
                for name, metadata in manifest["distributions"].items():
                    payload = (Path(tmp) / name).read_bytes()
                    self.assertEqual(len(payload), metadata["bytes"])
                    self.assertEqual(hashlib.sha256(payload).hexdigest(), metadata["sha256"])

    def test_source_codes_are_unique(self):
        source = json.loads(api.SOURCE.read_text(encoding="utf-8"))
        codes = [row["code"] for row in source["records"]]
        self.assertEqual(len(codes), len(set(codes)))


if __name__ == "__main__":
    unittest.main()
