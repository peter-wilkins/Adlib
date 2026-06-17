import json
import tempfile
import unittest
from pathlib import Path

from scripts import audio_ad_generate_elevenlabs_music


class AudioAdGenerateElevenLabsMusicTest(unittest.TestCase):
    def test_default_manifest_has_three_safe_music_auditions(self):
        manifest = json.loads(audio_ad_generate_elevenlabs_music.DEFAULT_MANIFEST.read_text(encoding="utf-8"))

        self.assertTrue(manifest["approvedForPaidGeneration"])
        self.assertEqual(manifest["endpoint"], "https://api.elevenlabs.io/v1/music")
        self.assertEqual(manifest["modelId"], "music_v2")
        self.assertEqual(len(manifest["takes"]), 3)
        manifest_text = json.dumps(manifest).lower()
        self.assertNotIn("mario kart", manifest_text)
        for take in manifest["takes"]:
            self.assertIn("no direct imitation", take["prompt"].lower())

    def test_write_outputs_stores_prompt_song_id_and_audio_paths(self):
        manifest = {
            "scriptId": "music_test",
            "scriptVersion": "v1",
            "campaign": "music-test",
            "endpoint": "https://api.elevenlabs.io/v1/music",
            "modelId": "music_v2",
            "outputFormat": "mp3_44100_128",
        }
        take = {
            "assetId": "test-music",
            "title": "Test Music",
            "project": "Jury Rigged",
            "assetKind": "music_audition",
            "folder": "music/test",
            "prompt": "Instrumental hornpipe.",
            "musicLengthMs": 3000,
        }
        audio = b"fake mp3"
        headers = {"song-id": "song_123"}
        payload = {
            "prompt": take["prompt"],
            "music_length_ms": 3000,
            "force_instrumental": True,
            "model_id": "music_v2",
        }

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            result = audio_ad_generate_elevenlabs_music.write_outputs(
                manifest,
                take,
                audio,
                headers,
                payload,
                root / "raw",
                root / "meta",
                root / "assets",
            )

            metadata = json.loads(Path(result["metadataPath"]).read_text(encoding="utf-8"))

        self.assertEqual(metadata["provider"], "elevenlabs")
        self.assertEqual(metadata["providerProduct"], "music")
        self.assertEqual(metadata["prompt"], "Instrumental hornpipe.")
        self.assertEqual(metadata["songId"], "song_123")
        self.assertTrue(metadata["rawAudioPath"].endswith(".mp3"))
        self.assertTrue(metadata["reaperAssetPath"].endswith(".mp3"))


if __name__ == "__main__":
    unittest.main()
