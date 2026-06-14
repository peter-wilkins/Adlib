# AdLib

AdLib is the local audio advert workshop for turning Product Truth into scripts,
searchable audio assets, ElevenLabs-generated voice lines, and Reaper/FFmpeg
assemblies.

Immediate priority: use the remaining ElevenLabs subscription window to create
useful reusable voice assets and first-pass adverts without letting paid
generation run ahead of approved scripts.

## Current Campaigns

- `jobdone-dog-callback`: JobDone advert with tradesperson, app voice, dog
  callback, door/footstep/suburban ambience SFX, and a rendered v1.
- `living-water-skills-pond-challenge`: aspirational Living Water Skills pond
  challenge advert with learner, mentor/app voice, and narrator.

## Important Paths

- `docs/adverts/`: scripts, manifests, render plans, and lock files.
- `docs/product-truths/`: source truth for advert claims.
- `docs/research/`: ElevenLabs and public SFX sourcing research.
- `scripts/`: generation, search, Reaper project setup, and workbench helpers.
- `local/audio-adverts/`: local Reaper projects and working audio assets.
- `local/reports/`: local browser workbenches and rendered previews.
- `data/raw/audio-ads/`: generated/downloaded source audio.
- `data/processed/audio-ads/`: generated metadata, candidates, and renders.

`local/` and `data/` are ignored because they may contain secrets, paid audio
outputs, private local paths, and bulky generated media.

## Useful Commands

List JobDone ElevenLabs voice-line tasks without spending credits:

```bash
python3 scripts/audio_ad_generate_elevenlabs_voice_lines.py --list
```

Generate the audio asset search workbench:

```bash
python3 scripts/generate_audio_asset_search_workbench.py
```

Run the focused tests:

```bash
python3 -m unittest discover -s tests
```

## Local Keys

The copied local env file is:

```text
local/audio-assets/.env
```

It may contain ElevenLabs and Freesound tokens. Do not print it, commit it, or
send it to another service.

