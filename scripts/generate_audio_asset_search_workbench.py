#!/usr/bin/env python3
"""Build a private searchable audio asset catalogue and player page."""

from __future__ import annotations

import html
import json
import re
import shutil
import subprocess
from dataclasses import asdict, dataclass
from datetime import datetime
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
PROCESSED_ROOT = ROOT / "data" / "processed" / "audio-ads"
REAPER_ASSET_ROOT = ROOT / "local" / "audio-adverts"
OUT_DIR = ROOT / "local" / "reports" / "audio-asset-search"
MEDIA_DIR = OUT_DIR / "media"
CATALOGUE_PATH = OUT_DIR / "catalogue.jsonl"
INDEX_PATH = OUT_DIR / "index.json"
HTML_PATH = OUT_DIR / "index.html"
SLUG_RE = re.compile(r"[^a-z0-9]+")
AUDIO_SUFFIXES = {".mp3", ".wav", ".ogg", ".m4a", ".flac"}


@dataclass(frozen=True)
class AudioAsset:
    asset_id: str
    title: str
    kind: str
    role: str
    campaign: str
    provider: str
    source: str
    source_url: str
    licence: str
    status: str
    intent: str
    text: str
    voice: str
    tags: list[str]
    duration_seconds: float | None
    original_path: str
    reaper_path: str
    media_url: str
    sha256: str
    notes: str
    created_at: str
    search_text: str


def main() -> int:
    assets = build_assets()
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    MEDIA_DIR.mkdir(parents=True, exist_ok=True)
    write_catalogue(assets)
    write_index(assets)
    write_html(assets)
    register_on_shelf()
    print(f"assets: {len(assets)}")
    print(f"catalogue: {CATALOGUE_PATH}")
    print(f"page: {HTML_PATH}")
    return 0


def build_assets() -> list[AudioAsset]:
    assets: list[AudioAsset] = []
    seen_keys: set[tuple[str, str]] = set()

    for path in sorted(PROCESSED_ROOT.rglob("*.json")):
        for asset in assets_from_metadata(path):
            key = (asset.asset_id, asset.sha256)
            if key in seen_keys:
                continue
            seen_keys.add(key)
            assets.append(asset)

    for path in sorted(REAPER_ASSET_ROOT.rglob("*")):
        if path.suffix.lower() not in AUDIO_SUFFIXES:
            continue
        if path.name.endswith(".reapeaks"):
            continue
        try:
            sha = file_sha256(path)
        except OSError:
            continue
        if any(asset.reaper_path == str(path) or asset.original_path == str(path) for asset in assets):
            continue
        asset = local_asset_from_file(path, sha)
        key = (asset.asset_id, asset.sha256)
        if key in seen_keys:
            continue
        seen_keys.add(key)
        assets.append(asset)

    return sorted(assets, key=lambda item: (item.campaign, item.kind, item.role, item.title.lower()))


def assets_from_metadata(path: Path) -> list[AudioAsset]:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return []
    schema = str(data.get("schema") or data.get("schemaVersion") or "")
    if data.get("provider") == "elevenlabs":
        asset = elevenlabs_asset(data)
        return [asset] if asset else []
    if schema == "workflow-manager.freesound-preview-fetch.v1":
        return freesound_assets(data)
    return []


def elevenlabs_asset(data: dict[str, Any]) -> AudioAsset | None:
    original = first_existing_path(data.get("reaperAssetPath"), data.get("rawAudioPath"), data.get("audioPath"))
    if original is None:
        return None
    sha = str(data.get("audioSha256") or file_sha256(original))
    created_at = str(data.get("createdAt") or "")
    campaign = str(data.get("campaign") or "")
    role = str(data.get("speaker") or "")
    asset_id = stable_asset_id(
        "el",
        data.get("scriptId"),
        data.get("scriptVersion"),
        data.get("assetId"),
        data.get("takeSlug"),
        data.get("voiceProfile"),
        created_at,
    )
    title = " / ".join(
        value
        for value in (
            str(data.get("assetId") or ""),
            str(data.get("takeSlug") or ""),
            str(data.get("voiceProfile") or ""),
        )
        if value
    )
    voice = str(data.get("voiceName") or data.get("voiceProfile") or "")
    tags = unique_tags(
        [
            "elevenlabs",
            "voice",
            role,
            campaign,
            data.get("scriptId"),
            data.get("scriptVersion"),
            data.get("assetId"),
            data.get("takeSlug"),
            data.get("voiceProfile"),
            data.get("voiceRole"),
            data.get("testStatus"),
            voice,
            *quality_gate_tags(data),
        ]
    )
    media_url = copy_media(original, asset_id, sha)
    duration = duration_for(original)
    status = selected_status_from_path(original, str(data.get("testStatus") or "needs_audition"))
    asset = AudioAsset(
        asset_id=asset_id,
        title=title or original.stem,
        kind="voice",
        role=role or "voice",
        campaign=campaign,
        provider="elevenlabs",
        source="ElevenLabs",
        source_url="",
        licence="ElevenLabs paid-plan output; verify before publication",
        status=status,
        intent=str(data.get("voiceRole") or ""),
        text=str(data.get("scriptText") or ""),
        voice=voice,
        tags=tags,
        duration_seconds=duration,
        original_path=str(data.get("rawAudioPath") or original),
        reaper_path=str(data.get("reaperAssetPath") or original),
        media_url=media_url,
        sha256=sha,
        notes=elevenlabs_notes(data),
        created_at=created_at,
        search_text="",
    )
    return with_search_text(asset)


