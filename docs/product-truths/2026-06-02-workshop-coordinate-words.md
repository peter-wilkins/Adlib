# Product Truth: Workshop Coordinate Words

Date: 2026-06-02

## Elevator Pitch

Workshop Coordinate Words is a simple location system for workshops: label where tools live, search by name on a phone, and give every bigger item a human-readable place code so people can find it and put it back.

## Quick Start Guide

1. Map the workshop into a simple coordinate scheme: walls, bays, shelves, drawers, bins, or zones.
2. Label the scheme physically so a human can decode it without training.
3. Add important tools and materials with names, aliases, photos, and location codes.
4. Search by tool name or describe it by voice.
5. Use requests, return notes, and moved-item reports only after the basic find/put-back loop works.
6. Run a time-and-motion pass before moving storage so the most-used things end up near the workbench.

## Internal Representation

```yaml
slug: workshop-coordinate-words
advert_priority: commercial_or_small_business
stage: idea_only
working_name_note: "Inspired by the phrase 'what three words for workshops'; avoid implying affiliation with what3words."
primary_user:
  - workshop owner
  - farm yard team
  - mechanics
  - shared maker/workshop users
buyer_job: find tools quickly and reduce repeated confusion about where things belong
core_loop:
  - define_coordinate_scheme
  - label_physical_locations
  - catalogue_items
  - search_or_voice_lookup
  - return_or_report_moved_item
  - improve_layout_from_usage
source_evidence:
  - Google Keep note imported 2026-06-02
truth_checks:
  - First prove people can find and return items faster.
  - Keep the coordinate scheme explainable in-app and on the wall.
  - Do not add blame/leaderboard features before measuring whether they help.
  - Treat inventory counts and purchasing as later modules.
allowed_ad_claims:
  - searchable tool locations
  - human-readable workshop codes
  - phone app and labels working together
  - layout improvement from usage observations
forbidden_ad_claims:
  - stock control is solved
  - theft prevention
  - automatic accountability
  - what3words affiliation
```

## One Sentence

Workshop Coordinate Words gives shared workshops a searchable, human-readable location code for tools and materials.

## User And Job

- User: people in shared workshops, farm yards, mechanics' bays, and tool-heavy spaces.
- Job: find the right thing, know where it belongs, and reduce repeated tool-location friction.

## Truth Levels

### Proven

- The concept appears in the 2026-06-02 Keep import:
  - use wall directions and a coordinate system for the back workshop.
  - search tools by name in a database / phone app.
  - larger items have the code written on them.
  - time-and-motion survey should place useful things close to the workbench.
  - admin may track requests and misplaced tools later.
  - the scheme can be defined in team settings.
  - dictation should convert human words into codes and explain the key.

### Working But Unproven

- No dedicated app exists yet.
- The exact coordinate grammar is not decided.
- The first real workshop fixture has not been mapped.

### Aspirational

- Voice lookup: "Where is the 13mm spanner?" returns a shelf/bin/wall code and a photo.
- Misplaced item report creates a useful nudge, not social friction.
- Purchase requests and farm machine/tool context can become later modules.

### False Or Stale

- It is not a full inventory, procurement, or asset-management system yet.
- It should not promise accountability until usage data proves the workflow is fair.
- It should not imply affiliation with what3words.

### Private Only

- Workshop layouts, expensive tool lists, user behaviour, and security-sensitive inventory details are private unless explicitly approved.

## Smallest Honest Pitch

Workshop Coordinate Words is a practical tool-location system: label the workshop, catalogue the tools, search by name, and make returning things to the right place easier.

## Docs/Copy To Change

1. Use "Workshop Coordinate Words" as the safer public name for now.
2. First copy should advertise "find and put back", not inventory control.
3. If a prototype is built, start with one real shelf/wall/bay and ten tools.

## Next Product Move

Create a one-page coordinate grammar and a tiny local prototype for ten tools in one workshop area.
