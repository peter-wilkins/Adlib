#!/usr/bin/env python3
"""Generate selected music, sting, and animated logo assets."""

from __future__ import annotations

import argparse
import json
import math
import os
import random
import re
import shutil
import struct
import subprocess
import tempfile
import urllib.error
import urllib.parse
import urllib.request
import wave
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from PIL import Image, ImageDraw, ImageFont

try:
    from audio_ad_generate_elevenlabs_dialogue import load_env_files, sha256_bytes
except ModuleNotFoundError:
    from scripts.audio_ad_generate_elevenlabs_dialogue import load_env_files, sha256_bytes


ROOT = Path(__file__).resolve().parents[1]
CANDIDATES_PATH = ROOT / "docs/adverts/selection-workbenches/2026-06-15-continuum-asset-candidates.json"
PICKS_PATH = ROOT / "docs/adverts/selection-workbenches/2026-06-15-continuum-asset-picks.json"
CAMPAIGN = "continuum-selected-assets-20260615"
RAW_DIR = ROOT / "data/raw/audio-ads" / CAMPAIGN / "elevenlabs/media-assets"
PROCESSED_DIR = ROOT / "data/processed/audio-ads" / CAMPAIGN / "elevenlabs/media-assets"
LOCAL_ASSET_DIR = ROOT / "local/audio-adverts" / CAMPAIGN / "assets/generated-media"
REPORT_DIR = ROOT / "local/reports/media-asset-workbench" / CAMPAIGN
ENV_PATHS = (
    ROOT / "local/audio-assets/.env",
    ROOT / "local/elevenlabs/.env",
)
FPS = 20
VIDEO_SIZE = (960, 540)
SAMPLE_RATE = 44100
SUPPORTED_TYPES = {"theme_music_brief", "audio_sting_brief", "animated_logo_brief"}


@dataclass(frozen=True)
class MediaAsset:
    asset_id: str
    project: str
    asset_type: str
    title: str
    duration_seconds: float
    audio_path: Path | None
    video_path: Path | None
    metadata_path: Path
    brief: str
    audio_brief: str
    visual_brief: str
    public_audio: str | None = None
    public_video: str | None = None


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--skip-elevenlabs", action="store_true", help="Use local synthetic placeholder audio only.")
    parser.add_argument("--force", action="store_true", help="Regenerate files that already exist.")
    parser.add_argument("--limit", type=int, help="Generate only the first N selected media assets.")
    args = parser.parse_args()

    items = selected_media_items()
    if args.limit:
        items = items[: args.limit]
    if not args.skip_elevenlabs:
        load_env_files(ENV_PATHS)
    api_key = os.environ.get("ELEVENLABS_API_KEY") if not args.skip_elevenlabs else None

    generated: list[MediaAsset] = []
    for index, item in enumerate(items, 1):
        print(f"[{index}/{len(items)}] {item['id']} {item['title']}", flush=True)
        generated.append(generate_item(item, api_key=api_key, force=args.force))

    write_workbench(generated)
    print(f"assets: {len(generated)}")
    print(f"page: {REPORT_DIR / 'index.html'}")
    print(f"data: {REPORT_DIR / 'assets.json'}")
    return 0


def selected_media_items() -> list[dict[str, Any]]:
    candidates = json.loads(CANDIDATES_PATH.read_text(encoding="utf-8"))
    picks = json.loads(PICKS_PATH.read_text(encoding="utf-8"))
    selected = set(picks["selectedIds"])
    items = [item for item in candidates["items"] if item["id"] in selected and item["assetType"] in SUPPORTED_TYPES]
    priority = {"theme_music_brief": 0, "audio_sting_brief": 1, "animated_logo_brief": 2}
    return sorted(items, key=lambda item: (priority[item["assetType"]], item["project"], item["title"]))


def generate_item(item: dict[str, Any], api_key: str | None, force: bool) -> MediaAsset:
    RAW_DIR.mkdir(parents=True, exist_ok=True)
    PROCESSED_DIR.mkdir(parents=True, exist_ok=True)
    LOCAL_ASSET_DIR.mkdir(parents=True, exist_ok=True)
    slug = item["id"]
    duration = parse_duration(str(item.get("duration") or "4s"))
    audio_path = LOCAL_ASSET_DIR / "audio" / f"{slug}.mp3"
    raw_audio_path = RAW_DIR / f"{slug}.mp3"
    video_path = LOCAL_ASSET_DIR / "video" / f"{slug}.mp4"
    metadata_path = PROCESSED_DIR / f"{slug}.json"

    audio_path.parent.mkdir(parents=True, exist_ok=True)
    video_path.parent.mkdir(parents=True, exist_ok=True)

    audio_brief = audio_prompt(item)
    if force or not audio_path.exists():
        audio_bytes, provider, headers = generate_audio(item, audio_brief, duration, api_key)
        audio_path.write_bytes(audio_bytes)
        raw_audio_path.write_bytes(audio_bytes)
    else:
        audio_bytes = audio_path.read_bytes()
        provider = "existing"
        headers = {}

    if item["assetType"] == "animated_logo_brief" and (force or not video_path.exists()):
        render_logo_video(item, duration, audio_path, video_path)

    metadata = {
        "schemaVersion": "adlib.generated-media-asset.v1",
        "createdAt": datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ"),
        "campaign": CAMPAIGN,
        "sourceCandidate": str(CANDIDATES_PATH.relative_to(ROOT)) + f"#{item['id']}",
        "assetId": item["id"],
        "project": item["project"],
        "assetType": item["assetType"],
        "title": item["title"],
        "durationSeconds": duration,
        "audioBrief": audio_brief,
        "visualBrief": item.get("visualBrief") or "",
        "provider": provider,
        "audioPath": str(audio_path),
        "rawAudioPath": str(raw_audio_path),
        "videoPath": str(video_path) if video_path.exists() else None,
        "audioSha256": sha256_bytes(audio_bytes),
        "responseHeaders": headers,
    }
    metadata_path.write_text(json.dumps(metadata, indent=2) + "\n", encoding="utf-8")
    return MediaAsset(
        asset_id=item["id"],
        project=item["project"],
        asset_type=item["assetType"],
        title=item["title"],
        duration_seconds=duration,
        audio_path=audio_path,
        video_path=video_path if video_path.exists() else None,
        metadata_path=metadata_path,
        brief=item.get("productionNotes") or item.get("angle") or "",
        audio_brief=audio_brief,
        visual_brief=item.get("visualBrief") or "",
    )


def generate_audio(
    item: dict[str, Any],
    prompt: str,
    duration: float,
    api_key: str | None,
) -> tuple[bytes, str, dict[str, str]]:
    if api_key and item["assetType"] == "theme_music_brief":
        try:
            return call_elevenlabs_music(api_key, prompt, duration)
        except Exception as error:
            print(f"  music API failed; using local fallback: {error}", flush=True)
    if api_key:
        try:
            return call_elevenlabs_sound(api_key, prompt, duration)
        except Exception as error:
            print(f"  sound API failed; using local fallback: {error}", flush=True)
    return local_audio_mp3(item, duration), "local_synthetic_fallback", {}


