#!/usr/bin/env python3
"""Generate a private workbench page for first-pass audio advert scripts."""

from __future__ import annotations

import html
import hashlib
import json
import shutil
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
OUT_DIR = ROOT / "local" / "reports" / "audio-advert-drafts"
OUT_PATH = OUT_DIR / "index.html"
SNAPSHOT_PATH = OUT_DIR / "drafts.json"
VERSION_PATH = OUT_DIR / "version.json"
MEDIA_DIR = OUT_DIR / "media"


@dataclass(frozen=True)
class ScriptLine:
    speaker: str
    text: str


@dataclass(frozen=True)
class SfxIntent:
    beat_id: str
    placement: str
    purpose: str
    desired_sound: str
    mood: str
    duration_seconds: str
    license_priority: str
    search_terms: tuple[str, ...]
    avoid: tuple[str, ...]
    first_guess_rule: str


@dataclass(frozen=True)
class AdvertDraft:
    script_id: str
    product: str
    duration: str
    target_audience: str
    intent: str
    tone: str
    truth_status: str
    source_basis: tuple[str, ...]
    checks: tuple[str, ...]
    next_edit_question: str
    lines: tuple[ScriptLine, ...]
    sfx_intents: tuple[SfxIntent, ...] = ()


@dataclass(frozen=True)
class AudioPreview:
    preview_id: str
    label: str
    description: str
    source_path: Path


LOCAL_AUDIO_PREVIEWS: tuple[AudioPreview, ...] = (
    AudioPreview(
        preview_id="jobdone-dog-callback-v0",
        label="JobDone dog callback v0",
        description="Dummy voice bed plus selected dog-bark previews; proves the repeatable FFmpeg graph renders.",
        source_path=ROOT / "data" / "processed" / "audio-ads" / "renders" / "jobdone-dog-callback-v0.wav",
    ),
)
GENERATED_AUDIO_GLOBS: tuple[tuple[str, str], ...] = (
    (
        "JobDone dog callback ElevenLabs",
        "Whole-advert dialogue take generated through ElevenLabs Text to Dialogue.",
        "data/raw/audio-ads/jobdone-dog-callback/elevenlabs/*",
    ),
)


