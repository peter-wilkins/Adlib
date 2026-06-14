# JobDone Dog Callback Render Plan

Date: 2026-06-02

Status: first agent guess. No audio downloaded yet. Candidate metadata is stored
in ignored local files under `data/processed/audio-ads/candidates/`.

## Script

Script ID: `JD_ad02_dog_callback`

Source board:
`http://100.112.20.26:8899/artifacts/audio-advert-drafts/#JD_ad02_dog_callback`

Goal: demonstrate JobDone recall with a concrete, memorable callback. The
remembered detail is not only the sink. It is Charlie, the ankle-biting dog.

## First SFX Choices

### Beat: `charlie_first_bite`

Placement: after the opening job detail, before the tradesperson says `Ow`.

First guess:

```json
{
  "beat_id": "charlie_first_bite",
  "asset_role": "primary",
  "source_provider": "freesound",
  "source_title": "single bark - small to medium dog",
  "source_url": "https://freesound.org/people/haulaway/sounds/630648/",
  "creator": "haulaway",
  "license": "Creative Commons 0",
  "duration_seconds": 1.43964,
  "reason": "Short enough for the opening gag, explicitly small-to-medium dog, less scary than larger bark options, and close to the desired 0.8-1.8s range.",
  "edit_handles": ["longer", "shorter", "more frantic", "smaller dog", "less annoying"]
}
```

Source link: https://freesound.org/people/haulaway/sounds/630648/

Fallback:

```json
{
  "beat_id": "charlie_first_bite",
  "asset_role": "fallback",
  "source_provider": "freesound",
  "source_title": "Small dog bark",
  "source_url": "https://freesound.org/people/giddster/sounds/484297/",
  "creator": "giddster",
  "license": "Creative Commons 0",
  "duration_seconds": 1.99136,
  "reason": "More clearly labelled as a small dog bark, useful if the first guess feels too plain or not dog-specific enough."
}
```

Fallback link: https://freesound.org/people/giddster/sounds/484297/

### Beat: `charlie_callback_warning`

Placement: after the app recalls Charlie, before or under the tradesperson says
`Oh, Charlie!`.

First guess:

```json
{
  "beat_id": "charlie_callback_warning",
  "asset_role": "primary",
  "source_provider": "freesound",
  "source_title": "Single Dog Bark (King Charles Spaniel)",
  "source_url": "https://freesound.org/people/JovianSounds/sounds/502655/",
  "creator": "JovianSounds",
  "license": "Creative Commons 0",
  "duration_seconds": 0.476009,
  "reason": "A short single bark from a small, friendly-sounding breed. Good for a light callback that should not fight the spoken recall line.",
  "edit_handles": ["longer", "more frantic", "make it distant", "friendlier", "less cute"]
}
```

Source link: https://freesound.org/people/JovianSounds/sounds/502655/

Fallback:

```json
{
  "beat_id": "charlie_callback_warning",
  "asset_role": "fallback",
  "source_provider": "freesound",
  "source_title": "Dog Shih Tzu Bark Single 07.wav",
  "source_url": "https://freesound.org/people/Glitchedtones/sounds/372526/",
  "creator": "Glitchedtones",
  "license": "Creative Commons 0",
  "duration_seconds": 0.816213,
  "reason": "Still a small-dog single bark, but slightly longer and more present if the King Charles bark feels too tiny."
}
```

Fallback link: https://freesound.org/people/Glitchedtones/sounds/372526/

## Draft Timing Plan

Repeatable render skeleton:
`docs/adverts/jobdone-dog-callback/`

```yaml
script_id: JD_ad02_dog_callback
render_plan_id: JD_ad02_dog_callback_sfx_guess_20260602
mix_strategy: voice-first, SFX ducked under speech only where needed
beats:
  - time_mode: relative
    after_line: "Mrs Jones, kitchen sink. Washer replaced. Isolation valve stiff."
    sfx: charlie_first_bite
    placement_note: start bark immediately after line; let final tail overlap the beginning of "Ow" if it improves comic timing
    expected_duration_seconds: 1.44
  - time_mode: relative
    after_line: "Confirmed entry: kitchen sink. Washer replaced. Isolation valve stiff. Charlie the dog bites ankles."
    sfx: charlie_callback_warning
    placement_note: short bark before "Oh, Charlie!" or tucked just under the first syllable, depending on voice timing
    expected_duration_seconds: 0.48
review_question: "Does Charlie feel comic and useful, or is the dog stealing attention from recall?"
```

## Search Evidence

Searches run:

```text
scripts/audio_asset_search_freesound.py "small dog bark" --limit 12 --min-duration 0.4 --max-duration 2.0 --extra-filter tag:dog --extra-filter tag:bark
scripts/audio_asset_search_freesound.py "single dog bark" --limit 12 --min-duration 0.3 --max-duration 1.4 --extra-filter tag:dog --extra-filter tag:bark
scripts/audio_asset_search_freesound.py "dog scramble" --limit 12 --min-duration 0.4 --max-duration 2.5 --extra-filter tag:dog
```

Results:

- `small dog bark`: 7 CC0 candidates
- `single dog bark`: 11 CC0 candidates
- `dog scramble`: 0 candidates with the strict tag filter

Interpretation: use bark-only candidates for the first draft. If the opening
needs actual movement, search later for generic `scramble`, `collar`, or
`dog running` and layer it quietly under the bark.

## Human Review Contract

Peter does not need to pick from raw candidates.

Ask for feedback in advert language:

- "longer dog bark"
- "more frantic"
- "smaller dog"
- "make Charlie sound further away"
- "less annoying"
- "dog is stealing the joke"

Then the agent adjusts the search or fallback choice.
