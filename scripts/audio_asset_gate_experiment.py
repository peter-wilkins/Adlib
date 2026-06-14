#!/usr/bin/env python3
"""Run repeatable Audio Asset Quality Gate experiments."""

from __future__ import annotations

import argparse
import json
import math
import os
import subprocess
import sys
import threading
import wave
from datetime import datetime, timezone
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUT_ROOT = ROOT / "local" / "reports" / "gate-experiments" / "audio-asset-quality-gate"
DEFAULT_REAL_TRANSCRIPTION_URL = "http://127.0.0.1:8789/v1/transcribe"
GATE_SCRIPT = ROOT / "scripts" / "audio_asset_quality_gate.py"
SCHEMA = "adlib.audio-asset-gate-experiment.v1"


CONTROLLED_CASES = [
    {
        "caseId": "good_exact",
        "scriptText": "Add that to the JobDone note.",
        "transcript": "Add that to the job done note.",
        "expectedGateStatus": "pass",
        "expectedDriftStatus": "exact_match",
        "expectedTestStatus": "preflight_passed_needs_creative_critic",
    },
    {
        "caseId": "good_with_direction",
        "scriptText": "[warm, practical] Exactly. I think you're ready.",
        "transcript": "Exactly. I think you're ready.",
        "expectedGateStatus": "pass",
        "expectedDriftStatus": "exact_match",
        "expectedTestStatus": "preflight_passed_needs_creative_critic",
    },
    {
        "caseId": "repair_extra_leading",
        "scriptText": "[warm, practical] Exactly. I think you're ready.",
        "transcript": "And exactly. I think you're ready.",
        "expectedGateStatus": "repair_needed",
        "expectedDriftStatus": "extra_leading_words",
        "expectedTestStatus": "repair_trim_leading_words",
    },
    {
        "caseId": "bad_extra_trailing",
        "scriptText": "Add that to the JobDone note.",
        "transcript": "Add that to the JobDone note. Thanks.",
        "expectedGateStatus": "fail",
        "expectedDriftStatus": "extra_trailing_words",
        "expectedTestStatus": "script_drift_extra_trailing_words",
    },
    {
        "caseId": "bad_mismatch",
        "scriptText": "Show me the last note for this place.",
        "transcript": "Show me the next job for this person.",
        "expectedGateStatus": "fail",
        "expectedDriftStatus": "mismatch",
        "expectedTestStatus": "script_drift_mismatch",
    },
]


LIVING_WATER_MENTOR_CASES = [
    {
        "caseId": "living_water_mentor_guidance_raw",
        "sourceMetadataPath": ROOT
        / "data/processed/audio-ads/living-water-skills-pond-challenge/elevenlabs/selected-lines/LWS_ad01_pond_challenge_mentor_guidance__selected_river_guidance__mentor_river_steward__20260603T115849Z.json",
        "audioPath": ROOT
        / "local/audio-adverts/living-water-skills-pond-challenge/assets/voice/mentor/selected/mentor_guidance__selected_river_guidance__mentor_river_steward.mp3",
    },
    {
        "caseId": "living_water_mentor_guidance_phone",
        "sourceMetadataPath": ROOT
        / "data/processed/audio-ads/living-water-skills-pond-challenge/elevenlabs/selected-lines/LWS_ad01_pond_challenge_mentor_guidance__selected_river_guidance__mentor_river_steward__20260603T115849Z.json",
        "audioPath": ROOT
        / "local/audio-adverts/living-water-skills-pond-challenge/assets/voice/mentor/selected/phone-processed/mentor_guidance__selected_river_guidance__mentor_river_steward__phone_speaker.mp3",
    },
    {
        "caseId": "living_water_mentor_submit_raw",
        "sourceMetadataPath": ROOT
        / "data/processed/audio-ads/living-water-skills-pond-challenge/elevenlabs/selected-lines/LWS_ad01_pond_challenge_mentor_submit__selected_river_submit__mentor_river_steward__20260603T115851Z.json",
        "audioPath": ROOT
        / "local/audio-adverts/living-water-skills-pond-challenge/assets/voice/mentor/selected/mentor_submit__selected_river_submit__mentor_river_steward.mp3",
    },
    {
        "caseId": "living_water_mentor_submit_phone",
        "sourceMetadataPath": ROOT
        / "data/processed/audio-ads/living-water-skills-pond-challenge/elevenlabs/selected-lines/LWS_ad01_pond_challenge_mentor_submit__selected_river_submit__mentor_river_steward__20260603T115851Z.json",
        "audioPath": ROOT
        / "local/audio-adverts/living-water-skills-pond-challenge/assets/voice/mentor/selected/phone-processed/mentor_submit__selected_river_submit__mentor_river_steward__phone_speaker.mp3",
    },
]


