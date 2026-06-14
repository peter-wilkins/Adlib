#!/usr/bin/env python3
"""Create the local REAPER project scaffold for the Living Water Skills advert."""

from __future__ import annotations

import shutil
import subprocess
import uuid
from dataclasses import dataclass
from pathlib import Path
from shlex import quote


ROOT = Path(__file__).resolve().parents[1]
PROJECT_DIR = ROOT / "local" / "audio-adverts" / "living-water-skills-pond-challenge"
ASSET_DIR = PROJECT_DIR / "assets"
PROJECT_PATH = PROJECT_DIR / "living-water-skills-pond-challenge.rpp"
OPEN_SCRIPT = PROJECT_DIR / "open-reaper.sh"
README_PATH = PROJECT_DIR / "README.md"


@dataclass(frozen=True)
class Event:
    track: str
    label: str
    path: Path
    position: float
    length: float | None = None
    volume_db: float = 0.0
    fade_in: float = 0.02
    fade_out: float = 0.08


FOLDERS = (
    "voice/learner/selected",
    "voice/mentor/selected/phone-processed",
    "voice/narrator/selected",
    "sfx/ambience/garden",
    "sfx/ambience/water",
    "renders",
    "reference",
)

COPIED_AMBIENCE = (
    (
        ROOT
        / "local/audio-adverts/jobdone-dog-callback/assets/sfx/ambience/suburban-garden/01-freesound-222026-in-an-english-suburban-garden.mp3",
        "sfx/ambience/garden/01-english-suburban-garden-birds.mp3",
    ),
    (
        ROOT
        / "local/audio-adverts/jobdone-dog-callback/assets/sfx/ambience/suburban-garden/02-freesound-378379-ambience-near-bird-feeders-wav.mp3",
        "sfx/ambience/garden/02-bird-feeder-ambience-alt.mp3",
    ),
)


def main() -> int:
    PROJECT_DIR.mkdir(parents=True, exist_ok=True)
    ASSET_DIR.mkdir(parents=True, exist_ok=True)
    for folder in FOLDERS:
        (ASSET_DIR / folder).mkdir(parents=True, exist_ok=True)

    copied = copy_known_ambience()
    generated = generate_placeholder_audio()
    events = build_events()
    write_reaper_project(events)
    write_open_script()
    write_readme(copied, generated)

    print(f"project: {PROJECT_PATH}")
    print(f"assets:  {ASSET_DIR}")
    print(f"open:    {OPEN_SCRIPT}")
    return 0


def copy_known_ambience() -> list[str]:
    copied: list[str] = []
    for source, relative_target in COPIED_AMBIENCE:
        if not source.exists():
            continue
        target = ASSET_DIR / relative_target
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, target)
        copied.append(str(target.relative_to(PROJECT_DIR)))
    return copied


def generate_placeholder_audio() -> list[str]:
    if not shutil.which("ffmpeg"):
        return []

    generated: list[str] = []
    commands = (
        (
            ASSET_DIR / "sfx/ambience/water/gentle-pond-water-placeholder.wav",
            [
                "ffmpeg",
                "-y",
                "-hide_banner",
                "-loglevel",
                "error",
                "-f",
                "lavfi",
                "-i",
                "anoisesrc=color=pink:duration=45:sample_rate=44100",
                "-af",
                "highpass=f=180,lowpass=f=1800,afftdn=nf=-28,afade=t=in:st=0:d=2,afade=t=out:st=43:d=2,volume=-19dB",
            ],
        ),
        (
            ASSET_DIR / "sfx/ambience/water/small-water-sparkle-placeholder.wav",
            [
                "ffmpeg",
                "-y",
                "-hide_banner",
                "-loglevel",
                "error",
                "-f",
                "lavfi",
                "-i",
                "anoisesrc=color=white:duration=45:sample_rate=44100",
                "-af",
                "highpass=f=1200,lowpass=f=5200,afade=t=in:st=0:d=2,afade=t=out:st=43:d=2,volume=-32dB",
            ],
        ),
    )
    for target, command in commands:
        target.parent.mkdir(parents=True, exist_ok=True)
        subprocess.run([*command, str(target)], check=True)
        generated.append(str(target.relative_to(PROJECT_DIR)))
    return generated