DRAFTS: tuple[AdvertDraft, ...] = (
    AdvertDraft(
        script_id="JD_ad01_yorkshire_interrupt",
        product="JobDone",
        duration="30 seconds",
        target_audience="Self-employed tradespeople who hate admin and enterprise software language.",
        intent="Make JobDone feel like a practical job diary, not SaaS theatre.",
        tone="Dry, grounded, Yorkshire interruption.",
        truth_status="Product Truth constrained. Ready for Peter edit before audio.",
        source_basis=(
            "docs/product-truths/2026-06-02-jobdone.md",
            "docs/adverts/jobdone-script-seeds.md",
        ),
        checks=(
            "Shows Capture -> Confirmation -> Timeline -> Recall.",
            "Does not claim automatic invoicing, accounting, or always-correct AI.",
            "Uses Contact and Location language instead of Customer as the system concept.",
        ),
        next_edit_question="Should the Yorkshire voice be funny-gruff, warm-gruff, or almost deadpan?",
        lines=(
            ScriptLine("Corporate voice", "Introducing the next generation field productivity intelligence platform for modern service operators."),
            ScriptLine("Yorkshireman", "No. Stop that."),
            ScriptLine("Yorkshireman", "It's a job diary, lad. You finish a job, say what happened before you drive off."),
            ScriptLine("App voice", "Captured: Mrs Jones. Kitchen tap. Washer replaced. Isolation valve stiff."),
            ScriptLine("Yorkshireman", "You check it, confirm it, and later ask what you did there last time."),
            ScriptLine("App voice", "Confirmed entry found: Mrs Jones, kitchen tap, washer replaced."),
            ScriptLine("Yorkshireman", "JobDone. Get it out of your head before you forget it."),
        ),
    ),
    AdvertDraft(
        script_id="JD_ad02_dog_callback",
        product="JobDone",
        duration="30 seconds",
        target_audience="Tradespeople who remember the job but forget the weird site details until too late.",
        intent="Show recall with a memorable comedy callback: the detail is not just the sink, it is Charlie the ankle-biting dog.",
        tone="Cheerful site comedy. Happy-chappy tradesperson, calm English actress narrator with a subtly sexy warmth, and real life still messy, funny, and human.",
        truth_status="Product Truth constrained. Ready for Peter edit before audio.",
        source_basis=(
            "docs/product-truths/2026-06-02-jobdone.md",
            "docs/adverts/jobdone-script-seeds.md",
            "Peter's 2026-06-02 dog callback note.",
        ),
        checks=(
            "Recall is grounded in a confirmed Entry.",
            "The dog detail is captured as ordinary job context, not magic inference.",
            "The callback demonstrates why small remembered details matter without pretending AI controls real life.",
        ),
        next_edit_question="Should Charlie be heard as one bark, a chase, or just the tradesperson shouting his name?",
        lines=(
            ScriptLine("Tradesperson", "Alright then, Mrs Jones. Bye."),
            ScriptLine("Scene", "Front door shuts."),
            ScriptLine("Device", "Small friendly beep: recording starts."),
            ScriptLine("Tradesperson", "Replaced the kitchen sink washer. Isolation valve is stiff here."),
            ScriptLine("Device", "Small friendly beep: note saved."),
            ScriptLine("Dog", "Small dog bark behind the closed door."),
            ScriptLine("Tradesperson", "Oh, and Charlie the dog bites ankles."),
            ScriptLine("Narrator", "Doodle doo doo. Doodle doo doo. Doodle doo doo. Three months later..."),
            ScriptLine("Scene", "Footsteps approach the same front door. Doorbell rings."),
            ScriptLine("App voice", "Results for Mrs Jones. Kitchen sink washer replaced. Isolation valve stiff. Charlie the dog bites ankles."),
            ScriptLine("Device", "Small clean beep: result found."),
            ScriptLine("Tradesperson", "Hmph, Charlie."),
            ScriptLine("Narrator", "JobDone. Remember the job."),
            ScriptLine("Dog", "Distant eager bark, footsteps, small kerfuffle as Charlie steals something."),
            ScriptLine("Tradesperson", "Oi, Charlie! Come back with that."),
        ),
        sfx_intents=(
            SfxIntent(
                beat_id="charlie_first_bite",
                placement="After opening job detail, before the tradesperson says 'Ow.'",
                purpose="Make the remembered site detail funny and concrete without derailing the product point.",
                desired_sound="small dog bark plus brief frantic scramble or collar movement",
                mood="comic, close, sudden, slightly chaotic, not scary",
                duration_seconds="0.8-1.8",
                license_priority="cc0",
                search_terms=(
                    "dog bark",
                    "small dog bark",
                    "dog scramble",
                    "frantic dog bark",
                ),
                avoid=(
                    "aggressive attack dog",
                    "long dog ambience bed",
                    "large scary dog",
                    "recognisable copyrighted media",
                ),
                first_guess_rule="Pick one short CC0 Freesound candidate that reads as a small comic dog, then place it under the 'Ow' beat.",
            ),
            SfxIntent(
                beat_id="charlie_callback_warning",
                placement="After the app recalls Charlie, before or under the tradesperson says 'Oh, Charlie!'",
                purpose="Create the payoff that JobDone remembered the weird practical detail before the next visit.",
                desired_sound="one short dog bark or distant eager bark",
                mood="callback, recognisable, lighter than the first bark, friendly rather than threatening",
                duration_seconds="0.4-1.2",
                license_priority="cc0",
                search_terms=(
                    "single dog bark",
                    "small dog bark",
                    "distant dog bark",
                ),
                avoid=(
                    "growling",
                    "dog attack",
                    "long barking sequence",
                    "sound that competes with the recalled app voice",
                ),
                first_guess_rule="Prefer a shorter/lighter bark than the opening SFX so Peter can ask for 'longer' or 'more frantic' only if the callback feels too small.",
            ),
        ),
    ),
    AdvertDraft(
        script_id="JD_ad03_customer_callback",
        product="JobDone",
        duration="30 seconds",
        target_audience="Tradespeople who get repeat visits, callbacks, and awkward 'what did you do last time?' questions.",
        intent="Make the value concrete during a real callback.",
        tone="Practical radio scene.",
        truth_status="Product Truth constrained. Ready for Peter edit before audio.",
        source_basis=(
            "docs/product-truths/2026-06-02-jobdone.md",
            "docs/adverts/jobdone-script-seeds.md",
        ),
        checks=(
            "Uses a recalled confirmed note rather than invented advice.",
            "Avoids promising customer comms automation.",
            "Shows low-admin phone capture.",
        ),
        next_edit_question="Should this one use a named trade, like plumber or electrician, or stay generic?",
        lines=(
            ScriptLine("Phone", "Hi, you came out a while back. Do you remember what you changed on the tap?"),
            ScriptLine("Tradesperson", "Give me a second."),
            ScriptLine("Tradesperson", "JobDone, recall Mrs Jones tap."),
            ScriptLine("App voice", "Confirmed entry: kitchen tap, washer replaced, isolation valve stiff."),
            ScriptLine("Tradesperson", "Yes. I replaced the washer, and noted the isolation valve was stiff."),
            ScriptLine("Narrator", "When every job becomes a proper memory, callbacks get easier."),
            ScriptLine("Narrator", "JobDone. Capture, confirm, recall."),
        ),
    ),
    AdvertDraft(
        script_id="JD_ad04_van_diary",
        product="JobDone",
        duration="15 seconds",
        target_audience="Solo operators who finish jobs in the van and lose details by the end of the day.",
        intent="A simple cutdown that can become the first paid audio test.",
        tone="Plain spoken, sincere practical.",
        truth_status="Product Truth constrained. Shortlist candidate for first ElevenLabs test after approval.",
        source_basis=(
            "docs/product-truths/2026-06-02-jobdone.md",
            "docs/adverts/jobdone-script-seeds.md",
        ),
        checks=(
            "One feature: remember the job properly.",
            "No broad platform claims.",
            "Fits a short voice ad without jargon.",
        ),
        next_edit_question="Is this too plain, or is plain exactly right for the first test?",
        lines=(
            ScriptLine("Narrator", "You finish the job. You sit in the van. You say what happened."),
            ScriptLine("App voice", "Captured. Ready to confirm."),
            ScriptLine("Narrator", "Later, ask for the right job detail back from your confirmed timeline."),
            ScriptLine("Narrator", "JobDone. Your work, remembered properly."),
        ),
    ),
    AdvertDraft(
        script_id="JD_ad05_team_parent_manager",
        product="JobDone",
        duration="30 seconds",
        target_audience="Parents and small-team managers who need agreed jobs, follow-ups, and evidence to stay visible.",
        intent="Move the old chores-for-access idea into JobDone Team: not a separate product, a team/household coordination angle.",
        tone="Calm practical coordination, not surveillance.",
        truth_status="Concept seed only. Team is named in JobDone's product language, but this needs a fresh Product Truth pass before public copy.",
        source_basis=(
            "docs/product-truths/2026-06-02-jobdone.md",
            "Peter's 2026-06-02 note: target parents and managers through the JobDone Team section.",
        ),
        checks=(
            "Frames Team as shared confirmed job memory, not a parental-control product.",
            "Avoids claiming finished rewards, payments, router control, or HR workflow.",
            "Needs JobDone Team reality check before paid generation.",
        ),
        next_edit_question="Should the Team advert first target households, small trade crews, or managers?",
        lines=(
            ScriptLine("Manager", "Did anyone sort the gate, call the supplier, and check the van keys?"),
            ScriptLine("Team member", "I did the gate. Not the supplier."),
            ScriptLine("Narrator", "Some jobs do not need a meeting. They need a confirmed note everyone can trust."),
            ScriptLine("App voice", "Gate fixed. Supplier still open. Van keys with Sam."),
            ScriptLine("Parent", "Same at home. If it matters, capture it. If it is done, confirm it."),
            ScriptLine("Narrator", "JobDone Team. Shared job memory without turning life into admin."),
        ),
    ),
)