def freesound_assets(data: dict[str, Any]) -> list[AudioAsset]:
    downloaded_by_id = {item.get("asset_id"): item for item in data.get("downloaded") or []}
    assets: list[AudioAsset] = []
    for candidate in (data.get("search") or {}).get("candidates") or []:
        downloaded = downloaded_by_id.get(candidate.get("asset_id"), {})
        original = first_existing_path(
            candidate.get("file_path"),
            downloaded.get("raw_path"),
            downloaded.get("reaper_path"),
        )
        if original is None:
            continue
        sha = str(candidate.get("file_sha256") or downloaded.get("sha256") or file_sha256(original))
        asset_id = str(candidate.get("asset_id") or stable_asset_id("fs", candidate.get("source_id"), sha[:10]))
        title = str(candidate.get("source_title") or downloaded.get("source_title") or original.stem)
        query = str(data.get("query") or "")
        source_url = str(candidate.get("source_url") or downloaded.get("source_url") or "")
        media_url = copy_media(original, asset_id, sha)
        duration = as_float(candidate.get("duration_seconds") or downloaded.get("duration_seconds")) or duration_for(original)
        reaper_path = str(downloaded.get("reaper_path") or candidate.get("reaper_path") or original)
        tags = unique_tags(
            [
                "freesound",
                "sfx",
                query,
                candidate.get("source_title"),
                candidate.get("creator"),
                candidate.get("source_provider"),
                *(candidate.get("tags") or []),
            ]
        )
        asset = AudioAsset(
            asset_id=asset_id,
            title=title,
            kind="sfx",
            role="sfx",
            campaign="external-sfx",
            provider="freesound",
            source=str(candidate.get("creator") or "Freesound"),
            source_url=source_url,
            licence=str(candidate.get("license") or downloaded.get("license") or ""),
            status=str(candidate.get("approval_status") or "preview_downloaded_needs_audition"),
            intent=query,
            text=str(candidate.get("description") or ""),
            voice="",
            tags=tags,
            duration_seconds=duration,
            original_path=str(candidate.get("file_path") or downloaded.get("raw_path") or original),
            reaper_path=reaper_path,
            media_url=media_url,
            sha256=sha,
            notes=f"rating={candidate.get('rating', '')}; downloads={candidate.get('download_count', '')}",
            created_at=str(candidate.get("downloaded_at") or data.get("queried_at") or ""),
            search_text="",
        )
        assets.append(with_search_text(asset))
    return assets


def local_asset_from_file(path: Path, sha: str) -> AudioAsset:
    relative = path.relative_to(ROOT) if path.is_relative_to(ROOT) else path
    parts = list(relative.parts)
    tags = unique_tags(parts + re.split(r"[_\\-\\.]+", path.stem))
    kind = "sfx" if "sfx" in parts else "voice" if "voice" in parts else "audio"
    role = role_from_parts(parts, kind)
    status = selected_status_from_path(path, "local_unindexed")
    asset_id = stable_asset_id("local", path.stem, sha[:10])
    asset = AudioAsset(
        asset_id=asset_id,
        title=path.stem,
        kind=kind,
        role=role,
        campaign=campaign_from_parts(parts),
        provider="local",
        source="local asset folder",
        source_url="",
        licence="unknown",
        status=status,
        intent=" ".join(tags),
        text="",
        voice="",
        tags=tags,
        duration_seconds=duration_for(path),
        original_path=str(path),
        reaper_path=str(path),
        media_url=copy_media(path, asset_id, sha),
        sha256=sha,
        notes="Discovered from local audio asset folder without sidecar metadata.",
        created_at=datetime.fromtimestamp(path.stat().st_mtime).astimezone().isoformat(timespec="seconds"),
        search_text="",
    )
    return with_search_text(asset)


