# JobDone Dog Callback Repeatable Render

Status: skeleton only. No audio assets are downloaded in this repo.

Purpose: keep the human advert idea and the executable FFmpeg render source close
together without inventing a large internal audio schema.

## Files

- `README.md` - human intent, workflow, and current status.
- `assets.lock.json` - source URLs, licence facts, local path placeholders, and
  expected roles.
- `filter_complex.ffgraph` - FFmpeg filtergraph source for this advert mix.
- `fetch_sfx_previews.sh` - downloads the currently selected Freesound preview
  files into ignored local storage.
- `make_dummy_voice.sh` - creates a local synthetic stand-in voice bed for
  proving the graph.
- `elevenlabs-dialogue-v1.json` - approved first Text-to-Dialogue manifest for
  one bounded paid ElevenLabs experiment.
- `elevenlabs-voice-lines-v1.json` - approved separate voice-line manifest for
  REAPER asset auditioning.
- `elevenlabs-voice-lines-v2.json` - regional UK/Ireland voice audition
  manifest after the first polished/premade batch was rejected.
- `elevenlabs-prompt-variants-v1.json` - Eleven v3 prompt/style variants for
  David tradesperson reads and Lily narrator/app reads.
- `elevenlabs-david-directed-v1.json` - targeted David v2 candidates after the
  v3 prompt variants drifted too far from the selected voice identity.
- `elevenlabs-david-dog-emphasis-v1.json` - more emphatic David dog-call
  candidates after the directed v2 batch got close.
- `render.sh` - exact command wrapper that checks required files, prints the
  FFmpeg version, and renders the mix.

## Source Of Truth Split

Use both:

1. Human truth: `docs/adverts/jobdone-dog-callback-render-plan.md`
2. Executable render truth: `filter_complex.ffgraph` plus `render.sh`

The filtergraph is allowed to become the repeatable render source of truth. It
is not expected to carry all editorial context, licence evidence, or Product
Truth decisions.

## Inputs

The current skeleton expects these local ignored files:

```text
data/raw/audio-ads/jobdone-dog-callback/voice.wav
data/raw/audio-ads/external-sfx/dog-bark/haulaway-630648-single-bark-small-to-medium-dog.mp3
data/raw/audio-ads/external-sfx/dog-bark/joviansounds-502655-single-dog-bark-king-charles-spaniel.mp3
```

The SFX paths correspond to the first agent guesses:

- Opening bite: https://freesound.org/people/haulaway/sounds/630648/
- Callback warning: https://freesound.org/people/JovianSounds/sounds/502655/

## Output

Default output:

```text
data/processed/audio-ads/renders/jobdone-dog-callback-v0.wav
```

This output is ignored local state.

## Timing Assumptions

The filtergraph currently uses fixed offsets:

- opening bite at `4.2s`
- callback warning at `22.5s`

Those are placeholders until the voice track exists. Once voice is generated or
recorded, adjust the millisecond delays in `filter_complex.ffgraph`.

## Render

To prove the current graph without spending ElevenLabs credits:

```bash
docs/adverts/jobdone-dog-callback/fetch_sfx_previews.sh
docs/adverts/jobdone-dog-callback/make_dummy_voice.sh
docs/adverts/jobdone-dog-callback/render.sh
```

## ElevenLabs Whole-Advert Experiment

Peter authorised one real ElevenLabs spend experiment on 2026-06-02: generate
the whole dog-callback advert through Text to Dialogue before building more
local production machinery.

Result: this is **not** the production path. The generated take was useful as a
negative test, but it was too far from the intended advert:

- the tradesperson voice was sterile rather than a cheerful real tradesperson
- the narrator voice leaked into the app voice role
- beeps, barks, doorbell, and door/footstep cues were not reliable
- the whole take was around 40 seconds, too long for the target spot

New production direction:

```text
collect small assets -> edit the advert by hand -> then automate the proven job
```

Editor direction:

```text
Use REAPER first, not Audacity, for the manual creative pass.
```

Reason: Peter wants a folder-based asset browser where he can audition ten dog
barks, choose the right one, and drag it onto the timeline. REAPER's Media
Explorer is a better fit for that than Audacity's import/drag workflow.

Create or refresh the local REAPER project with:

```bash
scripts/setup_jobdone_reaper_project.py
```

This writes ignored local state to:

```text
local/audio-adverts/jobdone-dog-callback/
```

Open it with:

```bash
local/audio-adverts/jobdone-dog-callback/open-reaper.sh
```