class FakeTranscriptionServer:
    def __init__(self, transcripts_by_filename: dict[str, str]) -> None:
        self.transcripts_by_filename = transcripts_by_filename
        self.server = HTTPServer(("127.0.0.1", 0), self.handler_class())
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)

    @property
    def url(self) -> str:
        host, port = self.server.server_address
        return f"http://{host}:{port}/v1/transcribe"

    def __enter__(self) -> "FakeTranscriptionServer":
        self.thread.start()
        return self

    def __exit__(self, *args: object) -> None:
        self.server.shutdown()
        self.thread.join(timeout=5)

    def handler_class(self) -> type[BaseHTTPRequestHandler]:
        transcripts_by_filename = self.transcripts_by_filename

        class Handler(BaseHTTPRequestHandler):
            def do_GET(self) -> None:  # noqa: N802 - BaseHTTPRequestHandler API
                if self.path == "/health":
                    self.write_json({"ok": True, "schema": "fake.transcription-api.v1"})
                    return
                self.send_error(404)

            def do_POST(self) -> None:  # noqa: N802 - BaseHTTPRequestHandler API
                length = int(self.headers.get("Content-Length") or "0")
                body = self.rfile.read(length)
                filename = self.headers.get("X-Filename", "")
                transcript = transcripts_by_filename.get(filename)
                if transcript is None:
                    self.send_error(404, f"no fixture transcript for {filename}")
                    return
                self.write_json(
                    {
                        "schema": "fake.transcription-api.v1",
                        "filename": filename,
                        "contentType": self.headers.get("Content-Type"),
                        "byteLength": len(body),
                        "language": "en",
                        "text": transcript,
                        "postProcessedText": None,
                        "backend": {
                            "provider": "openai",
                            "processorId": "whisper-1",
                        },
                    }
                )

            def log_message(self, format: str, *args: object) -> None:
                return

            def write_json(self, payload: dict[str, Any]) -> None:
                encoded = json.dumps(payload).encode("utf-8")
                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self.send_header("Content-Length", str(len(encoded)))
                self.end_headers()
                self.wfile.write(encoded)

        return Handler


def main() -> int:
    args = parse_args()
    run_dir = run_directory(args.out_root)
    report = {
        "schemaVersion": SCHEMA,
        "createdAt": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "runDir": str(run_dir),
        "controlled": [],
        "realLivingWater": [],
    }

    controlled = run_controlled_cases(run_dir)
    report["controlled"] = controlled

    if args.include_real_living_water:
        report["realLivingWater"] = run_living_water_cases(
            run_dir,
            transcription_url=args.real_transcription_url,
            required_transcriber=args.required_transcriber,
        )

    report_path = run_dir / "report.json"
    report_path.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    latest_path = args.out_root / "latest-report.json"
    latest_path.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    html_path = run_dir / "index.html"
    html_path.write_text(render_html_report(report), encoding="utf-8")
    (args.out_root / "index.html").write_text(render_html_report(report), encoding="utf-8")

    print(f"report: {report_path}")
    print(f"page: {html_path}")
    print(summary_line("controlled", controlled))
    if args.include_real_living_water:
        print(summary_line("real living water", report["realLivingWater"]))
    return 0 if all_passed(controlled) else 1


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out-root", type=Path, default=DEFAULT_OUT_ROOT)
    parser.add_argument(
        "--include-real-living-water",
        action="store_true",
        help="Also run the real Living Water mentor clips through Whisper-Wayland.",
    )
    parser.add_argument(
        "--real-transcription-url",
        default=os.environ.get("ADLIB_TRANSCRIPTION_API_URL", DEFAULT_REAL_TRANSCRIPTION_URL),
    )
    parser.add_argument(
        "--required-transcriber",
        default=os.environ.get("ADLIB_REQUIRED_TRANSCRIBER", "whisper-1"),
    )
    return parser.parse_args()


