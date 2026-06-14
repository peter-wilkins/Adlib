# JobDone Advert Script Seeds

Date captured: 2026-06-02

Purpose: preserve the useful advert directions found in local ChatGPT captures before drafting JobDone scripts.

## Source Capture

- Source title: `Continuum Advert Workflow`
- Source URL: `https://chatgpt.com/c/6a0e98a2-23c0-8325-92b6-42dc6edd1b01`
- Local source: `local/chatgpt-web-probe/chatgpt-web-conversations.jsonl`, line 37
- Captured at: `2026-05-23T16:34:59Z`

This was a seed discussion, not finished script copy.

## Useful Product Signal

The advert should demonstrate **recall**, not just recording.

The user should understand:

```text
I speak the job detail now.
Later, I can ask for the right job detail back.
```

This matches the Product Truth for JobDone:

```text
Capture -> Confirmation -> Timeline -> Recall
```

## Tone Directions Found

The source suggested generating short 30-second audio advert scripts for:

1. Gruff Yorkshire tradesman.
2. Fake corporate advert interrupted by realism.
3. Radio drama.
4. Customer callback.
5. Van diary.
6. Deadpan comedy.
7. Sincere practical.
8. Sci-fi recall.
9. Before-and-after.
10. Testimonial.

The two Peter explicitly remembered later, before the 2026-06-02 correction:

1. **Space / sci-fi recall** - likely a more cinematic "memory retrieval" advert.
2. **Grumpy Yorkshireman interrupts enterprise advert** - likely the strongest JobDone fit because it keeps the product grounded, practical, and dry rather than sounding like enterprise SaaS.

On 2026-06-02 Peter corrected the direction:

- Drop the sci-fi direction for JobDone; that idea belongs elsewhere in Continuum.
- Add the dog callback idea:
  - opening beat: a tradesperson captures "fix the sink" plus the detail that Charlie the dog bites ankles
  - closing callback: before returning, JobDone recalls the dog detail and the tradesperson reacts, "Oh, Charlie!"
  - sound-effect selection should be agent-first: the agent searches CC0 Freesound candidates in the context of the script beat, picks its best first choice, and Peter reviews the advert moment rather than raw sound libraries
- Choremore is no longer an active product; parent/manager targeting should come through the JobDone Team angle.

## Dog Callback SFX Intents

The dog-callback script should carry structured `sfx_intent` metadata. Peter
should not have to browse sound libraries.

First render-plan draft:
`docs/adverts/jobdone-dog-callback-render-plan.md`

Opening beat:

```yaml
beat_id: charlie_first_bite
placement: After opening job detail, before the tradesperson says "Ow."
purpose: Make the remembered site detail funny and concrete without derailing the product point.
desired_sound: small dog bark plus brief frantic scramble or collar movement
mood: comic, close, sudden, slightly chaotic, not scary
duration_seconds: 0.8-1.8
license_priority: cc0
search_terms:
  - dog bark
  - small dog bark
  - dog scramble
  - frantic dog bark
avoid:
  - aggressive attack dog
  - long dog ambience bed
  - large scary dog
  - recognisable copyrighted media
first_guess_rule: Pick one short CC0 Freesound candidate that reads as a small comic dog, then place it under the "Ow" beat.
```

Callback beat:

```yaml
beat_id: charlie_callback_warning
placement: After the app recalls Charlie, before or under the tradesperson says "Oh, Charlie!"
purpose: Create the payoff that JobDone remembered the weird practical detail before the next visit.
desired_sound: one short dog bark or distant eager bark
mood: callback, recognisable, lighter than the first bark, friendly rather than threatening
duration_seconds: 0.4-1.2
license_priority: cc0
search_terms:
  - single dog bark
  - small dog bark
  - distant dog bark
avoid:
  - growling
  - dog attack
  - long barking sequence
  - sound that competes with the recalled app voice
first_guess_rule: Prefer a shorter/lighter bark than the opening SFX so Peter can ask for "longer" or "more frantic" only if the callback feels too small.
```

## Prior Preference Summary

Local capture summary also records:

- Peter wants 30-second audio ads to communicate the core value proposition as recall / retrieval, not just recording.
- Feature detail should be avoided.
- For Jobs Done, Peter likes grounded Yorkshire practicality, dry humour, and understated realism.

Source: `local/chatgpt-web-probe/ai-project-suggestions-20260530.json`

## Production Workflow Seed

The source suggested keeping a tiny production log:

```text
Script ID -> voice -> tone -> file name -> usable? -> notes
```

Example filename pattern:

```text
JD_ad01_yorkshire_gruff_v03.mp3
```

Track:

- script version
- ElevenLabs voice name / id
- settings
- generation date
- best line
- usable or not
- product / tone bucket

## Product Truth QA

Before generating paid audio, each script must pass:

1. Uses only `allowed_ad_claims` from `docs/product-truths/2026-06-02-jobdone.md`.
2. Avoids `forbidden_ad_claims`.
3. Demonstrates Recall, not just recording.
4. Does not claim automatic invoicing, CRM replacement, or always-correct AI answers.
5. Makes the review / confirmation step feel simple, not invisible.

## Next Move

Draft rough scripts:

1. `JD_ad01_yorkshire_interrupt`
2. `JD_ad02_dog_callback`
3. `JD_ad03_van_diary`
4. `JD_ad04_customer_callback`
5. `JD_ad05_team_parent_manager`

Then run Product Truth QA before any ElevenLabs generation.
