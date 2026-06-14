# ElevenLabs Audio Advert Workflow Research

Date: 2026-06-02

Purpose: decide how the Audio Advert Generator should use ElevenLabs APIs without wasting paid generations or losing edit control.

## Recommendation

Use a two-track workflow:

1. **Scratch dialogue preview**: use ElevenLabs Text to Dialogue to generate a whole multi-speaker advert quickly, especially when interruptions and conversational rhythm matter.
2. **Editable production assets**: generate each reusable line, phrase, sting, and music bed as a separate asset, then assemble locally with `ffmpeg`.

For the grumpy Yorkshireman advert, the strongest path is:

1. Choose or design a stable Yorkshireman voice once.
2. Generate each Yorkshireman line as its own timestamped line asset.
3. Generate the corporate narrator and app voice as their own line assets.
4. Save all raw generated audio and metadata.
5. Assemble the advert locally, where silence, overlap, interrupt timing, music, and SFX can be changed without another paid voice generation.

The whole-dialogue endpoint is useful for discovering timing and tone, but it should not be the only saved production asset because it gives less control over later comedy timing.

## Relevant ElevenLabs APIs

### Text To Speech

Official endpoint:

```text
POST https://api.elevenlabs.io/v1/text-to-speech/:voice_id
```

Use this for one voice at a time: narrator lines, Yorkshireman lines, app voice lines, and alternate takes.

Useful inputs:

- `text`
- `model_id`
- `voice_settings`
- `seed`
- `previous_text` / `next_text`
- `previous_request_ids` / `next_request_ids`
- `output_format`

Recommended V0 output:

```text
mp3_44100_128
```

Reason: it is the default-ish practical format and avoids depending on higher paid tiers before we know the workflow is valuable. If Peter has a tier that supports it, production editing can move to WAV/PCM or convert generated MP3 to WAV locally before mixing.

### Text To Speech With Timestamps

Official endpoint:

```text
POST https://api.elevenlabs.io/v1/text-to-speech/:voice_id/with-timestamps
```

Use this when we want character-level timing metadata for one generated line. It returns:

- `audio_base64`
- `alignment`
- `normalized_alignment`

This is useful for:

- subtitle/caption alignment
- finding duration without relying only on `ffprobe`
- clipping around unwanted lead-in or trailing silence
- later UI previews where words highlight during playback

### Text To Dialogue

Official endpoint:

```text
POST https://api.elevenlabs.io/v1/text-to-dialogue
```

Input shape:

```json
{
  "inputs": [
    { "text": "[giggling] Knock knock", "voice_id": "voice_1" },
    { "text": "[curious] Who is there?", "voice_id": "voice_2" }
  ],
  "model_id": "eleven_v3"
}
```

Use this for scratch whole-advert renders where flow matters. It supports multiple speakers in one request and can produce more natural handoff/interruption rhythm than isolated line generation.

Important limits:

- maximum 10 unique voice IDs
- for reliable generation, keep total request text at or below about 2,000 characters
- output is still nondeterministic, even with a seed

### Text To Dialogue With Timestamps

Official endpoint:

```text
POST https://api.elevenlabs.io/v1/text-to-dialogue/with-timestamps
```

Use this for scratch renders that also need timing metadata. It returns:

- `audio_base64`
- `voice_segments`
- character alignment

This is the best scratch endpoint for the first Yorkshireman/corporate-interruption experiment because it gives us a whole take and segment timing.

### Voices And Voice Design

Voices are referenced by `voice_id`. The voice search/list endpoint is:

```text
GET https://api.elevenlabs.io/v2/voices
```

Use this to search saved, default, community, workspace, generated, or cloned voices depending on account access.

Voice Design is relevant when the library does not have a suitable voice. It generates preview voices from a description, then the chosen preview can be saved into the voice library.

For the Yorkshireman:

- prefer a licensed/library voice if good enough
- otherwise use Voice Design with a synthetic voice description
- do not clone a real person's voice unless rights and consent are explicit

Example voice design prompt direction:

```text
Middle-aged Yorkshire tradesman, warm-gruff, dry humour, grounded, natural conversational pace, slightly gravelly, not theatrical, good studio quality.
```

### Sound Effects

Official endpoint:

```text
POST https://api.elevenlabs.io/v1/sound-generation
```

Use this for:

- short braams
- whooshes
- subtle van ambience
- mission-control beeps
- transition stings
- low background textures

Useful inputs:

- `text`
- `duration_seconds`
- `loop`
- `prompt_influence`
- `model_id`

Limits:

- duration must be 0.5 to 30 seconds for the API field
- looping is available for the v2 sound model

### Music

Official endpoint:

```text
POST https://api.elevenlabs.io/v1/music
```

Use this later for custom music beds. It supports:

- prompt-based generation
- composition plans
- `music_length_ms`
- `force_instrumental`
- `seed`

For V0 adverts, do not start with generated full music unless there is a clear advert concept. Start with voice and simple SFX, then add music if the spot needs it.

### Forced Alignment

Forced Alignment aligns known text to existing audio. It is not needed for the first slice because the `with-timestamps` endpoints already return alignment for generated speech. It becomes useful if we import externally edited audio or human voice takes later.

## Structured Script Format

The generator should not send plain screenplay text straight to ElevenLabs. It should use a structured manifest.

Example:

