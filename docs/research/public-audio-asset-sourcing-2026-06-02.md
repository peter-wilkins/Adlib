# Public Audio Asset Sourcing Research

Date: 2026-06-02

Purpose: decide whether the Audio Advert Generator should download public/free sound effects ahead of time, or search when needed.

## Recommendation

Use a **small curated starter cache plus on-demand search**.

Do not bulk-download huge sound libraries. That creates license, storage, and maintenance drag before we know which adverts are real.

Do pre-cache a tiny set of high-probability reusable advert sounds:

1. dog bark / small dog bark
2. dog running / scramble
3. record scratch / interruption sting
4. phone ring / notification beep
5. van door / van ambience
6. knock at door
7. short whoosh
8. room tone / quiet house ambience

For anything more specific, search on demand.

The key is to catalogue every selected asset with source URL, license, creator, download date, hash, and attribution requirement. The catalogue matters more than the folder.

## Human Review Model

Do not make Peter browse or choose raw sound-effect libraries unless there is a
specific problem.

Default workflow:

1. The advert script declares an `sfx_intent` for a beat.
2. The agent searches for compatible candidates.
3. The agent makes its best first choice, with one fallback.
4. The chosen sound is placed into the draft advert render plan.
5. Peter reviews the advert moment in context.
6. Peter gives natural feedback, such as "longer", "more frantic", "smaller
   dog", "further away", or "less annoying".

This keeps Peter's attention on whether the advert works. The asset catalogue is
an agent tool and audit record, not the main human interface.

## Quick Links

Start here:

- Freesound search: https://freesound.org/search/
- Freesound API credential page: https://freesound.org/apiv2/apply
- Freesound API docs: https://freesound.org/docs/api/overview.html
- Openverse audio search: https://openverse.org/search/audio
- Pixabay sound effects: https://pixabay.com/sound-effects/
- YouTube Audio Library help: https://support.google.com/youtube/answer/3376882
- ZapSplat: https://www.zapsplat.com/
- OpenGameArt audio: https://opengameart.org/art-search-advanced?keys=&field_art_type_tid%5B%5D=13

License references:

- CC0 public domain dedication: https://creativecommons.org/publicdomain/zero/1.0/
- CC-BY 4.0: https://creativecommons.org/licenses/by/4.0/
- CC-BY-NC 4.0: https://creativecommons.org/licenses/by-nc/4.0/
- Pixabay license summary: https://pixabay.com/service/license-summary/
- BBC Sound Effects licensing: https://sound-effects.bbcrewind.co.uk/licensing
- ZapSplat standard license: https://www.zapsplat.com/license-type/standard-license/

## Source Ranking

### 1. Freesound CC0

Best first stop for sound effects.

Link: https://freesound.org/search/

API: https://freesound.org/docs/api/overview.html

Why:

- large database of audio snippets and field recordings
- API supports search and metadata
- license field includes `Creative Commons 0`
- can filter searches to CC0 before downloading
- metadata includes source URL, tags, duration, format, rating, previews, user, and license

Use:

```text
license:"Creative Commons 0"
duration:[0.2 TO 8.0]
query: dog bark
```

Notes:

- Original-file downloads require OAuth2.
- Preview MP3/OGG URLs are easier to fetch but may not be production quality.
- For V0, previews are fine for rough mixes; production can fetch originals once we have OAuth/API setup.
- CC-BY is usable if we are willing to keep attribution. Prefer CC0 unless a CC-BY asset is clearly much better.
- Avoid CC-BY-NC for adverts or public product material.

### 2. Openverse

Good discovery layer, not final proof.

Link: https://openverse.org/search/audio

API note: https://docs.openverse.org/api/reference/made_with_ov.html

Why:

- indexes openly licensed media, including audio
- can search across multiple providers
- includes Creative Commons and public domain material

Risk:

- Openverse itself warns that license information must be verified at the source before use.

Use:

- discover candidates
- follow source link
- store the original source license, not only Openverse metadata

### 3. Pixabay

Useful convenience source, but not public domain.

Link: https://pixabay.com/sound-effects/

License: https://pixabay.com/service/license-summary/

Why:

- easy sound-effect search
- free use
- no attribution required in normal use
- allows modification/adaptation into new works

Risks:

- custom Pixabay Content License, not CC0/public domain
- prohibited standalone redistribution
- explicit warning that extra rights may apply
- bulk/systematic copying is restricted
- no warranty that all permissions exist

Use:

- fine for one-off advert SFX if the asset is generic and no recognisable brand/person is involved
- store the license snapshot and page URL
- do not bulk-download Pixabay

### 4. YouTube Audio Library

Useful if the target output is a YouTube video.

Link: https://support.google.com/youtube/answer/3376882

Why:

- YouTube says its Audio Library music/SFX are copyright-safe for YouTube videos
- some items require no attribution; some Creative Commons items require attribution
- YouTube Partner Program monetization is supported for Audio Library assets

Risk:

- less ideal as a general-purpose asset library for non-YouTube adverts
- use the exact license information shown in YouTube Studio for each asset

Use:

- good for YouTube-first video adverts
- not first choice for generic product audio spots

### 5. ZapSplat

Useful fallback if attribution is acceptable.

Link: https://www.zapsplat.com/

License: https://www.zapsplat.com/license-type/standard-license/

Why:

