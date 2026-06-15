import json
import tempfile
import unittest
from pathlib import Path

from scripts import generate_asset_selection_workbench


class GenerateAssetSelectionWorkbenchTest(unittest.TestCase):
    def test_render_page_contains_selection_controls(self):
        data = {
            "schema": "adlib.asset-selection-workbench.v1",
            "batchId": "test-batch",
            "title": "Test Batch",
            "summary": "Pick assets.",
            "selectionNote": "Test note.",
            "items": [
                {
                    "id": "asset-1",
                    "project": "Field Relay",
                    "assetType": "audio_ad_script",
                    "priority": "high",
                    "title": "Field Relay Test",
                    "scriptText": "Field Relay test copy.",
                }
            ],
        }

        page = generate_asset_selection_workbench.render_page(data)

        self.assertIn("adlib-selection:${DATA.batchId}", page)
        self.assertIn("Export picks", page)
        self.assertIn('type="checkbox"', page)
        self.assertIn("Field Relay Test", page)
        self.assertIn("Field Relay test copy.", page)

    def test_write_workbench_outputs_html_and_json(self):
        data = generate_asset_selection_workbench.load_workbench(
            Path("docs/adverts/selection-workbenches/2026-06-15-continuum-asset-candidates.json")
        )

        with tempfile.TemporaryDirectory() as tmp:
            out_dir = Path(tmp)
            generate_asset_selection_workbench.write_workbench(data, out_dir)

            page = (out_dir / "index.html").read_text(encoding="utf-8")
            exported = json.loads((out_dir / "candidates.json").read_text(encoding="utf-8"))

        self.assertEqual(exported["batchId"], "continuum-asset-candidates-20260615")
        self.assertGreaterEqual(len(exported["items"]), 30)
        self.assertIn("Field Relay - Hands Free 30s", page)
        self.assertIn("Downwind Logo - Breaking Wave Wipe", page)


if __name__ == "__main__":
    unittest.main()