def call_elevenlabs_sound(api_key: str, prompt: str, duration: float) -> tuple[bytes, str, dict[str, str]]:
    url = "https://api.elevenlabs.io/v1/sound-generation?" + urllib.parse.urlencode(
        {"output_format": "mp3_44100_128"}
    )
    payload = {
        "text": prompt,
        "duration_seconds": round(duration, 2),
        "prompt_influence": 0.55,
        "model_id": "eleven_text_to_sound_v2",
    }
    return post_audio(url, api_key, payload, "elevenlabs_sound_generation")


def call_elevenlabs_music(api_key: str, prompt: str, duration: float) -> tuple[bytes, str, dict[str, str]]:
    url = "https://api.elevenlabs.io/v1/music/stream?" + urllib.parse.urlencode(
        {"output_format": "mp3_44100_128"}
    )
    payload = {
        "prompt": prompt,
        "music_length_ms": int(duration * 1000),
        "force_instrumental": True,
        "model_id": "music_v1",
    }
    return post_audio(url, api_key, payload, "elevenlabs_music")


def post_audio(url: str, api_key: str, payload: dict[str, Any], provider: str) -> tuple[bytes, str, dict[str, str]]:
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
        with urllib.request.urlopen(request, timeout=240) as response:
            audio = response.read()
            headers = {key.lower(): value for key, value in response.headers.items()}
            return audio, provider, headers
    except urllib.error.HTTPError as error:
        detail = error.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"HTTP {error.code}: {detail[:500]}") from error


def audio_prompt(item: dict[str, Any]) -> str:
    if item["assetType"] == "theme_music_brief":
        return (
            "Instrumental nautical pirate game show theme, 20 seconds. "
            "Fast hornpipe or jig, fiddle and concertina lead, stomping percussion, "
            "rope creaks, tiny cannon thump, big final logo hit. "
            "Funny, energetic, suitable for a YouTube challenge show. No vocals."
        )
    if item.get("audioBrief"):
        return str(item["audioBrief"])
    return (
        f"{item['title']}. Short polished logo sting. "
        f"{item.get('visualBrief', '')} {item.get('productionNotes', '')}"
    ).strip()


def parse_duration(value: str) -> float:
    match = re.search(r"([0-9]+(?:\.[0-9]+)?)", value)
    if not match:
        return 4.0
    return max(0.5, min(30.0, float(match.group(1))))


def local_audio_mp3(item: dict[str, Any], duration: float) -> bytes:
    with tempfile.TemporaryDirectory() as tmp:
        wav_path = Path(tmp) / "fallback.wav"
        mp3_path = Path(tmp) / "fallback.mp3"
        if item["assetType"] == "theme_music_brief":
            write_hornpipe_wav(wav_path, duration)
        else:
            write_sting_wav(wav_path, duration, item["id"])
        subprocess.run(
            [
                "ffmpeg",
                "-y",
                "-hide_banner",
                "-loglevel",
                "error",
                "-i",
                str(wav_path),
                "-codec:a",
                "libmp3lame",
                "-b:a",
                "128k",
                str(mp3_path),
            ],
            check=True,
        )
        return mp3_path.read_bytes()


def write_hornpipe_wav(path: Path, duration: float) -> None:
    melody = [
        ("D5", 0.16),
        ("F#5", 0.16),
        ("A5", 0.16),
        ("D6", 0.24),
        ("B5", 0.16),
        ("A5", 0.16),
        ("F#5", 0.16),
        ("E5", 0.24),
        ("D5", 0.16),
        ("E5", 0.16),
        ("F#5", 0.16),
        ("A5", 0.24),
        ("G5", 0.16),
        ("F#5", 0.16),
        ("E5", 0.16),
        ("D5", 0.32),
    ]
    samples = [0.0] * int(duration * SAMPLE_RATE)
    cursor = 0.0
    while cursor < duration:
        for note, length in melody:
            if cursor >= duration:
                break
            add_pluck(samples, cursor, min(length, duration - cursor), note_freq(note), 0.34)
            cursor += length
        cursor += 0.02
    for beat in frange(0, duration, 0.48):
        add_thump(samples, beat, 0.06, 0.35)
    if duration > 1.2:
        add_noise_burst(samples, duration - 0.9, 0.18, 0.28)
        add_tone(samples, duration - 0.35, 0.32, note_freq("D4"), 0.28)
    write_wav(path, samples)


def write_sting_wav(path: Path, duration: float, seed_text: str) -> None:
    rnd = random.Random(seed_text)
    samples = [0.0] * int(duration * SAMPLE_RATE)
    notes = ["D5", "F#5", "A5", "B5", "D6", "E6"]
    for i, start in enumerate(frange(0.05, min(duration, 1.5), 0.18)):
        add_pluck(samples, start, 0.14, note_freq(notes[(i + rnd.randrange(3)) % len(notes)]), 0.28)
    if "splash" in seed_text or "water" in seed_text or "wave" in seed_text:
        add_noise_burst(samples, max(0.1, duration * 0.58), 0.35, 0.42)
    if "flash" in seed_text or "glint" in seed_text or "scan" in seed_text:
        add_glint(samples, duration * 0.62, 0.32)
    if "cannon" in seed_text or "pirate" in seed_text or "jury" in seed_text:
        add_thump(samples, duration * 0.72, 0.14, 0.6)
    add_tone(samples, max(0.0, duration - 0.32), min(0.3, duration), note_freq("D4"), 0.24)
    write_wav(path, samples)


def write_wav(path: Path, samples: list[float]) -> None:
    peak = max(0.01, max(abs(sample) for sample in samples))
    scale = min(1.0, 0.92 / peak)
    with wave.open(str(path), "wb") as handle:
        handle.setnchannels(1)
        handle.setsampwidth(2)
        handle.setframerate(SAMPLE_RATE)
        for sample in samples:
            value = int(max(-1.0, min(1.0, sample * scale)) * 32767)
            handle.writeframes(struct.pack("<h", value))


def add_tone(samples: list[float], start: float, duration: float, freq: float, amp: float) -> None:
    start_i = max(0, int(start * SAMPLE_RATE))
    end_i = min(len(samples), int((start + duration) * SAMPLE_RATE))
    length = max(1, end_i - start_i)
    for i in range(start_i, end_i):
        t = (i - start_i) / SAMPLE_RATE
        envelope = min(1.0, (i - start_i) / max(1, length * 0.08)) * max(0.0, 1 - (i - start_i) / length)
        samples[i] += math.sin(2 * math.pi * freq * t) * amp * envelope