def run_directory(out_root: Path) -> Path:
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    run_dir = out_root / timestamp
    run_dir.mkdir(parents=True, exist_ok=True)
    return run_dir


def run_controlled_cases(run_dir: Path) -> list[dict[str, Any]]:
    case_dir = run_dir / "controlled"
    audio_dir = case_dir / "audio"
    meta_dir = case_dir / "metadata"
    audio_dir.mkdir(parents=True, exist_ok=True)
    meta_dir.mkdir(parents=True, exist_ok=True)

    metadata_paths = []
    transcripts = {}
    for index, case in enumerate(CONTROLLED_CASES, start=1):
        audio_path = audio_dir / f"{case['caseId']}.wav"
        metadata_path = meta_dir / f"{case['caseId']}.json"
        write_fixture_audio(audio_path, frequency=280 + index * 40)
        write_fixture_metadata(metadata_path, case, audio_path)
        transcripts[audio_path.name] = str(case["transcript"])
        metadata_paths.append(metadata_path)

    with FakeTranscriptionServer(transcripts) as server:
        run_gate(metadata_paths, server.url, required_transcriber="whisper-1")

    return [case_result(case, meta_dir / f"{case['caseId']}.json") for case in CONTROLLED_CASES]


def run_living_water_cases(
    run_dir: Path,
    *,
    transcription_url: str,
    required_transcriber: str,
) -> list[dict[str, Any]]:
    case_dir = run_dir / "living-water"
    meta_dir = case_dir / "metadata"
    meta_dir.mkdir(parents=True, exist_ok=True)

    metadata_paths = []
    cases = []
    for case in LIVING_WATER_MENTOR_CASES:
        source_metadata_path = Path(case["sourceMetadataPath"])
        audio_path = Path(case["audioPath"])
        if not source_metadata_path.exists() or not audio_path.exists():
            cases.append(
                {
                    "caseId": case["caseId"],
                    "status": "missing_fixture",
                    "sourceMetadataPath": str(source_metadata_path),
                    "audioPath": str(audio_path),
                }
            )
            continue
        metadata = json.loads(source_metadata_path.read_text(encoding="utf-8"))
        metadata["reaperAssetPath"] = str(audio_path)
        metadata["rawAudioPath"] = str(audio_path)
        metadata["testStatus"] = "needs_audition"
        metadata_path = meta_dir / f"{case['caseId']}.json"
        metadata_path.write_text(json.dumps(metadata, indent=2) + "\n", encoding="utf-8")
        metadata_paths.append(metadata_path)
        cases.append({"caseId": case["caseId"], "metadataPath": str(metadata_path)})

    if metadata_paths:
        run_gate(metadata_paths, transcription_url, required_transcriber=required_transcriber)

    results_by_path = {
        str(meta_dir / f"{case['caseId']}.json"): living_water_result(
            case["caseId"],
            meta_dir / f"{case['caseId']}.json",
        )
        for case in LIVING_WATER_MENTOR_CASES
        if (meta_dir / f"{case['caseId']}.json").exists()
    }
    return [results_by_path.get(row.get("metadataPath"), row) for row in cases]


