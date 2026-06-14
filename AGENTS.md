# Agent Instructions

AdLib owns Peter's audio advert generation workflow.

## Current Priority

There are about six days left on the current ElevenLabs subscription. Prefer
work that converts approved Product Truth and existing scripts into reusable
voice assets, searchable metadata, and first-pass advert renders.

## Guardrails

- Do not publish or commit `local/`, `data/raw/`, or `data/processed/`.
- Do not print API keys or env files.
- Do not spend ElevenLabs credits unless the manifest is approved or Peter has
  explicitly approved the exact generation.
- Generated audio should be findable later: save metadata, voice, prompt,
  script text, provider response IDs, and local path.
- Prefer small reusable assets over one-shot finished adverts unless the goal is
  a quick audition.
- Product Truth constrains claims. If a script makes a claim not supported by
  `docs/product-truths/`, stop and grill before generation.

## Working Style

- Keep scripts CLI-first and local-first.
- Use Reaper for manual creative polishing when useful; do not overbuild UI
  before the workflow is proven.
- Preserve existing local assets. Do not delete or overwrite generated audio
  unless Peter explicitly says it is disposable.

