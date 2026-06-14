# Audio Advert Generator

Planning project for turning truthful product spines into copy and audio adverts generated through the ElevenLabs API.

The current rule is product truth before audio generation. Do not spend paid generations on loose slogans until the relevant product has a Product Truth brief.

## Goal

Create reusable product copy, scripts, and audio asset metadata from proven product claims, then build tooling later to stitch adverts from scripts, voice takes, music beds, pauses, and calls to action.

Peter does not want to use his own voice yet. Start with AI-generated voices and later compare performance.

The generated audio assets must be searchable. V0 can use JSON or JSONL
catalogue files because they are easy for agents to inspect and diff. Move to
SQLite when search needs real queries, indexes, or filtering across many
campaigns, voices, tags, costs, and test results.

## Principles

- Start from Product Truth briefs, not aspirational marketing.
- Label claims as proven, working-but-unproven, aspirational, stale, or private-only before writing copy.
- Do not clone real people's voices without explicit rights.
- Prefer stock/library or generated synthetic voices.
- Keep every generated asset indexed with enough metadata to reproduce or audit it.
- Store raw generated audio locally first.
- Make variants cheap: same script, many voices; same voice, many emotional directions.
- Treat voice choice as a marketing test, not personal taste.

## Podcast Advert Script Automation

Research note:
`docs/adverts/podcast-ad-script-automation-research-2026-06-14.md`

Current rule: generate scripts from a structured advert brief, not a blank
prompt. The minimum useful brief is:

```text
Product Truth + audience + advert format + single job + mandatory claims + CTA
```

AdLib should support at least four script outputs:

- `produced_spot_15s`
- `produced_spot_30s`
- `host_read_talking_points_60s`
- `host_read_verbatim_30s`

Script generation should happen before audio generation and should have its own
gate:

- one advert has one job
- first three seconds are concrete
- CTA is singular and hearable
- mandatory copy is separated from optional host talking points
- every claim maps back to Product Truth
- vision trailer claims are labelled as vision, not current truth
- professional disregard filter passes: no competitor slams, contempt phrases,
  or making the audience feel foolish
- no implementation leakage: do not name internal providers, APIs, manifests,
  local paths, or preflight mechanics in public copy unless that is the product
  being sold
- audio recall hook exists: a searchable phrase, spoken URL, or brand-family
  line that helps listeners find the product after hearing the advert

The searched public skills ecosystem did not show a strong podcast-ad-specific
skill. Generic copywriting skills exist, but AdLib's useful edge is local and
domain-specific: Product Truth constraints, reusable audio assets, transcript
gates, render timing, and searchable metadata. Prefer creating a local
`adlib-podcast-ad-writer` skill once the script gate stabilises.

## ElevenLabs Notes

Checked on 2026-05-22:

- Text to Speech docs:
  `https://elevenlabs.io/docs/product/speech-synthesis/overview`
- Text to Speech API docs:
  `https://elevenlabs.io/docs/api-reference/text-to-speech`
- UK/EEA Terms of Service:
  `https://elevenlabs.io/terms-of-use-eu`
- Publish/commercial-use help page:
  `https://help.elevenlabs.io/hc/en-us/articles/13313564601361-Can-I-publish-the-content-I-generate-on-the-platform`

ElevenLabs TTS supports lifelike audio with nuance, pacing, emotional awareness, multiple languages, voice styles, and ad/media use cases.

Every change to text, voice settings, or parameters can create a new paid generation. Save exact inputs and settings before generation.

Terms note that, as between user and ElevenLabs, the user retains rights in output, but ElevenLabs receives broad licences to content for service provision/improvement. Avoid uploading Peter's own voice until comfortable with those terms.

Session update from 2026-06-14:

- Do not put long pronunciation instructions in the TTS text for critical
  repair lines. ElevenLabs may speak the instruction out loud.
- Exact spoken text is safest for technical preflight.
- Bracketed Eleven v3 audio tags can help performance, but are risky until the
  transcription gate proves they did not leak into speech.
- Punctuation can fix pronunciation but create bad timing gaps.
- The `Pond Challenge` case proved that the correct long-term fix is
  ElevenLabs pronunciation dictionary support, not punctuation hacks.
- The gate now treats `frogspawn` and `frog spawn` as equivalent, because
  Whisper may split the same ecological term in otherwise acceptable speech.

Updated API workflow research on 2026-06-02:

- Research note:
  `docs/research/elevenlabs-audio-advert-workflow-2026-06-02.md`
- Decision:
  use ElevenLabs to generate raw voice, dialogue, SFX, and music assets; assemble adverts locally with `ffmpeg` so timing, overlaps, silence, and comedy beats can be edited without paying for new voice generations.
- Scratch path:
  use Text to Dialogue with timestamps for whole-scene preview renders.
- Production path:
  generate each line or reusable beat as its own timestamped asset, save metadata, then mix locally from a render plan.

## External Sound Effects

Do not generate every bark, door knock, record scratch, or ambience with paid
tokens by default. Use a small curated starter cache plus on-demand search.

Research note:
`docs/research/public-audio-asset-sourcing-2026-06-02.md`

Decision:

- search Freesound CC0 first
- use Openverse as discovery only, then verify the original source license
- use Pixabay or ZapSplat as fallbacks with their custom license and attribution
  requirements recorded
- avoid BBC Sound Effects for public adverts unless a commercial license has
  been bought
- pre-cache only the reusable advert staples, such as dog barks, interruption
  stings, phone rings, door knocks, whooshes, and room tone

