#!/usr/bin/env python3
"""Generate a whole audio-advert dialogue take with ElevenLabs."""

from __future__ import annotations

import argparse
import base64
import hashlib
import json
import os
import re
import sys
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_MANIFEST = ROOT / "docs" / "adverts" / "jobdone-dog-callback" / "elevenlabs-dialogue-v1.json"
DEFAULT_AUDIO_DIR = ROOT / "data" / "raw" / "audio-ads" / "jobdone-dog-callback" / "elevenlabs"
DEFAULT_META_DIR = ROOT / "data" / "processed" / "audio-ads" / "jobdone-dog-callback" / "elevenlabs"
ENV_PATHS = (
    ROOT / "local" / "audio-assets" / ".env",
    ROOT / "local" / "elevenlabs" / ".env",
)
VOICES_ENDPOINT = "https://api.elevenlabs.io/v2/voices"


class GenerationError(RuntimeError):
    pass


def main() -> int:
    args = parse_args()
    load_env_files(ENV_PATHS)
    manifest = load_manifest(args.manifest)
    if not manifest.get("approvedForPaidGeneration"):
        raise SystemExit("manifest is not approved for paid generation")
    api_key = os.environ.get("ELEVENLABS_API_KEY")
    if not api_key:
        raise SystemExit("missing ELEVENLABS_API_KEY; add it to local/audio-assets/.env or the shell environment")

    voices = fetch_available_voices(api_key)
    selected_voices = select_manifest_voices(manifest, voices)
    payload = build_dialogue_payload(manifest, selected_voices)
    if args.print_payload:
        print(json.dumps(redact_payload(payload), indent=2))

    audio, response_meta = call_elevenlabs_dialogue(api_key, manifest, payload)
    written = write_generation(manifest, selected_voices, payload, audio, response_meta, args.audio_dir, args.meta_dir)
    print(f"wrote audio: {written['audioPath']}")
    print(f"wrote metadata: {written['metadataPath']}")
    print(f"sha256: {written['audioSha256']}")
    return 0


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", type=Path, default=DEFAULT_MANIFEST)
    parser.add_argument("--audio-dir", type=Path, default=DEFAULT_AUDIO_DIR)
    parser.add_argument("--meta-dir", type=Path, default=DEFAULT_META_DIR)
    parser.add_argument("--print-payload", action="store_true", help="Also print the request body without the API key.")
    return parser.parse_args()


def load_env_files(paths: tuple[Path, ...]) -> None:
    for path in paths:
        if not path.exists():
            continue
        for raw_line in path.read_text(encoding="utf-8").splitlines():
            line = raw_line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, value = line.split("=", 1)
            key = key.strip()
            value = value.strip().strip('"').strip("'")
            if key and key not in os.environ:
                os.environ[key] = value