def first_existing_path(*values: Any) -> Path | None:
    for value in values:
        if not value:
            continue
        path = Path(str(value))
        if path.exists() and path.suffix.lower() in AUDIO_SUFFIXES:
            return path
    return None


def copy_media(path: Path, asset_id: str, sha: str) -> str:
    suffix = path.suffix.lower() or ".audio"
    target_name = f"{safe_slug(asset_id)}__{sha[:10]}{suffix}"
    target = MEDIA_DIR / target_name
    target.parent.mkdir(parents=True, exist_ok=True)
    if not target.exists() or target.stat().st_size != path.stat().st_size:
        shutil.copy2(path, target)
    return f"media/{target_name}"


def write_catalogue(assets: list[AudioAsset]) -> None:
    CATALOGUE_PATH.write_text(
        "".join(json.dumps(asdict(asset), sort_keys=True) + "\n" for asset in assets),
        encoding="utf-8",
    )


def write_index(assets: list[AudioAsset]) -> None:
    payload = {
        "schemaVersion": "workflow-manager.audio-asset-catalogue.v0",
        "generatedAt": datetime.now().astimezone().isoformat(timespec="seconds"),
        "assetCount": len(assets),
        "assets": [asdict(asset) for asset in assets],
    }
    INDEX_PATH.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def write_html(assets: list[AudioAsset]) -> None:
    generated = datetime.now().astimezone().isoformat(timespec="seconds")
    payload = json.dumps([asdict(asset) for asset in assets], ensure_ascii=False)
    HTML_PATH.write_text(
        f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Audio Asset Search</title>
  <style>
    :root {{
      color-scheme: light dark;
      font-family: Inter, ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
      --bg: #f5f7f8;
      --ink: #182026;
      --muted: #61717d;
      --panel: #ffffff;
      --line: #d7dee4;
      --accent: #0f766e;
      --selected: #0f766e;
      --reject: #a33b34;
    }}
    @media (prefers-color-scheme: dark) {{
      :root {{
        --bg: #11161a;
        --ink: #eef4f6;
        --muted: #9aaab4;
        --panel: #1b2329;
        --line: #33414a;
        --accent: #5eead4;
        --selected: #5eead4;
        --reject: #fca5a5;
      }}
    }}
    * {{ box-sizing: border-box; }}
    body {{
      margin: 0;
      background: var(--bg);
      color: var(--ink);
    }}
    main {{
      width: min(1280px, calc(100vw - 24px));
      margin: 0 auto;
      padding: 18px 0 54px;
    }}
    header {{
      display: grid;
      gap: 8px;
      margin-bottom: 14px;
    }}
    h1 {{
      margin: 0;
      font-size: 2rem;
      line-height: 1.05;
      letter-spacing: 0;
    }}
    .meta, .hint {{
      color: var(--muted);
      font-size: 0.92rem;
    }}
    .searchbar {{
      position: sticky;
      top: 48px;
      z-index: 10;
      display: grid;
      grid-template-columns: 1fr auto auto auto auto;
      gap: 8px;
      padding: 10px;
      background: color-mix(in oklab, var(--bg) 86%, transparent);
      border: 1px solid var(--line);
      border-radius: 8px;
      backdrop-filter: blur(10px);
    }}
    input, select, button, textarea {{
      font: inherit;
      border-radius: 6px;
      border: 1px solid var(--line);
      background: var(--panel);
      color: var(--ink);
    }}
    input, select {{
      min-height: 38px;
      padding: 0 10px;
    }}
    button {{
      min-height: 38px;
      padding: 0 12px;
      cursor: pointer;
    }}
    button.primary {{
      border-color: color-mix(in oklab, var(--accent) 70%, var(--line));
      background: color-mix(in oklab, var(--accent) 16%, var(--panel));
      font-weight: 700;
    }}
    .layout {{
      display: grid;
      grid-template-columns: minmax(0, 1fr) 360px;
      gap: 14px;
      margin-top: 14px;
      align-items: start;
    }}
    .player, .results, .side {{
      background: var(--panel);
      border: 1px solid var(--line);
      border-radius: 8px;
    }}
    .player {{
      padding: 14px;
      display: grid;
      gap: 12px;
      margin-bottom: 14px;
    }}
    .now {{
      display: grid;
      gap: 5px;
    }}
    .now h2 {{
      margin: 0;
      font-size: 1.25rem;
      line-height: 1.2;
    }}
    audio {{
      width: 100%;
    }}
    .controls {{
      display: flex;
      gap: 8px;
      flex-wrap: wrap;
    }}
    .path {{
      font-family: ui-monospace, SFMono-Regular, Menlo, Consolas, monospace;
      color: var(--muted);
      overflow-wrap: anywhere;
      font-size: 0.82rem;
    }}
    .results {{
      overflow: hidden;
    }}
    .row {{
      display: grid;
      grid-template-columns: 44px minmax(0, 1fr) auto;
      gap: 10px;
      align-items: start;
      padding: 12px;
      border-bottom: 1px solid var(--line);
    }}
    .row:last-child {{
      border-bottom: 0;
    }}
    .row.active {{
      background: color-mix(in oklab, var(--accent) 10%, transparent);
    }}
    .row.selected {{
      border-left: 5px solid var(--selected);
    }}
    .row.rejected {{
      opacity: 0.56;
      border-left: 5px solid var(--reject);
    }}
    .row h3 {{
      margin: 0 0 4px;
      font-size: 1rem;
      line-height: 1.2;
    }}
    .chips {{
      display: flex;
      flex-wrap: wrap;
      gap: 5px;
      margin-top: 6px;
    }}
    .chip {{
      padding: 2px 7px;
      border: 1px solid var(--line);
      border-radius: 999px;
      color: var(--muted);
      font-size: 0.78rem;
    }}
    .side {{
      padding: 14px;
      display: grid;
      gap: 14px;
      position: sticky;
      top: 108px;
    }}
    .side h2 {{
      margin: 0;
      font-size: 1.05rem;
    }}
    textarea {{
      min-height: 84px;
      padding: 10px;
      resize: vertical;
    }}
    .copyFallback {{
      width: 100%;
      min-height: 120px;
      margin-top: 8px;
      font-family: ui-monospace, SFMono-Regular, Menlo, Consolas, monospace;
      font-size: 0.82rem;
    }}
    .copyFallback[hidden] {{
      display: none;
    }}
    pre {{
      white-space: pre-wrap;
      overflow-wrap: anywhere;
      margin: 0;
      padding: 10px;
      border: 1px solid var(--line);
      border-radius: 6px;
      color: var(--muted);
      max-height: 260px;
      overflow: auto;
    }}
    @media (max-width: 850px) {{
      .searchbar {{
        grid-template-columns: 1fr;
        top: 44px;
      }}
      .layout {{
        grid-template-columns: 1fr;
      }}
      .side {{
        position: static;
      }}
    }}
  </style>
</head>
<body>
<main>
  <header>
    <h1>Audio Asset Search</h1>
    <div class="meta">{len(assets)} assets indexed. Generated {html.escape(generated)}.</div>
    <div class="hint">Shortcuts after pressing Play once: Space play/pause, N next, P previous, S select, R reject.</div>
  </header>
  <section class="searchbar" aria-label="Search controls">
    <input id="query" type="search" placeholder="dog emphatic, Lily robot, doorbell urgent" autocomplete="off" autofocus>
    <select id="kind">
      <option value="">All kinds</option>
      <option value="voice">Voice</option>
      <option value="sfx">SFX</option>
      <option value="audio">Other audio</option>
    </select>
    <select id="status">
      <option value="">All status</option>
      <option value="selected">Selected</option>
      <option value="rejected">Rejected</option>
      <option value="needs">Needs audition</option>
    </select>
    <button id="playTop" class="primary">Play</button>
    <button id="clear">Clear</button>
  </section>
  <section class="layout">
    <div>
      <section class="player" aria-label="Current audio">
        <div class="now">
          <h2 id="nowTitle">No asset selected</h2>
          <div id="nowMeta" class="meta"></div>
          <div id="nowPath" class="path"></div>
        </div>
        <audio id="audio" controls preload="none"></audio>
        <div class="controls">
          <button id="prev">Previous</button>
          <button id="next" class="primary">Next</button>
          <button id="select">Select</button>
          <button id="reject">Reject</button>
          <button id="copyPath">Copy path</button>
        </div>
      </section>
      <section id="results" class="results" aria-label="Search results"></section>
    </div>
    <aside class="side">
      <section>
        <h2>Notes</h2>
        <textarea id="notes" placeholder="Private audition note for this asset"></textarea>
      </section>
      <section>
        <h2>Selected Assets</h2>
        <div class="controls">
          <button id="copySelectedPaths">Copy paths</button>
          <button id="copySelectedJson">Copy JSON</button>
        </div>
        <div class="meta">Selection is saved in this browser. Copy JSON is the handoff to an advert build plan.</div>
        <div id="copyStatus" class="meta"></div>
        <textarea id="copyFallback" class="copyFallback" readonly hidden></textarea>
        <pre id="selectedList"></pre>
      </section>
      <section>
        <h2>Current Record</h2>
        <pre id="record"></pre>
      </section>
    </aside>
  </section>
</main>
<script>
const ASSETS = {payload};
const STORE_KEY = "workflow.audioAssetSearch.annotations.v0";
let annotations = loadAnnotations();
let filtered = [];
let currentIndex = -1;
const els = {{
  query: document.getElementById("query"),
  kind: document.getElementById("kind"),
  status: document.getElementById("status"),
  clear: document.getElementById("clear"),
  playTop: document.getElementById("playTop"),
  results: document.getElementById("results"),
  audio: document.getElementById("audio"),
  nowTitle: document.getElementById("nowTitle"),
  nowMeta: document.getElementById("nowMeta"),
  nowPath: document.getElementById("nowPath"),
  prev: document.getElementById("prev"),
  next: document.getElementById("next"),
  select: document.getElementById("select"),
  reject: document.getElementById("reject"),
  copyPath: document.getElementById("copyPath"),
  copySelectedPaths: document.getElementById("copySelectedPaths"),
  copySelectedJson: document.getElementById("copySelectedJson"),
  copyStatus: document.getElementById("copyStatus"),
  copyFallback: document.getElementById("copyFallback"),
  notes: document.getElementById("notes"),
  selectedList: document.getElementById("selectedList"),
  record: document.getElementById("record"),
}};

function loadAnnotations() {{
  try {{
    return JSON.parse(localStorage.getItem(STORE_KEY) || "{{}}");
  }} catch {{
    return {{}};
  }}
}}

function saveAnnotations() {{
  localStorage.setItem(STORE_KEY, JSON.stringify(annotations));
  renderSelectedList();
}}

function annotationFor(asset) {{
  return annotations[asset.asset_id] || {{}};
}}

function statusFor(asset) {{
  return annotationFor(asset).status || asset.status || "";
}}

function tokensFor(value) {{
  return String(value || "").toLowerCase().split(/[^a-z0-9]+/).filter(Boolean);
}}

function searchFields(asset) {{
  const localUnindexed = asset.provider === "local";
  const trustedTags = !localUnindexed && asset.kind === "sfx";
  return {{
    title: tokensFor(asset.title),
    tags: trustedTags && Array.isArray(asset.tags) ? asset.tags.map(tag => String(tag).toLowerCase()) : [],
    priority: tokensFor([localUnindexed ? "" : asset.intent, asset.voice, asset.role, asset.kind, asset.provider].join(" ")),
    body: tokensFor([asset.text, asset.source, asset.notes, localUnindexed ? "" : asset.reaper_path, localUnindexed ? "" : asset.original_path].join(" ")),
  }};
}}

function termScore(term, fields, haystack) {{
  if (fields.tags.includes(term)) return 140;
  if (fields.title.includes(term)) return 120;
  if (fields.priority.includes(term)) return 95;
  if (fields.body.includes(term)) return 70;

  const tokens = [...fields.title, ...fields.tags, ...fields.priority, ...fields.body];
  if (term.length <= 3) {{
    return 0;
  }}

  if (fields.title.some(token => token.startsWith(term))) return 80;
  if (fields.tags.some(token => token.startsWith(term))) return 75;
  if (fields.priority.some(token => token.startsWith(term))) return 60;
  if (tokens.some(token => token.includes(term))) return 35;
  if (haystack.includes(term)) return 10;
  return 0;
}}

function assetSearchScore(asset, terms, haystack) {{
  if (!terms.length) return 0;
  const fields = searchFields(asset);
  let score = 0;
  for (const term of terms) {{
    const value = termScore(term, fields, haystack);
    if (!value) return 0;
    score += value;
  }}
  const status = statusFor(asset).toLowerCase();
  if (status === "selected") score += 12;
  if (asset.kind === "sfx") score += 3;
  return score;
}}

function applyFilters() {{
  const query = els.query.value.trim().toLowerCase();
  const terms = query.split(/\\s+/).filter(Boolean);
  const kind = els.kind.value;
  const wantedStatus = els.status.value;
  const scored = [];
  ASSETS.forEach((asset, originalIndex) => {{
    if (kind && asset.kind !== kind) return false;
    const status = statusFor(asset).toLowerCase();
    if (wantedStatus === "selected" && status !== "selected") return false;
    if (wantedStatus === "rejected" && status !== "rejected") return false;
    if (wantedStatus === "needs" && !status.includes("needs")) return false;
    const haystack = asset.search_text.toLowerCase() + " " + (annotationFor(asset).notes || "").toLowerCase();
    const score = assetSearchScore(asset, terms, haystack);
    if (terms.length && !score) return false;
    scored.push({{asset, score, originalIndex}});
  }});
  if (terms.length) {{
    scored.sort((a, b) => b.score - a.score || a.asset.title.localeCompare(b.asset.title));
  }} else {{
    scored.sort((a, b) => a.originalIndex - b.originalIndex);
  }}
  filtered = scored.map(row => row.asset);
  currentIndex = filtered.length ? Math.max(0, Math.min(currentIndex, filtered.length - 1)) : -1;
  renderResults();
  renderCurrent(false);
}}

function renderResults() {{
  if (!filtered.length) {{
    els.results.innerHTML = `<div class="row"><div></div><div>No matching assets.</div><div></div></div>`;
    return;
  }}
  els.results.innerHTML = filtered.map((asset, index) => {{
    const status = statusFor(asset).toLowerCase();
    const klass = [
      "row",
      index === currentIndex ? "active" : "",
      status === "selected" ? "selected" : "",
      status === "rejected" ? "rejected" : "",
    ].filter(Boolean).join(" ");
    const chips = [asset.kind, asset.role, asset.provider, asset.voice, asset.licence, statusFor(asset)]
      .filter(Boolean)
      .slice(0, 8)
      .map(value => `<span class="chip">${{escapeHtml(value)}}</span>`)
      .join("");
    return `<article class="${{klass}}" data-index="${{index}}">
      <button data-action="play" data-index="${{index}}">Play</button>
      <div>
        <h3>${{escapeHtml(asset.title)}}</h3>
        <div class="meta">${{escapeHtml(asset.intent || asset.text || asset.source || "")}}</div>
        <div class="chips">${{chips}}</div>
      </div>
      <button data-action="focus" data-index="${{index}}">Use</button>
    </article>`;
  }}).join("");
}}

function renderCurrent(autoplay = false) {{
  const asset = filtered[currentIndex];
  if (!asset) {{
    els.nowTitle.textContent = "No asset selected";
    els.nowMeta.textContent = "";
    els.nowPath.textContent = "";
    els.audio.removeAttribute("src");
    els.notes.value = "";
    els.record.textContent = "";
    return;
  }}
  els.nowTitle.textContent = asset.title;
  const duration = asset.duration_seconds ? `${{Number(asset.duration_seconds).toFixed(2)}}s` : "unknown duration";
  els.nowMeta.textContent = [asset.kind, asset.role, asset.provider, asset.voice, duration, statusFor(asset)].filter(Boolean).join(" | ");
  els.nowPath.textContent = asset.reaper_path || asset.original_path;
  els.audio.src = asset.media_url;
  els.notes.value = annotationFor(asset).notes || "";
  els.record.textContent = JSON.stringify({{...asset, annotation: annotationFor(asset)}}, null, 2);
  renderResults();
  if (autoplay) els.audio.play().catch(() => {{}});
}}

function playIndex(index) {{
  if (index < 0 || index >= filtered.length) return;
  currentIndex = index;
  renderCurrent(true);
}}

function next() {{
  if (!filtered.length) return;
  playIndex((currentIndex + 1 + filtered.length) % filtered.length);
}}

function prev() {{
  if (!filtered.length) return;
  playIndex((currentIndex - 1 + filtered.length) % filtered.length);
}}

function setCurrentStatus(status) {{
  const asset = filtered[currentIndex];
  if (!asset) return;
  annotations[asset.asset_id] = {{
    ...annotationFor(asset),
    status,
    notes: els.notes.value,
    updatedAt: new Date().toISOString(),
  }};
  saveAnnotations();
  applyFilters();
}}

function renderSelectedList() {{
  const rows = selectedAssets()
    .map(asset => `${{asset.title}}\\n${{asset.reaper_path || asset.original_path}}\\n${{annotationFor(asset).notes || ""}}`)
    .join("\\n\\n");
  els.selectedList.textContent = rows || "No selected assets yet.";
}}

function selectedAssets() {{
  return ASSETS.filter(asset => annotationFor(asset).status === "selected" || asset.status === "selected");
}}

function selectedManifest() {{
  return selectedAssets().map(asset => ({{
    asset_id: asset.asset_id,
    title: asset.title,
    kind: asset.kind,
    role: asset.role,
    campaign: asset.campaign,
    provider: asset.provider,
    source_url: asset.source_url,
    licence: asset.licence,
    status: statusFor(asset),
    intent: asset.intent,
    text: asset.text,
    voice: asset.voice,
    tags: asset.tags,
    duration_seconds: asset.duration_seconds,
    reaper_path: asset.reaper_path || asset.original_path,
    media_url: asset.media_url,
    notes: annotationFor(asset).notes || asset.notes || "",
  }}));
}}

async function copyText(text, label) {{
  if (!text) {{
    showCopyStatus(`Nothing to copy for ${{label}}.`);
    return false;
  }}

  els.copyFallback.hidden = true;
  els.copyFallback.value = text;

  if (navigator.clipboard && window.isSecureContext) {{
    try {{
      await navigator.clipboard.writeText(text);
      showCopyStatus(`Copied ${{label}}.`);
      return true;
    }} catch (error) {{
      // Fall through to the older selection-based copy path.
    }}
  }}

  try {{
    els.copyFallback.hidden = false;
    els.copyFallback.focus();
    els.copyFallback.select();
    els.copyFallback.setSelectionRange(0, text.length);
    if (document.execCommand("copy")) {{
      showCopyStatus(`Copied ${{label}}.`);
      els.copyFallback.hidden = true;
      return true;
    }}
  }} catch (error) {{
    // Keep the textarea visible for manual copy.
  }}

  els.copyFallback.hidden = false;
  els.copyFallback.focus();
  els.copyFallback.select();
  showCopyStatus(`Copy failed. Text is selected below; use Ctrl+C.`);
  return false;
}}

function showCopyStatus(message) {{
  els.copyStatus.textContent = message;
}}

function escapeHtml(value) {{
  return String(value).replace(/[&<>"']/g, ch => ({{
    "&": "&amp;",
    "<": "&lt;",
    ">": "&gt;",
    "\\"": "&quot;",
    "'": "&#039;",
  }}[ch]));
}}

