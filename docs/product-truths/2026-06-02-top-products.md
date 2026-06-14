# Product Truth: Top Product Set

Date: 2026-06-02

Purpose: decide which products deserve Product Truth briefs before writing copy, public docs, or ElevenLabs API audio scripts.

## Product Truth Format

Each Product Truth should start with the pieces a human or buyer can use:

1. **Elevator Pitch** - the honest public-facing value in plain language.
2. **Quick Start Guide** - first steps for a real user, even if the current answer is "not built yet".
3. **Internal Representation** - structured facts that agents can use to generate docs, test product claims, run QA sessions, and prevent adverts drifting away from reality.

The internal representation should be boring and inspectable. Markdown with YAML-like fields is enough for now. Use a database only when we need queries over many product truths.

## Selection Rule

The current priority is not "all interesting internal tools". It is:

1. Things that could plausibly make money.
2. Things Peter wants to advertise.
3. Social / Earth good causes, especially water restoration and Living Water Skills.
4. Tools that directly help create truthful adverts for the above.

Internal Workflow Manager tools still matter, but they are not the first advert targets unless they support those priorities.

## Top Product Truth Set

| Rank | Product | Why It Is Top | Truth Brief |
| ---: | --- | --- | --- |
| 1 | JobDone | Commercial app candidate with a clear user: self-employed tradespeople who need voice capture, confirmation, timeline, and recall. | `docs/product-truths/2026-06-02-jobdone.md` |
| 2 | Living Water Skills | Social / Earth good product: practical water-cycle restoration learning, logbook evidence, safe review, and public story generation. | `docs/product-truths/2026-06-02-living-water-skills.md` |
| 3 | Jury-Rigged Video Creation Software | Content/product candidate: playful physical challenge design plus capture/edit workflow for videos and competitions. | `docs/product-truths/2026-06-02-jury-rigged-video-creation.md` |
| 4 | Workshop Coordinate Words | Practical small-business/workshop tool candidate: human-readable coordinate labels, searchable tools, requests, and return discipline. | `docs/product-truths/2026-06-02-workshop-coordinate-words.md` |
| 5 | Audio Advert Generator | Dogfood tool that turns Product Truth into approved scripts, searchable audio assets, and ElevenLabs API outputs. | `docs/product-truths/2026-06-02-audio-advert-generator.md` |

## Parked For Later Truth Passes

| Product | Why Parked |
| --- | --- |
| Regenerative AI Water Broadcast | Still useful, but Living Water Skills is the clearer product-shaped water priority right now. |
| Continuum Kit / Bootstrap Sharing | Important long-term story, but less directly monetisable than JobDone and less concrete than Living Water Skills. |
| Phone Control Surface | Crucial internal conduit, but not first in the advert queue. |
| Project Status / CEO Orientation | Valuable internal orientation tool; use it as evidence, not as the first public product. |
| Thought Backlog / Intake Mode | Strong internal Workflow Manager capability; not the next advert target. |
| Personal Dictionary / Transcript Cleanup | Important support capability; fold into phone/dictation story later. |
| Listen | Useful app snap; park until the media-player product surface is cleaner. |

## Copy And Audio Consequence

Do not start paid ElevenLabs generation from slogans.

First dogfood copy/audio candidates:

1. JobDone: practical tradesperson advert.
2. Living Water Skills: public good / learning pathway advert.
3. Jury-Rigged: short teaser for the video/game concept, explicitly labelled early concept.
4. Workshop Coordinate Words: practical "find the thing" workshop advert.

Every script should cite which Product Truth fields it used. If the script claims more than the Product Truth allows, it fails QA.