def main() -> int:
    generated = datetime.now().astimezone().isoformat(timespec="seconds")
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    audio_previews = publish_audio_previews(collect_audio_previews())
    SNAPSHOT_PATH.write_text(json.dumps(snapshot(generated, audio_previews), indent=2) + "\n", encoding="utf-8")
    VERSION_PATH.write_text(json.dumps({"generatedAt": generated}) + "\n", encoding="utf-8")
    OUT_PATH.write_text(render_page(generated, audio_previews), encoding="utf-8")
    print(f"wrote: {OUT_PATH}")
    return 0


def publish_audio_previews(
    previews: tuple[AudioPreview, ...] | None = None,
    media_dir: Path = MEDIA_DIR,
) -> list[dict[str, object]]:
    if previews is None:
        previews = LOCAL_AUDIO_PREVIEWS
    media_dir.mkdir(parents=True, exist_ok=True)
    published: list[dict[str, object]] = []
    for preview in previews:
        suffix = preview.source_path.suffix or ".wav"
        filename = f"{preview.preview_id}{suffix}"
        media_path = media_dir / filename
        href = f"media/{filename}"
        item: dict[str, object] = {
            "previewId": preview.preview_id,
            "label": preview.label,
            "description": preview.description,
            "sourcePath": str(preview.source_path),
            "href": href,
            "available": preview.source_path.exists(),
        }
        if preview.source_path.exists():
            shutil.copy2(preview.source_path, media_path)
            item.update(
                {
                    "bytes": media_path.stat().st_size,
                    "sha256": file_sha256(media_path),
                }
            )
        elif media_path.exists():
            media_path.unlink()
        published.append(item)
    return published