els.query.addEventListener("input", applyFilters);
els.query.addEventListener("keydown", event => {{
  if (event.key !== "Enter") return;
  event.preventDefault();
  applyFilters();
  playIndex(0);
}});
els.kind.addEventListener("change", applyFilters);
els.status.addEventListener("change", applyFilters);
els.clear.addEventListener("click", () => {{
  els.query.value = "";
  els.kind.value = "";
  els.status.value = "";
  applyFilters();
}});
els.playTop.addEventListener("click", () => playIndex(currentIndex >= 0 ? currentIndex : 0));
els.prev.addEventListener("click", prev);
els.next.addEventListener("click", next);
els.select.addEventListener("click", () => setCurrentStatus("selected"));
els.reject.addEventListener("click", () => setCurrentStatus("rejected"));
els.copyPath.addEventListener("click", async () => {{
  const asset = filtered[currentIndex];
  if (!asset) return;
  await copyText(asset.reaper_path || asset.original_path, "asset path");
}});
els.copySelectedPaths.addEventListener("click", async () => {{
  const text = selectedAssets().map(asset => asset.reaper_path || asset.original_path).join("\\n");
  await copyText(text, "selected paths");
}});
els.copySelectedJson.addEventListener("click", async () => {{
  await copyText(JSON.stringify(selectedManifest(), null, 2), "selected JSON");
}});
els.notes.addEventListener("change", () => {{
  const asset = filtered[currentIndex];
  if (!asset) return;
  annotations[asset.asset_id] = {{
    ...annotationFor(asset),
    notes: els.notes.value,
    updatedAt: new Date().toISOString(),
  }};
  saveAnnotations();
}});
els.results.addEventListener("click", event => {{
  const button = event.target.closest("button[data-index]");
  if (!button) return;
  const index = Number(button.dataset.index);
  if (button.dataset.action === "play") playIndex(index);
  if (button.dataset.action === "focus") {{
    currentIndex = index;
    renderCurrent(false);
  }}
}});
document.addEventListener("keydown", event => {{
  if (event.target.matches("input, textarea, select")) return;
  if (event.key === " ") {{
    event.preventDefault();
    if (els.audio.paused) els.audio.play().catch(() => {{}});
    else els.audio.pause();
  }}
  if (event.key.toLowerCase() === "n") next();
  if (event.key.toLowerCase() === "p") prev();
  if (event.key.toLowerCase() === "s") setCurrentStatus("selected");
  if (event.key.toLowerCase() === "r") setCurrentStatus("rejected");
}});

