#!/usr/bin/env python3
"""Generate a local REAPER rough assembly script for the JobDone dog advert."""

from __future__ import annotations

import json
import subprocess
from datetime import datetime
from pathlib import Path
from shlex import quote


ROOT = Path(__file__).resolve().parents[1]
PROJECT_DIR = ROOT / "local" / "audio-adverts" / "jobdone-dog-callback"
BASE_PROJECT = PROJECT_DIR / "jobdone-dog-callback.rpp"
OUT_DIR = PROJECT_DIR / "rough-assembly-v1"
MANIFEST_PATH = OUT_DIR / "rough-assembly-v1.json"
LUA_PATH = OUT_DIR / "assemble-rough-v1.lua"
OPEN_SCRIPT = OUT_DIR / "open-rough-v1.sh"


def main() -> int:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    events = enrich_events(rough_events())
    write_manifest(events)
    write_lua(events)
    write_open_script()
    print(f"manifest: {MANIFEST_PATH}")
    print(f"reascript: {LUA_PATH}")
    print(f"open: {OPEN_SCRIPT}")
    return 0


def rough_events() -> list[dict[str, object]]:
    """First rough layout from Peter's selected asset list plus inferred app voice."""

    return [
        {
            "time": 0.00,
            "track": "SFX - Beeps",
            "label": "record-start-friendly-beep",
            "path": PROJECT_DIR / "Audio Files" / "record-start-friendly-beep.wav",
            "volume_db": -4,
            "fade_in": 0.0,
            "fade_out": 0.02,
            "note": "Tiny gadget cue before the JobDone capture.",
        },
        {
            "time": 0.12,
            "track": "Voice - Tradesperson",
            "label": "Kitchen sink washer replaced. Isolation valve stiff.",
            "path": PROJECT_DIR / "assets/voice/tradesperson/directed-v2/plumber_capture__v2_machine_note_passive__david_machine_note.mp3",
            "volume_db": 0,
            "fade_in": 0.02,
            "fade_out": 0.05,
            "note": "Passive machine-note delivery.",
        },
        {
            "time": 3.55,
            "track": "SFX - Beeps",
            "label": "record-end-friendly-beep",
            "path": PROJECT_DIR / "Audio Files" / "record-start-friendly-beep.wav",
            "volume_db": -7,
            "fade_in": 0.0,
            "fade_out": 0.02,
            "note": "Second cue to show capture finished.",
        },
        {
            "time": 3.75,
            "track": "Voice - Tradesperson",
            "label": "Oh, and Charlie the dog bites ankles.",
            "path": PROJECT_DIR / "assets/voice/tradesperson/plumber_charlie_note__selected_david_afterthought__yorkshire_david.mp3",
            "volume_db": 0,
            "fade_in": 0.02,
            "fade_out": 0.05,
            "note": "The memorable detail.",
        },
        {
            "time": 5.55,
            "track": "SFX - Dog",
            "label": "small-dog-bark-first-gag",
            "path": PROJECT_DIR / "Audio Files" / "03-freesound-270586-small-dog-barking.mp3",
            "volume_db": -10,
            "fade_in": 0.01,
            "fade_out": 0.18,
            "note": "Layer under/after Charlie warning; probably trim in REAPER.",
        },
        {
            "time": 6.65,
            "track": "SFX - Scene",
            "label": "door-open-close-transition",
            "path": PROJECT_DIR / "assets/sfx/doors/02-freesound-471923-66-puertaabri-ndose2-wav.mp3",
            "volume_db": -8,
            "fade_in": 0.01,
            "fade_out": 0.05,
            "note": "Scene exit/transition.",
        },
        {
            "time": 7.15,
            "track": "SFX - Scene",
            "label": "footsteps-away",
            "path": PROJECT_DIR / "assets/sfx/footsteps/04-freesound-584323-abrupt-stopping-on-gravel-road-2-wav.mp3",
            "volume_db": -14,
            "fade_in": 0.04,
            "fade_out": 0.25,
            "note": "Optional movement bed; likely too long and should be trimmed.",
        },
        {
            "time": 9.55,
            "track": "SFX - Scene",
            "label": "return-visit-doorbell",
            "path": PROJECT_DIR / "assets/sfx/doorbells/04-freesound-804731-belldoor-samsung-galaxy-smartphone-doorbell-single-ring-nicholas-judy-tdc.mp3",
            "volume_db": -12,
            "fade_in": 0.01,
            "fade_out": 0.2,
            "note": "Return visit cue.",
        },
        {
            "time": 10.15,
            "track": "Voice - App",
            "label": "Results for Mrs Jones...",
            "path": PROJECT_DIR / "Audio Files" / "app_results__v3_soft_robot__lily_soft_robot_app.mp3",
            "volume_db": -1,
            "fade_in": 0.02,
            "fade_out": 0.05,
            "note": "Inferred from current search result because recall needs an app voice.",
        },
        {
            "time": 18.85,
            "track": "SFX - Dog",
            "label": "small-dog-bark-callback",
            "path": PROJECT_DIR / "Audio Files" / "03-freesound-270586-small-dog-barking.mp3",
            "volume_db": -12,
            "fade_in": 0.01,
            "fade_out": 0.18,
            "note": "Callback bark before the final line.",
        },
        {
            "time": 19.35,
            "track": "Voice - Tradesperson",
            "label": "Oi! Charlie! Come back with that!",
            "path": PROJECT_DIR / "assets/voice/tradesperson/selected/plumber_final_dog__selected__david_emphatic_dog.mp3",
            "volume_db": 0,
            "fade_in": 0.02,
            "fade_out": 0.08,
            "note": "Selected David emphatic dog call.",
        },
        {
            "time": 21.45,
            "track": "Voice - Narrator",
            "label": "JobDone. Remember the job.",
            "path": PROJECT_DIR / "Audio Files" / "tagline__v3_warm_intimate__lily_warm_narrator.mp3",
            "volume_db": -1,
            "fade_in": 0.03,
            "fade_out": 0.16,
            "note": "Warm Lily tagline, after comedy callback.",
        },
    ]