def run_gate(
    metadata_paths: list[Path],
    transcription_url: str,
    *,
    required_transcriber: str,
) -> None:
    command = [
        sys.executable,
        str(GATE_SCRIPT),
        "--force",
        "--keep-going",
        "--transcription-url",
        transcription_url,
        "--required-transcriber",
        required_transcriber,
    ]
    for path in metadata_paths:
        command.extend(["--metadata", str(path)])
    subprocess.run(command, cwd=ROOT, check=True)


def write_fixture_metadata(path: Path, case: dict[str, Any], audio_path: Path) -> None:
    payload = {
        "schemaVersion": "workflow-manager.audio-advert-voice-asset.v1",
        "createdAt": datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ"),
        "provider": "elevenlabs",
        "endpoint": "fixture://audio-asset-quality-gate",
        "modelId": "fixture",
        "outputFormat": "wav_16000",
        "campaign": "gate-experiment",
        "scriptId": "gate_experiment",
        "scriptVersion": "fixture",
        "assetId": case["caseId"],
        "takeSlug": "fixture",
        "speaker": "fixture",
        "scriptText": case["scriptText"],
        "voiceProfile": "fixture_voice",
        "voiceId": "fixture",
        "voiceName": "Fixture Voice",
        "voiceRole": "quality gate fixture",
        "voiceSettings": {},
        "rawAudioPath": str(audio_path),
        "reaperAssetPath": str(audio_path),
        "audioSha256": "",
        "audioBytes": audio_path.stat().st_size,
        "responseHeaders": {},
        "testStatus": "needs_audition",
    }
    path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")


def write_fixture_audio(path: Path, *, frequency: int) -> None:
    sample_rate = 16000
    seconds = 0.35
    amplitude = 1800
    frames = int(sample_rate * seconds)
    with wave.open(str(path), "wb") as handle:
        handle.setnchannels(1)
        handle.setsampwidth(2)
        handle.setframerate(sample_rate)
        for index in range(frames):
            value = int(amplitude * math.sin(2 * math.pi * frequency * index / sample_rate))
            handle.writeframesraw(value.to_bytes(2, byteorder="little", signed=True))


def case_result(case: dict[str, Any], metadata_path: Path) -> dict[str, Any]:
    metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
    preflight = metadata["qualityGate"]["technicalPreflight"]
    drift = preflight["scriptDrift"]
    result = {
        "caseId": case["caseId"],
        "metadataPath": str(metadata_path),
        "expectedGateStatus": case["expectedGateStatus"],
        "actualGateStatus": preflight["status"],
        "expectedDriftStatus": case["expectedDriftStatus"],
        "actualDriftStatus": drift["status"],
        "expectedTestStatus": case["expectedTestStatus"],
        "actualTestStatus": metadata["testStatus"],
        "repairPlan": preflight.get("assetRepair"),
    }
    result["passed"] = (
        result["expectedGateStatus"] == result["actualGateStatus"]
        and result["expectedDriftStatus"] == result["actualDriftStatus"]
        and result["expectedTestStatus"] == result["actualTestStatus"]
    )
    return result


def living_water_result(case_id: str, metadata_path: Path) -> dict[str, Any]:
    metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
    preflight = metadata["qualityGate"]["technicalPreflight"]
    drift = preflight["scriptDrift"]
    transcription = preflight["transcription"]
    return {
        "caseId": case_id,
        "metadataPath": str(metadata_path),
        "audioPath": preflight["audio"]["path"],
        "gateStatus": preflight["status"],
        "driftStatus": drift["status"],
        "testStatus": metadata["testStatus"],
        "extraLeadingWords": drift["extra_leading_words"],
        "approvedSpokenText": drift["approvedSpokenText"],
        "spokenText": drift["spokenText"],
        "repairPlan": preflight.get("assetRepair"),
        "transcriber": transcription.get("backend", {}).get("processorId"),
    }


