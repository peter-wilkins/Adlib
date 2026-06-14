#!/usr/bin/env python3
"""Generate separate ElevenLabs voice-line assets for audio advert editing."""

from __future__ import annotations

import argparse
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

from audio_ad_generate_elevenlabs_dialogue import load_env_files, output_suffix, sha256_bytes


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_MANIFEST = ROOT / "docs" / "adverts" / "jobdone-dog-callback" / "elevenlabs-voice-lines-v1.json"
DEFAULT_AUDIO_DIR = ROOT / "data" / "raw" / "audio-ads" / "jobdone-dog-callback" / "elevenlabs" / "voice-lines"
DEFAULT_META_DIR = ROOT / "data" / "processed" / "audio-ads" / "jobdone-dog-callback" / "elevenlabs" / "voice-lines"
DEFAULT_REAPER_ASSET_DIR = ROOT / "local" / "audio-adverts" / "jobdone-dog-callback" / "assets"
ENV_PATHS = (
    ROOT / "local" / "audio-assets" / ".env",
    ROOT / "local" / "elevenlabs" / ".env",
)


class GenerationError(RuntimeError):
    pass


def main() -> int:
    args = parse_args()
    load_env_files(ENV_PATHS)
    manifest = json.loads(args.manifest.read_text(encoding="utf-8"))
    if not manifest.get("approvedForPaidGeneration"):
        raise SystemExit("manifest is not approved for paid generation")
    if args.audition_text:
        manifest["_auditionText"] = args.audition_text
        manifest["_auditionId"] = args.audition_id
        manifest["_auditionSlug"] = args.audition_slug
        manifest["_auditionFolder"] = args.audition_folder
    api_key = os.environ.get("ELEVENLABS_API_KEY")
    if not api_key:
        raise SystemExit("missing ELEVENLABS_API_KEY in local/audio-assets/.env or shell environment")

    tasks = expand_tasks(manifest)
    if args.asset_id:
        tasks = [task for task in tasks if task["assetId"] in set(args.asset_id)]
    if args.voice_profile:
        tasks = [task for task in tasks if task["voiceProfile"] in set(args.voice_profile)]
    if args.limit:
        tasks = tasks[: args.limit]

    if args.list:
        for task in tasks:
            print(task_name(task))
        return 0

    if not tasks:
        raise SystemExit("no matching voice-line tasks")

    written = []
    for task in tasks:
        print(f"generating {task_name(task)}", flush=True)
        audio, headers = call_tts(api_key, manifest, task)
        written.append(write_outputs(manifest, task, audio, headers, args.audio_dir, args.meta_dir, args.reaper_asset_dir))

    print()
    print(f"generated {len(written)} voice assets")
    for item in written:
        print(f"- {item['reaperAssetPath']}")
    return 0


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", type=Path, default=DEFAULT_MANIFEST)
    parser.add_argument("--audio-dir", type=Path, default=DEFAULT_AUDIO_DIR)
    parser.add_argument("--meta-dir", type=Path, default=DEFAULT_META_DIR)
    parser.add_argument("--reaper-asset-dir", type=Path, default=DEFAULT_REAPER_ASSET_DIR)
    parser.add_argument("--asset-id", action="append", help="Only generate this asset id; may be repeated.")
    parser.add_argument("--voice-profile", action="append", help="Only generate this voice profile; may be repeated.")
    parser.add_argument("--limit", type=int, help="Generate only the first N matching tasks.")
    parser.add_argument("--list", action="store_true", help="List tasks without spending credits.")
    parser.add_argument("--audition-text", help="Generate one same-text audition clip for every selected voice profile.")
    parser.add_argument("--audition-id", default="voice_audition", help="Asset id to use with --audition-text.")
    parser.add_argument("--audition-slug", default="same_text", help="Take slug to use with --audition-text.")
    parser.add_argument("--audition-folder", default="voice/auditions", help="REAPER asset folder to use with --audition-text.")
    return parser.parse_args()


def expand_tasks(manifest: dict[str, Any]) -> list[dict[str, Any]]:
    voice_profiles = manifest["voiceProfiles"]
    if manifest.get("_auditionText"):
        return [
            make_task(
                {
                    "assetId": manifest["_auditionId"],
                    "takeSlug": manifest["_auditionSlug"],
                    "speaker": "voice_audition",
                    "folder": manifest["_auditionFolder"],
                    "text": manifest["_auditionText"],
                    "voiceProfiles": [profile_id],
                },
                profile_id,
                voice_profiles[profile_id],
            )
            for profile_id in voice_profiles
        ]

    tasks: list[dict[str, Any]] = []
    for take in manifest["takes"]:
        for profile_id in take["voiceProfiles"]:
            profile = voice_profiles[profile_id]
            tasks.append(make_task(take, profile_id, profile))
    return tasks


