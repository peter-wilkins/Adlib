#!/usr/bin/env python3
"""Build a focused listening page for one generated audio campaign."""

from __future__ import annotations

import argparse
import html
import json
import shutil
from datetime import datetime
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
PROCESSED_ROOT = ROOT / "data" / "processed" / "audio-ads"
DEFAULT_OUT_ROOT = ROOT / "local" / "reports" / "campaign-audio-workbench"
AUDIO_SUFFIXES = {".mp3", ".wav", ".ogg", ".m4a", ".flac"}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--campaign", required=True)
    parser.add_argument("--out-dir", type=Path)
    args = parser.parse_args()

    out_dir = args.out_dir or DEFAULT_OUT_ROOT / args.campaign
    assets = build_assets(args.campaign, out_dir)
    write_page(args.campaign, assets, out_dir)
    print(f"assets: {len(assets)}")
    print(f"page: {out_dir / 'index.html'}")
    print(f"data: {out_dir / 'assets.json'}")
    return 0


def build_assets(campaign: str, out_dir: Path) -> list[dict[str, Any]]:
    meta_root = PROCESSED_ROOT / campaign
    metadata_paths = sorted(meta_root.rglob("*.json"))
    if not metadata_paths:
        raise SystemExit(f"no metadata found for campaign: {campaign}")
    media_dir = out_dir / "media"
    media_dir.mkdir(parents=True, exist_ok=True)
    assets: list[dict[str, Any]] = []
    for path in metadata_paths:
        data = load_metadata(path)
        if not data:
            continue
        source = first_existing_path(data.get("reaperAssetPath"), data.get("rawAudioPath"), data.get("audioPath"))
        if source is None or source.suffix.lower() not in AUDIO_SUFFIXES:
            continue
        media_name = stable_media_name(data, source)
        shutil.copy2(source, media_dir / media_name)
        assets.append(asset_from_metadata(data, f"media/{media_name}"))
    return sorted(assets, key=lambda item: (item["project"], item["title"], item["assetId"]))


def load_metadata(path: Path) -> dict[str, Any] | None:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    if data.get("provider") != "elevenlabs":
        return None
    return data


def first_existing_path(*values: Any) -> Path | None:
    for value in values:
        if not value:
            continue
        path = Path(str(value))
        if path.exists():
            return path
    return None


def stable_media_name(data: dict[str, Any], source: Path) -> str:
    stem = "__".join(
        safe_slug(str(value))
        for value in (
            data.get("assetId"),
            data.get("takeSlug"),
            data.get("voiceProfile"),
        )
        if value
    )
    return f"{stem or safe_slug(source.stem)}{source.suffix.lower()}"


def asset_from_metadata(data: dict[str, Any], media_url: str) -> dict[str, Any]:
    preflight = ((data.get("qualityGate") or {}).get("technicalPreflight") or {})
    drift = preflight.get("scriptDrift") or {}
    transcription = preflight.get("transcription") or {}
    source_draft = str(data.get("sourceDraft") or "")
    return {
        "assetId": data.get("assetId") or "",
        "takeSlug": data.get("takeSlug") or "",
        "project": project_from_source(source_draft, str(data.get("title") or "")),
        "title": data.get("title") or data.get("assetId") or "",
        "assetKind": data.get("assetKind") or "",
        "voice": data.get("voiceName") or data.get("voiceProfile") or "",
        "createdAt": data.get("createdAt") or "",
        "media": media_url,
        "scriptText": data.get("scriptText") or "",
        "sourceDraft": source_draft,
        "testStatus": data.get("testStatus") or "",
        "gateStatus": preflight.get("status") or "",
        "driftStatus": drift.get("status") or "",
        "similarity": drift.get("similarity"),
        "transcript": transcription.get("text") or "",
        "transcriber": (transcription.get("backend") or {}).get("processorId") or "",
    }


