import unittest
from pathlib import Path

from scripts import generate_audio_advert_drafts


class GenerateAudioAdvertDraftsTest(unittest.TestCase):
    def test_dog_callback_snapshot_includes_sfx_intents(self):
        snapshot = generate_audio_advert_drafts.snapshot("2026-06-02T12:00:00+01:00")
        dog = next(draft for draft in snapshot["drafts"] if draft["scriptId"] == "JD_ad02_dog_callback")

        self.assertEqual(
            [intent["beatId"] for intent in dog["sfxIntents"]],
            ["charlie_first_bite", "charlie_callback_warning"],
        )
        self.assertIn("small dog bark", dog["sfxIntents"][0]["searchTerms"])
        self.assertEqual(dog["sfxIntents"][0]["licensePriority"], "cc0")
        self.assertIn("long barking sequence", dog["sfxIntents"][1]["avoid"])

    def test_page_renders_audio_previews(self):
        audio_previews = [
            {
                "previewId": "jobdone-dog-callback-v0",
                "label": "JobDone dog callback v0",
                "description": "Test render.",
                "sourcePath": "/tmp/jobdone-dog-callback-v0.wav",
                "href": "media/jobdone-dog-callback-v0.wav",
                "available": True,
                "bytes": 1234,
                "sha256": "abc123",
            }
        ]

        page = generate_audio_advert_drafts.render_page(
            "2026-06-02T12:00:00+01:00",
            audio_previews,
        )
        snapshot = generate_audio_advert_drafts.snapshot(
            "2026-06-02T12:00:00+01:00",
            audio_previews,
        )

        self.assertIn('<audio controls preload="metadata" src="media/jobdone-dog-callback-v0.wav">', page)
        self.assertIn("Open audio file", page)
        self.assertEqual(snapshot["audioPreviews"][0]["previewId"], "jobdone-dog-callback-v0")

    def test_collect_audio_previews_includes_generated_audio(self):
        original_globs = generate_audio_advert_drafts.GENERATED_AUDIO_GLOBS
        original_previews = generate_audio_advert_drafts.LOCAL_AUDIO_PREVIEWS
        try:
            generate_audio_advert_drafts.LOCAL_AUDIO_PREVIEWS = ()
            generate_audio_advert_drafts.GENERATED_AUDIO_GLOBS = (
                ("Generated", "Generated description.", "tests/fixtures/audio-previews/*"),
            )
            fixture = Path("tests/fixtures/audio-previews/test-take.mp3")
            fixture.parent.mkdir(parents=True, exist_ok=True)
            fixture.write_bytes(b"mp3")

            previews = generate_audio_advert_drafts.collect_audio_previews()

            self.assertEqual(len(previews), 1)
            self.assertEqual(previews[0].preview_id, "test-take")
            self.assertEqual(previews[0].label, "Generated: test-take")
        finally:
            generate_audio_advert_drafts.GENERATED_AUDIO_GLOBS = original_globs
            generate_audio_advert_drafts.LOCAL_AUDIO_PREVIEWS = original_previews
            fixture.unlink(missing_ok=True)


if __name__ == "__main__":
    unittest.main()
