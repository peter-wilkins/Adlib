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

    def test_picks_reference_known_candidate_ids(self):
        candidates = generate_asset_selection_workbench.load_workbench(
            Path("docs/adverts/selection-workbenches/2026-06-15-continuum-asset-candidates.json")
        )
        picks = json.loads(
            Path("docs/adverts/selection-workbenches/2026-06-15-continuum-asset-picks.json").read_text(
                encoding="utf-8"
            )
        )
        candidate_ids = {item["id"] for item in candidates["items"]}
        selected_ids = set(picks["selectedIds"])
        not_selected_ids = set(picks["notSelectedIds"])

        self.assertEqual(picks["selectedCount"], len(picks["selectedIds"]))
        self.assertFalse(selected_ids & not_selected_ids)
        self.assertTrue(selected_ids <= candidate_ids)
        self.assertTrue(not_selected_ids <= candidate_ids)
        self.assertEqual(selected_ids | not_selected_ids, candidate_ids)

    def test_selected_spoken_assets_are_in_lily_manifest(self):
        candidates = generate_asset_selection_workbench.load_workbench(
            Path("docs/adverts/selection-workbenches/2026-06-15-continuum-asset-candidates.json")
        )
        picks = json.loads(
            Path("docs/adverts/selection-workbenches/2026-06-15-continuum-asset-picks.json").read_text(
                encoding="utf-8"
            )
        )
        manifest = json.loads(
            Path("docs/adverts/selection-workbenches/elevenlabs-continuum-selected-voice-v1.json").read_text(
                encoding="utf-8"
            )
        )
        selected_ids = set(picks["selectedIds"])
        selected_spoken_ids = {
            item["id"]
            for item in candidates["items"]
            if item["id"] in selected_ids and item["assetType"] in {"audio_ad_script", "audio_sting_script"}
        }
        manifest_source_ids = {take["sourceDraft"].split("#", 1)[1] for take in manifest["takes"]}

        self.assertEqual(selected_spoken_ids, manifest_source_ids)
        self.assertEqual(set(manifest["voiceProfiles"]), {"narrator_lily"})
        for take in manifest["takes"]:
            self.assertEqual(take["voiceProfiles"], ["narrator_lily"])

    def test_movie_trailer_batch_contains_jobdone_gary_story(self):
        trailers = generate_asset_selection_workbench.load_workbench(
            Path("docs/adverts/selection-workbenches/2026-06-16-movie-trailer-candidates.json")
        )
        items = trailers["items"]
        gary = next(item for item in items if item["id"] == "jobdone-gary-great-leak-trailer-150")

        self.assertEqual(len(items), 7)
        self.assertEqual(gary["assetType"], "movie_trailer_script")
        self.assertIn("great leak", gary["title"].lower())
        self.assertIn("Poor Gary", gary["scriptText"])
        self.assertIn("Timeline", gary["scriptText"])
        self.assertIn("jobdone.continuumkit.org", gary["scriptText"])


if __name__ == "__main__":
    unittest.main()