def collect_audio_previews() -> tuple[AudioPreview, ...]:
    previews = list(LOCAL_AUDIO_PREVIEWS)
    seen = {preview.source_path for preview in previews}
    for label_prefix, description, glob_pattern in GENERATED_AUDIO_GLOBS:
        for path in sorted(ROOT.glob(glob_pattern)):
            if path in seen or path.suffix.lower() not in {".mp3", ".wav", ".ogg", ".opus", ".m4a"}:
                continue
            previews.append(
                AudioPreview(
                    preview_id=path.stem,
                    label=f"{label_prefix}: {path.stem}",
                    description=description,
                    source_path=path,
                )
            )
            seen.add(path)
    return tuple(previews)


def file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def snapshot(generated: str, audio_previews: list[dict[str, object]] | None = None) -> dict[str, object]:
    return {
        "schemaVersion": "workflow-manager.audio-advert-drafts.v1",
        "generatedAt": generated,
        "audioPreviews": audio_previews or [],
        "drafts": [
            {
                "scriptId": draft.script_id,
                "product": draft.product,
                "duration": draft.duration,
                "targetAudience": draft.target_audience,
                "intent": draft.intent,
                "tone": draft.tone,
                "truthStatus": draft.truth_status,
                "sourceBasis": list(draft.source_basis),
                "checks": list(draft.checks),
                "nextEditQuestion": draft.next_edit_question,
                "lines": [{"speaker": line.speaker, "text": line.text} for line in draft.lines],
                "sfxIntents": [
                    {
                        "beatId": intent.beat_id,
                        "placement": intent.placement,
                        "purpose": intent.purpose,
                        "desiredSound": intent.desired_sound,
                        "mood": intent.mood,
                        "durationSeconds": intent.duration_seconds,
                        "licensePriority": intent.license_priority,
                        "searchTerms": list(intent.search_terms),
                        "avoid": list(intent.avoid),
                        "firstGuessRule": intent.first_guess_rule,
                    }
                    for intent in draft.sfx_intents
                ],
            }
            for draft in DRAFTS
        ],
    }