def enrich_events(events: list[dict[str, object]]) -> list[dict[str, object]]:
    enriched: list[dict[str, object]] = []
    for event in events:
        path = Path(event["path"])
        if not path.exists():
            raise FileNotFoundError(path)
        row = {**event}
        row["path"] = str(path)
        row["duration"] = ffprobe_duration(path)
        enriched.append(row)
    return enriched


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


def write_manifest(events: list[dict[str, object]]) -> None:
    payload = {
        "schemaVersion": "workflow-manager.jobdone-reaper-rough-assembly.v1",
        "generatedAt": datetime.now().astimezone().isoformat(timespec="seconds"),
        "source": "Peter pasted Audio Asset Search selected assets; app voice inferred from current Lily result.",
        "baseProject": str(BASE_PROJECT),
        "roughScript": str(LUA_PATH),
        "events": events,
        "humanPolishNotes": [
            "Trim bark clips rather than letting full files play.",
            "Move app voice earlier/later until the recall joke lands.",
            "Adjust doorbell/footsteps/door levels or delete if they clutter the gag.",
            "Keep narrator/tagline after the dog callback so the advert stays humble.",
        ],
    }
    MANIFEST_PATH.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")


def write_lua(events: list[dict[str, object]]) -> None:
    tracks = [
        "Voice - Tradesperson",
        "Voice - App",
        "Voice - Narrator",
        "SFX - Beeps",
        "SFX - Dog",
        "SFX - Scene",
    ]
    lua_events = ",\n".join(lua_event(event) for event in events)
    lua_tracks = ", ".join(lua_string(track) for track in tracks)
    LUA_PATH.write_text(
        f"""-- Auto-generated by scripts/generate_jobdone_reaper_rough_assembly.py
-- Run inside REAPER. It deletes/recreates only tracks prefixed with "Rough V1 -".

local TRACKS = {{{lua_tracks}}}
local EVENTS = {{
{lua_events}
}}
local PREFIX = "Rough V1 - "

local function starts_with(value, prefix)
  return string.sub(value, 1, string.len(prefix)) == prefix
end

local function db_to_gain(db)
  return 10 ^ (db / 20)
end

local function delete_previous_rough_tracks()
  for i = reaper.CountTracks(0) - 1, 0, -1 do
    local track = reaper.GetTrack(0, i)
    local _, name = reaper.GetSetMediaTrackInfo_String(track, "P_NAME", "", false)
    if starts_with(name, PREFIX) then
      reaper.DeleteTrack(track)
    end
  end
end

local function delete_previous_rough_markers()
  local total_markers = reaper.CountProjectMarkers(0)
  for i = total_markers - 1, 0, -1 do
    local _, is_region, _, _, name, marker_id = reaper.EnumProjectMarkers(i)
    if name and starts_with(name, "Rough V1:") then
      reaper.DeleteProjectMarker(0, marker_id, is_region)
    end
  end
end

local function create_track(name, index)
  reaper.InsertTrackAtIndex(index, true)
  local track = reaper.GetTrack(0, index)
  reaper.GetSetMediaTrackInfo_String(track, "P_NAME", PREFIX .. name, true)
  return track
end

local function add_item(track, event)
  local source = reaper.PCM_Source_CreateFromFile(event.path)
  if not source then
    reaper.ShowConsoleMsg("Could not load: " .. event.path .. "\\n")
    return
  end
  local source_length = reaper.GetMediaSourceLength(source)
  local length = event.duration or source_length
  local item = reaper.AddMediaItemToTrack(track)
  local take = reaper.AddTakeToMediaItem(item)
  reaper.SetMediaItemTake_Source(take, source)
  reaper.GetSetMediaItemTakeInfo_String(take, "P_NAME", event.label, true)
  reaper.SetMediaItemInfo_Value(item, "D_POSITION", event.time)
  reaper.SetMediaItemInfo_Value(item, "D_LENGTH", length)
  reaper.SetMediaItemInfo_Value(item, "D_VOL", db_to_gain(event.volume_db or 0))
  reaper.SetMediaItemInfo_Value(item, "D_FADEINLEN", event.fade_in or 0)
  reaper.SetMediaItemInfo_Value(item, "D_FADEOUTLEN", event.fade_out or 0)
  reaper.SetMediaItemSelected(item, false)
end

reaper.Undo_BeginBlock()
delete_previous_rough_tracks()
delete_previous_rough_markers()

local track_by_name = {{}}
for index, name in ipairs(TRACKS) do
  track_by_name[name] = create_track(name, index - 1)
end

for _, event in ipairs(EVENTS) do
  local track = track_by_name[event.track]
  if track then
    add_item(track, event)
  end
end

reaper.AddProjectMarker2(0, false, 0.0, 0, "Rough V1: capture", -1, 0)
reaper.AddProjectMarker2(0, false, 9.55, 0, "Rough V1: recall", -1, 0)
reaper.AddProjectMarker2(0, false, 19.35, 0, "Rough V1: dog callback", -1, 0)
reaper.AddProjectMarker2(0, false, 21.45, 0, "Rough V1: tagline", -1, 0)
reaper.SetEditCurPos(0, true, false)
reaper.UpdateArrange()
reaper.Undo_EndBlock("Build JobDone dog callback rough assembly v1", -1)
""",
        encoding="utf-8",
    )


