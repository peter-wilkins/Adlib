# Selection Workbenches

Selection workbenches are public-safe candidate batches for choosing what to
turn into real audio, video, or music assets.

Each JSON file is source data. Generate the browsable tick-box page with:

```bash
python3 scripts/generate_asset_selection_workbench.py
```

The generated local page is written under `local/reports/` and should not be
committed. Public copies can be placed on the Continuum workbench server when a
batch needs to be shared.

## Current Batches

- `2026-06-15-continuum-asset-candidates.json`: Lily-only Field Relay redo
  candidates, Entrepreneurs AI Developer School scripts, Continuum memory and
  context scripts, Jury Rigged music/sting briefs, and animated logo briefs for
  the main Continuum projects.
- `2026-06-15-continuum-asset-picks.json`: Peter's exported selection from the
  public tick-box page, stored as stable candidate IDs for follow-on generation
  manifests.
- `elevenlabs-continuum-selected-voice-v1.json`: Lily-only ElevenLabs manifest
  for the selected spoken advert and voice-sting candidates.

## Media Generation

Selected non-voice media assets are generated with:

```bash
python3 scripts/generate_selected_media_assets.py
```

That script reads the candidate and picks JSON, generates selected music and
sound effects through ElevenLabs, renders animated logo MP4s locally with
FFmpeg/Pillow, and writes a browsable workbench under `local/reports/`.