def build_events() -> list[Event]:
    events = [
        Event(
            "SFX - Garden Birds",
            "English suburban garden birds",
            ASSET_DIR / "sfx/ambience/garden/01-english-suburban-garden-birds.mp3",
            0.0,
            length=42.0,
            volume_db=-20,
            fade_in=1.0,
            fade_out=2.0,
        ),
        Event(
            "SFX - Pond Water",
            "gentle pond water placeholder",
            ASSET_DIR / "sfx/ambience/water/gentle-pond-water-placeholder.wav",
            0.0,
            length=42.0,
            volume_db=-17,
            fade_in=1.0,
            fade_out=2.0,
        ),
        Event(
            "SFX - Pond Water",
            "small water sparkle placeholder",
            ASSET_DIR / "sfx/ambience/water/small-water-sparkle-placeholder.wav",
            0.0,
            length=42.0,
            volume_db=-9,
            fade_in=1.0,
            fade_out=2.0,
        ),
        Event(
            "Voice - Learner",
            "It's working. My pond's holding water now.",
            ASSET_DIR / "voice/learner/selected/learner_discovery__selected_original_maya_opening__learner_maya.mp3",
            1.0,
            volume_db=0,
        ),
        Event(
            "Voice - App Mentor Phone",
            "Nice work. Add native pond plants...",
            ASSET_DIR / "voice/mentor/selected/phone-processed/mentor_guidance__selected_river_guidance__mentor_river_steward__phone_speaker.mp3",
            9.1,
            volume_db=-2,
        ),
        Event(
            "Voice - Learner",
            "So basically make it a good home and be patient?",
            ASSET_DIR / "voice/learner/selected/learner_patience__selected_original_maya_patient__learner_maya.mp3",
            22.0,
            volume_db=0,
        ),
        Event(
            "Voice - App Mentor Phone",
            "Ready to submit Level 2 Pond Challenge.",
            ASSET_DIR / "voice/mentor/selected/phone-processed/mentor_submit__selected_river_submit__mentor_river_steward__phone_speaker.mp3",
            25.4,
            volume_db=-2,
        ),
        Event(
            "Voice - Narrator",
            "Living Water Skills tagline.",
            ASSET_DIR / "voice/narrator/selected/narrator_tagline__selected_lily_earn_levels__narrator_lily.mp3",
            31.4,
            volume_db=-1,
            fade_out=0.35,
        ),
    ]
    for event in events:
        if not event.path.exists():
            raise FileNotFoundError(event.path)
    return events


def write_reaper_project(events: list[Event]) -> None:
    tracks = (
        "Voice - Learner",
        "Voice - App Mentor Phone",
        "Voice - Narrator",
        "SFX - Garden Birds",
        "SFX - Pond Water",
        "Reference / Notes",
    )
    events_by_track = {track: [event for event in events if event.track == track] for track in tracks}
    track_blocks = "\n".join(render_track(track, events_by_track[track]) for track in tracks)
    PROJECT_PATH.write_text(
        f"""<REAPER_PROJECT 0.1 "7.73/linux-x86_64" 0
  RIPPLE 0
  GROUPOVERRIDE 0 0 0
  AUTOXFADE 1
  ENVATTACH 1
  PANMODE 3
  PROJOFFS 0 0 0
  GRID 3199 8 1 8 1 0 0 0
  TIMEMODE 1 5 -1 30 0 0 -1 0
  CURSOR 0
  ZOOM 130 0 0
  USE_REC_CFG 0
  RECMODE 1
  LOOP 0
  RECORD_PATH "Audio Files" ""
  RENDER_FILE "assets/renders/living-water-skills-pond-challenge.wav"
  RENDER_FMT 0 2 0
  RENDER_RANGE 1 0 42
  RENDER_RESAMPLE 3 0 1
  RENDER_ADDTOPROJ 0
  RENDER_STEMS 0
  RENDER_DITHER 0
  TIMELOCKMODE 1
  TEMPOENVLOCKMODE 1
  ITEMMIX 1
  DEFPITCHMODE 589824 0
  SAMPLERATE 44100 0 0
  TEMPO 120 4 4 0
  PLAYRATE 1 0 0.25 4
  SELECTION 0 42
  SELECTION2 0 42
  MASTERAUTOMODE 0
  MASTER_VOLUME 1 0 -1 -1 1
  GLOBAL_AUTO -1
  MARKER 1 1 "Learner asks about pond" 0 0 1 B {{{guid('marker:learner')}}} 0 2
  MARKER 2 9.1 "Phone mentor guidance" 0 0 1 B {{{guid('marker:mentor-guidance')}}} 0 2
  MARKER 3 22 "Learner understands patience" 0 0 1 B {{{guid('marker:learner-patience')}}} 0 2
  MARKER 4 25.4 "Ready to submit Level 2" 0 0 1 B {{{guid('marker:level-2')}}} 0 2
  MARKER 5 31.4 "Narrator tagline" 0 0 1 B {{{guid('marker:tagline')}}} 0 2
{track_blocks}
>
""",
        encoding="utf-8",
    )


