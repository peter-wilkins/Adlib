#!/usr/bin/env python3
"""Run the Audio Asset Quality Gate technical preflight on generated assets."""

from __future__ import annotations

import argparse
import difflib
import hashlib
import json
import mimetypes
import os
import re
import sys
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_PROCESSED_ROOT = ROOT / "data" / "processed" / "audio-ads"
DEFAULT_TRANSCRIPTION_URL = "http://127.0.0.1:8788/v1/transcribe"
GATE_SCHEMA = "adlib.audio-asset-quality-gate.v1"
WORD_RE = re.compile(r"[a-z0-9]+(?:'[a-z0-9]+)?")
CANONICAL_TOKEN_PHRASES = {
    ("ad", "lib"): "adlib",
    ("check", "dam"): "checkdam",
    ("eleven", "labs"): "elevenlabs",
    ("job", "done"): "jobdone",
    ("missus",): "mrs",
    ("wind", "stats"): "windstats",
}


class QualityGateError(RuntimeError):
    pass


@dataclass(frozen=True)
class ScriptDriftResult:
    status: str
    gate_status: str
    test_status: str
    approved_tokens: list[str]
    spoken_tokens: list[str]
    extra_leading_words: list[str]
    extra_trailing_words: list[str]
    similarity: float
    message: str


def main() -> int:
    args = parse_args()
    paths = list(metadata_paths(args))
    if args.limit:
        paths = paths[: args.limit]

    if not paths:
        print("no matching ElevenLabs voice metadata found")
        return 0

    if not args.skip_health:
        check_health(args.transcription_url, args.timeout)

    rows = []
    for path in paths:
        try:
            rows.append(run_preflight(path, args))
        except QualityGateError as error:
            print(f"failed {path}: {error}", file=sys.stderr)
            if args.keep_going:
                rows.append({"metadataPath": str(path), "status": "error", "error": str(error)})
                continue
            return 1

    passed = sum(1 for row in rows if row.get("gateStatus") == "pass")
    repair = sum(1 for row in rows if row.get("gateStatus") == "repair_needed")
    failed = sum(1 for row in rows if row.get("gateStatus") == "fail")
    skipped = sum(1 for row in rows if row.get("status") == "skipped")
    print(f"preflighted {len(rows) - skipped}; passed={passed}; repair={repair}; failed={failed}; skipped={skipped}")
    for row in rows:
        label = row.get("label") or row.get("metadataPath")
        if row.get("status") == "skipped":
            print(f"- skipped {label}")
        elif row.get("status") == "error":
            print(f"- error {label}: {row.get('error')}")
        else:
            print(f"- {row['gateStatus']} {row['driftStatus']} {label}")
    return 0 if not args.fail_on_drift or failed == 0 else 2


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--metadata", action="append", type=Path, help="Metadata JSON to preflight; may be repeated.")
    parser.add_argument("--processed-root", type=Path, default=DEFAULT_PROCESSED_ROOT)
    parser.add_argument("--campaign", help="Only preflight one campaign.")
    parser.add_argument("--asset-id", action="append", help="Only preflight this asset id; may be repeated.")
    parser.add_argument("--take-slug", action="append", help="Only preflight this take slug; may be repeated.")
    parser.add_argument("--voice-profile", action="append", help="Only preflight this voice profile; may be repeated.")
    parser.add_argument("--status", action="append", help="Only preflight metadata with this testStatus; may be repeated.")
    parser.add_argument("--limit", type=int, help="Preflight only the first N matching metadata files.")
    parser.add_argument("--force", action="store_true", help="Preflight even if technical preflight already exists.")
    parser.add_argument("--dry-run", action="store_true", help="Print results without updating metadata.")
    parser.add_argument("--keep-going", action="store_true", help="Continue after an individual asset fails.")
    parser.add_argument("--fail-on-drift", action="store_true", help="Exit 2 if any asset fails script-drift checks.")
    parser.add_argument("--skip-health", action="store_true", help="Skip transcription API health check.")
    parser.add_argument(
        "--transcription-url",
        default=os.environ.get("ADLIB_TRANSCRIPTION_API_URL", DEFAULT_TRANSCRIPTION_URL),
        help="Whisper-Wayland transcription endpoint.",
    )
    parser.add_argument("--language", default="en")
    parser.add_argument("--post-process", action="store_true", help="Ask Whisper-Wayland for its cleanup pass too.")
    parser.add_argument(
        "--required-transcriber",
        default=os.environ.get("ADLIB_REQUIRED_TRANSCRIBER", "whisper-1"),
        help="Require this backend processorId from Whisper-Wayland; empty string allows any.",
    )
    parser.add_argument("--timeout", type=float, default=60.0)
    return parser.parse_args()


