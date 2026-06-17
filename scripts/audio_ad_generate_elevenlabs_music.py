#!/usr/bin/env python3
"""Generate ElevenLabs music audition clips from an approved manifest."""

from __future__ import annotations

import argparse
import html
import json
import os
import re
import shutil
import sys
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

try:
    from audio_ad_generate_elevenlabs_dialogue import load_env_files, output_suffix, sha256_bytes
except ModuleNotFoundError:
    from scripts.audio_ad_generate_elevenlabs_dialogue import load_env_files, output_suffix, sha256_bytes


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_MANIFEST = (
    ROOT
    / "docs"
    / "adverts"
    / "selection-workbenches"
    / "elevenlabs-arcade-hornpipe-music-auditions-v1.json"
)
ENV_PATHS = (
    ROOT / "local" / "audio-assets" / ".env",
    ROOT / "local" / "elevenlabs" / ".env",
)


class MusicGenerationError(RuntimeError):
    pass


def main() -> int:
    args = parse_args()
    manifest = json.loads(args.manifest.read_text(encoding="utf-8"))
    takes = list(manifest.get("takes", []))
    if args.asset_id:
        selected = set(args.asset_id)
        takes = [take for take in takes if take["assetId"] in selected]
    if args.limit:
        takes = takes[: args.limit]
    if args.list:
        for take in takes:
            print(f"{take['assetId']}: {take['title']} ({take.get('musicLengthMs')} ms)")
        return 0
    if not takes:
        raise SystemExit("no matching music tasks")
    if not manifest.get("approvedForPaidGeneration"):
        raise SystemExit("manifest is not approved for paid generation")

    load_env_files(ENV_PATHS)
    api_key = os.environ.get("ELEVENLABS_API_KEY")
    if not api_key:
        raise SystemExit("missing ELEVENLABS_API_KEY in local/audio-assets/.env or shell environment")

    raw_dir, meta_dir, asset_dir, report_dir = resolve_output_dirs(args, manifest)
    written = []
    for index, take in enumerate(takes, 1):
        print(f"[{index}/{len(takes)}] generating {take['assetId']}", flush=True)
        audio, headers, payload = call_music(api_key, manifest, take)
        written.append(write_outputs(manifest, take, audio, headers, payload, raw_dir, meta_dir, asset_dir))

    write_workbench(manifest, written, report_dir)
    print()
    print(f"generated {len(written)} music assets")
    for item in written:
        print(f"- {item['assetPath']}")
    print(f"page: {report_dir / 'index.html'}")
    print(f"data: {report_dir / 'assets.json'}")
    return 0


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", type=Path, default=DEFAULT_MANIFEST)
    parser.add_argument("--raw-dir", type=Path)
    parser.add_argument("--meta-dir", type=Path)
    parser.add_argument("--asset-dir", type=Path)
    parser.add_argument("--report-dir", type=Path)
    parser.add_argument("--asset-id", action="append", help="Only generate this asset id; may be repeated.")
    parser.add_argument("--limit", type=int, help="Generate only the first N matching tasks.")
    parser.add_argument("--list", action="store_true", help="List tasks without spending credits.")
    return parser.parse_args()


def resolve_output_dirs(args: argparse.Namespace, manifest: dict[str, Any]) -> tuple[Path, Path, Path, Path]:
    campaign = str(manifest["campaign"])
    raw_dir = args.raw_dir or ROOT / "data" / "raw" / "audio-ads" / campaign / "elevenlabs" / "music"
    meta_dir = args.meta_dir or ROOT / "data" / "processed" / "audio-ads" / campaign / "elevenlabs" / "music"
    asset_dir = args.asset_dir or ROOT / "local" / "audio-adverts" / campaign / "assets"
    report_dir = args.report_dir or ROOT / "local" / "reports" / "music-audition-workbench" / campaign
    return raw_dir, meta_dir, asset_dir, report_dir


