# Podcast Advert Script Automation Research

Date: 2026-06-14

Purpose: turn AdLib from "generate a few nice clips" into a repeatable system
for creating many claim-safe podcast advert scripts, reusable audio assets, and
first-pass renders without burning ElevenLabs credits on avoidable mistakes.

## Current Conclusion

AdLib should generate scripts from a structured advert brief, not from a blank
prompt. The useful unit is:

```text
Product Truth + audience + advert format + single job + mandatory claims + CTA
```

Then generate:

1. a few script structures,
2. reusable line assets,
3. a rough render with timing,
4. technical preflight,
5. creative critic pass,
6. searchable metadata,
7. only then an outside/audience test.

## Podcast Advert Patterns

### Formats

- **Produced spot**: 15-30 seconds, tightly scripted, scalable, useful for
  dynamic insertion and repeatable brand assets.
- **Host-read sponsorship**: usually 60-120 seconds, strongest when it feels
  like the host's own recommendation.
- **Native/branded segment**: longer, editorial, high trust, not the immediate
  AdLib MVP target.

Sources:

- Spotify: podcast ads can be host-read in the show's tone/style, or voiced by
  talent for a podcast environment.
  <https://ads.spotify.com/en-US/news-and-insights/podcast-advertising-101/>
- Acast: produced ads are short 15-30 second spots; host reads are commonly
  60-120 seconds and work because listeners trust the host relationship.
  <https://advertise.acast.com/news-and-insights/podcast-advertising-the-ultimate-guide>
- Matinee: campaign fit matters: host-read for trust, produced spots for
  scalable direct response, native branded content for affinity.
  <https://matinee.co.uk/blog/podcast-advertising-guide/>

### Script Inputs

Every generated podcast advert script should declare:

- `audience`: who is listening and what they already care about.
- `goal`: one job only, such as awareness, trust, click, trial, or recall.
- `format`: produced spot, host-read talking points, host-read verbatim line,
  or longer native segment.
- `placement`: pre-roll, mid-roll, post-roll, or reusable video/social cut.
- `mandatory copy points`: exact claims that must survive generation.
- `optional talking points`: host or narrator can choose from these.
- `cta`: one next action, easy to hear and remember.
- `claim posture`: current truth or vision trailer.
- `proof`: what Product Truth fields support the claims.

Sources:

- Rephonic: start with audience, goals, message, ad type, then write; avoid
  trying to do every goal at once because too much choice weakens action.
  <https://rephonic.com/blog/podcast-advertising-examples/>
- Gumball: give hosts four or five talking points but require only one to
  three; mark any mandatory copy points clearly.
  <https://blog.gumball.fm/how-to-write-host-read-ad-as-a-brand/>

## Automation Rules For Good Scripts

1. **One advert, one job.** Awareness, trust, signup, or recall: pick one.
2. **Audience first.** The hook should use the listener's problem language, not
   internal product language.
3. **Make the first three seconds concrete.** A real moment beats a vague claim.
4. **Use Product Truth as the claim boundary.** Vision trailer claims must be
   labelled; do not let them masquerade as shipped product claims.
5. **Write for the ear.** Short sentences, one idea per breath, no visual-only
   logic, no dense feature lists.
6. **Give host-read variants talking points, not a stiff script.** Keep
   mandatory legal/truth lines explicit and short.
7. **Make produced spots modular.** Generate reusable hooks, product lines,
   proof lines, CTAs, stings, and disclaimers separately.
8. **Gate before taste.** First prove the words match. Then judge whether it
   sounds credible.
9. **Render before paid feedback.** PickFu or similar review should see complete
   adverts with timing, bed, mix, and CTA, not raw line assets.
10. **Every asset must be searchable.** Rejected attempts are still useful
    evidence if labelled correctly.

## Skills Search

Searches run:

```bash
npx skills find "podcast advertising copywriting"
npx skills find "marketing copywriting"
```

Findings:

- No strong, podcast-ad-specific skill appeared.
- `nexu-io/open-design@copywriting` looked like the strongest general
  copywriting candidate from install count, but it is broad, not podcast-specific.
- `guia-matthieu/clawfu-skills@copywriting-classic` is useful for Ogilvy-style
  fundamentals, but it is not tailored to audio or host-read production.
- `boraoztunc/skills@ogilvy-copywriting` is another advertising-copy candidate,
  but lower install count than the broad copywriting skill.

Recommendation:

Do not install a generic copywriting skill yet. Build an AdLib-specific local
skill/workflow first, because the valuable knowledge here is not generic
copywriting. It is:

- Product Truth constraints,
- podcast/audio format,
- reusable line assets,
- transcription gates,
- timing gates,
- searchable generated metadata,
- render-first review.

Candidate local skill name:

```text
adlib-podcast-ad-writer
```

It should produce:

- host-read talking-point sheets,
- 15/30 second produced spot scripts,
- reusable asset manifests,
- CTA variants,
- technical preflight expectations,
- creative critic rubrics.

## ElevenLabs Lessons From Living Water

### Do Not Put Long Direction Text In The Spoken Prompt

The rejected V1 repair used direction text like "pronounce pond with a crisp
final d". ElevenLabs spoke those instructions out loud.

Rule: for safety-critical repair lines, send exact spoken words only. Put
creative direction in metadata, not in the TTS text, unless the tag form has
already been tested for that model and voice.

### Bracket Tags Are Powerful But Risky

Eleven v3 can interpret bracketed audio tags, but current experiments show they
can leak into the generated speech or alter the script. Use them only for
auditions or non-critical lines until the gate proves the words survive.

Source:

- ElevenLabs describes v3 audio tags as bracketed words that the model can use
  to direct audible action.
  <https://elevenlabs.io/blog/v3-audiotags>

### Pronunciation Dictionaries Are The Correct Long-Term Fix

ElevenLabs supports pronunciation dictionaries, including IPA and CMU alphabets,
and the TTS API accepts pronunciation dictionary locators. That is a better fix
for "Pond" vs "Pawn" than punctuation hacks, but it requires adding dictionary
management to AdLib and changes external ElevenLabs state.

Sources:

- ElevenLabs pronunciation dictionaries guide:
  <https://elevenlabs.io/docs/eleven-api/guides/how-to/text-to-speech/pronunciation-dictionaries>
- ElevenLabs Create Speech API accepts up to three pronunciation dictionary
  locators per request.
  <https://elevenlabs.io/docs/api-reference/text-to-speech/convert>

### Punctuation Hack Results

Living Water mentor submit line:

```text
Exactly. I think you're ready to submit your Level 2 Pond Challenge now.
```

Observed attempts:

- V2 exact text, no punctuation between Pond and Challenge: Whisper heard
  "Pawn Challenge"; rejected.
- V3 with `Pond. Challenge`: Whisper heard "Pond. Challenge"; gate passed, but
  the full stop created too much dead air for the asset.
- V4 exact text, slower and more stable, no full stop: Whisper still heard
  "Pawn Challenge"; rejected.

Decision:

- Keep V3 only as a temporary timing/audition fallback.
- Do not promote V4 for reuse.
- Next proper fix is either a pronunciation dictionary for `Pond Challenge` or a
  different mentor voice for that phrase.

### Canonical Token Normalisation

The gate now treats these as equivalent:

- `frogspawn`
- `frog spawn`

This is necessary because Whisper often splits the ecological term even when the
voice asset is acceptable.

## Quality Gates To Add Next

### Script Gate

Before paid generation:

- Product Truth claims pass.
- One advert has one job.
- CTA is singular and hearable.
- Host-read scripts separate mandatory copy from optional talking points.
- Produced spots stay within rough word budget:
  - 15 seconds: about 35-45 words,
  - 30 seconds: about 70-85 words,
  - 60 seconds: about 140-170 words.

### Audio Asset Gate

For each generated line:

- transcript matches approved spoken script after canonical normalisation,
- no extra leading or trailing words,
- no spoken direction text,
- no known mispronunciations,
- duration is within target range,
- audio is not clipped or too quiet,
- candidate repair is verified before promotion.

### Rendered Advert Gate

For complete adverts:

- final transcript matches expected script,
- total duration is within slot,
- silence gaps are within limits,
- CTA is audible,
- background bed does not mask speech,
- loudness/peak target passes,
- creative critic says it sounds human, useful, and not cheap.

## Immediate Next Build

1. Add pronunciation dictionary support to the ElevenLabs generation script.
2. Add script-generation templates for:
   - `produced_spot_15s`,
   - `produced_spot_30s`,
   - `host_read_talking_points_60s`,
   - `host_read_verbatim_30s`.
3. Add a script critic that checks:
   - one job,
   - audience fit,
   - first-three-seconds hook,
   - CTA clarity,
   - Product Truth support.
4. Add a rendered advert timing gate that measures:
   - total duration,
   - silence gaps,
   - speech overlap,
   - mean/max volume.
5. Create a local `adlib-podcast-ad-writer` skill once these rules settle.
