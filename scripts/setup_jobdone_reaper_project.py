#!/usr/bin/env python3
"""Create the local REAPER project scaffold for the JobDone dog advert."""

from __future__ import annotations

import json
import shutil
import subprocess
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PLAN_PATH = ROOT / "docs" / "adverts" / "jobdone-dog-callback" / "asset-collection-v2.json"
OUT_DIR = ROOT / "local" / "audio-adverts" / "jobdone-dog-callback"
ASSET_DIR = OUT_DIR / "assets"
PROJECT_PATH = OUT_DIR / "jobdone-dog-callback.rpp"
OPEN_SCRIPT = OUT_DIR / "open-reaper.sh"


FOLDERS = (
    "voice/tradesperson",
    "voice/tradesperson/auditions",
    "voice/tradesperson/directed-v2",
    "voice/tradesperson/directed-v2/dog-emphasis",
    "voice/tradesperson/prompt-variants",
    "voice/tradesperson/selected",
    "voice/narrator",
    "voice/narrator/auditions",
    "voice/narrator/prompt-variants",
    "voice/app",
    "voice/app/auditions",
    "voice/app/prompt-variants",
    "sfx/beeps",
    "sfx/dog-barks",
    "sfx/doors",
    "sfx/doorbells",
    "sfx/footsteps",
    "sfx/kerfuffle",
    "renders",
    "reference",
)

KNOWN_AUDIO = (
    (
        ROOT / "data/raw/audio-ads/external-sfx/dog-bark/haulaway-630648-single-bark-small-to-medium-dog.mp3",
        "sfx/dog-barks/01-haulaway-small-to-medium-dog-bark.mp3",
    ),
    (
        ROOT / "data/raw/audio-ads/external-sfx/dog-bark/joviansounds-502655-single-dog-bark-king-charles-spaniel.mp3",
        "sfx/dog-barks/02-joviansounds-king-charles-single-bark.mp3",
    ),
    (
        ROOT / "data/raw/audio-ads/external-sfx/dog-bark/haulaway-630648-single-bark-small-to-medium-dog.mp3",
        "sfx/kerfuffle/01-dog-bark-for-kerfuffle-start.mp3",
    ),
    (
        ROOT / "data/processed/audio-ads/renders/jobdone-dog-callback-v0.wav",
        "renders/jobdone-dog-callback-v0-dummy-mix.wav",
    ),
    (
        ROOT / "data/raw/audio-ads/jobdone-dog-callback/elevenlabs/JD_ad02_dog_callback_v1_elevenlabs_dialogue_20260602T173045Z.mp3",
        "reference/one-shot-v1-rejected-too-long.mp3",
    ),
)


def main() -> int:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    ASSET_DIR.mkdir(parents=True, exist_ok=True)
    for folder in FOLDERS:
        (ASSET_DIR / folder).mkdir(parents=True, exist_ok=True)

    copied = copy_known_audio()
    generated = generate_placeholder_audio()
    write_voice_prompt_files()
    write_reaper_project()
    write_open_script()
    write_readme(copied, generated)

    print(f"project: {PROJECT_PATH}")
    print(f"assets:  {ASSET_DIR}")
    print(f"open:    {OPEN_SCRIPT}")
    return 0


def copy_known_audio() -> list[str]:
    copied: list[str] = []
    for source, relative_target in KNOWN_AUDIO:
        if not source.exists():
            continue
        target = ASSET_DIR / relative_target
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, target)
        copied.append(str(target.relative_to(OUT_DIR)))
    return copied


