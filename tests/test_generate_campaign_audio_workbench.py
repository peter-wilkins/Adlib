import tempfile
import unittest
from pathlib import Path

from scripts import generate_campaign_audio_workbench


class GenerateCampaignAudioWorkbenchTest(unittest.TestCase):
    def test_render_page_contains_audio_and_gate_status(self):
        payload = {
            "campaign": "test-campaign",
            "generatedAt": "2026-06-15T12:00:00+01:00",
            "assets": [
                {
                    "assetId": "asset",
                    "takeSlug": "complete",
                    "project": "Field Relay",
                    "title": "Field Relay Test",
                    "assetKind": "complete_advert_preview",
                    "voice": "Lily",
                    "media": "media/asset.mp3",
                    "scriptText": "Approved script.",
                    "testStatus": "preflight_passed_needs_creative_critic",
                    "transcript": "Approved script.",
                }
            ],
        }

        page = generate_campaign_audio_workbench.render_page(payload)

        self.assertIn("media/asset.mp3", page)
        self.assertIn("Field Relay Test", page)
        self.assertIn("word gate pass", page)
        self.assertIn("1 generated audio clips", page)
        self.assertNotIn("generated Lily clips", page)

    def test_asset_from_metadata_extracts_gate_transcript(self):
        data = {
            "provider": "elevenlabs",
            "assetId": "fieldrelay_lily_test",
            "takeSlug": "complete_spot",
            "title": "Field Relay Test",
            "assetKind": "complete_advert_preview",
            "voiceName": "Lily",
            "scriptText": "Approved script.",
            "sourceDraft": "docs/adverts/selection-workbenches/source.json#fieldrelay-lily-test",
            "testStatus": "script_drift_mismatch",
            "qualityGate": {
                "technicalPreflight": {
                    "status": "fail",
                    "scriptDrift": {"status": "mismatch", "similarity": 0.9},
                    "transcription": {
                        "text": "Spoken script.",
                        "backend": {"processorId": "whisper-1"},
                    },
                }
            },
        }

        asset = generate_campaign_audio_workbench.asset_from_metadata(data, "media/test.mp3")

        self.assertEqual(asset["project"], "Field Relay")
        self.assertEqual(asset["driftStatus"], "mismatch")
        self.assertEqual(asset["transcript"], "Spoken script.")
        self.assertEqual(asset["transcriber"], "whisper-1")

    def test_project_from_source_prefers_title_over_batch_filename(self):
        project = generate_campaign_audio_workbench.project_from_source(
            "docs/adverts/selection-workbenches/2026-06-15-continuum-asset-candidates.json#jury-rigged-show-trailer-30",
            "Jury Rigged - Show Trailer 30s",
        )

        self.assertEqual(project, "Jury Rigged")

    def test_project_from_source_detects_jobdone_from_source(self):
        project = generate_campaign_audio_workbench.project_from_source(
            "scripts/generate_audio_advert_drafts.py#JD_ad01_yorkshire_interrupt",
            "JobDone Yorkshire Enterprise Interrupt Audition",
        )

        self.assertEqual(project, "JobDone")

    def test_build_assets_copies_campaign_media(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            source = root / "asset.mp3"
            source.write_bytes(b"mp3")
            metadata_dir = root / "processed" / "test-campaign" / "elevenlabs"
            metadata_dir.mkdir(parents=True)
            (metadata_dir / "asset.json").write_text(
                """
{
  "provider": "elevenlabs",
  "campaign": "test-campaign",
  "assetId": "asset",
  "takeSlug": "complete",
  "voiceProfile": "narrator_lily",
  "title": "Test Asset",
  "reaperAssetPath": "%s",
  "scriptText": "Approved script.",
  "testStatus": "preflight_passed_needs_creative_critic"
}
"""
                % source,
                encoding="utf-8",
            )
            original_root = generate_campaign_audio_workbench.PROCESSED_ROOT
            try:
                generate_campaign_audio_workbench.PROCESSED_ROOT = root / "processed"
                assets = generate_campaign_audio_workbench.build_assets("test-campaign", root / "out")
            finally:
                generate_campaign_audio_workbench.PROCESSED_ROOT = original_root

        self.assertEqual(len(assets), 1)
        self.assertEqual(assets[0]["media"], "media/asset__complete__narrator-lily.mp3")


if __name__ == "__main__":
    unittest.main()