renderSelectedList();
applyFilters();
</script>
</body>
</html>
""",
        encoding="utf-8",
    )


def register_on_shelf() -> None:
    shelf_script = ROOT / "scripts" / "lab_shelf.py"
    if not shelf_script.exists():
        print(f"shelf: skipped missing {shelf_script}")
        return
    subprocess.run(
        [
            "python3",
            str(shelf_script),
            "add",
            str(OUT_DIR),
            "--title",
            "Audio Asset Search",
            "--slug",
            "audio-asset-search",
            "--note",
            "Search and audition generated voice clips and SFX assets.",
        ],
        cwd=ROOT,
        check=True,
        stdout=subprocess.DEVNULL,
    )


def with_search_text(asset: AudioAsset) -> AudioAsset:
    values = [
        asset.asset_id,
        asset.title,
        asset.kind,
        asset.role,
        asset.campaign,
        asset.provider,
        asset.source,
        asset.source_url,
        asset.licence,
        asset.status,
        asset.intent,
        asset.text,
        asset.voice,
        " ".join(asset.tags),
        asset.original_path,
        asset.reaper_path,
        asset.notes,
    ]
    return AudioAsset(**{**asdict(asset), "search_text": " ".join(str(value) for value in values if value)})


def stable_asset_id(*parts: Any) -> str:
    return safe_slug("__".join(str(part) for part in parts if part))


def safe_slug(value: str) -> str:
    slug = SLUG_RE.sub("-", value.lower()).strip("-")
    return slug[:180] or "asset"


def unique_tags(values: list[Any]) -> list[str]:
    tags: list[str] = []
    seen: set[str] = set()
    for value in values:
        if value is None:
            continue
        if isinstance(value, (list, tuple)):
            iterable = value
        else:
            iterable = re.split(r"[^A-Za-z0-9]+", str(value))
        for raw in iterable:
            tag = str(raw).strip().lower()
            if not tag or tag in seen:
                continue
            seen.add(tag)
            tags.append(tag)
    return tags


def selected_status_from_path(path: Path, fallback: str) -> str:
    parts = {part.lower() for part in path.parts}
    if "selected" in parts:
        return "selected"
    if "rejected" in parts:
        return "rejected"
    return fallback


def role_from_parts(parts: list[str], kind: str) -> str:
    if kind == "sfx":
        try:
            index = parts.index("sfx")
            return parts[index + 1]
        except (ValueError, IndexError):
            return "sfx"
    if kind == "voice":
        for role in ("tradesperson", "narrator", "app"):
            if role in parts:
                return role
        return "voice"
    return "audio"


def campaign_from_parts(parts: list[str]) -> str:
    if "audio-adverts" in parts:
        index = parts.index("audio-adverts")
        if index + 1 < len(parts):
            return parts[index + 1]
    return ""


def elevenlabs_notes(data: dict[str, Any]) -> str:
    return "; ".join(bit for bit in (response_notes(data), quality_gate_notes(data)) if bit)


def response_notes(data: dict[str, Any]) -> str:
    headers = data.get("responseHeaders") or (data.get("responseMeta") or {}).get("headers") or {}
    bits = []
    for key in ("character-cost", "request-id", "history-item-id", "tts-latency-ms"):
        if headers.get(key):
            bits.append(f"{key}={headers[key]}")
    return "; ".join(bits)


def quality_gate_tags(data: dict[str, Any]) -> list[str]:
    preflight = technical_preflight(data)
    if not preflight:
        return []
    drift = preflight.get("scriptDrift") if isinstance(preflight.get("scriptDrift"), dict) else {}
    transcription = preflight.get("transcription") if isinstance(preflight.get("transcription"), dict) else {}
    backend = transcription.get("backend") if isinstance(transcription.get("backend"), dict) else {}
    return unique_tags(
        [
            "quality-gate",
            "technical-preflight",
            preflight.get("status"),
            drift.get("status"),
            backend.get("provider"),
            backend.get("processorId"),
        ]
    )


def quality_gate_notes(data: dict[str, Any]) -> str:
    preflight = technical_preflight(data)
    if not preflight:
        return ""
    drift = preflight.get("scriptDrift") if isinstance(preflight.get("scriptDrift"), dict) else {}
    transcription = preflight.get("transcription") if isinstance(preflight.get("transcription"), dict) else {}
    backend = transcription.get("backend") if isinstance(transcription.get("backend"), dict) else {}
    bits = [
        f"preflight={preflight.get('status')}",
        f"script-drift={drift.get('status')}",
    ]
    if backend.get("processorId"):
        bits.append(f"transcriber={backend.get('processorId')}")
    if drift.get("extra_leading_words"):
        bits.append("trim-leading=" + " ".join(str(word) for word in drift["extra_leading_words"]))
    transcript = transcription.get("postProcessedText") or transcription.get("text")
    if transcript:
        bits.append(f"transcript={transcript}")
    return "; ".join(bit for bit in bits if bit and not bit.endswith("=None"))


def technical_preflight(data: dict[str, Any]) -> dict[str, Any] | None:
    gate = data.get("qualityGate")
    if not isinstance(gate, dict):
        return None
    preflight = gate.get("technicalPreflight")
    return preflight if isinstance(preflight, dict) else None


def duration_for(path: Path) -> float | None:
    try:
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
            capture_output=True,
            text=True,
        )
    except (OSError, subprocess.CalledProcessError):
        return None
    return as_float(result.stdout.strip())


def as_float(value: Any) -> float | None:
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def file_sha256(path: Path) -> str:
    import hashlib

    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


if __name__ == "__main__":
    raise SystemExit(main())
