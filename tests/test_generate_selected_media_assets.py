import unittest

from scripts import generate_selected_media_assets


class GenerateSelectedMediaAssetsTest(unittest.TestCase):
    def test_selected_media_items_are_the_non_voice_picks(self):
        items = generate_selected_media_assets.selected_media_items()
        ids = {item["id"] for item in items}

        self.assertEqual(len(items), 29)
        self.assertIn("jury-rigged-theme-hornpipe-20", ids)
        self.assertIn("downwind-video-logo-breaking-wave", ids)
        self.assertIn("jury-rigged-sting-captains-bad-idea", ids)
        self.assertNotIn("school-docs-to-demo-30", ids)

    def test_parse_duration_reads_seconds(self):
        self.assertEqual(generate_selected_media_assets.parse_duration("20s"), 20)
        self.assertEqual(generate_selected_media_assets.parse_duration("4.5 seconds"), 4.5)
        self.assertEqual(generate_selected_media_assets.parse_duration("unknown"), 4.0)

    def test_audio_prompt_for_theme_is_instrumental_hornpipe(self):
        item = {
            "assetType": "theme_music_brief",
            "title": "Jury Rigged - Main Hornpipe Theme",
            "audioBrief": "Fast comic hornpipe.",
        }

        prompt = generate_selected_media_assets.audio_prompt(item)

        self.assertIn("hornpipe", prompt.lower())
        self.assertIn("No vocals", prompt)

    def test_render_workbench_contains_video_and_audio_controls(self):
        page = generate_selected_media_assets.render_workbench(
            {
                "campaign": "test",
                "generatedAt": "2026-06-15T12:00:00+01:00",
                "assets": [
                    {
                        "assetId": "logo",
                        "project": "Downwind",
                        "assetType": "animated_logo_brief",
                        "title": "Downwind Logo",
                        "durationSeconds": 4,
                        "audio": "media/logo.mp3",
                        "video": "media/logo.mp4",
                        "brief": "brief",
                        "audioBrief": "audio",
                        "visualBrief": "visual",
                    }
                ],
            }
        )

        self.assertIn("Downwind Logo", page)
        self.assertIn("video controls", page)
        self.assertIn("audio controls", page)


if __name__ == "__main__":
    unittest.main()
