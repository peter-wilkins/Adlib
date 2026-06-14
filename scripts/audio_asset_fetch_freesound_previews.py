#!/usr/bin/env python3
"""Search Freesound and copy preview MP3s into the local REAPER asset library."""

from __future__ import annotations

import argparse
import json
import mimetypes
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import audio_asset_search_freesound as freesound


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_RAW_DIR = ROOT / "data" / "raw" / "audio-ads" / "external-sfx" / "freesound-previews"
DEFAULT_META_DIR = ROOT / "data" / "processed" / "audio-ads" / "external-sfx" / "freesound-previews"
DEFAULT_REAPER_ASSET_DIR = ROOT / "local" / "audio-adverts" / "jobdone-dog-callback" / "assets"


def main() -> int:
    args = parse_args()
    token = freesound.find_api_token(args.env_file)
    if not token:
        print(freesound.missing_token_message(args.env_file))
        return 2

    requested_at = utc_now()
    search_filter = freesound.build_filter(args.license, args.min_duration, args.max_duration, args.extra_filter)
    params = freesound.build_search_params(args.query, search_filter, args.sort, args.limit, token)
    redacted_url = freesound.build_url({**params, "token": "REDACTED"})
    document = freesound.build_candidate_document(
        freesound.fetch_json(freesound.build_url(params)),
        args.query,
        search_filter,
        args.sort,
        requested_at,
        redacted_url,
    )

    target_folder = normalise_target_folder(args.target_folder)
    target_dir = args.reaper_asset_dir / target_folder
    target_dir.mkdir(parents=True, exist_ok=True)
    raw_query_dir = args.raw_dir / freesound.slugify(args.query)
    raw_query_dir.mkdir(parents=True, exist_ok=True)
    args.meta_dir.mkdir(parents=True, exist_ok=True)

    downloaded = []
    for index, candidate in enumerate(document["candidates"], start=1):
        if len(downloaded) >= args.take:
            break
        preview_url = candidate.get("preferred_preview_url") or ""
        if not preview_url:
            continue
        asset = download_candidate(candidate, preview_url, index, raw_query_dir, target_dir)
        downloaded.append(asset)

    output_doc = {
        "schema": "workflow-manager.freesound-preview-fetch.v1",
        "queried_at": requested_at,
        "query": args.query,
        "target_folder": str(target_folder),
        "search": document,
        "downloaded": downloaded,
    }
    meta_path = args.meta_dir / f"freesound-preview-fetch-{freesound.slugify(args.query)}-{compact_stamp(requested_at)}.json"
    meta_path.write_text(json.dumps(output_doc, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    print(f"metadata: {meta_path}")
    print(f"downloaded: {len(downloaded)}")
    for asset in downloaded:
        print(f"- {asset['reaper_path']}")
    return 0


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("query")
    parser.add_argument("--target-folder", required=True, help="Relative folder under the REAPER assets dir, e.g. sfx/doorbells")
    parser.add_argument("--limit", type=int, default=12, help="Search result count to inspect.")
    parser.add_argument("--take", type=int, default=6, help="Number of preview files to download.")
    parser.add_argument("--min-duration", type=float, default=0.15)
    parser.add_argument("--max-duration", type=float, default=8.0)
    parser.add_argument("--license", default="Creative Commons 0")
    parser.add_argument("--sort", default="rating_desc", choices=["score", "duration_desc", "duration_asc", "created_desc", "created_asc", "downloads_desc", "downloads_asc", "rating_desc", "rating_asc"])
    parser.add_argument("--extra-filter", action="append", default=[])
    parser.add_argument("--env-file", type=Path, default=freesound.DEFAULT_ENV_FILE)
    parser.add_argument("--raw-dir", type=Path, default=DEFAULT_RAW_DIR)
    parser.add_argument("--meta-dir", type=Path, default=DEFAULT_META_DIR)
    parser.add_argument("--reaper-asset-dir", type=Path, default=DEFAULT_REAPER_ASSET_DIR)
    return parser.parse_args()


def normalise_target_folder(value: str) -> Path:
    path = Path(value)
    if path.is_absolute() or ".." in path.parts:
        raise SystemExit("--target-folder must be a safe relative path")
    return path


def download_candidate(candidate: dict[str, Any], preview_url: str, index: int, raw_dir: Path, target_dir: Path) -> dict[str, str]:
    extension = extension_for_preview(preview_url)
    stem = f"{index:02d}-freesound-{candidate['source_id']}-{freesound.slugify(candidate['source_title'])}"
    raw_path = raw_dir / f"{stem}{extension}"
    reaper_path = target_dir / f"{stem}{extension}"
    request = urllib.request.Request(preview_url, headers={"User-Agent": "workflow-manager-audio-assets/0.1"})
    try:
        with urllib.request.urlopen(request, timeout=30) as response:
            audio = response.read()
    except urllib.error.URLError as exc:
        raise SystemExit(f"download failed for {preview_url}: {exc}") from exc

    raw_path.write_bytes(audio)
    reaper_path.write_bytes(audio)
    candidate["downloaded_at"] = utc_now()
    candidate["download_url"] = preview_url
    candidate["file_path"] = str(raw_path)
    candidate["file_sha256"] = freesound_hash(audio)
    candidate["approval_status"] = "preview_downloaded_needs_audition"
    return {
        "asset_id": candidate["asset_id"],
        "source_url": candidate["source_url"],
        "source_title": candidate["source_title"],
        "license": candidate["license"],
        "duration_seconds": str(candidate.get("duration_seconds", "")),
        "raw_path": str(raw_path),
        "reaper_path": str(reaper_path),
        "sha256": candidate["file_sha256"],
    }


def extension_for_preview(url: str) -> str:
    path = url.split("?", 1)[0]
    guessed = mimetypes.guess_extension(mimetypes.guess_type(path)[0] or "")
    if guessed:
        return guessed
    if path.endswith(".ogg"):
        return ".ogg"
    if path.endswith(".wav"):
        return ".wav"
    return ".mp3"


def freesound_hash(data: bytes) -> str:
    import hashlib

    return hashlib.sha256(data).hexdigest()


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")


def compact_stamp(value: str) -> str:
    return value.replace("-", "").replace(":", "").replace("+", "Z")


if __name__ == "__main__":
    raise SystemExit(main())