Generated ElevenLabs assets and external SFX assets both need catalogue records
with source, license, hash, duration, tags, usage notes, and approval status.

Freesound V0:

```bash
scripts/audio_asset_search_freesound.py "dog bark" --limit 10
```

This searches and writes ignored candidate metadata only. It does not download
audio. The token lives in `local/audio-assets/.env` as
`FREESOUND_API_TOKEN=<token>`.

### Agent-First SFX Selection

Peter should not pick raw sounds in isolation. The agent should choose the best
candidate for the current advert beat, then Peter reviews the advert moment.

Example beat:

```yaml
sfx_intent:
  beat_id: charlie_dog_callback
  purpose: comic callback after the hurried founder line
  desired_sound: small dog bark / frantic dog movement
  mood: comic, close, slightly chaotic, not scary
  duration_seconds: 1.0-2.0
  license_priority: cc0
  search_terms:
    - dog bark
    - small dog bark
    - frantic dog bark
  avoid:
    - aggressive attack dog
    - long ambience bed
    - recognisable copyrighted media
```

Agent workflow:

1. Read the script beat and Product Truth context.
2. Convert `sfx_intent` into one or more Freesound searches.
3. Pick one best CC0 candidate and one fallback.
4. Record why it chose the candidate.
5. Use it in the draft advert render plan.
6. Ask Peter to review the advert moment, not the whole asset library.

Peter feedback should be natural:

- "make the bark longer"
- "more frantic"
- "less annoying"
- "make it distant"
- "use a smaller dog"

Only expose raw candidate lists when the first guess fails or the agent cannot
find a compatible asset.

## Asset Metadata

Each generated asset should record:

- `asset_id`
- `created_at`
- `campaign`
- `script_id`
- `script_text`
- `voice_provider`
- `voice_id`
- `voice_name`
- `model_id`
- `voice_settings`
- `style_direction`
- `intended_duration_seconds`
- `actual_duration_seconds`
- `language`
- `file_path`
- `file_sha256`
- `format`
- `credits_or_cost`
- `licence_terms_url`
- `licence_terms_checked_at`
- `notes`
- `test_status`
- `performance_notes`

## Audio Asset Search V0

The first local reverse-index workbench is:

```bash
scripts/generate_audio_asset_search_workbench.py
```

It scans:

- ElevenLabs metadata under `data/processed/audio-ads/**`
- downloaded Freesound preview metadata under `data/processed/audio-ads/external-sfx/`
- local REAPER asset folders under `local/audio-adverts/`

It writes ignored local artifacts:

```text
local/reports/audio-asset-search/catalogue.jsonl
local/reports/audio-asset-search/index.json
local/reports/audio-asset-search/index.html
local/reports/audio-asset-search/media/
```

The HTML page is registered on the Private Lab Shelf as `Audio Asset Search`.
It supports quick search, playable results, next/previous, select/reject, and
browser-local audition notes. Folders remain useful while editing a specific
advert, but the catalogue is the better long-term way to find reusable assets.

## Local Storage

Recommended ignored paths:

```text
data/raw/audio-ads/
data/processed/audio-ads/assets.sqlite
data/processed/audio-ads/catalogue.json
data/processed/audio-ads/catalogue.jsonl
```

The repo should contain scripts and schemas, not generated voice assets.

Search should work over at least:

- campaign
- script text
- voice provider
- voice name / id
- model id
- tags
- style direction
- language
- generated date
- cost / credits
- licence snapshot date
- test status
- performance notes

## First Batch

First, create Product Truth briefs for the top products and draft plain written copy from the proven claims.

Current dogfood advert set:

1. JobDone.
2. Living Water Skills.
3. Jury-Rigged Video Creation Software.
4. Workshop Coordinate Words.

Each brief should start with:

1. elevator pitch
2. quick start guide
3. internal representation for docs, QA, automated tests, and advert generation

Every generated script should record which Product Truth fields it used. If the
script makes a claim that is not in `allowed_ad_claims`, or contradicts
`forbidden_ad_claims`, it fails Product Truth QA.

Then create small scripts for the regenerative AI water message:

1. `Use AI. Repair Water.` - 15 seconds.
2. `Use AI. Repair Water.` - 30 seconds.
3. `Not an Offset` - 30 seconds.
4. `Continuum Pledge` - 45 seconds.
5. `Direct to Checkdam` - 30 seconds.

For each:

- generate 5 voice variants
- use at least 2 pacing/emotion variants
- keep text unchanged for free regenerations where possible
- tag voice impression: trustworthy, calm, urgent, warm, technical, poetic

## Tool Shape

Start CLI-first:

```text
scripts/audio_ad_catalog_init.py
scripts/audio_ad_search.py <query>
scripts/audio_ad_generate_elevenlabs.py <script.md>
scripts/audio_ad_import.py <audio-file> --metadata metadata.json
scripts/audio_ad_render_plan.py <script.md>
```

Later tool:

- choose script
- choose voice/tone
- pick intro/outro/call-to-action
- stitch with ffmpeg
- export final spot and metadata
- write a Continuum Entry for every generated asset
- search previous assets before generating a near-duplicate

## Open Questions

1. Does Peter want the first test audience to hear "Continuum", "Checkdam", or both?
2. Should the generated voice sound like a public-service announcement, a founder's note, or a podcast sponsor read?
3. Which channel matters first: LinkedIn, podcast pre-roll, short social audio, or embedded checkdam.org audio?
