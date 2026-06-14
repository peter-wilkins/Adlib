# Product Truth: Audio Advert Generator

Date: 2026-06-02

## Elevator Pitch

Audio Advert Generator turns Product Truth into truthful scripts, searchable audio assets, and ElevenLabs API-generated adverts without letting paid generations or marketing copy run ahead of reality.

## Quick Start Guide

1. Choose a Product Truth brief from the current advert set.
2. Draft a 15-second and 30-second script only from allowed claims.
3. Run Product Truth QA against forbidden claims, stale claims, and private-only material.
4. Get Peter's explicit approval before any paid ElevenLabs generation.
5. Generate audio, then save the asset and searchable metadata in the local catalogue.
6. Compare, tag, and reuse previous assets before creating near-duplicates.

## Internal Representation

```yaml
slug: audio-advert-generator
advert_priority: enabling_tool
stage: planning
primary_user: Peter as product/story editor
buyer_job: generate truthful advert scripts and searchable audio assets from Product Truth briefs
core_loop:
  - select_product_truth
  - draft_script
  - run_truth_qa
  - approve_paid_generation
  - generate_with_elevenlabs_api
  - catalogue_asset
  - compare_and_reuse
source_docs:
  - docs/audio-advert-generator.md
  - docs/product-truths/
truth_checks:
  - No paid generation without explicit approval.
  - Scripts must cite Product Truth fields.
  - Search previous assets before generating near-duplicates.
  - Raw generated audio assets stay local unless approved for publishing.
allowed_ad_claims:
  - local workflow
  - Product Truth source discipline
  - ElevenLabs API generation after approval
  - searchable JSON/JSONL catalogue in V0
forbidden_ad_claims:
  - finished production tool
  - automatic truthful marketing without review
  - public asset upload by default
```

## One Sentence

Audio Advert Generator is a planned local toolchain that turns Product Truth briefs into approved advert scripts, searchable metadata, and ElevenLabs API-generated audio assets.

## User And Job

- User: Peter, acting as product/story editor before public copy or audio is published.
- Job: generate truthful, repeatable, searchable audio adverts without wasting ElevenLabs credits or letting marketing outrun product reality.

## Truth Levels

### Proven

- `docs/audio-advert-generator.md` defines the project, asset metadata fields, local storage paths, first batch ideas, and CLI-first tool shape.
- ElevenLabs is the intended concrete provider/API for text-to-speech generation.
- The current rules require Product Truth briefs before script/audio generation.
- Existing ElevenLabs docs/terms/help links were captured on 2026-05-22.
- The first likely campaign source is `Regenerative AI Water Broadcast`, especially `Use AI. Repair Water.`

### Working But Unproven

- No checked-in audio generation scripts exist yet.
- No ElevenLabs API key handling, request wrapper, metadata database, or generated audio import path exists yet.
- No generated audio assets have been catalogued in the repo.
- No advert script has been approved for paid generation yet.

### Aspirational

- CLI tools:
  - `scripts/audio_ad_catalog_init.py`
  - `scripts/audio_ad_generate_elevenlabs.py`
  - `scripts/audio_ad_import.py`
  - `scripts/audio_ad_render_plan.py`
- Local ignored asset store under `data/raw/audio-ads/` and `data/processed/audio-ads/`.
- Searchable catalogue as JSON/JSONL first, with SQLite when query/index needs justify it.
- Multiple approved voice/settings variants per script.
- Reproducible metadata for provider, voice, model, settings, script, cost/credits, file hash, licence snapshot, and test outcome.
- Later stitching with music beds, pauses, calls to action, and `ffmpeg`.

### False Or Stale

- ElevenLabs is not a style. It is the provider/API intended for generation.
- This is not currently a finished audio-ad app.
- This should not generate paid audio from slogans, vibes, or aspirational claims.
- This should not upload Peter's own voice unless there is a separate explicit decision.

### Private Only

- API keys, generated raw audio, local asset catalogues, private scripts, and unpublished campaign strategy are private.
- Public copy/audio requires Peter approval of exact script, claims, provider, and voice choice.

## Smallest Honest Pitch

Audio Advert Generator will be a local workflow for writing truthful advert scripts from Product Truth briefs, generating audio through the ElevenLabs API, and saving enough searchable metadata to find, compare, and audit every asset. Right now it is a planning project with a clear first campaign, not a working generator.

## Docs/Copy To Change

1. `docs/audio-advert-generator.md` - keep ElevenLabs framed as the concrete API/provider.
2. `docs/backlog.md` and `docs/project-ideas.md` - keep the row truth-first and API-specific.
3. Future implementation docs - add API key handling, searchable metadata schema, and a no-paid-generation-without-approval rule.

## Next Product Move

Draft the first two scripts from the Regenerative AI Water Broadcast truth brief:

1. `Use AI. Repair Water.` - 15 seconds.
2. `Use AI. Repair Water.` - 30 seconds.

Do not call the ElevenLabs API until Peter approves exact text, voice choice, and spend.
