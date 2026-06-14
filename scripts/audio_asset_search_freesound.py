#!/usr/bin/env python3
"""Search Freesound for reusable audio advert sound-effect candidates.

This is deliberately no-download by default. It writes candidate metadata with
preview URLs, source URLs, license data, and enough audit fields to decide later
whether to download/use the asset.
"""

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


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_ENV_FILE = ROOT / "local/audio-assets/.env"
DEFAULT_OUT_DIR = ROOT / "data/processed/audio-ads/candidates"
API_URL = "https://freesound.org/apiv2/search/"
APPLY_URL = "https://freesound.org/apiv2/apply"

DEFAULT_FIELDS = [
    "id",
    "name",
    "url",
    "username",
    "license",
    "tags",
    "duration",
    "type",
    "filesize",
    "previews",
    "description",
    "created",
    "avg_rating",
    "num_ratings",
    "num_downloads",
    "score",
]

LICENSE_URLS = {
    "Creative Commons 0": "https://creativecommons.org/publicdomain/zero/1.0/",
    "Attribution": "https://creativecommons.org/licenses/by/4.0/",
    "Attribution NonCommercial": "https://creativecommons.org/licenses/by-nc/4.0/",
}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("query", nargs="?", help="Search query, for example: dog bark")
    parser.add_argument("--limit", type=int, default=10, help="Number of candidates to return, max 150")
    parser.add_argument("--min-duration", type=float, default=0.2)
    parser.add_argument("--max-duration", type=float, default=8.0)
    parser.add_argument("--license", default="Creative Commons 0")
    parser.add_argument(
        "--sort",
        default="rating_desc",
        choices=["score", "duration_desc", "duration_asc", "created_desc", "created_asc", "downloads_desc", "downloads_asc", "rating_desc", "rating_asc"],
    )
    parser.add_argument("--extra-filter", action="append", default=[], help='Additional Freesound filter, e.g. tag:dog')
    parser.add_argument("--env-file", type=Path, default=DEFAULT_ENV_FILE)
    parser.add_argument("--out", type=Path, help="Write exact output JSON path")
    parser.add_argument("--out-dir", type=Path, default=DEFAULT_OUT_DIR)
    parser.add_argument("--no-write", action="store_true", help="Print JSON instead of writing to data/processed")
    parser.add_argument("--print-url", action="store_true", help="Print redacted API URL to stderr")
    parser.add_argument("--init-env", action="store_true", help="Create ignored local env placeholder and exit")
    args = parser.parse_args()

    if args.init_env:
        init_env_file(args.env_file)
        return 0
    if not args.query:
        parser.error("query is required unless --init-env is used")

    token = find_api_token(args.env_file)
    if not token:
        print(missing_token_message(args.env_file), file=sys.stderr)
        return 2

    requested_at = utc_now()
    search_filter = build_filter(args.license, args.min_duration, args.max_duration, args.extra_filter)
    params = build_search_params(args.query, search_filter, args.sort, args.limit, token)
    redacted_url = build_url({**params, "token": "REDACTED"})
    if args.print_url:
        print(redacted_url, file=sys.stderr)

    response = fetch_json(build_url(params))
    document = build_candidate_document(response, args.query, search_filter, args.sort, requested_at, redacted_url)
    output = json.dumps(document, indent=2, sort_keys=True) + "\n"
    if args.no_write:
        print(output, end="")
        return 0

    out_path = args.out or default_output_path(args.out_dir, args.query, requested_at)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(output, encoding="utf-8")
    print(f"wrote: {out_path}")
    print(f"candidates: {len(document['candidates'])}")
    return 0


def init_env_file(path: Path) -> None:
    path = resolve_path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists():
        print(f"exists: {path}")
        return
    path.write_text(
        "# Freesound APIv2 token. Request one at https://freesound.org/apiv2/apply\n"
        "FREESOUND_API_TOKEN=\n",
        encoding="utf-8",
    )
    print(f"created: {path}")
    print(f"request token: {APPLY_URL}")


def find_api_token(env_file: Path, environ: dict[str, str] | None = None) -> str:
    env = dict(environ or os.environ)
    file_env = read_env_file(resolve_path(env_file))
    for key in ("FREESOUND_API_TOKEN", "FREESOUND_API_KEY"):
        if env.get(key):
            return env[key].strip()
        if file_env.get(key):
            return file_env[key].strip()
    return ""


def read_env_file(path: Path) -> dict[str, str]:
    if not path.exists():
        return {}
    values: dict[str, str] = {}
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        value = value.strip().strip('"').strip("'")
        values[key.strip()] = value
    return values


def missing_token_message(env_file: Path) -> str:
    path = resolve_path(env_file)
    return "\n".join(
        [
            "Missing Freesound API token.",
            f"Request one here: {APPLY_URL}",
            f"Then store it in ignored local config: {path}",
            "",
            "Expected line:",
            "FREESOUND_API_TOKEN=<your token>",
            "",
            f"To create the placeholder file now: scripts/audio_asset_search_freesound.py --init-env",
        ]
    )