def project_from_source(source_draft: str, title: str) -> str:
    title_value = title.lower()
    if "jury" in title_value:
        return "Jury Rigged"
    if "field relay" in title_value:
        return "Field Relay"
    if "developer school" in title_value:
        return "Entrepreneurs AI Developer School"
    if "continuum" in title_value:
        return "Continuum Kit"
    if "jobdone" in title_value or "job done" in title_value:
        return "JobDone"

    value = source_draft.lower()
    if "jobdone" in value or "job-done" in value or "job done" in value:
        return "JobDone"
    if "fieldrelay" in value or "field-relay" in value:
        return "Field Relay"
    if "school" in value or "developer school" in value:
        return "Entrepreneurs AI Developer School"
    if "jury" in value:
        return "Jury Rigged"
    if "continuum" in value:
        return "Continuum Kit"
    return "Audio"


def write_page(campaign: str, assets: list[dict[str, Any]], out_dir: Path) -> None:
    out_dir.mkdir(parents=True, exist_ok=True)
    payload = {
        "campaign": campaign,
        "generatedAt": datetime.now().astimezone().isoformat(timespec="seconds"),
        "assets": assets,
    }
    (out_dir / "assets.json").write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    (out_dir / "index.html").write_text(render_page(payload), encoding="utf-8")


def render_page(payload: dict[str, Any]) -> str:
    data = json.dumps(payload, ensure_ascii=True, separators=(",", ":"))
    campaign = html.escape(str(payload["campaign"]))
    count = len(payload["assets"])
    pass_count = sum(1 for asset in payload["assets"] if asset.get("testStatus") == "preflight_passed_needs_creative_critic")
    return f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>{campaign} Audio Workbench</title>
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
      --warn: #a16207;
      --good: #087443;
    }}
    @media (prefers-color-scheme: dark) {{
      :root {{
        --bg: #101412;
        --ink: #eff4ef;
        --muted: #9cafaa;
        --panel: #18201d;
        --line: #304039;
        --accent: #5eead4;
        --warn: #fbbf24;
        --good: #86efac;
      }}
    }}
    * {{ box-sizing: border-box; }}
    body {{ margin: 0; background: var(--bg); color: var(--ink); }}
    main {{ width: min(1120px, calc(100vw - 24px)); margin: 0 auto; padding: 18px 0 54px; }}
    header {{ display: grid; gap: 8px; margin-bottom: 14px; }}
    h1 {{ margin: 0; font-size: clamp(1.7rem, 3vw, 2.8rem); letter-spacing: 0; }}
    .meta {{ color: var(--muted); line-height: 1.45; }}
    .toolbar {{
      position: sticky;
      top: 0;
      z-index: 5;
      display: grid;
      grid-template-columns: 1fr minmax(150px, .35fr) auto;
      gap: 8px;
      padding: 10px;
      border: 1px solid var(--line);
      border-radius: 8px;
      background: color-mix(in oklab, var(--bg) 92%, transparent);
      backdrop-filter: blur(10px);
    }}
    input, select, button {{
      min-height: 40px;
      border: 1px solid var(--line);
      border-radius: 6px;
      background: var(--panel);
      color: var(--ink);
      font: inherit;
      padding: 0 10px;
    }}
    button {{ cursor: pointer; font-weight: 700; border-color: var(--accent); }}
    .grid {{ display: grid; gap: 12px; margin-top: 14px; }}
    .card {{ background: var(--panel); border: 1px solid var(--line); border-radius: 8px; padding: 12px; display: grid; gap: 10px; }}
    .card-head {{ display: grid; grid-template-columns: minmax(0, 1fr) auto; gap: 10px; align-items: start; }}
    h2 {{ margin: 0; font-size: 1.1rem; letter-spacing: 0; }}
    .chips {{ display: flex; flex-wrap: wrap; gap: 6px; }}
    .chip {{ border: 1px solid var(--line); border-radius: 999px; padding: 2px 8px; color: var(--muted); font-size: .82rem; }}
    .chip.pass {{ color: var(--good); border-color: color-mix(in oklab, var(--good) 45%, var(--line)); }}
    .chip.fail {{ color: var(--warn); border-color: color-mix(in oklab, var(--warn) 45%, var(--line)); }}
    audio {{ width: 100%; }}
    details {{ border-top: 1px solid var(--line); padding-top: 8px; }}
    summary {{ cursor: pointer; color: var(--muted); }}
    pre {{ white-space: pre-wrap; overflow-wrap: anywhere; margin: 8px 0 0; color: var(--muted); font-size: .9rem; }}
    @media (max-width: 720px) {{
      .toolbar {{ grid-template-columns: 1fr; position: static; }}
      .card-head {{ grid-template-columns: 1fr; }}
    }}
  </style>