def render_track(name: str, events: list[Event]) -> str:
    items = "\n".join(render_item(event, index) for index, event in enumerate(events, start=1))
    return f"""  <TRACK {{{guid('track:' + name)}}}
    NAME "{name}"
    PEAKCOL 16576
    BEAT -1
    AUTOMODE 0
    PANLAWFLAGS 3
    VOLPAN 1 0 -1 -1 1
    MUTESOLO 0 0 0
    IPHASE 0
    PLAYOFFS 0 1
    ISBUS 0 0
    BUSCOMP 0 0 0 0 0
    SHOWINMIX 1 0.6667 0.5 1 0.5 0 0 0 0
    FIXEDLANES 9 0 0 0 0
    SEL 0
    REC 0 0 1 0 0 0 0 0
    VU 64
    NCHAN 2
    FX 1
    TRACKID {{{guid('trackid:' + name)}}}
    PERF 0
    MIDIOUT -1
    MAINSEND 1 0
{items}
  >"""


def render_item(event: Event, index: int) -> str:
    length = event.length if event.length is not None else ffprobe_duration(event.path)
    source_type = source_type_for(event.path)
    rel_path = event.path.relative_to(PROJECT_DIR).as_posix()
    return f"""    <ITEM
      POSITION {event.position:g}
      SNAPOFFS 0
      LENGTH {length:g}
      LOOP 1
      ALLTAKES 0
      FADEIN 1 {event.fade_in:g} 0 1 0 0 0
      FADEOUT 1 {event.fade_out:g} 0 1 0 0 0
      MUTE 0 0
      SEL 0
      IGUID {{{guid('item:' + event.track + ':' + event.label)}}}
      IID {index}
      NAME "{escape_rpp(event.label)}"
      VOLPAN {db_to_gain(event.volume_db):.6f} 0 1 -1
      SOFFS 0
      PLAYRATE 1 1 0 -1 0 0.0025
      CHANMODE 0
      GUID {{{guid('take:' + event.track + ':' + event.label)}}}
      <SOURCE {source_type}
        FILE "{escape_rpp(rel_path)}"{' 1' if source_type == 'MP3' else ''}
      >
    >"""


def source_type_for(path: Path) -> str:
    if path.suffix.lower() == ".mp3":
        return "MP3"
    return "WAVE"


def ffprobe_duration(path: Path) -> float:
    result = subprocess.run(
        [
            "ffprobe",
            "-v",
            "error",
            "-show_entries",
            "format=duration",
            "-of",
            "default=noprint_wrappers=1:nokey=1",
            str(path),
        ],
        check=True,
        text=True,
        capture_output=True,
    )
    return round(float(result.stdout.strip()), 3)


def db_to_gain(db: float) -> float:
    return 10 ** (db / 20)


def guid(seed: str) -> str:
    return str(uuid.uuid5(uuid.NAMESPACE_URL, f"workflow-manager:living-water-skills:{seed}")).upper()


def escape_rpp(value: str) -> str:
    return value.replace('"', "'")


def write_open_script() -> None:
    OPEN_SCRIPT.write_text(
        f"""#!/usr/bin/env bash
set -euo pipefail
cd {quote(str(PROJECT_DIR))}
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


def write_readme(copied: list[str], generated: list[str]) -> None:
    current_asset_list = "\n".join(
        f"- `{path.relative_to(PROJECT_DIR)}`"
        for path in sorted(ASSET_DIR.rglob("*"))
        if path.is_file() and path.suffix != ".reapeaks"
    )
    README_PATH.write_text(
        f"""# Living Water Skills Pond Challenge REAPER Project

Open this project in REAPER:

```text
{PROJECT_PATH}
```

Shortcut:

```bash
{OPEN_SCRIPT}
```

The first rough layout uses:

- original Maya learner clips
- River mentor clips with phone-speaker processing
- Lily narrator tagline
- copied garden-bird ambience from the JobDone project
- generated pond-water placeholders

Copied ambience:

{chr(10).join(f"- `{path}`" for path in copied) or "- None."}

Generated placeholder audio:

{chr(10).join(f"- `{path}`" for path in generated) or "- None."}

Current asset library:

{current_asset_list or "- None yet."}
""",
        encoding="utf-8",
    )


if __name__ == "__main__":
    raise SystemExit(main())