def add_pluck(samples: list[float], start: float, duration: float, freq: float, amp: float) -> None:
    start_i = max(0, int(start * SAMPLE_RATE))
    end_i = min(len(samples), int((start + duration) * SAMPLE_RATE))
    for i in range(start_i, end_i):
        t = (i - start_i) / SAMPLE_RATE
        envelope = math.exp(-8.0 * t / max(0.03, duration))
        tone = math.sin(2 * math.pi * freq * t) + 0.35 * math.sin(2 * math.pi * freq * 2 * t)
        samples[i] += tone * amp * envelope


def add_thump(samples: list[float], start: float, duration: float, amp: float) -> None:
    start_i = max(0, int(start * SAMPLE_RATE))
    end_i = min(len(samples), int((start + duration) * SAMPLE_RATE))
    for i in range(start_i, end_i):
        t = (i - start_i) / SAMPLE_RATE
        freq = 70 - 35 * min(1.0, t / max(0.01, duration))
        envelope = math.exp(-9.0 * t / max(0.03, duration))
        samples[i] += math.sin(2 * math.pi * freq * t) * amp * envelope


def add_noise_burst(samples: list[float], start: float, duration: float, amp: float) -> None:
    rnd = random.Random(int(start * 1000) + len(samples))
    start_i = max(0, int(start * SAMPLE_RATE))
    end_i = min(len(samples), int((start + duration) * SAMPLE_RATE))
    length = max(1, end_i - start_i)
    for i in range(start_i, end_i):
        position = (i - start_i) / length
        envelope = math.sin(math.pi * position) * (1 - position * 0.4)
        samples[i] += rnd.uniform(-1, 1) * amp * envelope


def add_glint(samples: list[float], start: float, duration: float) -> None:
    add_tone(samples, start, duration * 0.6, note_freq("D7"), 0.16)
    add_tone(samples, start + duration * 0.12, duration * 0.5, note_freq("A7"), 0.12)


def note_freq(note: str) -> float:
    names = {"C": -9, "C#": -8, "D": -7, "D#": -6, "E": -5, "F": -4, "F#": -3, "G": -2, "G#": -1, "A": 0, "A#": 1, "B": 2}
    match = re.fullmatch(r"([A-G]#?)([0-8])", note)
    if not match:
        return 440.0
    name, octave = match.groups()
    semitones = names[name] + (int(octave) - 4) * 12
    return 440.0 * (2 ** (semitones / 12))


def frange(start: float, stop: float, step: float):
    value = start
    while value < stop:
        yield value
        value += step


def render_logo_video(item: dict[str, Any], duration: float, audio_path: Path, out_path: Path) -> None:
    with tempfile.TemporaryDirectory() as tmp:
        frame_dir = Path(tmp) / "frames"
        frame_dir.mkdir()
        frame_count = max(1, int(duration * FPS))
        for frame in range(frame_count):
            progress = frame / max(1, frame_count - 1)
            image = render_frame(item, progress, frame, frame_count)
            image.save(frame_dir / f"{frame:05d}.png")
        subprocess.run(
            [
                "ffmpeg",
                "-y",
                "-hide_banner",
                "-loglevel",
                "error",
                "-framerate",
                str(FPS),
                "-i",
                str(frame_dir / "%05d.png"),
                "-i",
                str(audio_path),
                "-filter_complex",
                "[1:a]apad[a]",
                "-map",
                "0:v:0",
                "-map",
                "[a]",
                "-t",
                f"{duration:.2f}",
                "-c:v",
                "libx264",
                "-pix_fmt",
                "yuv420p",
                "-c:a",
                "aac",
                "-b:a",
                "128k",
                str(out_path),
            ],
            check=True,
        )


def render_frame(item: dict[str, Any], p: float, frame: int, frame_count: int) -> Image.Image:
    width, height = VIDEO_SIZE
    project = item["project"]
    asset_id = item["id"]
    palette = palette_for(project)
    img = Image.new("RGB", VIDEO_SIZE, palette["bg"])
    draw = ImageDraw.Draw(img)
    draw_background(draw, palette, p)
    title = title_text(item)

    if "downwind-video-logo-breaking-wave" == asset_id:
        draw_wave(draw, p, palette)
    elif "downwind-video-logo-stickman-crash" == asset_id:
        draw_stick_crash(draw, p, palette)
    elif "downwind-video-logo-spin-flash" == asset_id:
        draw_spin_flash(draw, p, title, palette)
        return img
    elif "jury-rigged-video-logo-pirate-flag" == asset_id:
        draw_flag(draw, p, palette)
    elif "jury-rigged-video-logo-rope-knot" == asset_id:
        draw_rope(draw, p, palette)
    elif "jury-rigged-video-logo-plank-splash" == asset_id:
        draw_plank_splash(draw, p, palette)
    elif "fieldrelay-video-logo-tricorder-scan" == asset_id:
        draw_scan(draw, p, palette)
    elif "fieldrelay-video-logo-boot-compass" == asset_id:
        draw_boot_compass(draw, p, palette)
    elif "fieldrelay-video-logo-radio-packet" == asset_id:
        draw_radio_packet(draw, p, palette)
    elif "jobdone-video-logo-job-card" == asset_id:
        draw_job_card(draw, p, palette)
    elif "jobdone-video-logo-van-door" == asset_id:
        draw_van_door(draw, p, palette)
    elif "jobdone-video-logo-timeline" == asset_id:
        draw_timeline(draw, p, palette)
    elif "continuum-video-logo-thread" == asset_id:
        draw_thread(draw, p, palette)
    elif "continuum-video-logo-context-snap" == asset_id:
        draw_context_snap(draw, p, palette)
    elif "continuum-video-logo-second-bootstrap" == asset_id:
        draw_bootstrap(draw, p, palette)
    elif "adlib-video-logo-docs-waveform" == asset_id:
        draw_docs_waveform(draw, p, palette)
    elif "adlib-video-logo-mic-stamp" == asset_id:
        draw_mic_stamp(draw, p, palette)
    elif "adlib-video-logo-script-to-speaker" == asset_id:
        draw_script_speaker(draw, p, palette)
    elif "school-video-logo-workbench-sparks" == asset_id:
        draw_workbench_sparks(draw, p, palette)
    elif "school-video-logo-agent-classroom" == asset_id:
        draw_agent_classroom(draw, p, palette)
    elif "school-video-logo-build-test-sell" == asset_id:
        draw_build_test_sell(draw, p, palette)
    elif "living-water-video-logo-ripple-map" == asset_id:
        draw_ripple_map(draw, p, palette)
    elif "living-water-video-logo-stone-flow" == asset_id:
        draw_stone_flow(draw, p, palette)
    elif "living-water-video-logo-field-notebook" == asset_id:
        draw_field_notebook(draw, p, palette)
    else:
        draw_generic_logo(draw, p, palette)

    draw_wordmark(draw, title, p, palette)
    return img


