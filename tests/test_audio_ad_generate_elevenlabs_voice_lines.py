import argparse
import json
import subprocess
import tempfile
import unittest
from pathlib import Path

from scripts import audio_ad_generate_elevenlabs_voice_lines

ROOT = Path(__file__).resolve().parents[1]


class AudioAdGenerateElevenLabsVoiceLinesTest(unittest.TestCase):
    def test_default_output_dirs_follow_manifest_campaign(self):
        args = argparse.Namespace(audio_dir=None, meta_dir=None, reaper_asset_dir=None)
        manifest = {"campaign": "living-water-skills-pond-challenge"}

        audio_dir, meta_dir, reaper_asset_dir = audio_ad_generate_elevenlabs_voice_lines.resolve_output_dirs(
            args,
            manifest,
        )

        self.assertEqual(
            audio_dir,
            audio_ad_generate_elevenlabs_voice_lines.ROOT
            / "data/raw/audio-ads/living-water-skills-pond-challenge/elevenlabs/voice-lines",
        )
        self.assertEqual(
            meta_dir,
            audio_ad_generate_elevenlabs_voice_lines.ROOT
            / "data/processed/audio-ads/living-water-skills-pond-challenge/elevenlabs/voice-lines",
        )
        self.assertEqual(
            reaper_asset_dir,
            audio_ad_generate_elevenlabs_voice_lines.ROOT
            / "local/audio-adverts/living-water-skills-pond-challenge/assets",
        )

    def test_list_does_not_require_paid_generation_approval(self):
        manifest = {
            "scriptId": "TEST",
            "scriptVersion": "draft",
            "campaign": "test-campaign",
            "approvedForPaidGeneration": False,
            "voiceProfiles": {
                "voice": {
                    "voiceId": "voice-id",
                    "voiceName": "Test Voice",
                    "defaultSettings": {},
                }
            },
            "takes": [
                {
                    "assetId": "line",
                    "takeSlug": "draft",
                    "speaker": "speaker",
                    "folder": "voice/test",
                    "text": "Draft line.",
                    "voiceProfiles": ["voice"],
                }
            ],
        }
        with tempfile.NamedTemporaryFile("w", suffix=".json", encoding="utf-8") as handle:
            json.dump(manifest, handle)
            handle.flush()

            result = subprocess.run(
                [
                    "python3",
                    "scripts/audio_ad_generate_elevenlabs_voice_lines.py",
                    "--manifest",
                    handle.name,
                    "--list",
                ],
                cwd=ROOT,
                text=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                check=False,
            )

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stdout.strip(), "line:draft:voice:test-voice")


if __name__ == "__main__":
    unittest.main()