</head>
<body>
  <main>
    <header>
      <h1>{campaign} Audio Workbench</h1>
      <div class="meta">{count} generated audio clips. Technical gate exact passes: {pass_count} / {count}. Yellow badges mean listen with human ears before keeping.</div>
    </header>
    <section class="toolbar">
      <input id="q" type="search" placeholder="search title, script, transcript" autocomplete="off">
      <select id="project"><option value="">All projects</option></select>
      <button id="next">Play next</button>
    </section>
    <section id="list" class="grid"></section>
  </main>
  <script>
    const DATA = {data};
    const q = document.querySelector("#q");
    const project = document.querySelector("#project");
    const list = document.querySelector("#list");
    const next = document.querySelector("#next");
    let rendered = [];
    let currentIndex = -1;
    function esc(value) {{
      return String(value ?? "").replace(/[&<>"']/g, (ch) => ({{
        "&": "&amp;",
        "<": "&lt;",
        ">": "&gt;",
        '"': "&quot;",
        "'": "&#039;"
      }}[ch]));
    }}
    function gateLabel(asset) {{
      return asset.testStatus === "preflight_passed_needs_creative_critic" ? "word gate pass" : "strict gate mismatch";
    }}
    function gateClass(asset) {{
      return asset.testStatus === "preflight_passed_needs_creative_critic" ? "pass" : "fail";
    }}
    function matches(asset) {{
      const needle = q.value.trim().toLowerCase();
      const hay = [asset.project, asset.title, asset.assetKind, asset.voice, asset.scriptText, asset.transcript, asset.testStatus].join(" ").toLowerCase();
      return (!needle || hay.includes(needle)) && (!project.value || asset.project === project.value);
    }}
    for (const value of [...new Set(DATA.assets.map((asset) => asset.project))].sort()) {{
      const option = document.createElement("option");
      option.value = value;
      option.textContent = value;
      project.appendChild(option);
    }}
    function render() {{
      rendered = DATA.assets.filter(matches);
      list.innerHTML = rendered.map((asset, index) => `<article class="card" data-index="${{index}}">
        <div class="card-head">
          <div>
            <h2>${{esc(asset.title)}}</h2>
            <div class="meta">${{esc(asset.project)}} · ${{esc(asset.voice)}} · ${{esc(asset.assetKind)}}</div>
          </div>
          <div class="chips">
            <span class="chip ${{gateClass(asset)}}">${{gateLabel(asset)}}</span>
            <span class="chip">${{esc(asset.testStatus)}}</span>
          </div>
        </div>
        <audio controls preload="none" src="${{esc(asset.media)}}"></audio>
        <details open><summary>Script</summary><pre>${{esc(asset.scriptText)}}</pre></details>
        <details><summary>Transcript</summary><pre>${{esc(asset.transcript || "No transcript stored.")}}</pre></details>
      </article>`).join("");
      currentIndex = -1;
    }}
    function playAt(index) {{
      const cards = [...document.querySelectorAll(".card")];
      if (!cards.length) return;
      currentIndex = (index + cards.length) % cards.length;
      const audio = cards[currentIndex].querySelector("audio");
      audio.scrollIntoView({{ block: "center", behavior: "smooth" }});
      audio.play();
    }}
    list.addEventListener("play", (event) => {{
      if (event.target.tagName !== "AUDIO") return;
      for (const audio of document.querySelectorAll("audio")) if (audio !== event.target) audio.pause();
      currentIndex = Number(event.target.closest(".card").dataset.index);
    }}, true);
    list.addEventListener("ended", () => playAt(currentIndex + 1), true);
    q.addEventListener("input", render);
    project.addEventListener("change", render);
    next.addEventListener("click", () => playAt(currentIndex + 1));
    render();
  </script>
</body>
</html>
"""


def safe_slug(value: str) -> str:
    chars: list[str] = []
    previous_dash = False
    for char in value.lower():
        if char.isalnum():
            chars.append(char)
            previous_dash = False
        elif not previous_dash:
            chars.append("-")
            previous_dash = True
    return "".join(chars).strip("-")[:120]


if __name__ == "__main__":
    raise SystemExit(main())