def generate_placeholder_audio() -> list[str]:
    if not shutil.which("ffmpeg"):
        return []

    generated: list[str] = []
    commands = (
        (
            ASSET_DIR / "sfx/beeps/record-start-friendly-beep.wav",
            [
                "ffmpeg",
                "-y",
                "-hide_banner",
                "-loglevel",
                "error",
                "-f",
                "lavfi",
                "-i",
                "sine=frequency=880:duration=0.12:sample_rate=44100",
                "-af",
                "afade=t=in:st=0:d=0.01,afade=t=out:st=0.10:d=0.02,volume=-8dB",
            ],
        ),
        (
            ASSET_DIR / "sfx/beeps/note-saved-friendly-beep.wav",
            [
                "ffmpeg",
                "-y",
                "-hide_banner",
                "-loglevel",
                "error",
                "-f",
                "lavfi",
                "-i",
                "sine=frequency=1320:duration=0.10:sample_rate=44100",
                "-af",
                "afade=t=in:st=0:d=0.01,afade=t=out:st=0.08:d=0.02,volume=-8dB",
            ],
        ),
        (
            ASSET_DIR / "sfx/beeps/result-found-clean-beep.wav",
            [
                "ffmpeg",
                "-y",
                "-hide_banner",
                "-loglevel",
                "error",
                "-f",
                "lavfi",
                "-i",
                "sine=frequency=1760:duration=0.09:sample_rate=44100",
                "-af",
                "afade=t=in:st=0:d=0.01,afade=t=out:st=0.07:d=0.02,volume=-9dB",
            ],
        ),
        (
            ASSET_DIR / "sfx/doorbells/simple-two-tone-doorbell.wav",
            [
                "ffmpeg",
                "-y",
                "-hide_banner",
                "-loglevel",
                "error",
                "-f",
                "lavfi",
                "-i",
                "sine=frequency=880:duration=0.22:sample_rate=44100",
                "-f",
                "lavfi",
                "-i",
                "sine=frequency=660:duration=0.30:sample_rate=44100",
                "-filter_complex",
                "[0:a][1:a]concat=n=2:v=0:a=1,volume=-10dB",
            ],
        ),
        (
            ASSET_DIR / "sfx/doors/placeholder-front-door-shut.wav",
            [
                "ffmpeg",
                "-y",
                "-hide_banner",
                "-loglevel",
                "error",
                "-f",
                "lavfi",
                "-i",
                "anoisesrc=color=brown:duration=0.18:sample_rate=44100",
                "-af",
                "lowpass=f=420,afade=t=out:st=0.11:d=0.07,volume=-15dB",
            ],
        ),
        (
            ASSET_DIR / "sfx/footsteps/placeholder-four-footsteps.wav",
            [
                "ffmpeg",
                "-y",
                "-hide_banner",
                "-loglevel",
                "error",
                "-f",
                "lavfi",
                "-i",
                "sine=frequency=95:duration=0.08:sample_rate=44100",
                "-filter_complex",
                "[0:a]asplit=4[a][b][c][d];[a]adelay=0|0[a0];[b]adelay=260|260[b0];[c]adelay=520|520[c0];[d]adelay=780|780[d0];[a0][b0][c0][d0]amix=inputs=4,volume=-14dB",
            ],
        ),
    )

    for target, command in commands:
        target.parent.mkdir(parents=True, exist_ok=True)
        subprocess.run([*command, str(target)], check=True)
        generated.append(str(target.relative_to(OUT_DIR)))
    return generated


def write_voice_prompt_files() -> None:
    plan = json.loads(PLAN_PATH.read_text(encoding="utf-8"))
    folder_by_speaker = {
        "tradesperson": "voice/tradesperson",
        "narrator": "voice/narrator",
        "app_voice": "voice/app",
    }
    for asset in plan["assets"]:
        if not asset["kind"].startswith("voice"):
            continue
        speaker = asset.get("speaker", "tradesperson")
        folder = ASSET_DIR / folder_by_speaker.get(speaker, "voice/tradesperson")
        text_path = folder / f"{asset['assetId']}.txt"
        text_path.write_text(
            "\n".join(
                (
                    f"asset_id: {asset['assetId']}",
                    f"speaker: {speaker}",
                    f"text: {asset['text']}",
                    f"target: {asset['target']}",
                    "",
                )
            ),
            encoding="utf-8",
        )