def build_filter(license_name: str, min_duration: float, max_duration: float, extra_filters: list[str] | None = None) -> str:
    parts: list[str] = []
    if license_name:
        parts.append(f'license:"{license_name}"')
    if min_duration > 0 or max_duration > 0:
        start = format_duration(min_duration) if min_duration > 0 else "*"
        end = format_duration(max_duration) if max_duration > 0 else "*"
        parts.append(f"duration:[{start} TO {end}]")
    parts.extend(filter(None, extra_filters or []))
    return " ".join(parts)


def build_search_params(query: str, search_filter: str, sort: str, limit: int, token: str) -> dict[str, str]:
    page_size = max(1, min(limit, 150))
    return {
        "query": query,
        "filter": search_filter,
        "sort": sort,
        "fields": ",".join(DEFAULT_FIELDS),
        "page_size": str(page_size),
        "token": token,
    }


def build_url(params: dict[str, str]) -> str:
    return API_URL + "?" + urllib.parse.urlencode(params)


def fetch_json(url: str) -> dict[str, Any]:
    request = urllib.request.Request(url, headers={"User-Agent": "workflow-manager-audio-assets/0.1"})
    try:
        with urllib.request.urlopen(request, timeout=20) as response:
            return json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")
        raise SystemExit(f"Freesound API error {exc.code}: {detail}") from exc
    except urllib.error.URLError as exc:
        raise SystemExit(f"Freesound API connection failed: {exc}") from exc


def build_candidate_document(
    response: dict[str, Any],
    query: str,
    search_filter: str,
    sort: str,
    requested_at: str,
    redacted_url: str,
) -> dict[str, Any]:
    results = response.get("results") or []
    return {
        "schema": "continuum.audio_asset_candidates.v1",
        "provider": "freesound",
        "queried_at": requested_at,
        "query": query,
        "filter": search_filter,
        "sort": sort,
        "redacted_request_url": redacted_url,
        "result_count": response.get("count"),
        "next": redact_token_url(response.get("next")),
        "previous": redact_token_url(response.get("previous")),
        "candidates": [normalise_candidate(item, query, requested_at) for item in results],
    }


def normalise_candidate(sound: dict[str, Any], query: str, checked_at: str) -> dict[str, Any]:
    sound_id = sound.get("id")
    license_name = sound.get("license") or ""
    previews = sound.get("previews") or {}
    source_url = sound.get("url") or f"https://freesound.org/s/{sound_id}/"
    return {
        "asset_id": f"sfx_{slugify(query)}_{checked_at[:10].replace('-', '')}_freesound_{sound_id}",
        "asset_kind": "external_sfx",
        "source_provider": "freesound",
        "source_id": sound_id,
        "source_url": source_url,
        "source_title": sound.get("name") or "",
        "creator": sound.get("username") or "",
        "license": license_name,
        "license_url": LICENSE_URLS.get(license_name, ""),
        "attribution_required": license_name == "Attribution",
        "commercial_use_status": commercial_status(license_name),
        "license_checked_at": checked_at,
        "downloaded_at": "",
        "download_url": "",
        "preview_urls": previews,
        "preferred_preview_url": previews.get("preview-hq-mp3") or previews.get("preview-lq-mp3") or "",
        "file_path": "",
        "file_sha256": "",
        "duration_seconds": sound.get("duration"),
        "format": sound.get("type") or "",
        "filesize_bytes": sound.get("filesize"),
        "tags": sound.get("tags") or [],
        "description": sound.get("description") or "",
        "source_created_at": sound.get("created") or "",
        "rating": sound.get("avg_rating"),
        "rating_count": sound.get("num_ratings"),
        "download_count": sound.get("num_downloads"),
        "score": sound.get("score"),
        "usage_notes": "",
        "approval_status": "candidate",
    }


def commercial_status(license_name: str) -> str:
    if license_name in {"Creative Commons 0", "Attribution"}:
        return "allowed"
    if license_name == "Attribution NonCommercial":
        return "rejected_public_adverts_noncommercial"
    return "unknown_review_required"


def default_output_path(out_dir: Path, query: str, requested_at: str) -> Path:
    stamp = requested_at.replace("-", "").replace(":", "").replace("+", "Z")
    return resolve_path(out_dir) / f"freesound-{slugify(query)}-{stamp}.json"


def redact_token_url(url: Any) -> str | None:
    if not url:
        return None
    parsed = urllib.parse.urlsplit(str(url))
    query = urllib.parse.parse_qsl(parsed.query, keep_blank_values=True)
    redacted_query = [(key, "REDACTED" if key == "token" else value) for key, value in query]
    return urllib.parse.urlunsplit(parsed._replace(query=urllib.parse.urlencode(redacted_query)))


def format_duration(value: float) -> str:
    return f"{value:g}"


def slugify(value: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-")
    return slug or "sound"


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")


def resolve_path(path: Path) -> Path:
    path = path.expanduser()
    if path.is_absolute():
        return path
    return ROOT / path


if __name__ == "__main__":
    raise SystemExit(main())