def make_task(take: dict[str, Any], profile_id: str, profile: dict[str, Any]) -> dict[str, Any]:
    settings = dict(profile.get("defaultSettings", {}))
    settings.update(take.get("voiceSettings", {}))
    return {
        **take,
        "voiceProfile": profile_id,
        "voiceId": profile["voiceId"],
        "voiceName": profile["voiceName"],
        "voiceRole": profile.get("role"),
        "voiceSettings": settings,
    }


def call_tts(api_key: str, manifest: dict[str, Any], task: dict[str, Any]) -> tuple[bytes, dict[str, str]]:
    output_format = manifest.get("outputFormat", "mp3_44100_128")
    endpoint = manifest["endpoint"].format(voice_id=urllib.parse.quote(task["voiceId"], safe=""))
    url = endpoint + "?" + urllib.parse.urlencode({"output_format": output_format})
    payload = {
        "text": task["text"],
        "model_id": manifest.get("modelId", "eleven_multilingual_v2"),
        "voice_settings": task["voiceSettings"],
    }
    request = urllib.request.Request(
        url,
        data=json.dumps(payload).encode("utf-8"),
        headers={
            "xi-api-key": api_key,
            "Content-Type": "application/json",
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=180) as response:
            return response.read(), {key.lower(): value for key, value in response.headers.items()}
    except urllib.error.HTTPError as error:
        detail = error.read().decode("utf-8", errors="replace")
        raise GenerationError(f"{task_name(task)} failed: HTTP {error.code}: {detail}") from error


def write_outputs(
    manifest: dict[str, Any],
    task: dict[str, Any],
    audio: bytes,
    headers: dict[str, str],
    audio_dir: Path,
    meta_dir: Path,
    reaper_asset_dir: Path,
) -> dict[str, str]:
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    suffix = output_suffix(manifest.get("outputFormat", "mp3_44100_128"))
    raw_stem = f"{manifest['scriptId']}_{task['assetId']}__{task['takeSlug']}__{task['voiceProfile']}__{timestamp}"
    asset_stem = f"{task['assetId']}__{task['takeSlug']}__{task['voiceProfile']}"

    audio_dir.mkdir(parents=True, exist_ok=True)
    meta_dir.mkdir(parents=True, exist_ok=True)
    raw_path = audio_dir / f"{raw_stem}{suffix}"
    meta_path = meta_dir / f"{raw_stem}.json"
    reaper_path = reaper_asset_dir / task["folder"] / f"{asset_stem}{suffix}"
    reaper_path.parent.mkdir(parents=True, exist_ok=True)

    raw_path.write_bytes(audio)
    reaper_path.write_bytes(audio)
    audio_sha = sha256_bytes(audio)
    metadata = {
        "schemaVersion": "workflow-manager.audio-advert-voice-asset.v1",
        "createdAt": timestamp,
        "provider": "elevenlabs",
        "endpoint": manifest["endpoint"],
        "modelId": manifest.get("modelId", "eleven_multilingual_v2"),
        "outputFormat": manifest.get("outputFormat", "mp3_44100_128"),
        "campaign": manifest["campaign"],
        "scriptId": manifest["scriptId"],
        "scriptVersion": manifest["scriptVersion"],
        "assetId": task["assetId"],
        "takeSlug": task["takeSlug"],
        "speaker": task["speaker"],
        "scriptText": task["text"],
        "voiceProfile": task["voiceProfile"],
        "voiceId": task["voiceId"],
        "voiceName": task["voiceName"],
        "voiceRole": task.get("voiceRole"),
        "voiceSettings": task["voiceSettings"],
        "rawAudioPath": str(raw_path),
        "reaperAssetPath": str(reaper_path),
        "audioSha256": audio_sha,
        "audioBytes": len(audio),
        "responseHeaders": headers,
        "testStatus": "needs_audition",
    }
    meta_path.write_text(json.dumps(metadata, indent=2) + "\n", encoding="utf-8")
    return {
        "rawAudioPath": str(raw_path),
        "metadataPath": str(meta_path),
        "reaperAssetPath": str(reaper_path),
        "audioSha256": audio_sha,
    }


def task_name(task: dict[str, Any]) -> str:
    return f"{task['assetId']}:{task['takeSlug']}:{task['voiceProfile']}:{slug(task['voiceName'])}"


def slug(value: str) -> str:
    value = value.lower()
    value = re.sub(r"[^a-z0-9]+", "-", value)
    return value.strip("-")[:80]


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except GenerationError as error:
        print(str(error), file=sys.stderr)
        raise SystemExit(1)