def write_reaper_project() -> None:
    tracks = (
        "Voice - Tradesperson",
        "Voice - App",
        "Voice - Narrator",
        "SFX - Beeps",
        "SFX - Dog",
        "SFX - Scene",
        "Reference",
    )
    track_blocks = "\n".join(render_track(track) for track in tracks)
    PROJECT_PATH.write_text(
        f"""<REAPER_PROJECT 0.1 "7.73/linux-x86_64" 0
  RIPPLE 0
  GROUPOVERRIDE 0 0 0
  AUTOXFADE 1
  ENVATTACH 1
  PANMODE 3
  PROJOFFS 0 0 0
  TEMPO 120 4 4
  PLAYRATE 1 0 0.25 4
  SELECTION 0 0
  SELECTION2 0 0
  MASTERAUTOMODE 0
  CURSOR 0
  ZOOM 100 0 0
  USE_REC_CFG 0
  RECMODE 1
  LOOP 0
  RECORD_PATH "Audio Files" ""
  RENDER_FILE "assets/renders"
  RENDER_PATTERN "jobdone-dog-callback"
{track_blocks}
>
""",
        encoding="utf-8",
    )


def render_track(name: str) -> str:
    return f"""  <TRACK
    NAME "{name}"
    PEAKCOL 16576
    BEAT -1
    AUTOMODE 0
    VOLPAN 1 0 1 -1
    MUTESOLO 0 0 0
    IPHASE 0
    ISBUS 0 0
    SEL 0
    REC 0 0 1 0 0 0 0 0
    NCHAN 2
    FX 1
    TRACKID {{{name_to_guid(name)}}}
    PERF 0
    MIDIOUT -1
    MAINSEND 1 0
  >"""


def name_to_guid(name: str) -> str:
    import uuid

    return str(uuid.uuid5(uuid.NAMESPACE_URL, f"workflow-manager:jobdone-dog-callback:{name}")).upper()


def write_open_script() -> None:
    OPEN_SCRIPT.write_text(
        f"""#!/usr/bin/env bash
set -euo pipefail
cd {quote(str(OUT_DIR))}
if command -v pw-jack >/dev/null 2>&1; then
  exec pw-jack reaper {quote(str(PROJECT_PATH))}
fi

echo "pw-jack is not installed; REAPER may fail if it tries to use JACK audio." >&2
echo "Run: do-now install-reaper-audio" >&2
exec reaper {quote(str(PROJECT_PATH))}
""",
        encoding="utf-8",
    )
    OPEN_SCRIPT.chmod(0o755)


def quote(value: str) -> str:
    return "'" + value.replace("'", "'\"'\"'") + "'"


def write_readme(copied: list[str], generated: list[str]) -> None:
    seeded_asset_list = "\n".join(f"- `{path}`" for path in [*copied, *generated])
    current_asset_list = "\n".join(
        f"- `{path.relative_to(OUT_DIR)}`"
        for path in sorted(ASSET_DIR.rglob("*"))
        if path.is_file() and path.suffix != ".reapeaks"
    )
    (OUT_DIR / "README.md").write_text(
        f"""# JobDone Dog Callback REAPER Project

Open this project with:

```bash
{OPEN_SCRIPT}
```

The asset library lives at:

```text
{ASSET_DIR}
```

In REAPER, use Media Explorer to browse `assets/`, preview candidates, and drag
chosen sounds onto the matching tracks.

Seeded audio refreshed by the setup script:

{seeded_asset_list or "- None yet."}

Current files in the asset library:

{current_asset_list or "- None yet."}

Voice folders contain `.txt` prompt cards for reference plus generated MP3 takes
when they have been created.
""",
        encoding="utf-8",
    )


if __name__ == "__main__":
    raise SystemExit(main())