def summary_line(label: str, rows: list[dict[str, Any]]) -> str:
    if not rows:
        return f"{label}: none"
    passed = sum(1 for row in rows if row.get("passed") is True)
    failed = sum(1 for row in rows if row.get("passed") is False)
    other = len(rows) - passed - failed
    return f"{label}: {len(rows)} rows; passed={passed}; failed={failed}; other={other}"


def all_passed(rows: list[dict[str, Any]]) -> bool:
    return all(row.get("passed") is True for row in rows)


def render_html_report(report: dict[str, Any]) -> str:
    return f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Audio Asset Gate Experiment</title>
  <style>
    body {{ font-family: system-ui, sans-serif; margin: 24px; line-height: 1.4; }}
    table {{ border-collapse: collapse; width: 100%; margin: 16px 0 32px; }}
    th, td {{ border: 1px solid #ccd3d8; padding: 8px; vertical-align: top; text-align: left; }}
    th {{ background: #eef3f6; }}
    code {{ overflow-wrap: anywhere; }}
    .pass {{ color: #0f6b45; font-weight: 700; }}
    .repair {{ color: #8a5b00; font-weight: 700; }}
    .fail {{ color: #9b2d24; font-weight: 700; }}
  </style>
</head>
<body>
  <h1>Audio Asset Gate Experiment</h1>
  <p>Created {escape_html(report.get("createdAt", ""))}</p>
  <h2>Controlled Fixture Cases</h2>
  {render_controlled_table(report.get("controlled") or [])}
  <h2>Real Living Water Mentor Cases</h2>
  {render_real_table(report.get("realLivingWater") or [])}
</body>
</html>
"""


def render_controlled_table(rows: list[dict[str, Any]]) -> str:
    if not rows:
        return "<p>No controlled cases.</p>"
    body = "\n".join(
        "<tr>"
        f"<td>{escape_html(row.get('caseId'))}</td>"
        f"<td>{status_span(row.get('actualGateStatus'))}</td>"
        f"<td>{escape_html(row.get('actualDriftStatus'))}</td>"
        f"<td>{escape_html(row.get('actualTestStatus'))}</td>"
        f"<td>{'yes' if row.get('passed') else 'no'}</td>"
        f"<td><code>{escape_html(row.get('metadataPath'))}</code></td>"
        "</tr>"
        for row in rows
    )
    return (
        "<table><thead><tr><th>Case</th><th>Gate</th><th>Drift</th><th>Status</th>"
        "<th>Expected?</th><th>Metadata</th></tr></thead><tbody>"
        + body
        + "</tbody></table>"
    )


def render_real_table(rows: list[dict[str, Any]]) -> str:
    if not rows:
        return "<p>Not run.</p>"
    body = "\n".join(
        "<tr>"
        f"<td>{escape_html(row.get('caseId'))}</td>"
        f"<td>{status_span(row.get('gateStatus'))}</td>"
        f"<td>{escape_html(row.get('driftStatus'))}</td>"
        f"<td>{escape_html(' '.join(row.get('extraLeadingWords') or []))}</td>"
        f"<td>{escape_html(row.get('approvedSpokenText'))}</td>"
        f"<td>{escape_html(row.get('spokenText'))}</td>"
        f"<td><code>{escape_html(row.get('audioPath'))}</code></td>"
        "</tr>"
        for row in rows
    )
    return (
        "<table><thead><tr><th>Case</th><th>Gate</th><th>Drift</th><th>Extra lead</th>"
        "<th>Approved spoken text</th><th>Whisper text</th><th>Audio</th></tr></thead><tbody>"
        + body
        + "</tbody></table>"
    )


def status_span(value: object) -> str:
    text = str(value or "")
    klass = "pass" if text == "pass" else "repair" if text == "repair_needed" else "fail"
    return f'<span class="{klass}">{escape_html(text)}</span>'


def escape_html(value: object) -> str:
    return (
        str(value or "")
        .replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
    )


if __name__ == "__main__":
    raise SystemExit(main())
