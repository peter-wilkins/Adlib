#!/usr/bin/env python3
"""Build a public-safe asset selection workbench from candidate scripts."""

from __future__ import annotations

import argparse
import html
import json
from datetime import datetime
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_SOURCE = ROOT / "docs/adverts/selection-workbenches/2026-06-15-continuum-asset-candidates.json"
DEFAULT_OUT_DIR = ROOT / "local/reports/asset-selection-workbench/2026-06-15-continuum-assets"
HTML_NAME = "index.html"
DATA_NAME = "candidates.json"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path, default=DEFAULT_SOURCE)
    parser.add_argument("--out-dir", type=Path, default=DEFAULT_OUT_DIR)
    args = parser.parse_args()

    data = load_workbench(args.source)
    write_workbench(data, args.out_dir)
    print(f"items: {len(data['items'])}")
    print(f"page: {args.out_dir / HTML_NAME}")
    print(f"data: {args.out_dir / DATA_NAME}")
    return 0


def load_workbench(path: Path) -> dict[str, Any]:
    data = json.loads(path.read_text(encoding="utf-8"))
    if data.get("schema") != "adlib.asset-selection-workbench.v1":
        raise ValueError(f"unsupported schema in {path}")
    items = data.get("items")
    if not isinstance(items, list) or not items:
        raise ValueError(f"workbench has no items: {path}")
    seen: set[str] = set()
    for item in items:
        item_id = str(item.get("id") or "")
        if not item_id:
            raise ValueError("all items need an id")
        if item_id in seen:
            raise ValueError(f"duplicate item id: {item_id}")
        seen.add(item_id)
        for key in ("project", "assetType", "title", "priority"):
            if not item.get(key):
                raise ValueError(f"{item_id} missing {key}")
    return data