def load_manifest(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def fetch_available_voices(api_key: str) -> list[dict[str, Any]]:
    params = urllib.parse.urlencode({"page_size": 100})
    request = urllib.request.Request(
        f"{VOICES_ENDPOINT}?{params}",
        headers={"xi-api-key": api_key},
        method="GET",
    )
    try:
        with urllib.request.urlopen(request, timeout=30) as response:
            data = json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as error:
        detail = error.read().decode("utf-8", errors="replace")
        raise GenerationError(f"voice lookup failed: HTTP {error.code}: {detail}") from error
    return list(data.get("voices", []))


def select_manifest_voices(manifest: dict[str, Any], voices: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    selected: dict[str, dict[str, Any]] = {}
    for speaker_id, speaker in manifest["speakers"].items():
        voice_id = os.environ.get(speaker.get("voiceIdEnv", ""))
        if voice_id:
            selected[speaker_id] = {
                "voice_id": voice_id,
                "name": speaker.get("role", speaker_id),
                "selection_reason": f"env:{speaker['voiceIdEnv']}",
            }
            continue
        selected[speaker_id] = select_voice_for_speaker(speaker, voices)
    return selected


def select_voice_for_speaker(speaker: dict[str, Any], voices: list[dict[str, Any]]) -> dict[str, Any]:
    if not voices:
        raise GenerationError("no voices returned by ElevenLabs")
    terms = [str(term).lower() for term in speaker.get("voiceSearchTerms", [])]
    best_voice = voices[0]
    best_score = -1
    for voice in voices:
        searchable = json.dumps(voice, sort_keys=True).lower()
        score = sum(1 for term in terms if term in searchable)
        if score > best_score:
            best_voice = voice
            best_score = score
    return {
        "voice_id": best_voice["voice_id"],
        "name": best_voice.get("name", best_voice["voice_id"]),
        "selection_reason": f"auto-score:{best_score}",
    }


def build_dialogue_payload(manifest: dict[str, Any], selected_voices: dict[str, dict[str, Any]]) -> dict[str, Any]:
    validate_manifest_inputs(manifest)
    return {
        "inputs": [
            {
                "text": line["text"],
                "voice_id": selected_voices[line["speaker"]]["voice_id"],
            }
            for line in manifest["inputs"]
        ],
        "model_id": manifest.get("modelId", "eleven_v3"),
        "seed": manifest.get("seed"),
    }


def validate_manifest_inputs(manifest: dict[str, Any]) -> None:
    empty_lines = [
        line.get("lineId", "<unknown>")
        for line in manifest["inputs"]
        if not visible_text_after_tags(str(line.get("text", "")))
    ]
    if empty_lines:
        raise GenerationError(
            "manifest has inputs that ElevenLabs will treat as empty after tag stripping: "
            + ", ".join(empty_lines)
        )


def visible_text_after_tags(text: str) -> str:
    return re.sub(r"\[[^\]]*\]", "", text).strip()


def redact_payload(payload: dict[str, Any]) -> dict[str, Any]:
    return {
        **payload,
        "inputs": [
            {
                **item,
                "voice_id": item["voice_id"][:4] + "..." + item["voice_id"][-4:],
            }
            for item in payload["inputs"]
        ],
    }


def call_elevenlabs_dialogue(
    api_key: str,
    manifest: dict[str, Any],
    payload: dict[str, Any],
) -> tuple[bytes, dict[str, Any]]:
    output_format = manifest.get("outputFormat", "mp3_44100_128")
    url = manifest["endpoint"] + "?" + urllib.parse.urlencode({"output_format": output_format})
    body = json.dumps(payload).encode("utf-8")
    request = urllib.request.Request(
        url,
        data=body,
        headers={
            "xi-api-key": api_key,
            "Content-Type": "application/json",
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=180) as response:
            response_body = response.read()
            headers = {key.lower(): value for key, value in response.headers.items()}
    except urllib.error.HTTPError as error:
        detail = error.read().decode("utf-8", errors="replace")
        raise GenerationError(f"generation failed: HTTP {error.code}: {detail}") from error

    data = json.loads(response_body.decode("utf-8"))
    audio = base64.b64decode(data["audio_base64"])
    data_without_audio = {key: value for key, value in data.items() if key != "audio_base64"}
    return audio, {
        "headers": headers,
        "response": data_without_audio,
    }


def write_generation(
    manifest: dict[str, Any],
    selected_voices: dict[str, dict[str, Any]],
    payload: dict[str, Any],
    audio: bytes,
    response_meta: dict[str, Any],
    audio_dir: Path,
    meta_dir: Path,
) -> dict[str, str]:
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    stem = f"{manifest['scriptId']}_{manifest['scriptVersion']}_elevenlabs_dialogue_{timestamp}"
    suffix = output_suffix(manifest.get("outputFormat", "mp3_44100_128"))
    audio_dir.mkdir(parents=True, exist_ok=True)
    meta_dir.mkdir(parents=True, exist_ok=True)
    audio_path = audio_dir / f"{stem}{suffix}"
    metadata_path = meta_dir / f"{stem}.json"
    audio_path.write_bytes(audio)
    audio_sha = sha256_bytes(audio)
    metadata = {
        "schemaVersion": "workflow-manager.audio-advert-generation.v1",
        "createdAt": timestamp,
        "provider": "elevenlabs",
        "endpoint": manifest["endpoint"],
        "modelId": manifest.get("modelId", "eleven_v3"),
        "outputFormat": manifest.get("outputFormat", "mp3_44100_128"),
        "scriptId": manifest["scriptId"],
        "scriptVersion": manifest["scriptVersion"],
        "campaign": manifest.get("campaign"),
        "selectedVoices": selected_voices,
        "payload": redact_payload(payload),
        "audioPath": str(audio_path),
        "audioSha256": audio_sha,
        "audioBytes": len(audio),
        "responseMeta": response_meta,
    }
    metadata_path.write_text(json.dumps(metadata, indent=2) + "\n", encoding="utf-8")
    return {
        "audioPath": str(audio_path),
        "metadataPath": str(metadata_path),
        "audioSha256": audio_sha,
    }


def output_suffix(output_format: str) -> str:
    if output_format.startswith("mp3_"):
        return ".mp3"
    if output_format.startswith("wav_"):
        return ".wav"
    if output_format.startswith("pcm_"):
        return ".pcm"
    return ".audio"


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except GenerationError as error:
        print(str(error), file=sys.stderr)
        raise SystemExit(1)