def render_page(generated: str, audio_previews: list[dict[str, object]] | None = None) -> str:
    cards = "\n".join(render_draft(draft) for draft in DRAFTS)
    audio_panel = render_audio_previews(audio_previews or [])
    return f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Audio Advert Draft Board</title>
  <style>
    :root {{
      color-scheme: light dark;
      font-family: Inter, ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
      line-height: 1.45;
      --bg: #f6f7f4;
      --ink: #1d242b;
      --muted: #65717b;
      --panel: #ffffff;
      --line: #d9dfd2;
      --accent: #0f766e;
      --soft: #eef4ef;
      --warn: #8a4b0f;
    }}
    @media (prefers-color-scheme: dark) {{
      :root {{
        --bg: #101417;
        --ink: #f2f5f3;
        --muted: #a7b0ab;
        --panel: #1a2024;
        --line: #334039;
        --accent: #5eead4;
        --soft: #18251f;
        --warn: #fbbf24;
      }}
    }}
    * {{ box-sizing: border-box; }}
    body {{
      margin: 0;
      background: var(--bg);
      color: var(--ink);
    }}
    main {{
      width: min(1160px, calc(100vw - 28px));
      margin: 0 auto;
      padding: 28px 0 72px;
    }}
    header {{
      display: grid;
      gap: 10px;
      margin-bottom: 18px;
    }}
    h1 {{
      margin: 0;
      font-size: clamp(2rem, 5vw, 4rem);
      line-height: 1;
      letter-spacing: 0;
    }}
    .lede {{
      margin: 0;
      max-width: 820px;
      color: var(--muted);
      font-size: 1.05rem;
    }}
    .guide {{
      display: grid;
      gap: 6px;
      margin: 18px 0 22px;
      padding: 14px 16px;
      background: var(--soft);
      border: 1px solid var(--line);
      border-radius: 8px;
    }}
    .guide p {{
      margin: 0;
    }}
    .board {{
      display: grid;
      gap: 16px;
    }}
    .audio-panel {{
      margin-bottom: 22px;
    }}
    .audio-list {{
      display: grid;
      gap: 12px;
    }}
    .audio-card {{
      display: grid;
      gap: 10px;
      padding: 14px;
      background: var(--panel);
      border: 1px solid var(--line);
      border-radius: 8px;
    }}
    .audio-card h3 {{
      margin: 0;
      font-size: 1rem;
    }}
    audio {{
      width: 100%;
      min-height: 40px;
    }}
    .meta {{
      margin: 0;
      color: var(--muted);
      font-size: 0.88rem;
      overflow-wrap: anywhere;
    }}
    article {{
      display: grid;
      gap: 14px;
      padding: 18px;
      background: var(--panel);
      border: 1px solid var(--line);
      border-radius: 8px;
    }}
    .draft-head {{
      display: grid;
      grid-template-columns: 1fr auto;
      gap: 12px;
      align-items: start;
    }}
    h2 {{
      margin: 0;
      font-size: 1.25rem;
      line-height: 1.2;
    }}
    .pill {{
      display: inline-block;
      padding: 4px 8px;
      border-radius: 999px;
      background: var(--soft);
      color: var(--accent);
      border: 1px solid var(--line);
      font-size: 0.82rem;
      font-weight: 700;
      white-space: nowrap;
    }}
    dl {{
      display: grid;
      grid-template-columns: minmax(120px, 180px) 1fr;
      gap: 8px 14px;
      margin: 0;
    }}
    dt {{
      color: var(--muted);
      font-size: 0.9rem;
    }}
    dd {{
      margin: 0;
    }}
    .script {{
      display: grid;
      gap: 8px;
      margin: 0;
      padding: 0;
      list-style: none;
    }}
    .line {{
      display: grid;
      grid-template-columns: minmax(92px, 130px) 1fr;
      gap: 10px;
      padding: 8px 0;
      border-top: 1px solid var(--line);
    }}
    .speaker {{
      color: var(--accent);
      font-weight: 800;
    }}
    .checks {{
      margin: 0;
      padding-left: 20px;
      color: var(--muted);
    }}
    .sfx-intents {{
      display: grid;
      gap: 10px;
    }}
    .sfx-intent {{
      display: grid;
      gap: 8px;
      padding: 12px;
      border: 1px solid var(--line);
      border-radius: 8px;
      background: var(--soft);
    }}
    .sfx-intent h3 {{
      margin: 0;
      font-size: 1rem;
    }}
    .chips {{
      display: flex;
      flex-wrap: wrap;
      gap: 6px;
      margin: 0;
      padding: 0;
      list-style: none;
    }}
    .chip {{
      padding: 3px 7px;
      border-radius: 999px;
      border: 1px solid var(--line);
      background: var(--panel);
      color: var(--muted);
      font-size: 0.82rem;
    }}
    .warning {{
      color: var(--warn);
      font-weight: 800;
    }}
    a {{ color: var(--accent); }}
    footer {{
      margin-top: 22px;
      color: var(--muted);
      font-size: 0.9rem;
    }}
  </style>
