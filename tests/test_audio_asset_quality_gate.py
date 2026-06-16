import unittest

from scripts.audio_asset_quality_gate import (
    QualityGateError,
    classify_script_drift,
    spoken_script_text,
    timed_tokens_from_words,
    trim_start_for_repair,
    validate_transcriber,
    word_tokens,
    words_url_for,
)


class AudioAssetQualityGateTest(unittest.TestCase):
    def test_word_tokens_normalize_case_and_punctuation(self):
        self.assertEqual(
            word_tokens("Confirmed? Good. That's in the timeline."),
            ["confirmed", "good", "that's", "in", "the", "timeline"],
        )

    def test_exact_script_match_passes(self):
        result = classify_script_drift(
            "What did I do at Mrs Jones last time?",
            "What did I do at Mrs Jones last time?",
        )

        self.assertEqual(result.status, "exact_match")
        self.assertEqual(result.gate_status, "pass")
        self.assertEqual(result.test_status, "preflight_passed_needs_creative_critic")

    def test_leading_performance_direction_is_not_spoken_script(self):
        self.assertEqual(
            spoken_script_text("[warm, practical] Exactly. I think you're ready."),
            "Exactly. I think you're ready.",
        )

    def test_bracketed_direction_does_not_create_drift(self):
        result = classify_script_drift(
            "[warm, practical] Exactly. I think you're ready.",
            "Exactly. I think you're ready.",
        )

        self.assertEqual(result.status, "exact_match")
        self.assertEqual(result.gate_status, "pass")

    def test_extra_leading_words_after_direction_are_repairable(self):
        result = classify_script_drift(
            "[warm, practical] Exactly. I think you're ready.",
            "And exactly. I think you're ready.",
        )

        self.assertEqual(result.status, "extra_leading_words")
        self.assertEqual(result.gate_status, "repair_needed")
        self.assertEqual(result.extra_leading_words, ["and"])

    def test_extra_leading_words_are_repairable(self):
        result = classify_script_drift(
            "Add that to the JobDone note.",
            "Sure. Add that to the JobDone note.",
        )

        self.assertEqual(result.status, "extra_leading_words")
        self.assertEqual(result.gate_status, "repair_needed")
        self.assertEqual(result.test_status, "repair_trim_leading_words")
        self.assertEqual(result.extra_leading_words, ["sure"])

    def test_project_name_spelling_variants_do_not_create_drift(self):
        result = classify_script_drift(
            "Add that to the JobDone note.",
            "Add that to the job done note.",
        )

        self.assertEqual(result.status, "exact_match")
        self.assertEqual(result.gate_status, "pass")

    def test_multi_word_brand_variants_do_not_create_drift(self):
        result = classify_script_drift(
            "Jury Rigged and Field Relay are part of the Continuum family.",
            "JuryRigged and field relay are part of the Continuum family.",
        )

        self.assertEqual(result.status, "exact_match")
        self.assertEqual(result.gate_status, "pass")

    def test_continuumkit_domain_tokenization_does_not_create_drift(self):
        result = classify_script_drift(
            "Go to downwind.continuumkit.org.",
            "Go to downwindcontinuumkit.org.",
        )

        self.assertEqual(result.status, "exact_match")
        self.assertEqual(result.gate_status, "pass")

    def test_compound_noun_tokenization_does_not_create_drift(self):
        result = classify_script_drift(
            "The whitecaps marked the line.",
            "The white caps marked the line.",
        )

        self.assertEqual(result.status, "exact_match")
        self.assertEqual(result.gate_status, "pass")

    def test_frogspawn_spelling_variants_do_not_create_drift(self):
        result = classify_script_drift(
            "Don't collect frogs or frogspawn from the wild.",
            "Don't collect frogs or frog spawn from the wild.",
        )

        self.assertEqual(result.status, "exact_match")
        self.assertEqual(result.gate_status, "pass")

    def test_spoken_mrs_variant_does_not_create_drift(self):
        result = classify_script_drift(
            "What did I do at Mrs Jones last time?",
            "What did I do at missus Jones last time?",
        )

        self.assertEqual(result.status, "exact_match")
        self.assertEqual(result.gate_status, "pass")

    def test_extra_trailing_words_fail(self):
        result = classify_script_drift(
            "Add that to the JobDone note.",
            "Add that to the JobDone note. Thanks.",
        )

        self.assertEqual(result.status, "extra_trailing_words")
        self.assertEqual(result.gate_status, "fail")
        self.assertEqual(result.extra_trailing_words, ["thanks"])

    def test_mismatch_fails(self):
        result = classify_script_drift(
            "Show me the last note for this place.",
            "Show me the next job for this person.",
        )

        self.assertEqual(result.status, "mismatch")
        self.assertEqual(result.gate_status, "fail")

    def test_required_transcriber_rejects_non_whisper_backend(self):
        with self.assertRaises(QualityGateError):
            validate_transcriber(
                {"backend": {"provider": "deepgram", "processorId": "nova-3"}},
                "whisper-1",
            )

    def test_required_transcriber_accepts_whisper_backend(self):
        validate_transcriber(
            {"backend": {"provider": "openai", "processorId": "whisper-1"}},
            "whisper-1",
        )

    def test_words_url_is_derived_from_transcription_url(self):
        self.assertEqual(
            words_url_for("http://127.0.0.1:8788/v1/transcribe?language=en"),
            "http://127.0.0.1:8788/v1/transcribe/words",
        )

    def test_timed_tokens_canonicalize_multi_word_project_names(self):
        tokens = timed_tokens_from_words(
            [
                {"word": "job", "startSeconds": 0.0, "endSeconds": 0.1},
                {"word": "done", "startSeconds": 0.1, "endSeconds": 0.3},
                {"word": "note", "startSeconds": 0.3, "endSeconds": 0.5},
            ]
        )

        self.assertEqual([token.token for token in tokens], ["jobdone", "note"])
        self.assertEqual(tokens[0].start_seconds, 0.0)
        self.assertEqual(tokens[0].end_seconds, 0.3)

    def test_trim_start_for_repair_uses_first_approved_word_timestamp(self):
        drift = classify_script_drift(
            "[warm, practical] Exactly. I think you're ready.",
            "And exactly. I think you're ready.",
        )

        trim_start = trim_start_for_repair(
            drift,
            {
                "words": [
                    {"word": "And", "startSeconds": 0.0, "endSeconds": 0.34},
                    {"word": "exactly", "startSeconds": 0.34, "endSeconds": 1.0},
                    {"word": "I", "startSeconds": 1.5, "endSeconds": 1.68},
                    {"word": "think", "startSeconds": 1.68, "endSeconds": 1.8},
                    {"word": "you're", "startSeconds": 1.8, "endSeconds": 1.96},
                    {"word": "ready", "startSeconds": 1.96, "endSeconds": 2.2},
                ]
            },
        )

        self.assertEqual(trim_start, 0.34)


if __name__ == "__main__":
    unittest.main()