Generate Peter's first selected-asset rough assembly with:

```bash
scripts/generate_jobdone_reaper_rough_assembly.py
```

This writes ignored local state to:

```text
local/audio-adverts/jobdone-dog-callback/rough-assembly-v1/
```

Open the rough assembly with:

```bash
local/audio-adverts/jobdone-dog-callback/rough-assembly-v1/open-rough-v1.sh
```

The ReaScript creates only tracks prefixed with `Rough V1 -`, so rerunning it
refreshes the rough layout without deleting Peter's hand-polished tracks.

The asset collection plan is:

```text
docs/adverts/jobdone-dog-callback/asset-collection-v2.json
```

Do not spend more ElevenLabs credits on one-shot dialogue for this advert.

The manifest is:

```text
docs/adverts/jobdone-dog-callback/elevenlabs-dialogue-v1.json
```

The generator loads `ELEVENLABS_API_KEY` from the shell, or from ignored local
env files:

```text
local/audio-assets/.env
local/elevenlabs/.env
```

Optional voice overrides:

```text
ELEVENLABS_VOICE_TRADESPERSON=
ELEVENLABS_VOICE_APP=
ELEVENLABS_VOICE_NARRATOR=
```

If those voice IDs are not set, the script asks ElevenLabs for available voices
and picks a best-effort match from the manifest's search terms.

Run:

```bash
scripts/audio_ad_generate_elevenlabs_dialogue.py
scripts/generate_audio_advert_drafts.py
```

## ElevenLabs Separate Voice Assets

Current production direction is separate voice clips, not whole-scene dialogue.
Generate lines from:

```text
docs/adverts/jobdone-dog-callback/elevenlabs-voice-lines-v1.json
```

List the planned paid generations without spending credits:

```bash
scripts/audio_ad_generate_elevenlabs_voice_lines.py --list
```

Generate the approved batch:

```bash
scripts/audio_ad_generate_elevenlabs_voice_lines.py
```

Useful filters while testing:

```bash
scripts/audio_ad_generate_elevenlabs_voice_lines.py --asset-id plumber_capture
scripts/audio_ad_generate_elevenlabs_voice_lines.py --voice-profile george
scripts/audio_ad_generate_elevenlabs_voice_lines.py --limit 1
```

Generate same-line auditions for every voice in a manifest:

```bash
scripts/audio_ad_generate_elevenlabs_voice_lines.py \
  --manifest docs/adverts/jobdone-dog-callback/elevenlabs-voice-lines-v2.json \
  --audition-text "Alright then, Mrs Jones. Replaced the kitchen sink washer. Isolation valve is stiff here. Charlie the dog bites ankles."
```

The first voice-audition batch in `elevenlabs-voice-lines-v1.json` was rejected:
too posh, too American, and not regional enough.

The second batch in `elevenlabs-voice-lines-v2.json` contains:

- tradesperson candidates: Yorkshire, Geordie, Northern English, Scottish,
  Scouse/Liverpool, Irish
- narrator candidate: Lily only, for the short tagline
- app voice candidates: generic British assistant voices, not an Alexa clone

Important direction:

- the time-jump is now an SFX/sting problem, not a spoken narrator line
- do not clone, impersonate, or market the app voice as Alexa
- keep auditions inside role folders so REAPER browsing stays simple:
  `voice/tradesperson/auditions`, `voice/narrator/auditions`, and
  `voice/app/auditions`

Peter selected `yorkshire_david` as the tradesperson voice after comparing it
with `scottish_chris`. Chris had useful regional character, but sounded too
tired and world weary for this advert.

Eleven v3 prompt/style variants are generated from:

```text
docs/adverts/jobdone-dog-callback/elevenlabs-prompt-variants-v1.json
```

They are written into:

```text
local/audio-adverts/jobdone-dog-callback/assets/voice/tradesperson/prompt-variants/
local/audio-adverts/jobdone-dog-callback/assets/voice/narrator/prompt-variants/
local/audio-adverts/jobdone-dog-callback/assets/voice/app/prompt-variants/
```

Use v3 prompt variants for auditioning delivery, not as guaranteed final takes.
The tags and settings can move the performance a lot; judge the clip by ear.
Peter rejected the first David v3 prompt variants as sounding like a different
person. For final continuity, prefer Eleven Multilingual v2 with restrained
settings and only targeted punctuation/text changes.

The next David continuity candidates are generated from:

```text
docs/adverts/jobdone-dog-callback/elevenlabs-david-directed-v1.json
```

They are written into:

```text
local/audio-adverts/jobdone-dog-callback/assets/voice/tradesperson/directed-v2/
```

The more emphatic dog-call candidates are generated from:

```text
docs/adverts/jobdone-dog-callback/elevenlabs-david-dog-emphasis-v1.json
```

They are written into:

```text
local/audio-adverts/jobdone-dog-callback/assets/voice/tradesperson/directed-v2/dog-emphasis/
```

Current selected dog-call take:

```text
local/audio-adverts/jobdone-dog-callback/assets/voice/tradesperson/directed-v2/dog-emphasis/plumber_final_dog__v2_oi_charlie_call__david_emphatic_dog.mp3
```

For editing convenience, keep a stable local copy at:

```text
local/audio-adverts/jobdone-dog-callback/assets/voice/tradesperson/selected/plumber_final_dog__selected__david_emphatic_dog.mp3
```

Licence check:

```text
docs/adverts/jobdone-dog-callback/voice-licence-check-2026-06-02.md
```

Check current ElevenLabs usage:

```bash
scripts/elevenlabs_status.py
```

If the API key has `user_read`, this shows the subscription tier, character
limit, remaining balance, and next reset. Without `user_read`, it still shows
usage history and local generated-asset metadata.

The old first batch contained:

- tradesperson candidates: George, Daniel, Chris
- narrator candidates: Lily, Alice
- app voice candidates: Alice, River

Timestamped originals and metadata are saved under ignored local storage:

```text
data/raw/audio-ads/jobdone-dog-callback/elevenlabs/voice-lines/
data/processed/audio-ads/jobdone-dog-callback/elevenlabs/voice-lines/
```

Role-specific audition copies are written straight into the ignored REAPER
asset library:

```text
local/audio-adverts/jobdone-dog-callback/assets/voice/tradesperson/auditions/
local/audio-adverts/jobdone-dog-callback/assets/voice/narrator/auditions/
local/audio-adverts/jobdone-dog-callback/assets/voice/app/auditions/
```

## Freesound Preview SFX Assets

For quick REAPER auditioning, fetch CC0 Freesound preview MP3s into a target
asset folder:

```bash
scripts/audio_asset_fetch_freesound_previews.py "doorbell" --target-folder sfx/doorbells --take 6
scripts/audio_asset_fetch_freesound_previews.py "wood door close" --target-folder sfx/doors --take 6
scripts/audio_asset_fetch_freesound_previews.py "footsteps walking" --target-folder sfx/footsteps --take 6 --extra-filter tag:footsteps
scripts/audio_asset_fetch_freesound_previews.py "small dog bark" --target-folder sfx/kerfuffle --take 6
```

This downloads preview audio only. It is good enough for creative auditioning.
Metadata, source links, licence names, and hashes are saved under ignored local
storage:

```text
data/processed/audio-ads/external-sfx/freesound-previews/
data/raw/audio-ads/external-sfx/freesound-previews/
```

For final public output, keep using the metadata to verify the original
Freesound source and licence before publishing.

Generated audio is saved under ignored local storage:

```text
data/raw/audio-ads/jobdone-dog-callback/elevenlabs/
```

Metadata, selected voices, request headers, hashes, and timestamp response data
are saved under:

```text
data/processed/audio-ads/jobdone-dog-callback/elevenlabs/
```

After regenerating the workbench page, the new MP3 appears in the private audio
advert player automatically.

To render with real or alternate inputs, override paths:

```bash
VOICE=/path/to/voice.wav \
OPENING_BARK=/path/to/opening-bark.wav \
CALLBACK_BARK=/path/to/callback-bark.wav \
docs/adverts/jobdone-dog-callback/render.sh /tmp/jobdone-dog-callback.wav
```

```bash
docs/adverts/jobdone-dog-callback/render.sh
```

The script fails if the local audio files are missing. That is deliberate: the
publishable repo contains the repeatable recipe, not the private/generated raw
audio assets.

## FFmpeg Note

On this machine, FFmpeg `8.0.1` marks `-filter_complex_script` as deprecated and
suggests `-/filter_complex` instead. The render script uses:

```text
-/filter_complex filter_complex.ffgraph
```

This lets the filtergraph live in a normal file without stuffing it into one
long shell argument.

The filtergraph file must be pure graph text. FFmpeg does not accept the `#`
comments that were useful in the first draft, so commentary belongs in this
README.
