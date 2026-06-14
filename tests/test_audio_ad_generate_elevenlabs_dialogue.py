import json
import unittest
from pathlib import Path

from scripts import audio_ad_generate_elevenlabs_dialogue


ROOT = Path(__file__).resolve().parents[1]


class AudioAdGenerateElevenLabsDialogueTest(unittest.TestCase):
    def test_manifest_is_approved_for_first_paid_experiment(self):
        manifest = audio_ad_generate_elevenlabs_dialogue.load_manifest(
            ROOT / "docs/adverts/jobdone-dog-callback/elevenlabs-dialogue-v1.json"
        )

        self.assertTrue(manifest["approvedForPaidGeneration"])
        self.assertEqual(manifest["scriptId"], "JD_ad02_dog_callback")
        self.assertEqual(manifest["modelId"], "eleven_v3")
        self.assertLess(total_input_characters(manifest), 2000)
        audio_ad_generate_elevenlabs_dialogue.validate_manifest_inputs(manifest)

    def test_payload_maps_lines_to_selected_voice_ids(self):
        manifest = {
            "inputs": [
                {"speaker": "tradesperson", "text": "Line one."},
                {"speaker": "app_voice", "text": "Line two."},
            ],
            "modelId": "eleven_v3",
            "seed": 123,
        }
        voices = {
            "tradesperson": {"voice_id": "voice_tradesperson"},
            "app_voice": {"voice_id": "voice_app"},
        }

        payload = audio_ad_generate_elevenlabs_dialogue.build_dialogue_payload(manifest, voices)

        self.assertEqual(payload["model_id"], "eleven_v3")
        self.assertEqual(payload["seed"], 123)
        self.assertEqual(
            payload["inputs"],
            [
                {"text": "Line one.", "voice_id": "voice_tradesperson"},
                {"text": "Line two.", "voice_id": "voice_app"},
            ],
        )

    def test_voice_selection_prefers_matching_terms(self):
        speaker = {"voiceSearchTerms": ["british", "calm"]}
        voices = [
            {"voice_id": "first", "name": "First", "description": "american loud"},
            {"voice_id": "second", "name": "Second", "description": "british calm narrator"},
        ]

        selected = audio_ad_generate_elevenlabs_dialogue.select_voice_for_speaker(speaker, voices)

        self.assertEqual(selected["voice_id"], "second")
        self.assertEqual(selected["selection_reason"], "auto-score:2")

    def test_manifest_validation_rejects_tag_only_inputs(self):
        manifest = {"inputs": [{"lineId": "sfx_only", "text": "[front door shuts]"}]}

        with self.assertRaises(audio_ad_generate_elevenlabs_dialogue.GenerationError):
            audio_ad_generate_elevenlabs_dialogue.validate_manifest_inputs(manifest)


def total_input_characters(manifest: dict[str, object]) -> int:
    return sum(len(line["text"]) for line in manifest["inputs"])


if __name__ == "__main__":
    unittest.main()
