# Product Truth: Personal Dictionary / Transcript Cleanup

Date: 2026-06-02

## One Sentence

Personal Dictionary is a local correction memory that helps transcription cleanup and agents understand Peter's project names, recurring dictation mistakes, and meaning-critical language.

## User And Job

- User: Peter speaking messy or low-energy dictation, plus local agents that need to interpret it.
- Job: reduce cognitive load from repeated misrecognitions while preserving raw capture and uncertainty.

## Truth Levels

### Proven

- `docs/personal-dictionary.md`, `docs/personal-dictionary-contract.md`, and `docs/personal-dictionary-api.md` define the local dictionary contract.
- `schemas/personal_dictionary_event.schema.json` exists.
- `scripts/build_personal_dictionary_context.py` exists and has tests.
- `scripts/personal_dictionary_api.py` exists and has tests.
- The documented storage model is local append-only correction events, not destructive replacement.
- The docs explicitly protect meaning-critical words such as `no`, `not`, names, and project terms.

### Working But Unproven

- The local API and context builder are implemented, but live use still needs review of rewrite logs before stronger claims.
- Dictionary context can help transcript cleanup, but automatic learning from ordinary user edits is not proven.
- Multi-project scope is designed, but practical scoping is still early.

### Aspirational

- Low-friction learning from edits, corrections, and ambiguity signals.
- Word-finding support using active project/domain language.
- Tone cues for uncertainty, sarcasm, emphasis, or correction.
- Shared language layer across Continuum, phone capture, and future voice interfaces.

### False Or Stale

- This is not an autocorrect dictionary in the normal phone-keyboard sense.
- It is not yet a fully automatic semantic extraction system.
- It is not yet multi-user production infrastructure.

### Private Only

- Correction events, rewrite logs, names, personal vocabulary, and project-language hints are local/private.
- Public examples need synthetic or redacted substitutions.

## Smallest Honest Pitch

Personal Dictionary is a local language memory for Peter's AI workflow. It records corrections and project vocabulary as append-only evidence, then gives transcript cleanup and agents better context without deleting raw capture. It is useful as a private support layer, not a standalone public product yet.

## Docs/Copy To Change

1. `docs/personal-dictionary.md` - add a "current implementation" box above the future-facing outputs.
2. `docs/audio-advert-generator.md` - mention dictionary/context cleanup as a prerequisite for spoken-script capture.
3. Future public copy - use synthetic examples, not Peter's private correction events.

## Next Product Move

Review the local rewrite feedback log and turn the highest-value repeated corrections into scoped events with visible proof.
