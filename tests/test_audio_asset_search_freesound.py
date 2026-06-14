import tempfile
import unittest
from pathlib import Path

from scripts import audio_asset_search_freesound as freesound


class AudioAssetSearchFreesoundTest(unittest.TestCase):
    def test_build_filter_defaults_to_cc0_and_short_duration(self):
        self.assertEqual(
            freesound.build_filter("Creative Commons 0", 0.2, 8.0, []),
            'license:"Creative Commons 0" duration:[0.2 TO 8]',
        )

    def test_build_filter_adds_extra_filters(self):
        self.assertEqual(
            freesound.build_filter("Creative Commons 0", 0.2, 8.0, ["tag:dog"]),
            'license:"Creative Commons 0" duration:[0.2 TO 8] tag:dog',
        )

    def test_find_api_token_reads_ignored_env_file(self):
        with tempfile.TemporaryDirectory() as tmp:
            env_file = Path(tmp) / ".env"
            env_file.write_text("FREESOUND_API_TOKEN=abc123\n", encoding="utf-8")

            self.assertEqual(
                freesound.find_api_token(env_file, environ={}),
                "abc123",
            )

    def test_build_search_params_caps_page_size(self):
        params = freesound.build_search_params("dog bark", "license:x", "rating_desc", 999, "secret")

        self.assertEqual(params["page_size"], "150")
        self.assertEqual(params["query"], "dog bark")
        self.assertEqual(params["token"], "secret")

    def test_normalise_candidate_records_license_and_preview(self):
        candidate = freesound.normalise_candidate(
            {
                "id": 123,
                "name": "Small bark",
                "url": "https://freesound.org/s/123/",
                "username": "sounduser",
                "license": "Creative Commons 0",
                "tags": ["dog", "bark"],
                "duration": 1.2,
                "type": "wav",
                "filesize": 1000,
                "previews": {"preview-hq-mp3": "https://cdn.example/bark.mp3"},
                "description": "A bark.",
                "created": "2026-01-01T00:00:00",
                "avg_rating": 4.5,
                "num_ratings": 3,
                "num_downloads": 99,
                "score": 12.3,
            },
            query="dog bark",
            checked_at="2026-06-02T12:00:00Z",
        )

        self.assertEqual(candidate["asset_id"], "sfx_dog-bark_20260602_freesound_123")
        self.assertEqual(candidate["license_url"], "https://creativecommons.org/publicdomain/zero/1.0/")
        self.assertFalse(candidate["attribution_required"])
        self.assertEqual(candidate["commercial_use_status"], "allowed")
        self.assertEqual(candidate["preferred_preview_url"], "https://cdn.example/bark.mp3")

    def test_candidate_document_redacts_pagination_tokens(self):
        document = freesound.build_candidate_document(
            {
                "count": 1,
                "next": "https://freesound.org/apiv2/search/?page=2&token=secret",
                "previous": None,
                "results": [],
            },
            query="dog bark",
            search_filter='license:"Creative Commons 0"',
            sort="rating_desc",
            requested_at="2026-06-02T12:00:00Z",
            redacted_url="https://freesound.org/apiv2/search/?token=REDACTED",
        )

        self.assertIn("token=REDACTED", document["next"])
        self.assertNotIn("secret", document["next"])


if __name__ == "__main__":
    unittest.main()