def draw_background(draw: ImageDraw.ImageDraw, palette: dict[str, Any], p: float) -> None:
    width, height = VIDEO_SIZE
    for y in range(height):
        mix = y / height
        color = blend(palette["bg"], palette["bg2"], mix * 0.65)
        draw.line([(0, y), (width, y)], fill=color)
    for i in range(9):
        x = int((i * 137 + p * 90) % (width + 80) - 40)
        y = int(height * (0.18 + (i % 4) * 0.18))
        draw.line([(x, y), (x + 90, y - 24)], fill=palette["line"], width=1)


def draw_wordmark(draw: ImageDraw.ImageDraw, text: str, p: float, palette: dict[str, Any]) -> None:
    width, height = VIDEO_SIZE
    font = font_for(64)
    sub_font = font_for(20)
    opacity_p = smoothstep(0.35, 0.82, p)
    y = int(height * 0.68 - 20 * (1 - opacity_p))
    bbox = draw.textbbox((0, 0), text, font=font)
    x = (width - (bbox[2] - bbox[0])) // 2
    draw.text((x + 3, y + 3), text, font=font, fill=palette["shadow"])
    draw.text((x, y), text, font=font, fill=palette["ink"])
    underline = int((width * 0.46) * opacity_p)
    draw.rounded_rectangle(
        [width // 2 - underline // 2, y + 82, width // 2 + underline // 2, y + 90],
        radius=4,
        fill=palette["accent"],
    )
    if p > 0.78:
        sparkle_x = width // 2 + int((p - 0.78) / 0.22 * width * 0.26)
        draw.line([(sparkle_x - 16, y + 28), (sparkle_x + 16, y - 4)], fill=palette["light"], width=3)
        draw.line([(sparkle_x - 10, y - 6), (sparkle_x + 10, y + 26)], fill=palette["light"], width=2)
    domain = domain_for(text)
    box = draw.textbbox((0, 0), domain, font=sub_font)
    draw.text(((width - (box[2] - box[0])) // 2, y + 102), domain, font=sub_font, fill=palette["muted"])


def draw_generic_logo(draw: ImageDraw.ImageDraw, p: float, palette: dict[str, Any]) -> None:
    width, height = VIDEO_SIZE
    r = int(60 + 40 * smoothstep(0, 1, p))
    cx, cy = width // 2, int(height * 0.38)
    draw.ellipse([cx - r, cy - r, cx + r, cy + r], outline=palette["accent"], width=8)
    draw.line([(cx - r, cy), (cx + r, cy)], fill=palette["light"], width=4)


def draw_wave(draw: ImageDraw.ImageDraw, p: float, palette: dict[str, Any]) -> None:
    width, height = VIDEO_SIZE
    crest = int(width * (p * 1.35 - 0.18))
    points = []
    for x in range(-20, width + 40, 20):
        y = int(height * 0.48 + math.sin((x + p * 260) / 70) * 34)
        if x < crest:
            points.append((x, y))
    if points:
        poly = [(0, height), *points, (crest + 90, height)]
        draw.polygon(poly, fill=palette["accent2"])
    for i in range(18):
        x = crest - i * 24
        y = int(height * 0.45 + math.sin(i) * 30)
        if 0 < x < width:
            draw.ellipse([x, y, x + 8, y + 8], fill=palette["light"])
    draw_hud(draw, p, palette)


def draw_spin_flash(draw: ImageDraw.ImageDraw, p: float, title: str, palette: dict[str, Any]) -> None:
    width, height = VIDEO_SIZE
    cx, cy = width // 2, int(height * 0.42)
    angle = p * math.tau * 1.3
    rx = int(180 * abs(math.cos(angle)) + 24)
    ry = 32
    draw.ellipse([cx - rx, cy - ry, cx + rx, cy + ry], fill=palette["accent"], outline=palette["light"], width=5)
    draw.line([(cx - rx, cy), (cx + rx, cy)], fill=palette["ink"], width=3)
    if p > 0.68:
        flash = smoothstep(0.68, 0.82, p) * (1 - smoothstep(0.86, 1, p))
        x = cx + rx - 20
        draw.line([(x - 80, cy + 60), (x + 80, cy - 60)], fill=palette["light"], width=max(1, int(14 * flash)))
    draw_wordmark(draw, title, p, palette)


def draw_stick_crash(draw: ImageDraw.ImageDraw, p: float, palette: dict[str, Any]) -> None:
    width, height = VIDEO_SIZE
    water_y = int(height * 0.56)
    draw.rectangle([0, water_y, width, height], fill=palette["accent2"])
    x = int(width * (0.16 + 0.52 * min(p, 0.75)))
    y = int(water_y - 80 + math.sin(p * math.tau * 2) * 25)
    if p < 0.68:
        draw.line([(x - 50, y + 55), (x + 80, y + 70)], fill=palette["ink"], width=5)
        draw.ellipse([x - 8, y - 8, x + 8, y + 8], fill=palette["ink"])
        draw.line([(x, y + 8), (x, y + 48)], fill=palette["ink"], width=4)
        draw.line([(x, y + 24), (x + 34, y + 8)], fill=palette["ink"], width=4)
        draw.line([(x + 34, y + 8), (x + 54, y - 26)], fill=palette["accent"], width=5)
        draw.arc([x + 38, y - 70, x + 140, y + 20], 230, 70, fill=palette["light"], width=5)
    else:
        splash_x = int(width * 0.58)
        for i in range(20):
            a = i / 20 * math.tau
            r = int(12 + 95 * smoothstep(0.68, 1, p))
            draw.ellipse([splash_x + math.cos(a) * r, water_y + math.sin(a) * r * 0.35, splash_x + math.cos(a) * r + 8, water_y + math.sin(a) * r * 0.35 + 8], fill=palette["light"])


def draw_flag(draw: ImageDraw.ImageDraw, p: float, palette: dict[str, Any]) -> None:
    width, height = VIDEO_SIZE
    unfurl = smoothstep(0.05, 0.8, p)
    pole_x = int(width * 0.28)
    draw.line([(pole_x, 120), (pole_x, 350)], fill=palette["ink"], width=8)
    flag_w = int(330 * unfurl)
    flag = [pole_x, 135, pole_x + flag_w, 275]
    draw.rectangle(flag, fill=palette["accent"], outline=palette["ink"], width=4)
    cx, cy = pole_x + flag_w // 2, 205
    if flag_w > 100:
        draw.ellipse([cx - 32, cy - 28, cx + 32, cy + 28], outline=palette["light"], width=5)
        draw.line([(cx - 62, cy + 48), (cx + 62, cy - 48)], fill=palette["light"], width=5)
        draw.line([(cx - 62, cy - 48), (cx + 62, cy + 48)], fill=palette["light"], width=5)


def draw_rope(draw: ImageDraw.ImageDraw, p: float, palette: dict[str, Any]) -> None:
    width, height = VIDEO_SIZE
    points = []
    for i in range(80):
        x = int(width * i / 79)
        y = int(height * 0.38 + math.sin(i / 6 + p * 8) * 46)
        points.append((x, y))
    draw.line(points, fill=palette["accent2"], width=14)
    knot = smoothstep(0.45, 1, p)
    cx, cy = width // 2, int(height * 0.38)
    r = int(20 + 80 * knot)
    draw.ellipse([cx - r, cy - r // 2, cx + r, cy + r // 2], outline=palette["light"], width=10)


def draw_plank_splash(draw: ImageDraw.ImageDraw, p: float, palette: dict[str, Any]) -> None:
    width, height = VIDEO_SIZE
    water = int(height * 0.62)
    draw.rectangle([0, water, width, height], fill=palette["accent2"])
    angle = -35 + 80 * smoothstep(0.1, 0.68, p)
    cx, cy = width // 2, int(height * 0.35)
    draw_rotated_rect(draw, cx, cy, 390, 42, angle, palette["accent"], palette["ink"])
    if p > 0.62:
        for i in range(18):
            a = i / 18 * math.tau
            r = int(40 + 160 * smoothstep(0.62, 1, p))
            x = cx + math.cos(a) * r
            y = water + math.sin(a) * r * 0.25
            draw.ellipse([x, y, x + 10, y + 10], fill=palette["light"])


def draw_scan(draw: ImageDraw.ImageDraw, p: float, palette: dict[str, Any]) -> None:
    width, height = VIDEO_SIZE
    icons = [(260, 210, "mud"), (410, 190, "rope"), (550, 215, "phone"), (690, 190, "note")]
    for x, y, label in icons:
        draw.rounded_rectangle([x - 40, y - 32, x + 40, y + 32], radius=10, outline=palette["line"], width=3)
        draw.text((x - 24, y - 10), label[:4], font=font_for(15), fill=palette["muted"])
    sx = int(width * p)
    draw.rectangle([sx - 5, 90, sx + 5, 340], fill=palette["light"])
    draw.rectangle([max(0, sx - 80), 90, sx, 340], fill=palette["line"])


def draw_boot_compass(draw: ImageDraw.ImageDraw, p: float, palette: dict[str, Any]) -> None:
    width, height = VIDEO_SIZE
    cx, cy = width // 2, int(height * 0.38)
    step = smoothstep(0, 0.38, p)
    draw.ellipse([cx - 130, cy - 44 + int((1 - step) * 180), cx + 130, cy + 44 + int((1 - step) * 180)], fill=palette["accent2"], outline=palette["ink"], width=4)
    compass = smoothstep(0.38, 1, p)
    r = int(40 + 120 * compass)
    draw.ellipse([cx - r, cy - r, cx + r, cy + r], outline=palette["light"], width=5)
    draw.polygon([(cx, cy - r + 15), (cx - 18, cy + 12), (cx + 18, cy + 12)], fill=palette["accent"])


def draw_radio_packet(draw: ImageDraw.ImageDraw, p: float, palette: dict[str, Any]) -> None:
    width, height = VIDEO_SIZE
    start = (180, 230)
    end = (760, 230)
    draw.rounded_rectangle([110, 180, 250, 280], radius=18, outline=palette["line"], width=4)
    draw.rounded_rectangle([690, 170, 830, 290], radius=18, outline=palette["line"], width=4)
    draw.text((134, 220), "say", font=font_for(28), fill=palette["ink"])
    draw.text((715, 220), "agent", font=font_for(25), fill=palette["ink"])
    px = int(start[0] + (end[0] - start[0]) * smoothstep(0.12, 0.85, p))
    draw.rounded_rectangle([px - 35, 205, px + 35, 255], radius=10, fill=palette["accent"])
    for i in range(4):
        x = int(start[0] + (px - start[0]) * i / 4)
        draw.ellipse([x, 227, x + 6, 233], fill=palette["light"])


def draw_job_card(draw: ImageDraw.ImageDraw, p: float, palette: dict[str, Any]) -> None:
    width, height = VIDEO_SIZE
    cards = [(-170, "CALL"), (0, "PHOTO"), (170, "QUOTE")]
    settle = smoothstep(0.1, 0.65, p)
    for offset, label in cards:
        x = int(width // 2 + offset * (1 - settle))
        y = int(170 + abs(offset) * 0.15 * (1 - settle))
        draw.rounded_rectangle([x - 115, y - 50, x + 115, y + 50], radius=10, fill=palette["panel"], outline=palette["line"], width=3)
        draw.text((x - 58, y - 13), label, font=font_for(28), fill=palette["ink"])
    if p > 0.62:
        draw.text((width // 2 - 70, 300), "DONE", font=font_for(54), fill=palette["accent"])


def draw_van_door(draw: ImageDraw.ImageDraw, p: float, palette: dict[str, Any]) -> None:
    width, height = VIDEO_SIZE
    door = int(260 * (1 - smoothstep(0.05, 0.55, p)))
    draw.rounded_rectangle([250 - door, 130, 710, 320], radius=18, fill=palette["panel"], outline=palette["ink"], width=5)
    draw.line([(480, 130), (480, 320)], fill=palette["line"], width=4)
    draw.ellipse([650, 260, 700, 310], fill=palette["accent"])
    if p > 0.55:
        draw.line([(420, 230), (466, 278), (550, 170)], fill=palette["light"], width=10)


def draw_timeline(draw: ImageDraw.ImageDraw, p: float, palette: dict[str, Any]) -> None:
    width, height = VIDEO_SIZE
    start_x, end_x, y = 180, 780, 250
    draw.line([(start_x, y), (end_x, y)], fill=palette["line"], width=5)
    labels = ["call", "visit", "quote", "photo", "done"]
    for i, label in enumerate(labels):
        x = int(start_x + (end_x - start_x) * i / (len(labels) - 1))
        visible = p > i * 0.14
        fill = palette["accent"] if visible else palette["line"]
        draw.ellipse([x - 18, y - 18, x + 18, y + 18], fill=fill)
        draw.text((x - 28, y + 34), label, font=font_for(18), fill=palette["ink"])


def draw_thread(draw: ImageDraw.ImageDraw, p: float, palette: dict[str, Any]) -> None:
    width, height = VIDEO_SIZE
    cx, cy = width // 2, 230
    points = []
    for i in range(9):
        a = i / 9 * math.tau + p * 2.5
        r = 160 * (1 - smoothstep(0.45, 0.95, p)) + 52
        x = int(cx + math.cos(a) * r)
        y = int(cy + math.sin(a) * r * 0.62)
        points.append((x, y))
        draw.rounded_rectangle([x - 34, y - 18, x + 34, y + 18], radius=8, fill=palette["panel"], outline=palette["line"], width=2)
    draw.line(points + [points[0]], fill=palette["accent"], width=4)


def draw_context_snap(draw: ImageDraw.ImageDraw, p: float, palette: dict[str, Any]) -> None:
    width, height = VIDEO_SIZE
    labels = ["capture", "context", "agent", "next", "decision"]
    for i, label in enumerate(labels):
        start_x = 130 + i * 160
        x = int(start_x + (width // 2 - start_x) * smoothstep(0.35, 0.75, p))
        y = int(180 + math.sin(i) * 60 * (1 - smoothstep(0.35, 0.75, p)))
        draw.text((x - 45, y), label, font=font_for(22), fill=palette["ink"])
    draw.line([(250, 290), (710, 290)], fill=palette["accent"], width=int(2 + 8 * smoothstep(0.6, 1, p)))


def draw_bootstrap(draw: ImageDraw.ImageDraw, p: float, palette: dict[str, Any]) -> None:
    width, height = VIDEO_SIZE
    left = [130, 155, 350, 305]
    right = [610, 155, 830, 305]
    draw.rounded_rectangle(left, radius=16, fill=palette["panel"], outline=palette["line"], width=3)
    draw.rounded_rectangle(right, radius=16, fill=palette["panel"], outline=palette["line"], width=3)
    draw.text((170, 215), "private", font=font_for(26), fill=palette["ink"])
    draw.text((660, 215), "yours", font=font_for(30), fill=palette["ink"])
    sx = int(350 + (610 - 350) * smoothstep(0.25, 0.75, p))
    draw.ellipse([sx - 18, 225, sx + 18, 261], fill=palette["accent"])


def draw_docs_waveform(draw: ImageDraw.ImageDraw, p: float, palette: dict[str, Any]) -> None:
    width, height = VIDEO_SIZE
    for i in range(3):
        x = int(220 + i * 50 + 120 * smoothstep(0.3, 0.8, p))
        y = 140 + i * 18
        draw.rounded_rectangle([x, y, x + 160, y + 210], radius=8, fill=palette["panel"], outline=palette["line"], width=3)
        for j in range(5):
            draw.line([(x + 25, y + 40 + j * 28), (x + 135, y + 40 + j * 28)], fill=palette["line"], width=3)
    for i in range(18):
        x = 480 + i * 18
        amp = int(50 * math.sin(i * 0.8 + p * 5))
        draw.line([(x, 250 - amp), (x, 250 + amp)], fill=palette["accent"], width=5)


def draw_mic_stamp(draw: ImageDraw.ImageDraw, p: float, palette: dict[str, Any]) -> None:
    width, height = VIDEO_SIZE
    page = [310, 135, 650, 330]
    draw.rounded_rectangle(page, radius=12, fill=palette["panel"], outline=palette["line"], width=4)
    y = int(80 + 110 * smoothstep(0.05, 0.48, p))
    draw.rounded_rectangle([430, y, 530, y + 110], radius=45, outline=palette["accent"], width=9)
    draw.line([(480, y + 110), (480, y + 165)], fill=palette["accent"], width=7)
    if p > 0.5:
        draw.text((390, 235), "ADLIB", font=font_for(50), fill=palette["accent"])


def draw_script_speaker(draw: ImageDraw.ImageDraw, p: float, palette: dict[str, Any]) -> None:
    width, height = VIDEO_SIZE
    for i in range(6):
        x1 = int(170 + i * 18 + 270 * smoothstep(0.25, 0.72, p))
        draw.line([(x1, 170 + i * 24), (x1 + 160, 170 + i * 24)], fill=palette["line"], width=4)
    speaker = [610, 190, 710, 290]
    draw.rectangle(speaker, outline=palette["accent"], width=6)
    draw.polygon([(610, 220), (560, 245), (610, 270)], fill=palette["accent"])
    radius = int(20 + 70 * smoothstep(0.55, 1, p))
    draw.arc([660 - radius, 240 - radius, 660 + radius, 240 + radius], -45, 45, fill=palette["light"], width=5)


def draw_workbench_sparks(draw: ImageDraw.ImageDraw, p: float, palette: dict[str, Any]) -> None:
    width, height = VIDEO_SIZE
    labels = ["note", "prompt", "code", "ad"]
    for i, label in enumerate(labels):
        x = 210 + i * 140
        y = int(155 + 40 * math.sin(i + p * 3))
        draw.rounded_rectangle([x - 52, y - 34, x + 52, y + 34], radius=9, fill=palette["panel"], outline=palette["line"], width=3)
        draw.text((x - 34, y - 12), label, font=font_for(22), fill=palette["ink"])
        if p > 0.35:
            draw.line([(x, y + 34), (width // 2, 300)], fill=palette["accent"], width=3)
    for i in range(10):
        a = i * 0.63 + p * 6
        draw.line([(480, 300), (480 + math.cos(a) * 55, 300 + math.sin(a) * 35)], fill=palette["light"], width=2)


def draw_agent_classroom(draw: ImageDraw.ImageDraw, p: float, palette: dict[str, Any]) -> None:
    width, height = VIDEO_SIZE
    draw.rounded_rectangle([260, 120, 700, 230], radius=12, outline=palette["line"], width=4)
    draw.text((385, 158), "loop", font=font_for(42), fill=palette["accent"])
    for row in range(2):
        for col in range(4):
            x = 250 + col * 150
            y = 285 + row * 55
            draw.rounded_rectangle([x, y, x + 80, y + 35], radius=8, fill=palette["panel"], outline=palette["line"], width=2)
    teacher_x = int(120 + 250 * smoothstep(0.1, 0.7, p))
    draw.ellipse([teacher_x, 240, teacher_x + 42, 282], fill=palette["accent"])


def draw_build_test_sell(draw: ImageDraw.ImageDraw, p: float, palette: dict[str, Any]) -> None:
    width, height = VIDEO_SIZE
    labels = ["Build", "Test", "Sell"]
    for i, label in enumerate(labels):
        local = smoothstep(i * 0.18, i * 0.18 + 0.35, p)
        x = 250 + i * 160
        y = int(220 - 70 * (1 - local))
        draw.rounded_rectangle([x - 68, y - 48, x + 68, y + 48], radius=12, fill=palette["panel"], outline=palette["accent"], width=4)
        draw.text((x - 45, y - 14), label, font=font_for(28), fill=palette["ink"])


def draw_ripple_map(draw: ImageDraw.ImageDraw, p: float, palette: dict[str, Any]) -> None:
    width, height = VIDEO_SIZE
    for i in range(6):
        y = 125 + i * 38
        draw.arc([180, y, 760, y + 120], 190, 350, fill=palette["line"], width=2)
    cx, cy = width // 2, 230
    r = int(20 + 190 * smoothstep(0.12, 1, p))
    draw.ellipse([cx - r, cy - r * 0.55, cx + r, cy + r * 0.55], outline=palette["accent"], width=5)
    draw.ellipse([cx - 8, cy - 8, cx + 8, cy + 8], fill=palette["light"])


def draw_stone_flow(draw: ImageDraw.ImageDraw, p: float, palette: dict[str, Any]) -> None:
    width, height = VIDEO_SIZE
    for i in range(3):
        y = 180 + i * 38
        points = [(x, int(y + math.sin(x / 70 + p * 4) * 14)) for x in range(120, 840, 30)]
        draw.line(points, fill=palette["accent2"], width=8)
    count = int(8 * smoothstep(0.15, 0.75, p))
    for i in range(count):
        x = 360 + (i % 4) * 55
        y = 210 + (i // 4) * 45
        draw.ellipse([x - 18, y - 13, x + 18, y + 13], fill=palette["accent"], outline=palette["ink"], width=2)


def draw_field_notebook(draw: ImageDraw.ImageDraw, p: float, palette: dict[str, Any]) -> None:
    width, height = VIDEO_SIZE
    open_p = smoothstep(0.08, 0.55, p)
    left = [250 - int(90 * open_p), 125, 480, 330]
    right = [480, 125, 710 + int(90 * open_p), 330]
    draw.rounded_rectangle(left, radius=10, fill=palette["panel"], outline=palette["line"], width=3)
    draw.rounded_rectangle(right, radius=10, fill=palette["panel"], outline=palette["line"], width=3)
    draw.line([(480, 125), (480, 330)], fill=palette["line"], width=5)
    draw.arc([360, 190, 620, 310], 190, 345, fill=palette["accent2"], width=4)
    draw.text((525, 205), "pond", font=font_for(34), fill=palette["accent"])


def draw_hud(draw: ImageDraw.ImageDraw, p: float, palette: dict[str, Any]) -> None:
    font = font_for(20)
    draw.text((650, 115), f"{18 + int(p * 7)} kt", font=font, fill=palette["light"])
    draw.text((650, 145), f"{12 + int(p * 12)} km", font=font, fill=palette["light"])
    draw.line([(640, 178), (810, 178)], fill=palette["line"], width=2)


def draw_rotated_rect(
    draw: ImageDraw.ImageDraw,
    cx: int,
    cy: int,
    w: int,
    h: int,
    angle_degrees: float,
    fill: tuple[int, int, int],
    outline: tuple[int, int, int],
) -> None:
    angle = math.radians(angle_degrees)
    corners = []
    for x, y in [(-w / 2, -h / 2), (w / 2, -h / 2), (w / 2, h / 2), (-w / 2, h / 2)]:
        rx = cx + x * math.cos(angle) - y * math.sin(angle)
        ry = cy + x * math.sin(angle) + y * math.cos(angle)
        corners.append((rx, ry))
    draw.polygon(corners, fill=fill, outline=outline)


def palette_for(project: str) -> dict[str, Any]:
    palettes = {
        "AdLib": {"bg": (246, 247, 242), "bg2": (224, 235, 231), "panel": (255, 255, 255), "ink": (22, 32, 31), "muted": (91, 105, 102), "line": (197, 210, 203), "accent": (15, 118, 110), "accent2": (62, 146, 204), "light": (255, 248, 190), "shadow": (204, 214, 208)},
        "Continuum Kit": {"bg": (242, 246, 247), "bg2": (225, 230, 242), "panel": (255, 255, 255), "ink": (26, 31, 45), "muted": (91, 99, 116), "line": (198, 207, 218), "accent": (41, 96, 176), "accent2": (15, 118, 110), "light": (255, 230, 130), "shadow": (199, 206, 218)},
        "Field Relay": {"bg": (242, 246, 238), "bg2": (220, 235, 224), "panel": (255, 255, 250), "ink": (26, 43, 31), "muted": (91, 108, 95), "line": (194, 211, 191), "accent": (66, 120, 70), "accent2": (72, 136, 160), "light": (247, 221, 115), "shadow": (203, 217, 201)},
        "JobDone": {"bg": (247, 246, 240), "bg2": (231, 235, 223), "panel": (255, 255, 255), "ink": (39, 37, 31), "muted": (106, 101, 88), "line": (212, 207, 190), "accent": (183, 92, 38), "accent2": (42, 119, 91), "light": (255, 225, 130), "shadow": (216, 211, 197)},
        "Downwind": {"bg": (238, 247, 249), "bg2": (211, 231, 238), "panel": (255, 255, 255), "ink": (18, 38, 48), "muted": (84, 105, 113), "line": (190, 213, 221), "accent": (26, 116, 168), "accent2": (50, 169, 188), "light": (255, 244, 174), "shadow": (196, 214, 221)},
        "Jury Rigged": {"bg": (246, 243, 235), "bg2": (233, 224, 205), "panel": (255, 252, 242), "ink": (45, 33, 25), "muted": (111, 94, 78), "line": (216, 199, 172), "accent": (138, 54, 40), "accent2": (45, 98, 111), "light": (255, 225, 125), "shadow": (218, 205, 181)},
        "Entrepreneurs AI Developer School": {"bg": (246, 246, 244), "bg2": (229, 233, 238), "panel": (255, 255, 255), "ink": (26, 30, 34), "muted": (91, 98, 106), "line": (204, 210, 216), "accent": (58, 88, 168), "accent2": (203, 117, 39), "light": (255, 228, 120), "shadow": (207, 212, 218)},
        "Living Water / Checkdam": {"bg": (242, 247, 243), "bg2": (220, 235, 224), "panel": (255, 255, 250), "ink": (28, 44, 37), "muted": (87, 108, 97), "line": (196, 213, 202), "accent": (45, 110, 86), "accent2": (75, 151, 170), "light": (240, 223, 128), "shadow": (202, 216, 207)},
    }
    return palettes.get(project, palettes["AdLib"])


def title_text(item: dict[str, Any]) -> str:
    project = item["project"]
    if project == "Entrepreneurs AI Developer School":
        return "AI Developer School"
    if project == "Living Water / Checkdam":
        return "Checkdam"
    return project


def domain_for(title: str) -> str:
    domains = {
        "AdLib": "adlib.continuumkit.org",
        "Continuum Kit": "continuumkit.org",
        "Field Relay": "fieldrelay.continuumkit.org",
        "JobDone": "jobdone.continuumkit.org",
        "Downwind": "downwind.continuumkit.org",
        "Jury Rigged": "juryrigged.continuumkit.org",
        "AI Developer School": "school.continuumkit.org",
        "Checkdam": "checkdam.org",
    }
    return domains.get(title, "")


def font_for(size: int) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    candidates = [
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
    ]
    for path in candidates:
        if Path(path).exists():
            return ImageFont.truetype(path, size)
    return ImageFont.load_default()


def smoothstep(edge0: float, edge1: float, x: float) -> float:
    if edge0 == edge1:
        return 1.0 if x >= edge1 else 0.0
    t = max(0.0, min(1.0, (x - edge0) / (edge1 - edge0)))
    return t * t * (3 - 2 * t)


def blend(a: tuple[int, int, int], b: tuple[int, int, int], t: float) -> tuple[int, int, int]:
    return tuple(int(a[i] * (1 - t) + b[i] * t) for i in range(3))


def write_workbench(assets: list[MediaAsset]) -> None:
    media_dir = REPORT_DIR / "media"
    media_dir.mkdir(parents=True, exist_ok=True)
    public_assets: list[dict[str, Any]] = []
    for asset in assets:
        audio_url = None
        video_url = None
        if asset.audio_path and asset.audio_path.exists():
            target = media_dir / asset.audio_path.name
            shutil.copy2(asset.audio_path, target)
            audio_url = f"media/{target.name}"
        if asset.video_path and asset.video_path.exists():
            target = media_dir / asset.video_path.name
            shutil.copy2(asset.video_path, target)
            video_url = f"media/{target.name}"
        public_assets.append(
            {
                "assetId": asset.asset_id,
                "project": asset.project,
                "assetType": asset.asset_type,
                "title": asset.title,
                "durationSeconds": asset.duration_seconds,
                "audio": audio_url,
                "video": video_url,
                "brief": asset.brief,
                "audioBrief": asset.audio_brief,
                "visualBrief": asset.visual_brief,
            }
        )
    payload = {
        "campaign": CAMPAIGN,
        "generatedAt": datetime.now().astimezone().isoformat(timespec="seconds"),
        "assets": public_assets,
    }
    (REPORT_DIR / "assets.json").write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    (REPORT_DIR / "index.html").write_text(render_workbench(payload), encoding="utf-8")


def render_workbench(payload: dict[str, Any]) -> str:
    data = json.dumps(payload, ensure_ascii=True, separators=(",", ":"))
    return f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Continuum Media Assets</title>
  <style>
    :root {{
      color-scheme: light dark;
      font-family: Inter, ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
      --bg: #f6f7f2;
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
    main {{ width: min(1180px, calc(100vw - 24px)); margin: 0 auto; padding: 18px 0 54px; }}
    h1 {{ margin: 0; font-size: clamp(1.7rem, 3vw, 2.8rem); letter-spacing: 0; }}
    header {{ display: grid; gap: 8px; margin-bottom: 14px; }}
    .meta {{ color: var(--muted); line-height: 1.45; }}
    .toolbar {{ position: sticky; top: 0; z-index: 5; display: grid; grid-template-columns: 1fr minmax(160px, .35fr) minmax(160px, .35fr); gap: 8px; padding: 10px; border: 1px solid var(--line); border-radius: 8px; background: color-mix(in oklab, var(--bg) 92%, transparent); backdrop-filter: blur(10px); }}
    input, select {{ min-height: 40px; border: 1px solid var(--line); border-radius: 6px; background: var(--panel); color: var(--ink); font: inherit; padding: 0 10px; }}
    .grid {{ display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 12px; margin-top: 14px; }}
    .card {{ background: var(--panel); border: 1px solid var(--line); border-radius: 8px; padding: 12px; display: grid; gap: 10px; }}
    h2 {{ margin: 0; font-size: 1.08rem; letter-spacing: 0; }}
    .chips {{ display: flex; flex-wrap: wrap; gap: 6px; }}
    .chip {{ border: 1px solid var(--line); border-radius: 999px; padding: 2px 8px; color: var(--muted); font-size: .82rem; }}
    video, audio {{ width: 100%; }}
    video {{ aspect-ratio: 16 / 9; background: #111; border-radius: 6px; }}
    details {{ border-top: 1px solid var(--line); padding-top: 8px; }}
    summary {{ cursor: pointer; color: var(--muted); }}
    pre {{ white-space: pre-wrap; overflow-wrap: anywhere; margin: 8px 0 0; color: var(--muted); font-size: .9rem; }}
    @media (max-width: 860px) {{ .toolbar, .grid {{ grid-template-columns: 1fr; position: static; }} }}
  </style>
</head>
<body>
  <main>
    <header>
      <h1>Continuum Media Assets</h1>
      <div class="meta">Selected generated music, stings, and animated logo videos. Use these as first-pass assets, not final brand masters.</div>
      <div class="meta" id="count"></div>
    </header>
    <section class="toolbar">
      <input id="q" type="search" placeholder="search project, title, brief" autocomplete="off">
      <select id="project"><option value="">All projects</option></select>
      <select id="type"><option value="">All types</option></select>
    </section>
    <section id="list" class="grid"></section>
  </main>
  <script>
    const DATA = {data};
    const q = document.querySelector("#q");
    const project = document.querySelector("#project");
    const type = document.querySelector("#type");
    const list = document.querySelector("#list");
    const count = document.querySelector("#count");
    function esc(value) {{
      return String(value ?? "").replace(/[&<>"']/g, ch => ({{"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&#039;"}}[ch]));
    }}
    for (const value of [...new Set(DATA.assets.map(asset => asset.project))].sort()) {{
      const option = document.createElement("option");
      option.value = value;
      option.textContent = value;
      project.appendChild(option);
    }}
    for (const value of [...new Set(DATA.assets.map(asset => asset.assetType))].sort()) {{
      const option = document.createElement("option");
      option.value = value;
      option.textContent = value.replaceAll("_", " ");
      type.appendChild(option);
    }}
    function matches(asset) {{
      const needle = q.value.trim().toLowerCase();
      const hay = [asset.project, asset.assetType, asset.title, asset.brief, asset.audioBrief, asset.visualBrief].join(" ").toLowerCase();
      return (!needle || hay.includes(needle)) && (!project.value || asset.project === project.value) && (!type.value || asset.assetType === type.value);
    }}
    function render() {{
      const rows = DATA.assets.filter(matches);
      count.textContent = `${{rows.length}} visible, ${{DATA.assets.length}} total.`;
      list.innerHTML = rows.map(asset => `<article class="card">
        <div>
          <h2>${{esc(asset.title)}}</h2>
          <div class="meta">${{esc(asset.project)}} · ${{esc(asset.assetType.replaceAll("_", " "))}} · ${{esc(asset.durationSeconds)}}s</div>
        </div>
        <div class="chips"><span class="chip">${{esc(asset.project)}}</span><span class="chip">${{esc(asset.assetType.replaceAll("_", " "))}}</span></div>
        ${{asset.video ? `<video controls preload="metadata" src="${{esc(asset.video)}}"></video>` : ""}}
        ${{asset.audio ? `<audio controls preload="metadata" src="${{esc(asset.audio)}}"></audio>` : ""}}
        <details><summary>Brief</summary><pre>${{esc(asset.visualBrief || asset.audioBrief || asset.brief)}}</pre></details>
      </article>`).join("");
    }}
    q.addEventListener("input", render);
    project.addEventListener("change", render);
    type.addEventListener("change", render);
    render();
  </script>
</body>
</html>
"""


if __name__ == "__main__":
    raise SystemExit(main())