</head>
<body>
  <main>
    <header>
      <h1>Audio Advert Draft Board</h1>
      <p class="lede">First-pass scripts for dogfooding the Audio Advert Generator. Each draft has a target audience, a truth status, and a next edit question before any paid ElevenLabs generation.</p>
      <p class="lede">Generated {html.escape(generated)}. This page polls <code>version.json</code> and reloads itself when regenerated.</p>
    </header>
    <section class="guide" aria-label="How to use">
      <p><strong>Use it like this:</strong> pick one audience, choose whether the script is honest enough, then edit for voice before generating audio.</p>
      <p><strong>Rule:</strong> Product Truth first. Paid audio only after Peter approves exact script, voice, provider, and spend.</p>
    </section>
    {audio_panel}
    <section class="board" aria-label="Advert drafts">
      {cards}
    </section>
    <footer>
      Source generator: <code>scripts/generate_audio_advert_drafts.py</code>. Snapshot: <a href="drafts.json">drafts.json</a>.
    </footer>
  </main>
  <script>
    const initialGeneratedAt = {json.dumps(generated)};
    async function checkForUpdate() {{
      try {{
        const response = await fetch("version.json?ts=" + Date.now(), {{ cache: "no-store" }});
        if (!response.ok) return;
        const version = await response.json();
        if (version.generatedAt && version.generatedAt !== initialGeneratedAt) {{
          location.reload();
        }}
      }} catch (_error) {{}}
    }}
    setInterval(checkForUpdate, 8000);
  </script>
</body>
</html>
"""


def render_audio_previews(audio_previews: list[dict[str, object]]) -> str:
    if not audio_previews:
        body = """<p>No local audio previews are registered yet.</p>"""
    else:
        body = "\n".join(render_audio_preview(preview) for preview in audio_previews)
    return f"""<section class="guide audio-panel" aria-label="Local audio previews">
  <h2>Local audio previews</h2>
  <p>Known local WAV renders are copied into this report so the private workbench can play them in the browser.</p>
  <div class="audio-list">
    {body}
  </div>