def call_music(
    api_key: str,
    manifest: dict[str, Any],
    take: dict[str, Any],
) -> tuple[bytes, dict[str, str], dict[str, Any]]:
    output_format = manifest.get("outputFormat", "mp3_44100_128")
    endpoint = manifest.get("endpoint", "https://api.elevenlabs.io/v1/music")
    url = endpoint + "?" + urllib.parse.urlencode({"output_format": output_format})
    payload = {
        "prompt": take["prompt"],
        "music_length_ms": int(take.get("musicLengthMs") or 18000),
        "force_instrumental": bool(manifest.get("forceInstrumental", True)),
        "model_id": manifest.get("modelId", "music_v2"),
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
        with urllib.request.urlopen(request, timeout=300) as response:
            return response.read(), {key.lower(): value for key, value in response.headers.items()}, payload
    except urllib.error.HTTPError as error:
        detail = error.read().decode("utf-8", errors="replace")
        raise MusicGenerationError(f"{take['assetId']} failed: HTTP {error.code}: {detail}") from error


def write_outputs(
    manifest: dict[str, Any],
    take: dict[str, Any],
    audio: bytes,
    headers: dict[str, str],
    payload: dict[str, Any],
    raw_dir: Path,
    meta_dir: Path,
    asset_dir: Path,
) -> dict[str, str]:
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    suffix = output_suffix(manifest.get("outputFormat", "mp3_44100_128"))
    raw_stem = f"{manifest['scriptId']}_{take['assetId']}__{timestamp}"
    asset_stem = f"{take['assetId']}__{manifest['scriptVersion']}"
    raw_path = raw_dir / f"{raw_stem}{suffix}"
    metadata_path = meta_dir / f"{raw_stem}.json"
    asset_path = asset_dir / take["folder"] / f"{asset_stem}{suffix}"
    raw_path.parent.mkdir(parents=True, exist_ok=True)
    metadata_path.parent.mkdir(parents=True, exist_ok=True)
    asset_path.parent.mkdir(parents=True, exist_ok=True)
    raw_path.write_bytes(audio)
    asset_path.write_bytes(audio)
    audio_sha = sha256_bytes(audio)
    metadata = {
        "schemaVersion": "adlib.elevenlabs-music-asset.v1",
        "createdAt": timestamp,
        "provider": "elevenlabs",
        "providerProduct": "music",
        "endpoint": manifest.get("endpoint", "https://api.elevenlabs.io/v1/music"),
        "modelId": manifest.get("modelId", "music_v2"),
        "outputFormat": manifest.get("outputFormat", "mp3_44100_128"),
        "campaign": manifest["campaign"],
        "scriptId": manifest["scriptId"],
        "scriptVersion": manifest["scriptVersion"],
        "assetId": take["assetId"],
        "title": take["title"],
        "project": take.get("project") or "",
        "assetKind": take.get("assetKind") or "music_audition",
        "prompt": take["prompt"],
        "scriptText": take["prompt"],
        "musicLengthMs": int(take.get("musicLengthMs") or payload["music_length_ms"]),
        "forceInstrumental": bool(payload["force_instrumental"]),
        "rawAudioPath": str(raw_path),
        "reaperAssetPath": str(asset_path),
        "audioSha256": audio_sha,
        "audioBytes": len(audio),
        "responseHeaders": headers,
        "songId": headers.get("song-id"),
        "requestPayload": payload,
        "testStatus": "needs_music_review",
    }
    metadata_path.write_text(json.dumps(metadata, indent=2) + "\n", encoding="utf-8")
    return {
        "assetId": take["assetId"],
        "title": take["title"],
        "project": take.get("project") or "",
        "assetKind": take.get("assetKind") or "music_audition",
        "prompt": take["prompt"],
        "assetPath": str(asset_path),
        "metadataPath": str(metadata_path),
        "audioSha256": audio_sha,
        "songId": headers.get("song-id") or "",
    }


def write_workbench(manifest: dict[str, Any], assets: list[dict[str, str]], report_dir: Path) -> None:
    media_dir = report_dir / "media"
    media_dir.mkdir(parents=True, exist_ok=True)
    public_assets = []
    for asset in assets:
        source = Path(asset["assetPath"])
        media_name = f"{safe_slug(asset['assetId'])}{source.suffix.lower()}"
        shutil.copy2(source, media_dir / media_name)
        public_assets.append({**asset, "audio": f"media/{media_name}"})
    payload = {
        "campaign": manifest["campaign"],
        "generatedAt": datetime.now().astimezone().isoformat(timespec="seconds"),
        "assets": public_assets,
    }
    (report_dir / "assets.json").write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    (report_dir / "index.html").write_text(render_workbench(payload), encoding="utf-8")


def render_workbench(payload: dict[str, Any]) -> str:
    cards = []
    for asset in payload["assets"]:
        cards.append(
            f"""
      <article class="card">
        <h2>{html.escape(asset["title"])}</h2>
        <p>{html.escape(asset["project"])} · {html.escape(asset["assetKind"])}</p>
        <audio controls preload="none" src="{html.escape(asset["audio"])}"></audio>
        <details open><summary>Prompt</summary><pre>{html.escape(asset["prompt"])}</pre></details>
        <details><summary>Metadata</summary><pre>songId: {html.escape(asset.get("songId") or "not returned")}
sha256: {html.escape(asset["audioSha256"])}</pre></details>
      </article>
            """
        )
    return f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>{html.escape(payload["campaign"])} Music Auditions</title>
  <style>
    :root {{
      color-scheme: light dark;
      font-family: Inter, ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
      --bg: #f7f8f5;
      --ink: #17201d;
      --muted: #61716b;
      --panel: #ffffff;
      --line: #d7ddd3;
      --accent: #0f766e;
    }}
    @media (prefers-color-scheme: dark) {{
      :root {{ --bg: #101412; --ink: #eff4ef; --muted: #9cafaa; --panel: #18201d; --line: #304039; --accent: #5eead4; }}
    }}
    * {{ box-sizing: border-box; }}
    body {{ margin: 0; background: var(--bg); color: var(--ink); }}
    main {{ width: min(980px, calc(100vw - 24px)); margin: 0 auto; padding: 22px 0 54px; }}
    h1 {{ margin: 0 0 8px; font-size: clamp(1.7rem, 3vw, 2.7rem); letter-spacing: 0; }}
    .meta, p {{ color: var(--muted); line-height: 1.45; }}
    .grid {{ display: grid; gap: 12px; margin-top: 14px; }}
    .card {{ background: var(--panel); border: 1px solid var(--line); border-radius: 8px; padding: 14px; display: grid; gap: 10px; }}
    h2 {{ margin: 0; font-size: 1.12rem; letter-spacing: 0; }}
    audio {{ width: 100%; }}
    details {{ border-top: 1px solid var(--line); padding-top: 8px; }}
    summary {{ cursor: pointer; color: var(--muted); }}
    pre {{ white-space: pre-wrap; overflow-wrap: anywhere; margin: 8px 0 0; color: var(--muted); font-size: .9rem; }}
    a {{ color: var(--accent); }}
  </style>
</head>
<body>
  <main>
    <h1>Arcade Hornpipe Music Auditions</h1>
    <div class="meta">Three instrumental ElevenLabs music clips for Jury Rigged / Downwind. These are first-pass direction tests, not final masters. <a href="assets.json">Metadata</a>.</div>
    <section class="grid">
      {''.join(cards)}
    </section>
  </main>
</body>
</html>
"""


def safe_slug(value: str) -> str:
    value = value.lower()
    value = re.sub(r"[^a-z0-9]+", "-", value)
    return value.strip("-")[:100]


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except MusicGenerationError as error:
        print(str(error), file=sys.stderr)
        raise SystemExit(1)
