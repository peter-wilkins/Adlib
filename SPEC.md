# Adlib MVP Spec

## One-line description

Adlib is an AI tool for creating natural, host-read style podcast adverts from a short brief.

## Working problem statement

Podcast adverts work best when they sound like they belong in the show. Most ad creation tools are either too generic, too corporate, or too focused on delivery infrastructure rather than the creative act of making a spoken advert.

Adlib helps a podcaster, producer, or advertiser quickly turn a product brief into a short, natural audio advert script that can be read by a host or generated as audio.

## Core idea

The user gives Adlib a brief:

- What is being advertised?
- Who is the audience?
- What is the podcast or show style?
- What tone should the ad have?
- How long should the advert be?
- What must be included?
- What must not be said?

Adlib produces a polished podcast advert script, with optional variants and delivery notes.

## MVP goal

Build the smallest useful tool that proves whether people want AI help creating podcast adverts.

The MVP should answer this question:

> Can a user create a better podcast advert script in under two minutes than they could by starting from a blank page?

## Target users

### Primary

Independent podcasters, producers, and small media teams who need to create host-read adverts quickly.

### Secondary

Small brands or agencies that want podcast-style ad reads but do not know how to write them naturally.

## Initial use case

A user wants to create a 30 to 60 second host-read podcast advert.

They enter a short brief and receive:

1. A finished ad script.
2. A shorter version.
3. A more casual version.
4. Optional host delivery notes.

## Product principles

### Audio-friendly first

The product should be designed around spoken language, not written marketing copy. Scripts must sound natural when read aloud.

### Obvious beats clever

The tool should avoid jargon and ad-tech complexity. The user should immediately understand what to do.

### Creative, not infrastructure

This MVP is about creating adverts, not managing campaigns, targeting listeners, inserting ads into feeds, or analytics.

### Keep the host voice intact

The output should feel like something a real podcast host could say without sounding fake, over-polished, or salesy.

## MVP user flow

1. User opens the app.
2. User fills in a simple advert brief.
3. User clicks generate.
4. Adlib creates a script.
5. User can request variations.
6. User copies the script or saves it.

## Suggested first screen

A single form with these fields:

- Product or sponsor name
- What the product does
- Target listener
- Podcast/show description
- Tone
- Desired length
- Required points
- Things to avoid
- Call to action

Tone options:

- Natural
- Funny
- Serious
- Warm
- Enthusiastic
- Dry / understated
- Premium
- Founder-led

Length options:

- 15 seconds
- 30 seconds
- 60 seconds
- Custom

## Output format

Each generated advert should include:

```markdown
# Ad script

[The finished spoken advert]

## Short version

[A shorter cut]

## More casual version

[A more relaxed version]

## Delivery notes

- Suggested pacing
- Words to emphasise
- Where the host can personalise it
```

## Important quality rules

Generated scripts should:

- Sound good when spoken aloud.
- Avoid generic marketing filler.
- Avoid fake enthusiasm.
- Avoid phrases no real host would say.
- Be clear about the product.
- Include the call to action.
- Respect required claims and prohibited claims.
- Fit the requested duration.

Generated scripts should not:

- Sound like a banner ad.
- Overpromise.
- Invent factual claims.
- Use fake testimonials.
- Make regulated claims without user-provided wording.
- Add discounts, URLs, or offer codes unless provided.

## First technical shape

The simplest version can be a web app with:

- A form for the brief.
- A backend endpoint that calls an LLM.
- A prompt template tuned for spoken host-read adverts.
- A results page with copy buttons.
- A local history of generated adverts.

## Suggested stack

This can be changed later, but a simple starting point would be:

- Next.js or another lightweight web framework.
- Server-side LLM call.
- Markdown output rendering.
- Local storage or a simple database for saved adverts.

## Data model

### AdvertBrief

```ts
type AdvertBrief = {
  sponsorName: string;
  productDescription: string;
  targetListener?: string;
  showDescription?: string;
  tone: string;
  lengthSeconds: number;
  requiredPoints?: string;
  avoid?: string;
  callToAction?: string;
};
```

### GeneratedAdvert

```ts
type GeneratedAdvert = {
  id: string;
  brief: AdvertBrief;
  script: string;
  shortVersion?: string;
  casualVersion?: string;
  deliveryNotes?: string[];
  createdAt: string;
};
```

## Prompt behaviour

The system prompt should make the model behave like an experienced podcast ad copywriter.

It should prioritise:

- Spoken rhythm.
- Natural transitions.
- Clear benefit.
- Host credibility.
- Listener trust.
- Compliance with the brief.

It should avoid:

- Hype.
- Corporate copy.
- Robotic structure.
- Unsupported claims.
- Overly American ad language unless requested.

## Possible prompt skeleton

```text
You are an expert podcast ad copywriter.
Create a natural host-read podcast advert from the brief below.
The advert must sound good when spoken aloud.
Do not invent factual claims, discounts, testimonials, URLs, or guarantees.
Keep the tone human, specific, and credible.
Match the requested duration.
Return: main script, short version, more casual version, and delivery notes.
```

## MVP features

### Must have

- Create advert from brief.
- Choose tone.
- Choose length.
- Generate main script.
- Generate at least two variants.
- Copy result.
- Save recent generations locally or in simple storage.

### Should have

- Regenerate with feedback.
- Make it more natural.
- Make it shorter.
- Make it more like a host read.
- Add delivery notes.

### Not yet

- Audio generation.
- Dynamic ad insertion.
- Campaign management.
- Analytics.
- Payments.
- Multi-user accounts.
- Brand asset library.
- Full podcast feed integration.

## Validation plan

Test with 5 to 10 real or imagined sponsor briefs.

For each generated advert, check:

1. Would a real host say this?
2. Is the product clear?
3. Is the call to action clear?
4. Does it fit the requested time?
5. Is it better than a blank-page attempt?

## Example brief

```text
Sponsor: GreenKettle
Product: A smart kettle that learns your tea and coffee routine.
Audience: Busy remote workers who listen to a productivity podcast.
Show style: Conversational, warm, lightly funny.
Tone: Natural and understated.
Length: 30 seconds.
Required points: Learns your routine, saves energy, app control.
Avoid: Do not make health claims.
CTA: Visit greenkettle.example and use code PODCAST for 10% off.
```

## Success criteria for MVP

The MVP is successful if:

- A user can create a usable host-read advert in under two minutes.
- The generated advert sounds natural when read aloud.
- The user wants to generate a second version rather than abandon the tool.
- The tool clearly feels creative, not like an ad dashboard.

## Open questions

- Should Adlib start as text-only, or include AI voice generation early?
- Should it optimise for podcasters writing their own host reads, or advertisers briefing podcasters?
- Should the first version be a standalone web app, a CLI, or a GitHub-backed prompt tool?
- Should saved adverts be private by default?
- Should the product later support importing a podcast transcript to imitate the host style?

## Immediate next steps

1. Create the basic app shell.
2. Build the advert brief form.
3. Create the first prompt template.
4. Generate markdown output.
5. Add copy buttons.
6. Test with example briefs.
7. Refine the prompt based on what sounds bad when read aloud.