def write_workbench(data: dict[str, Any], out_dir: Path) -> None:
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / DATA_NAME).write_text(json.dumps(data, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    (out_dir / HTML_NAME).write_text(render_page(data), encoding="utf-8")


def render_page(data: dict[str, Any]) -> str:
    embedded = json.dumps(data, ensure_ascii=True, separators=(",", ":"))
    title = html.escape(str(data.get("title") or "Asset Selection Workbench"))
    summary = html.escape(str(data.get("summary") or ""))
    selection_note = html.escape(str(data.get("selectionNote") or ""))
    generated_at = html.escape(datetime.now().astimezone().isoformat(timespec="seconds"))
    return f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>{title}</title>
  <style>
    :root {{
      color-scheme: light dark;
      font-family: Inter, ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
      --bg: #f6f7f2;
      --ink: #17201d;
      --muted: #5e6f69;
      --panel: #ffffff;
      --line: #d7ddd3;
      --accent: #0f766e;
      --accent-2: #b45309;
      --accent-3: #4058a8;
      --picked: #ecfdf5;
    }}
    @media (prefers-color-scheme: dark) {{
      :root {{
        --bg: #101412;
        --ink: #eff4ef;
        --muted: #9cafaa;
        --panel: #18201d;
        --line: #304039;
        --accent: #5eead4;
        --accent-2: #fbbf24;
        --accent-3: #9fb4ff;
        --picked: #123329;
      }}
    }}
    * {{ box-sizing: border-box; }}
    body {{ margin: 0; background: var(--bg); color: var(--ink); }}
    main {{ width: min(1180px, calc(100vw - 24px)); margin: 0 auto; padding: 18px 0 54px; }}
    header {{ display: grid; gap: 8px; margin-bottom: 14px; }}
    h1 {{ margin: 0; font-size: clamp(1.7rem, 3vw, 2.8rem); letter-spacing: 0; }}
    .meta {{ color: var(--muted); line-height: 1.45; }}
    .toolbar {{
      position: sticky;
      top: 0;
      z-index: 5;
      display: grid;
      grid-template-columns: minmax(180px, 1fr) minmax(140px, .45fr) minmax(140px, .45fr) auto auto;
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
    button {{ cursor: pointer; }}
    button.primary {{ border-color: var(--accent); color: var(--ink); font-weight: 700; }}
    .countbar {{ display: flex; flex-wrap: wrap; gap: 8px; margin: 12px 0 0; }}
    .pill {{
      border: 1px solid var(--line);
      border-radius: 999px;
      padding: 4px 10px;
      color: var(--muted);
      background: color-mix(in oklab, var(--panel) 88%, transparent);
      font-size: .9rem;
    }}
    .grid {{ display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 12px; margin-top: 14px; }}
    .card {{
      display: grid;
      gap: 10px;
      min-width: 0;
      border: 1px solid var(--line);
      border-radius: 8px;
      padding: 12px;
      background: var(--panel);
    }}
    .card.picked {{ background: var(--picked); border-color: color-mix(in oklab, var(--accent) 50%, var(--line)); }}
    .card-head {{ display: grid; grid-template-columns: minmax(0, 1fr) auto; gap: 10px; align-items: start; }}
    h2 {{ margin: 0; font-size: 1.08rem; letter-spacing: 0; }}
    .pick {{
      display: inline-grid;
      grid-template-columns: 22px auto;
      align-items: center;
      gap: 7px;
      min-height: 32px;
      color: var(--ink);
      font-weight: 700;
      white-space: nowrap;
    }}
    .pick input {{ min-height: 22px; width: 22px; padding: 0; }}
    .chips {{ display: flex; flex-wrap: wrap; gap: 6px; }}
    .chip {{ border: 1px solid var(--line); border-radius: 999px; padding: 2px 8px; color: var(--muted); font-size: .82rem; }}
    .chip.high {{ color: var(--accent); border-color: color-mix(in oklab, var(--accent) 45%, var(--line)); }}
    .chip.medium {{ color: var(--accent-2); border-color: color-mix(in oklab, var(--accent-2) 45%, var(--line)); }}
    .chip.low {{ color: var(--accent-3); border-color: color-mix(in oklab, var(--accent-3) 45%, var(--line)); }}
    .copy {{
      white-space: pre-wrap;
      overflow-wrap: anywhere;
      line-height: 1.5;
      border-top: 1px solid var(--line);
      padding-top: 8px;
    }}
    details {{ border-top: 1px solid var(--line); padding-top: 8px; }}
    summary {{ cursor: pointer; color: var(--muted); }}
    .brief {{ color: var(--muted); line-height: 1.45; }}
    .empty {{ padding: 32px; text-align: center; color: var(--muted); border: 1px dashed var(--line); border-radius: 8px; }}
    @media (max-width: 860px) {{
      .toolbar {{ grid-template-columns: 1fr; position: static; }}
      .grid {{ grid-template-columns: 1fr; }}
      .card-head {{ grid-template-columns: 1fr; }}
      .pick {{ white-space: normal; }}
    }}
  </style>
</head>
<body>
  <main>
    <header>
      <h1>{title}</h1>
      <div class="meta">{summary}</div>
      <div class="meta">{selection_note}</div>
      <div class="meta">Generated {generated_at}. Ticks are saved in this browser.</div>
    </header>
    <section class="toolbar">
      <input id="q" type="search" placeholder="search project, angle, script" autocomplete="off">
      <select id="project"><option value="">All projects</option></select>
      <select id="type"><option value="">All asset types</option></select>
      <button id="pickedOnly">Picked only</button>
      <button id="export" class="primary">Export picks</button>
    </section>
    <section class="countbar">
      <span id="visibleCount" class="pill"></span>
      <span id="pickedCount" class="pill"></span>
      <button id="clear" class="pill">Clear ticks</button>
    </section>
    <section id="list" class="grid"></section>
  </main>
  <script>
    const DATA = {embedded};
    const storageKey = `adlib-selection:${{DATA.batchId}}`;
    const q = document.querySelector("#q");
    const project = document.querySelector("#project");
    const type = document.querySelector("#type");
    const list = document.querySelector("#list");
    const visibleCount = document.querySelector("#visibleCount");
    const pickedCount = document.querySelector("#pickedCount");
    const pickedOnly = document.querySelector("#pickedOnly");
    const exportButton = document.querySelector("#export");
    const clearButton = document.querySelector("#clear");
    let showPickedOnly = false;
    let picked = loadPicked();

    function loadPicked() {{
      try {{
        const value = JSON.parse(localStorage.getItem(storageKey) || "[]");
        return new Set(Array.isArray(value) ? value : []);
      }} catch {{
        return new Set();
      }}
    }}

    function savePicked() {{
      localStorage.setItem(storageKey, JSON.stringify([...picked].sort()));
    }}

    function esc(value) {{
      return String(value ?? "").replace(/[&<>"']/g, (ch) => ({{
        "&": "&amp;",
        "<": "&lt;",
        ">": "&gt;",
        '"': "&quot;",
        "'": "&#039;"
      }}[ch]));
    }}

    function asList(values) {{
      return (values || []).filter(Boolean).map((value) => `<span class="chip">${{esc(value)}}</span>`).join("");
    }}

    function textFor(item) {{
      return [
        item.project, item.assetType, item.priority, item.duration, item.audience,
        item.angle, item.domain, item.voiceDirection, item.title, item.scriptText,
        item.visualBrief, item.audioBrief, item.productionNotes
      ].join(" ").toLowerCase();
    }}

    function matches(item) {{
      const needle = q.value.trim().toLowerCase();
      if (needle && !textFor(item).includes(needle)) return false;
      if (project.value && item.project !== project.value) return false;
      if (type.value && item.assetType !== type.value) return false;
      if (showPickedOnly && !picked.has(item.id)) return false;
      return true;
    }}

    function render() {{
      const rows = DATA.items.filter(matches).sort((a, b) => {{
        const pa = a.priority === "high" ? 0 : a.priority === "medium" ? 1 : 2;
        const pb = b.priority === "high" ? 0 : b.priority === "medium" ? 1 : 2;
        return pa - pb || a.project.localeCompare(b.project) || a.title.localeCompare(b.title);
      }});
      visibleCount.textContent = `${{rows.length}} visible`;
      pickedCount.textContent = `${{picked.size}} picked`;
      if (!rows.length) {{
        list.innerHTML = `<div class="empty">No matching assets.</div>`;
        return;
      }}
      list.innerHTML = rows.map((item) => {{
        const isPicked = picked.has(item.id);
        const mainCopy = item.scriptText || item.visualBrief || item.audioBrief || "";
        const extraBriefs = [
          item.scriptText && item.visualBrief ? ["Visual", item.visualBrief] : null,
          item.scriptText && item.audioBrief ? ["Audio", item.audioBrief] : null,
          !item.scriptText && item.visualBrief && item.audioBrief ? ["Audio", item.audioBrief] : null,
          item.productionNotes ? ["Production", item.productionNotes] : null,
          item.voiceDirection ? ["Voice", item.voiceDirection] : null,
          item.claimPosture ? ["Claims", item.claimPosture] : null
        ].filter(Boolean);
        return `<article class="card ${{isPicked ? "picked" : ""}}" data-id="${{esc(item.id)}}">
          <div class="card-head">
            <div>
              <h2>${{esc(item.title)}}</h2>
              <div class="meta">${{esc(item.project)}}${{item.duration ? " · " + esc(item.duration) : ""}}${{item.domain ? " · " + esc(item.domain) : ""}}</div>
            </div>
            <label class="pick"><input type="checkbox" ${{isPicked ? "checked" : ""}} aria-label="Pick ${{esc(item.title)}}"> Pick</label>
          </div>
          <div class="chips">
            <span class="chip ${{esc(item.priority)}}">${{esc(item.priority)}}</span>
            <span class="chip">${{esc(item.assetType.replaceAll("_", " "))}}</span>
            ${{item.audience ? `<span class="chip">${{esc(item.audience)}}</span>` : ""}}
            ${{item.angle ? `<span class="chip">${{esc(item.angle)}}</span>` : ""}}
          </div>
          <div class="copy">${{esc(mainCopy)}}</div>
          ${{extraBriefs.length ? `<details><summary>Brief details</summary>${{extraBriefs.map(([label, value]) => `<p class="brief"><strong>${{esc(label)}}:</strong> ${{esc(value)}}</p>`).join("")}}<div class="chips">${{asList(item.sourceTruths)}}</div></details>` : ""}}
        </article>`;
      }}).join("");
    }}

    for (const value of [...new Set(DATA.items.map((item) => item.project))].sort()) {{
      const option = document.createElement("option");
      option.value = value;
      option.textContent = value;
      project.appendChild(option);
    }}

    for (const value of [...new Set(DATA.items.map((item) => item.assetType))].sort()) {{
      const option = document.createElement("option");
      option.value = value;
      option.textContent = value.replaceAll("_", " ");
      type.appendChild(option);
    }}

    list.addEventListener("change", (event) => {{
      if (event.target.tagName !== "INPUT") return;
      const card = event.target.closest(".card");
      if (!card) return;
      if (event.target.checked) picked.add(card.dataset.id);
      else picked.delete(card.dataset.id);
      savePicked();
      render();
    }});

    q.addEventListener("input", render);
    project.addEventListener("change", render);
    type.addEventListener("change", render);
    pickedOnly.addEventListener("click", () => {{
      showPickedOnly = !showPickedOnly;
      pickedOnly.textContent = showPickedOnly ? "Show all" : "Picked only";
      render();
    }});
    clearButton.addEventListener("click", () => {{
      picked = new Set();
      savePicked();
      render();
    }});
    exportButton.addEventListener("click", () => {{
      const selected = DATA.items.filter((item) => picked.has(item.id));
      const blob = new Blob([JSON.stringify({{
        batchId: DATA.batchId,
        exportedAt: new Date().toISOString(),
        selected
      }}, null, 2)], {{ type: "application/json" }});
      const link = document.createElement("a");
      link.href = URL.createObjectURL(blob);
      link.download = `${{DATA.batchId}}-picked.json`;
      link.click();
      URL.revokeObjectURL(link.href);
    }});

    render();
  </script>
</body>
</html>
"""


if __name__ == "__main__":
    raise SystemExit(main())
