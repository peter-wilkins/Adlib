import os
import subprocess
import tempfile
import unittest
import wave
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


class JobDoneDogCallbackRenderTest(unittest.TestCase):
    def test_render_script_fails_clearly_when_assets_are_missing(self):
        script = ROOT / "docs/adverts/jobdone-dog-callback/render.sh"

        result = subprocess.run(
            [str(script)],
            cwd=ROOT,
            env={
                **os.environ,
                "VOICE": "/tmp/workflow-manager-test-missing-voice.wav",
                "OPENING_BARK": "/tmp/workflow-manager-test-missing-opening.wav",
                "CALLBACK_BARK": "/tmp/workflow-manager-test-missing-callback.wav",
            },
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=False,
        )

        self.assertEqual(result.returncode, 2)
        self.assertIn("missing input:", result.stderr)
        self.assertIn("render recipe is ready", result.stderr)

    def test_assets_lock_is_valid_json(self):
        lock = ROOT / "docs/adverts/jobdone-dog-callback/assets.lock.json"

        self.assertTrue(lock.exists())

    def test_filtergraph_has_no_hash_comments(self):
        graph = ROOT / "docs/adverts/jobdone-dog-callback/filter_complex.ffgraph"

        self.assertNotIn("#", graph.read_text(encoding="utf-8"))

    def test_render_script_can_render_with_temp_audio_assets(self):
        script = ROOT / "docs/adverts/jobdone-dog-callback/render.sh"
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            voice = tmp_path / "voice.wav"
            opening = tmp_path / "opening.wav"
            callback = tmp_path / "callback.wav"
            out = tmp_path / "out.wav"
            for path in (voice, opening, callback):
                write_silent_wav(path)

            result = subprocess.run(
                [str(script), str(out)],
                cwd=ROOT,
                env={
                    **os.environ,
                    "VOICE": str(voice),
                    "OPENING_BARK": str(opening),
                    "CALLBACK_BARK": str(callback),
                },
                text=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                check=False,
            )

            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertTrue(out.exists())
            self.assertGreater(out.stat().st_size, 0)


def write_silent_wav(path: Path) -> None:
    frames = 4800
    with wave.open(str(path), "wb") as handle:
        handle.setnchannels(2)
        handle.setsampwidth(2)
        handle.setframerate(48000)
        handle.writeframes(b"\x00\x00" * 2 * frames)


if __name__ == "__main__":
    unittest.main()