</section>"""


def render_audio_preview(preview: dict[str, object]) -> str:
    label = html.escape(str(preview["label"]))
    description = html.escape(str(preview["description"]))
    source_path = html.escape(str(preview["sourcePath"]))
    href = html.escape(str(preview["href"]))
    if preview.get("available"):
        byte_count = int(preview.get("bytes", 0))
        sha256 = html.escape(str(preview.get("sha256", "")))
        player = f"""<audio controls preload="metadata" src="{href}"></audio>
      <p class="meta"><a href="{href}">Open audio file</a> | {byte_count:,} bytes | sha256 {sha256}</p>"""
    else:
        player = """<p class="warning">Render not found yet. Run <code>docs/adverts/jobdone-dog-callback/render.sh</code>.</p>"""
    return f"""<article class="audio-card">
    <h3>{label}</h3>
    <p>{description}</p>
    {player}
    <p class="meta">Local source: <code>{source_path}</code></p>
  </article>"""


def render_draft(draft: AdvertDraft) -> str:
    checks = "\n".join(f"<li>{html.escape(check)}</li>" for check in draft.checks)
    sources = ", ".join(html.escape(source) for source in draft.source_basis)
    lines = "\n".join(render_line(line) for line in draft.lines)
    sfx = render_sfx_intents(draft.sfx_intents)
    truth_class = "warning" if "Concept seed" in draft.truth_status else ""
    return f"""<article id="{html.escape(draft.script_id)}">
  <div class="draft-head">
    <div>
      <h2>{html.escape(draft.script_id)}</h2>
      <span class="pill">{html.escape(draft.product)}</span>
    </div>
    <span class="pill">{html.escape(draft.duration)}</span>
  </div>
  <dl>
    <dt>Target audience</dt><dd>{html.escape(draft.target_audience)}</dd>
    <dt>Intent</dt><dd>{html.escape(draft.intent)}</dd>
    <dt>Tone</dt><dd>{html.escape(draft.tone)}</dd>
    <dt>Truth status</dt><dd class="{truth_class}">{html.escape(draft.truth_status)}</dd>
    <dt>Source basis</dt><dd>{sources}</dd>
  </dl>
  <ol class="script">
    {lines}
  </ol>
  {sfx}
  <div>
    <strong>Truth checks</strong>
    <ul class="checks">
      {checks}
    </ul>
  </div>
  <p><strong>Next edit question:</strong> {html.escape(draft.next_edit_question)}</p>
</article>"""


def render_sfx_intents(intents: tuple[SfxIntent, ...]) -> str:
    if not intents:
        return ""
    cards = "\n".join(render_sfx_intent(intent) for intent in intents)
    return f"""<section class="sfx-intents" aria-label="Sound effect intents">
  <strong>Agent-first SFX intents</strong>
  {cards}
</section>"""


def render_sfx_intent(intent: SfxIntent) -> str:
    search_terms = "\n".join(f'<li class="chip">{html.escape(term)}</li>' for term in intent.search_terms)
    avoid = "\n".join(f'<li class="chip">{html.escape(term)}</li>' for term in intent.avoid)
    return f"""<div class="sfx-intent">
  <h3>{html.escape(intent.beat_id)}</h3>
  <dl>
    <dt>Placement</dt><dd>{html.escape(intent.placement)}</dd>
    <dt>Purpose</dt><dd>{html.escape(intent.purpose)}</dd>
    <dt>Desired sound</dt><dd>{html.escape(intent.desired_sound)}</dd>
    <dt>Mood</dt><dd>{html.escape(intent.mood)}</dd>
    <dt>Duration</dt><dd>{html.escape(intent.duration_seconds)}</dd>
    <dt>Licence priority</dt><dd>{html.escape(intent.license_priority)}</dd>
    <dt>First guess rule</dt><dd>{html.escape(intent.first_guess_rule)}</dd>
  </dl>
  <div>
    <strong>Search terms</strong>
    <ul class="chips">{search_terms}</ul>
  </div>
  <div>
    <strong>Avoid</strong>
    <ul class="chips">{avoid}</ul>
  </div>
</div>"""


def render_line(line: ScriptLine) -> str:
    return f"""<li class="line">
  <span class="speaker">{html.escape(line.speaker)}</span>
  <span>{html.escape(line.text)}</span>
</li>"""


if __name__ == "__main__":
    raise SystemExit(main())