def lua_event(event: dict[str, object]) -> str:
    fields = [
        ("track", lua_string(str(event["track"]))),
        ("label", lua_string(str(event["label"]))),
        ("path", lua_string(str(event["path"]))),
        ("time", str(event["time"])),
        ("duration", str(event["duration"])),
        ("volume_db", str(event["volume_db"])),
        ("fade_in", str(event["fade_in"])),
        ("fade_out", str(event["fade_out"])),
        ("note", lua_string(str(event["note"]))),
    ]
    body = ", ".join(f"{key} = {value}" for key, value in fields)
    return f"  {{{body}}}"


def lua_string(value: str) -> str:
    return json.dumps(value)


def write_open_script() -> None:
    OPEN_SCRIPT.write_text(
        f"""#!/usr/bin/env bash
set -euo pipefail
cd {quote(str(PROJECT_DIR))}
if command -v pw-jack >/dev/null 2>&1; then
  exec pw-jack reaper {quote(str(BASE_PROJECT))} {quote(str(LUA_PATH))}
fi

echo "pw-jack is not installed; REAPER may fail if it tries to use JACK audio." >&2
echo "Run: do-now install-reaper-audio" >&2
exec reaper {quote(str(BASE_PROJECT))} {quote(str(LUA_PATH))}
""",
        encoding="utf-8",
    )
    OPEN_SCRIPT.chmod(0o755)


if __name__ == "__main__":
    raise SystemExit(main())
