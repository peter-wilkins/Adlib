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
import subprocess
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
BRACKET_DIRECTION_RE = re.compile(r"\[[^\]]+\]")
CANONICAL_TOKEN_PHRASES = {
    ("ad", "lib"): "adlib",
    ("check", "dam"): "checkdam",
    ("eleven", "labs"): "elevenlabs",
    ("field", "relay"): "fieldrelay",
    ("fieldrelay", "continuumkit"): "fieldrelaycontinuumkit",
    ("frog", "spawn"): "frogspawn",
    ("job", "done"): "jobdone",
    ("jobdone", "continuumkit"): "jobdonecontinuumkit",
    ("jury", "rigged"): "juryrigged",
    ("juryrigged", "continuumkit"): "juryriggedcontinuumkit",
    ("missus",): "mrs",
    ("adlib", "continuumkit"): "adlibcontinuumkit",
    ("downwind", "continuumkit"): "downwindcontinuumkit",
    ("school", "continuumkit"): "schoolcontinuumkit",
    ("white", "caps"): "whitecaps",
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


@dataclass(frozen=True)
class TimedToken:
    token: str
    start_seconds: float
    end_seconds: float


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
    parser.add_argument(
        "--word-transcription-url",
        default=os.environ.get("ADLIB_WORD_TRANSCRIPTION_API_URL"),
        help="Whisper-Wayland word timestamp endpoint. Defaults to /words beside --transcription-url.",
    )
    parser.add_argument("--language", default="en")
    parser.add_argument("--post-process", action="store_true", help="Ask Whisper-Wayland for its cleanup pass too.")
    parser.add_argument(
        "--required-transcriber",
        default=os.environ.get("ADLIB_REQUIRED_TRANSCRIBER", "whisper-1"),
        help="Require this backend processorId from Whisper-Wayland; empty string allows any.",
    )
    parser.add_argument(
        "--repair-leading-words",
        action="store_true",
        help="Create a local clipped candidate when only extra leading words are present.",
    )
    parser.add_argument("--repair-dir", type=Path, help="Directory for clipped repair candidates.")
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
    repair = build_repair_plan(data, audio_path, drift)
    if args.repair_leading_words and drift.status == "extra_leading_words":
        repair = create_leading_word_repair(data, audio_path, drift, args)
    preflight = build_preflight(data, audio_path, transcript, drift, args.transcription_url, repair)

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


def transcribe_words(
    path: Path,
    *,
    word_transcription_url: str,
    timeout: float,
) -> dict[str, Any]:
    audio = path.read_bytes()
    boundary = "adlib-audio-boundary"
    content_type = mimetypes.guess_type(path.name)[0] or "application/octet-stream"
    body = multipart_file_body(boundary, "file", path.name, content_type, audio)
    request = urllib.request.Request(
        word_transcription_url,
        data=body,
        headers={"Content-Type": f"multipart/form-data; boundary={boundary}"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            payload = response.read().decode("utf-8")
    except urllib.error.HTTPError as error:
        detail = error.read().decode("utf-8", errors="replace")
        raise QualityGateError(f"word transcription API HTTP {error.code}: {detail}") from error
    except (TimeoutError, OSError, urllib.error.URLError) as error:
        raise QualityGateError(f"word transcription API request failed: {error}") from error

    try:
        return json.loads(payload)
    except json.JSONDecodeError as error:
        raise QualityGateError(f"word transcription API returned non-JSON: {payload[:200]}") from error


def multipart_file_body(
    boundary: str,
    field_name: str,
    filename: str,
    content_type: str,
    content: bytes,
) -> bytes:
    head = (
        f"--{boundary}\r\n"
        f'Content-Disposition: form-data; name="{field_name}"; filename="{filename}"\r\n'
        f"Content-Type: {content_type}\r\n\r\n"
    ).encode("utf-8")
    tail = f"\r\n--{boundary}--\r\n".encode("utf-8")
    return head + content + tail


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


def words_url_for(transcription_url: str) -> str:
    parsed = urllib.parse.urlparse(transcription_url)
    path = parsed.path.rstrip("/")
    if path.endswith("/words"):
        words_path = path
    elif path.endswith("/transcribe"):
        words_path = f"{path}/words"
    else:
        words_path = f"{path}/words"
    return urllib.parse.urlunparse(parsed._replace(path=words_path, query=""))


def classify_script_drift(approved_text: str, spoken_text: str) -> ScriptDriftResult:
    approved_spoken_text = spoken_script_text(approved_text)
    approved_tokens = word_tokens(approved_spoken_text)
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


def basic_word_tokens(value: str) -> list[str]:
    normalized = (
        value.lower()
        .replace("\u2019", "'")
        .replace("\u2018", "'")
        .replace("\u201c", '"')
        .replace("\u201d", '"')
    )
    return WORD_RE.findall(normalized)


def spoken_script_text(value: str) -> str:
    """Remove non-spoken performance directions from manifest script text."""
    without_directions = BRACKET_DIRECTION_RE.sub(" ", value)
    return re.sub(r"\s+", " ", without_directions).strip()


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


def timed_tokens_from_words(words: list[dict[str, Any]]) -> list[TimedToken]:
    raw_tokens: list[TimedToken] = []
    for item in words:
        try:
            start = float(item["startSeconds"])
            end = float(item["endSeconds"])
        except (KeyError, TypeError, ValueError) as error:
            raise QualityGateError(f"invalid word timestamp item: {item}") from error
        for token in basic_word_tokens(str(item.get("word") or "")):
            raw_tokens.append(TimedToken(token=token, start_seconds=start, end_seconds=end))
    return canonical_timed_tokens(raw_tokens)


def canonical_timed_tokens(tokens: list[TimedToken]) -> list[TimedToken]:
    canonical: list[TimedToken] = []
    index = 0
    while index < len(tokens):
        matched = False
        for phrase, replacement in CANONICAL_TOKEN_PHRASES.items():
            phrase_length = len(phrase)
            current = tuple(token.token for token in tokens[index : index + phrase_length])
            if current == phrase:
                canonical.append(
                    TimedToken(
                        token=replacement,
                        start_seconds=tokens[index].start_seconds,
                        end_seconds=tokens[index + phrase_length - 1].end_seconds,
                    )
                )
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


def trim_start_for_repair(drift: ScriptDriftResult, words_payload: dict[str, Any]) -> float:
    words = words_payload.get("words")
    if not isinstance(words, list):
        raise QualityGateError("word transcription response does not contain words[]")
    timed_tokens = timed_tokens_from_words(words)
    spoken_tokens = [token.token for token in timed_tokens]
    start_index = find_subsequence(spoken_tokens, drift.approved_tokens)
    if start_index <= 0:
        raise QualityGateError("could not align approved script with word timestamps")
    return timed_tokens[start_index].start_seconds


def build_preflight(
    data: dict[str, Any],
    audio_path: Path,
    transcript: dict[str, Any],
    drift: ScriptDriftResult,
    transcription_url: str,
    repair: dict[str, Any] | None,
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
            "approvedSpokenText": spoken_script_text(str(data.get("scriptText") or "")),
            "spokenText": transcript.get("postProcessedText") or transcript.get("text"),
        },
        "assetRepair": repair,
    }


def build_repair_plan(data: dict[str, Any], audio_path: Path, drift: ScriptDriftResult) -> dict[str, Any] | None:
    if drift.status != "extra_leading_words":
        return None
    return {
        "status": "candidate_not_applied",
        "method": "trim_leading_words",
        "reason": "Approved script is intact after leading words, but this gate needs word timestamps or manual editing before it can cut audio safely.",
        "sourcePath": str(audio_path),
        "extraLeadingWords": drift.extra_leading_words,
    }


def create_leading_word_repair(
    data: dict[str, Any],
    audio_path: Path,
    drift: ScriptDriftResult,
    args: argparse.Namespace,
) -> dict[str, Any]:
    word_url = args.word_transcription_url or words_url_for(args.transcription_url)
    word_payload = transcribe_words(
        audio_path,
        word_transcription_url=word_url,
        timeout=args.timeout,
    )
    validate_transcriber(word_payload, args.required_transcriber)
    trim_start = trim_start_for_repair(drift, word_payload)
    candidate_path = repair_candidate_path(data, audio_path, trim_start, args.repair_dir)
    created = trim_audio(audio_path, candidate_path, trim_start)
    verification_transcript = transcribe_file(
        candidate_path,
        transcription_url=args.transcription_url,
        language=args.language,
        post_process=args.post_process,
        timeout=args.timeout,
    )
    validate_transcriber(verification_transcript, args.required_transcriber)
    verification_text = str(
        verification_transcript.get("postProcessedText") or verification_transcript.get("text") or ""
    )
    verification_drift = classify_script_drift(str(data.get("scriptText") or ""), verification_text)
    if verification_drift.gate_status == "pass":
        status = "candidate_verified"
    elif created:
        status = "candidate_created_verification_failed"
    else:
        status = "candidate_exists_verification_failed"
    backend = word_payload.get("backend") if isinstance(word_payload.get("backend"), dict) else {}
    verification_backend = (
        verification_transcript.get("backend")
        if isinstance(verification_transcript.get("backend"), dict)
        else {}
    )
    return {
        "status": status,
        "method": "trim_leading_words",
        "reason": "Approved script is intact after leading words; word timestamps were used to create a clipped local candidate.",
        "sourcePath": str(audio_path),
        "candidatePath": str(candidate_path),
        "trimStartSeconds": round(trim_start, 4),
        "extraLeadingWords": drift.extra_leading_words,
        "wordTranscription": {
            "provider": "whisper-wayland",
            "endpoint": redact_local_query(word_url),
            "schema": word_payload.get("schema"),
            "text": word_payload.get("text"),
            "backend": {
                "provider": backend.get("provider"),
                "processorId": backend.get("processorId"),
            },
            "words": word_payload.get("words"),
        },
        "candidateVerification": {
            "status": verification_drift.gate_status,
            "scriptDrift": asdict(verification_drift),
            "transcription": {
                "provider": "whisper-wayland",
                "endpoint": redact_local_query(args.transcription_url),
                "schema": verification_transcript.get("schema"),
                "text": verification_transcript.get("text"),
                "postProcessedText": verification_transcript.get("postProcessedText"),
                "backend": {
                    "provider": verification_backend.get("provider"),
                    "processorId": verification_backend.get("processorId"),
                },
            },
        },
    }


def repair_candidate_path(
    data: dict[str, Any],
    audio_path: Path,
    trim_start_seconds: float,
    repair_dir: Path | None = None,
) -> Path:
    campaign = str(data.get("campaign") or "unknown-campaign")
    root = repair_dir or ROOT / "local" / "audio-adverts" / campaign / "assets" / "repairs" / "technical-preflight"
    trim_ms = int(round(trim_start_seconds * 1000))
    source_sha = sha256_file(audio_path)[:10] if audio_path.exists() else "unknownsha"
    return root / f"{audio_path.stem}__trim-leading-{trim_ms}ms__{source_sha}{audio_path.suffix}"


def trim_audio(source_path: Path, candidate_path: Path, trim_start_seconds: float) -> bool:
    candidate_path.parent.mkdir(parents=True, exist_ok=True)
    if candidate_path.exists():
        return False
    subprocess_args = [
        "ffmpeg",
        "-hide_banner",
        "-loglevel",
        "error",
        "-nostdin",
        "-i",
        str(source_path),
        "-af",
        f"atrim=start={trim_start_seconds:.4f},asetpts=PTS-STARTPTS",
        str(candidate_path),
    ]
    try:
        subprocess.run(subprocess_args, cwd=ROOT, check=True)
    except FileNotFoundError as error:
        raise QualityGateError("ffmpeg is required to create repair candidates") from error
    except subprocess.CalledProcessError as error:
        raise QualityGateError(f"ffmpeg failed to create repair candidate: {error}") from error
    return True


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
