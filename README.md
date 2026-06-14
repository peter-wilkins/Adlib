# AdLib

AdLib is a local-first workshop for creating natural spoken adverts. It helps
turn a product brief or claim-safe product truth into scripts, reusable voice
assets, searchable metadata, and rough audio advert assemblies.

The public MVP direction is in [SPEC.md](SPEC.md): help podcasters, producers,
and small brands create better host-read advert scripts faster than starting
from a blank page.

## What This Repo Contains

- Script and campaign planning documents for audio advert experiments.
- Product Truth documents used to keep advert claims grounded.
- ElevenLabs manifest tooling for approved voice-line generation.
- A technical preflight gate that checks generated speech against the approved
  script using a local transcription API.
- A searchable local audio asset workbench for auditioning reusable clips.
- Reaper and FFmpeg helper scripts for rough advert assembly.

This is not a hosted ad platform. It is a CLI-first creative workflow for
building, testing, and cataloguing spoken advert assets.

## Safe Commands

Run the tests:

```bash
python3 -m unittest discover -s tests
```

List configured ElevenLabs voice-line tasks without spending credits:

```bash
python3 scripts/audio_ad_generate_elevenlabs_voice_lines.py --list
```

Build the local searchable audio asset workbench:

```bash
python3 scripts/generate_audio_asset_search_workbench.py
```

Run technical preflight after starting a compatible local transcription API:

```bash
python3 scripts/audio_asset_quality_gate.py --campaign jobdone-reusable-recall
```

## Repository Map

- `docs/adverts/`: campaign scripts, manifests, render plans, and asset plans.
- `docs/product-truths/`: claim boundaries for advert copy.
- `docs/research/`: research notes for audio generation and public SFX sourcing.
- `scripts/`: CLI tools for generation, preflight, search, and assembly.
- `tests/`: focused regression tests for the local workflow.
- `privileged-actions/`: optional machine setup scripts that should be reviewed
  before running.

## Private And Generated Files

The repo intentionally ignores local secrets and generated media:

- `local/`
- `data/raw/`
- `data/processed/`

Those folders may contain API keys, paid audio outputs, private local paths, and
bulky generated assets. Public source should keep reusable code, manifests,
tests, and documentation, not private generated audio.

## Paid Generation Guardrail

ElevenLabs generation scripts require an approved manifest before spending
credits. Use `--list` first, review the manifest, then generate only the exact
approved batch.