def metadata_paths(args: argparse.Namespace) -> list[Path]:
    if args.metadata:
        return [path for path in args.metadata if metadata_matches(path, args)]

    root = args.processed_root
    if args.campaign:
        root = root / args.campaign
    return [path for path in sorted(root.rglob("*.json")) if metadata_matches(path, args)]


def metadata_matches(path: Path, args: argparse.Namespace) -> bool:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return False
    if data.get("provider") != "elevenlabs":
        return False
    if not data.get("scriptText"):
        return False
    if args.campaign and data.get("campaign") != args.campaign:
        return False
    if args.asset_id and data.get("assetId") not in set(args.asset_id):
        return False
    if args.take_slug and data.get("takeSlug") not in set(args.take_slug):
        return False
    if args.voice_profile and data.get("voiceProfile") not in set(args.voice_profile):
        return False
    if args.status and data.get("testStatus") not in set(args.status):
        return False
    if not args.force and technical_preflight(data):
        return False
    return True


def technical_preflight(data: dict[str, Any]) -> dict[str, Any] | None:
    gate = data.get("qualityGate")
    if not isinstance(gate, dict):
        return None
    preflight = gate.get("technicalPreflight")
    return preflight if isinstance(preflight, dict) else None


def check_health(transcription_url: str, timeout: float) -> None:
    parsed = urllib.parse.urlparse(transcription_url)
    health_url = urllib.parse.urlunparse((parsed.scheme, parsed.netloc, "/health", "", "", ""))
    try:
        with urllib.request.urlopen(health_url, timeout=timeout) as response:
            if response.status >= 400:
                raise QualityGateError(f"transcription API health returned HTTP {response.status}")
    except (OSError, urllib.error.URLError) as error:
        raise QualityGateError(
            f"transcription API is not reachable at {health_url}; start Whisper-Wayland on port 8788"
        ) from error


def run_preflight(path: Path, args: argparse.Namespace) -> dict[str, Any]:
    data = json.loads(path.read_text(encoding="utf-8"))
    audio_path = resolve_audio_path(data)
    transcript = transcribe_file(
        audio_path,
        transcription_url=args.transcription_url,
        language=args.language,
        post_process=args.post_process,
        timeout=args.timeout,
    )
    validate_transcriber(transcript, args.required_transcriber)
    spoken_text = str(transcript.get("postProcessedText") or transcript.get("text") or "")
    drift = classify_script_drift(str(data.get("scriptText") or ""), spoken_text)
    preflight = build_preflight(data, audio_path, transcript, drift, args.transcription_url)

    if not args.dry_run:
        data.setdefault("qualityGate", {})
        data["qualityGate"]["schemaVersion"] = GATE_SCHEMA
        data["qualityGate"]["updatedAt"] = preflight["updatedAt"]
        data["qualityGate"]["technicalPreflight"] = preflight
        data["testStatus"] = drift.test_status
        path.write_text(json.dumps(data, indent=2, sort_keys=False) + "\n", encoding="utf-8")

    return {
        "metadataPath": str(path),
        "label": asset_label(data),
        "gateStatus": drift.gate_status,
        "driftStatus": drift.status,
        "testStatus": drift.test_status,
    }


def resolve_audio_path(data: dict[str, Any]) -> Path:
    for key in ("reaperAssetPath", "rawAudioPath", "audioPath"):
        value = data.get(key)
        if not value:
            continue
        path = Path(str(value))
        if path.exists():
            return path
    raise QualityGateError(f"no existing audio path in metadata for {asset_label(data)}")