- clear free-user commercial-use path
- huge library

Risk:

- free/basic users generally need attribution
- account/download limits
- not public domain

Use:

- fallback for hard-to-find effects
- store attribution text in catalogue

### 6. OpenGameArt

Occasionally useful for CC0/game-style effects.

Link: https://opengameart.org/

FAQ: https://opengameart.org/content/faq

Why:

- individual asset pages show licenses
- some sound packs are CC0

Risk:

- mixed license site
- more game-focused than advert/field-recording-focused

Use:

- only when the exact pack is CC0 or otherwise compatible

### Avoid For Public Adverts: BBC Sound Effects Archive

Useful for personal, educational, or research experiments, but not for public/commercial adverts unless a commercial license is purchased.

Link: https://sound-effects.bbcrewind.co.uk/

Licensing: https://sound-effects.bbcrewind.co.uk/licensing

The BBC archive is large and tempting, but its free RemArc use is not the right fit for public product ads.

## License Policy For Our Catalogue

Use this priority order:

1. `cc0` / public-domain dedication
2. `cc-by` with attribution captured
3. custom free commercial license with no attribution, only if source is reputable
4. paid/generation provider after approval
5. non-commercial/research-only sources for private prototypes only

Reject for public adverts:

- `cc-by-nc`
- unclear license
- user-uploaded archive item with suspicious metadata
- recognisable brands, people, or copyrighted media in the recording
- "free" pages without a reusable license

## Catalogue Fields

Every external audio asset should record:

```json
{
  "asset_id": "sfx_dog_bark_small_20260602_freesound_123456",
  "asset_kind": "external_sfx",
  "source_provider": "freesound",
  "source_url": "https://freesound.org/s/123456/",
  "download_url": "pending",
  "source_title": "Small dog bark",
  "creator": "username",
  "license": "Creative Commons 0",
  "license_url": "https://creativecommons.org/publicdomain/zero/1.0/",
  "attribution_required": false,
  "attribution_text": "",
  "commercial_use_status": "allowed",
  "downloaded_at": "2026-06-02T00:00:00Z",
  "license_checked_at": "2026-06-02T00:00:00Z",
  "file_path": "data/raw/audio-ads/external-sfx/dog-bark/sfx_dog_bark_small_20260602_freesound_123456.mp3",
  "file_sha256": "pending",
  "duration_seconds": 1.4,
  "format": "mp3",
  "tags": ["dog", "bark", "small-dog", "callback"],
  "usage_notes": "Candidate Charlie dog callback bark.",
  "approval_status": "candidate"
}
```

## Search Workflow

1. Search Freesound with CC0 filter.
2. If nothing good, search Openverse and verify at source.
3. If still nothing, search Pixabay manually.
4. If still nothing, use ZapSplat with attribution or generate via ElevenLabs.
5. Never use BBC archive in public output unless we purchase/licence the sound.

## Download-Ahead Policy

Download ahead:

- a tiny reusable starter set
- sounds tied to currently active scripts
- anything that took more than five minutes to find and is likely to be reused

Search on demand:

- unusual one-off sound jokes
- campaign-specific ambience
- music beds
- anything with unclear license until the advert actually needs it

## First Slice

Build:

```text
scripts/audio_asset_search_freesound.py
scripts/audio_asset_catalog_add.py
scripts/audio_asset_catalog_search.py
```

V0 can be no-download:

1. search Freesound
2. return candidate JSON
3. store candidate metadata locally
4. only download when Peter approves a candidate

Status:

- `scripts/audio_asset_search_freesound.py` exists.
- It uses the current Freesound `/apiv2/search/` endpoint, not the deprecated
  text-search endpoint.
- It reads the API token from `FREESOUND_API_TOKEN`, `FREESOUND_API_KEY`, or
  ignored local config at `local/audio-assets/.env`.
- It stores candidate JSON under
  `data/processed/audio-ads/candidates/`, which is ignored local state.
- It does not download audio by default. Candidate records include preview URLs,
  source URLs, license data, rating/download metadata, tags, and approval status.
- Pagination URLs are token-redacted before being written.

Example:

```bash
scripts/audio_asset_search_freesound.py "dog bark" --limit 10
```

## Sources

- Creative Commons CC0: https://creativecommons.org/publicdomain/zero/1.0/
- Creative Commons Attribution 4.0: https://creativecommons.org/licenses/by/4.0/
- Creative Commons Attribution-NonCommercial 4.0: https://creativecommons.org/licenses/by-nc/4.0/
- Freesound API overview: https://freesound.org/docs/api/overview.html
- Freesound API resources: https://freesound.org/docs/api/resources_apiv2.html
- Freesound FAQ: https://freesound.org/help/faq/
- Openverse API note: https://docs.openverse.org/api/reference/made_with_ov.html
- Pixabay Content License summary: https://pixabay.com/service/license-summary/
- Pixabay Terms: https://pixabay.com/service/terms/
- YouTube Audio Library help: https://support.google.com/youtube/answer/3376882
- BBC Sound Effects licensing: https://sound-effects.bbcrewind.co.uk/licensing
- BBC Sound Effects about: https://sound-effects.bbcrewind.co.uk/about
- ZapSplat standard license: https://www.zapsplat.com/license-type/standard-license/
- OpenGameArt FAQ: https://opengameart.org/content/faq