```yaml
script_id: JD_ad01_yorkshire_interrupt
version: v01
campaign: jobdone-first-audio-test
product_truth: docs/product-truths/2026-06-02-jobdone.md
target_audience: self-employed tradespeople who hate admin and enterprise software language
approved_for_paid_generation: false
speakers:
  corporate:
    role: corporate narrator
    voice_provider: elevenlabs
    voice_id: pending
    voice_description: smooth enterprise advert narrator
  yorkshireman:
    role: grumpy Yorkshire tradesman
    voice_provider: elevenlabs
    voice_id: pending
    voice_description: middle-aged Yorkshire tradesman, dry, warm-gruff
  app_voice:
    role: JobDone app voice
    voice_provider: elevenlabs
    voice_id: pending
    voice_description: clear calm app assistant, neutral UK
lines:
  - line_id: l001
    kind: speech
    speaker: corporate
    text: Introducing the next generation field productivity intelligence platform for modern service operators.
    generation_mode: tts_line
    target_duration_ms: 4500
    edit_after_ms: 120
  - line_id: l002
    kind: speech
    speaker: yorkshireman
    text: No. Stop that.
    generation_mode: tts_line
    target_duration_ms: 1200
    overlap_previous_ms: 350
    edit_after_ms: 250
  - line_id: s001
    kind: sfx
    prompt: tiny record scratch, dry comedy interruption
    duration_ms: 700
```

## Asset Catalogue Format

Every generated thing should become an asset record.

```json
{
  "asset_id": "JD_ad01_v01_l002_yorkshireman_20260602T132500Z",
  "created_at": "2026-06-02T13:25:00Z",
  "campaign": "jobdone-first-audio-test",
  "script_id": "JD_ad01_yorkshire_interrupt",
  "script_version": "v01",
  "line_id": "l002",
  "asset_kind": "speech_line",
  "provider": "elevenlabs",
  "endpoint": "text-to-speech-with-timestamps",
  "model_id": "eleven_v3",
  "voice_id": "pending",
  "voice_label": "Yorkshireman",
  "text": "No. Stop that.",
  "text_sha256": "pending",
  "output_format": "mp3_44100_128",
  "file_path": "data/raw/audio-ads/jobdone/JD_ad01/v01/JD_ad01_v01_l002_yorkshireman_20260602T132500Z.mp3",
  "file_sha256": "pending",
  "duration_seconds": 1.2,
  "alignment_path": "data/processed/audio-ads/jobdone/JD_ad01/v01/JD_ad01_v01_l002_yorkshireman_20260602T132500Z.alignment.json",
  "request_id": "pending",
  "character_cost": "pending",
  "approval_id": "pending",
  "notes": "Good interruption candidate; trim 80ms front silence if needed."
}
```

## Render Plan Format

After generation, create a local render plan. This is the source of truth for `ffmpeg`.

```yaml
render_id: JD_ad01_v01_mix01
format: mp3
sample_rate: 44100
tracks:
  - asset_id: JD_ad01_v01_l001_corporate_20260602T132400Z
    start_ms: 0
    gain_db: -1
  - asset_id: JD_ad01_v01_l002_yorkshireman_20260602T132500Z
    start_ms: 3800
    gain_db: 0
  - asset_id: JD_ad01_v01_s001_record_scratch_20260602T132510Z
    start_ms: 3600
    gain_db: -8
```

This keeps comedy timing local and cheap.

## First Implementation Slice

Build the generator in this order:

1. `scripts/audio_ad_render_plan.py`
   - reads a structured script manifest
   - validates Product Truth reference and `approved_for_paid_generation`
   - outputs the planned assets and a render plan
   - no API calls
2. `scripts/audio_ad_catalog_init.py`
   - creates JSONL catalogue and ignored asset folders
3. `scripts/audio_ad_generate_elevenlabs.py`
   - defaults to dry-run
   - refuses to call API unless `--execute` and `approved_for_paid_generation: true`
   - saves audio, metadata, request id, character cost, and hashes
4. `scripts/audio_ad_mix_ffmpeg.py`
   - assembles generated assets with silence, overlaps, gains, and exports
5. Private HTML workbench
   - shows script, voices, generated assets, costs, and playable rough mixes

## Decision

Do not ask ElevenLabs to produce a finished advert as the main workflow.

Use ElevenLabs to produce the raw voice/SFX/music assets, then do advert assembly locally.

The exception is Text to Dialogue, which is useful as a scratch "does this scene work?" generator before committing to editable production assets.

## Sources

- ElevenLabs API overview: https://elevenlabs.io/docs/api-reference/introduction
- ElevenLabs overview: https://elevenlabs.io/docs/overview/intro
- Text to Speech: https://elevenlabs.io/docs/api-reference/text-to-speech/convert
- Text to Speech with timestamps: https://elevenlabs.io/docs/api-reference/text-to-speech/convert-with-timestamps
- Text to Dialogue: https://elevenlabs.io/docs/api-reference/text-to-dialogue/convert
- Text to Dialogue with timestamps: https://elevenlabs.io/docs/api-reference/text-to-dialogue/convert-with-timestamps
- Voices list/search: https://elevenlabs.io/docs/api-reference/voices/search
- Voice Design guide: https://elevenlabs.io/docs/eleven-creative/voices/voice-design
- Sound Effects overview: https://elevenlabs.io/docs/overview/capabilities/sound-effects
- Sound Effects API: https://elevenlabs.io/docs/api-reference/text-to-sound-effects/convert
- Music API: https://elevenlabs.io/docs/api-reference/music/compose
- Forced Alignment: https://elevenlabs.io/docs/api-reference/forced-alignment/create
