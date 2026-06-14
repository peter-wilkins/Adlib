# Product Truth: Thought Backlog / Intake Mode

Date: 2026-06-02

## One Sentence

Thought Backlog and Intake Mode preserve messy human input as source, then project it into the next useful thought, action, reminder, or parked branch without creating another planning silo.

## User And Job

- User: Peter and Workflow Manager agents recovering signal from dictation, notes, emails, brain dumps, and chat messages.
- Job: stop ideas from being lost or exploding into tasks; keep the next action visible while preserving provenance.

## Truth Levels

### Proven

- `docs/thought-backlog.md` defines the core rule: Thought is the source unit.
- `scripts/render_thought_backlog_projection.py` exists and is covered by `tests/test_render_thought_backlog_projection.py`.
- `scripts/project_status.py` reads the local Thought Backlog projection and renders one surfaced Thought.
- `docs/broad-first-intake-2026-05-24.md` demonstrates the broad-first branch matrix pattern.
- `docs/thought-backlog.md` defines note types for project thoughts, reminders, calendar reminders, waiting-for items, research questions, personal logs, and operational actions.

### Working But Unproven

- The projection model works for local captured sources, but Google Keep and other external notes are not yet a smooth import path.
- The broad-first matrix is useful, but it is still hand-curated rather than an always-current generated view.
- Squirrels are captured in backlog/docs, but there is no generated Squirrel Index yet.

### Aspirational

- A reliable Journey/Thought view that can generate thread-like projections without fixed silos.
- Calendar/reminder projections from captured thought fragments.
- A low-friction review flow where Peter can accept, park, split, or promote thoughts from the phone.
- Source-backed public story curation from private logs.

### False Or Stale

- The current status surface can show stale active branch text, so the Thought projection is not yet enough to restore full context.
- The product is not a full task manager, calendar, or knowledge graph.
- It does not yet automatically understand every messy note or email.

### Private Only

- Raw brain dumps, captured thoughts, Google Keep imports, and local projections are private by default.
- Public copy should describe the mechanism, not expose raw thought content.

## Smallest Honest Pitch

Thought Backlog is a local source-first planning layer. It keeps messy capture intact, extracts candidate thoughts and actions, and surfaces one useful next move so Peter does not have to reread everything. It is currently a private workflow projection, not a polished public task app.

## Docs/Copy To Change

1. `docs/thought-backlog.md` - add a compact current implementation section at the top.
2. `docs/project-workflow.md` - align status and thought projection rules with CEO-compact orientation.
3. `docs/backlog.md` - keep live branch state fresh enough that Thought projection does not point into stale context.

## Next Product Move

Make the first generated Thought/Squirrel Index, or make `project_status.py` CEO-compact so the surfaced Thought is actually usable on top of current work.
