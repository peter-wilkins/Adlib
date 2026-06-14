import unittest

from scripts.audio_asset_quality_gate import (
    QualityGateError,
    classify_script_drift,
    spoken_script_text,
    validate_transcriber,
    word_tokens,
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


if __name__ == "__main__":
    unittest.main()