def transcribe_file(
    path: Path,
    *,
    transcription_url: str,
    language: str,
    post_process: bool,
    timeout: float,
) -> dict[str, Any]:
    query = {"language": language}
    if post_process:
        query["postProcess"] = "true"
    url = with_query(transcription_url, query)
    audio = path.read_bytes()
    content_type = mimetypes.guess_type(path.name)[0] or "application/octet-stream"
    if path.suffix.lower() == ".mp3":
        content_type = "audio/mpeg"

    request = urllib.request.Request(
        url,
        data=audio,
        headers={
            "Content-Type": content_type,
            "X-Filename": path.name,
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            payload = response.read().decode("utf-8")
    except urllib.error.HTTPError as error:
        detail = error.read().decode("utf-8", errors="replace")
        raise QualityGateError(f"transcription API HTTP {error.code}: {detail}") from error
    except (TimeoutError, OSError, urllib.error.URLError) as error:
        raise QualityGateError(f"transcription API request failed: {error}") from error

    try:
        return json.loads(payload)
    except json.JSONDecodeError as error:
        raise QualityGateError(f"transcription API returned non-JSON: {payload[:200]}") from error


def validate_transcriber(transcript: dict[str, Any], required_processor_id: str) -> None:
    required_processor_id = required_processor_id.strip()
    if not required_processor_id:
        return
    backend = transcript.get("backend") if isinstance(transcript.get("backend"), dict) else {}
    actual_processor_id = str(backend.get("processorId") or "")
    if actual_processor_id == required_processor_id:
        return
    provider = backend.get("provider") or "unknown"
    raise QualityGateError(
        "transcription backend returned "
        f"{provider}:{actual_processor_id or 'unknown'}; expected {required_processor_id}. "
        "Start Whisper-Wayland with WHISPER_MODEL=whisper-1 and TRANSCRIPTION_RACE_MODELS unset."
    )


def with_query(url: str, extra: dict[str, str]) -> str:
    parsed = urllib.parse.urlparse(url)
    pairs = dict(urllib.parse.parse_qsl(parsed.query, keep_blank_values=True))
    pairs.update(extra)
    return urllib.parse.urlunparse(
        parsed._replace(query=urllib.parse.urlencode(pairs))
    )


def classify_script_drift(approved_text: str, spoken_text: str) -> ScriptDriftResult:
    approved_tokens = word_tokens(approved_text)
    spoken_tokens = word_tokens(spoken_text)
    similarity = sequence_similarity(approved_tokens, spoken_tokens)

    if not approved_tokens:
        return drift_result(
            "missing_approved_script",
            "fail",
            "preflight_failed_missing_script",
            approved_tokens,
            spoken_tokens,
            [],
            spoken_tokens,
            similarity,
            "Metadata has no approved script text.",
        )
    if not spoken_tokens:
        return drift_result(
            "empty_transcript",
            "fail",
            "preflight_failed_empty_transcript",
            approved_tokens,
            spoken_tokens,
            [],
            [],
            similarity,
            "Whisper returned no spoken words.",
        )
    if spoken_tokens == approved_tokens:
        return drift_result(
            "exact_match",
            "pass",
            "preflight_passed_needs_creative_critic",
            approved_tokens,
            spoken_tokens,
            [],
            [],
            similarity,
            "Spoken words match the approved script.",
        )

    start = find_subsequence(spoken_tokens, approved_tokens)
    if start != -1:
        leading = spoken_tokens[:start]
        trailing = spoken_tokens[start + len(approved_tokens) :]
        if leading and not trailing:
            return drift_result(
                "extra_leading_words",
                "repair_needed",
                "repair_trim_leading_words",
                approved_tokens,
                spoken_tokens,
                leading,
                [],
                similarity,
                "Approved script is intact after extra leading words; trim the start locally.",
            )
        if trailing and not leading:
            return drift_result(
                "extra_trailing_words",
                "fail",
                "script_drift_extra_trailing_words",
                approved_tokens,
                spoken_tokens,
                [],
                trailing,
                similarity,
                "Generated speech continues after the approved script.",
            )
        return drift_result(
            "extra_wrapping_words",
            "fail",
            "script_drift_extra_words",
            approved_tokens,
            spoken_tokens,
            leading,
            trailing,
            similarity,
            "Approved script is present but wrapped in extra words.",
        )

    return drift_result(
        "mismatch",
        "fail",
        "script_drift_mismatch",
        approved_tokens,
        spoken_tokens,
        [],
        [],
        similarity,
        "Spoken words do not match the approved script.",
    )


def drift_result(
    status: str,
    gate_status: str,
    test_status: str,
    approved_tokens: list[str],
    spoken_tokens: list[str],
    extra_leading_words: list[str],
    extra_trailing_words: list[str],
    similarity: float,
    message: str,
) -> ScriptDriftResult:
    return ScriptDriftResult(
        status=status,
        gate_status=gate_status,
        test_status=test_status,
        approved_tokens=approved_tokens,
        spoken_tokens=spoken_tokens,
        extra_leading_words=extra_leading_words,
        extra_trailing_words=extra_trailing_words,
        similarity=round(similarity, 4),
        message=message,
    )


def word_tokens(value: str) -> list[str]:
    normalized = (
        value.lower()
        .replace("\u2019", "'")
        .replace("\u2018", "'")
        .replace("\u201c", '"')
        .replace("\u201d", '"')
    )
    return canonical_tokens(WORD_RE.findall(normalized))


def canonical_tokens(tokens: list[str]) -> list[str]:
    canonical: list[str] = []
    index = 0
    while index < len(tokens):
        matched = False
        for phrase, replacement in CANONICAL_TOKEN_PHRASES.items():
            phrase_length = len(phrase)
            if tuple(tokens[index : index + phrase_length]) == phrase:
                canonical.append(replacement)
                index += phrase_length
                matched = True
                break
        if matched:
            continue
        canonical.append(tokens[index])
        index += 1
    return canonical


def sequence_similarity(left: list[str], right: list[str]) -> float:
    if not left and not right:
        return 1.0
    return difflib.SequenceMatcher(a=left, b=right).ratio()


def find_subsequence(haystack: list[str], needle: list[str]) -> int:
    if not needle:
        return -1
    last_start = len(haystack) - len(needle)
    for index in range(last_start + 1):
        if haystack[index : index + len(needle)] == needle:
            return index
    return -1


def build_preflight(
    data: dict[str, Any],
    audio_path: Path,
    transcript: dict[str, Any],
    drift: ScriptDriftResult,
    transcription_url: str,
) -> dict[str, Any]:
    updated_at = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    backend = transcript.get("backend") if isinstance(transcript.get("backend"), dict) else {}
    return {
        "schemaVersion": GATE_SCHEMA,
        "updatedAt": updated_at,
        "status": drift.gate_status,
        "assetId": data.get("assetId"),
        "takeSlug": data.get("takeSlug"),
        "voiceProfile": data.get("voiceProfile"),
        "audio": {
            "path": str(audio_path),
            "byteLength": audio_path.stat().st_size,
            "sha256": sha256_file(audio_path),
        },
        "transcription": {
            "provider": "whisper-wayland",
            "endpoint": redact_local_query(transcription_url),
            "schema": transcript.get("schema"),
            "filename": transcript.get("filename"),
            "contentType": transcript.get("contentType"),
            "byteLength": transcript.get("byteLength"),
            "language": transcript.get("language"),
            "text": transcript.get("text"),
            "postProcessedText": transcript.get("postProcessedText"),
            "backend": {
                "provider": backend.get("provider"),
                "processorId": backend.get("processorId"),
            },
        },
        "scriptDrift": {
            **asdict(drift),
            "approvedText": data.get("scriptText"),
            "spokenText": transcript.get("postProcessedText") or transcript.get("text"),
        },
    }


def redact_local_query(url: str) -> str:
    parsed = urllib.parse.urlparse(url)
    return urllib.parse.urlunparse(parsed._replace(query=""))


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def asset_label(data: dict[str, Any]) -> str:
    return ":".join(
        str(value)
        for value in (
            data.get("campaign"),
            data.get("assetId"),
            data.get("takeSlug"),
            data.get("voiceProfile"),
        )
        if value
    )


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except QualityGateError as error:
        print(str(error), file=sys.stderr)
        raise SystemExit(1)
