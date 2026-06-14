# Product Truth: Project Status / CEO Orientation

Date: 2026-06-02

Scope: Workflow Manager project status, CEO Mode, and the phone CEO/DevOps status projection.

## One Sentence

Project Status is the local orientation surface that tells Peter and a restarting agent what is current, what matters next, and where to look, without turning the whole backlog into reading debt.

## User And Job

User: Peter, Workflow Manager Chairman/Marvin, and future recovery agents.

Job: recover orientation after context drift, agent restarts, many active branches, or phone-based work.

## Truth Levels

### Proven

- `scripts/project_status.py` exists and reads project ideas, the active branch from `docs/backlog.md`, and the local Thought Backlog projection.
- `scripts/ceo_status_feed.py` exists and generates a private phone-ready CEO feed from project status inputs plus foreground agent and workstream status.
- `docs/ceo-mode.md` defines the intended product shape: a short chaos-reduction view answering "what is going on, what can I click, and what matters next?"
- `docs/ceo-status-snap.md` defines the phone CEO snap as a read-only projection, not a source of truth or command surface.
- `tests/test_project_status.py` covers project parsing, active branch marking, planning omission, and surfaced Thought rendering.

### Working But Unproven

- The phone CEO/DevOps status surface can display local status copies. The latest cleanup patch is deployed to the day phone at commit `76d29ea`, but still needs Peter's live acceptance.
- Foreground agent and workstream status are available inputs, but they are not yet clearly presented as one canonical Project Status product.
- The active branch mechanism works mechanically, but the current stored branch can be stale.

### Aspirational

- One compact default status view with active branch, surfaced Thought, top active projects, agent state, and next action.
- A one-screen private lab overview generated from the same source instead of another hand-maintained dashboard.
- Product Truth briefs for the top products, feeding honest docs, elevator pitches, adverts, and audio scripts.
- Copy and ElevenLabs API audio creation after the top product truths are nailed down.

### False Or Stale

- `docs/project-workflow.md` still says status should show `Done` projects first.
- `scripts/project_status.py` currently sorts `Done` projects first by default, which conflicts with the newer CEO Mode goal of reducing orientation load.
- `tests/test_project_status.py` currently enforces the stale `Done`-first behaviour.
- `docs/backlog.md` still names `Phone Loop Reliability / Restart Recovery` as the active branch, even though current work has moved through phone cleanup, Agent Kit mode/status work, and Product Truth.

### Private Only

- Raw Thought Backlog projections, foreground agent state, phone Bridge status, and workstream events are local/private evidence.
- This is not ready to expose as public status, screenshots, or marketing proof without redaction.

## Smallest Honest Pitch

Project Status is a private local orientation view for Workflow Manager. It gathers the current branch, surfaced Thought, active products, and agent/workstream signals so Peter or a restarting agent can recover focus quickly. Today the pieces exist, but the default status command is too verbose and stale-oriented; the next product slice is making it CEO-compact by default.

## Docs And Code To Reconcile

1. Update `docs/project-workflow.md` so status means CEO-compact orientation by default, not `Done`-first backlog reporting.
2. Update `scripts/project_status.py` and `tests/test_project_status.py` so the default view prioritises current active work and hides completed work unless explicitly requested.
3. Clarify in `docs/ceo-status-snap.md` that the phone snap is a projection over Project Status, not a second project-status product.
4. Update `docs/backlog.md` when a branch becomes current; stale active branch text creates false recovery state.

## Next Product Move

Recommended next slice: rewrite `scripts/project_status.py` into a CEO-compact default view, with `--done` or `--all` for deeper backlog views.

After that, run this Product Truth pass across the top products. Once those truthful product spines exist, start the product-copy and audio-generation backlog item so written copy and ElevenLabs API scripts are based on proven product reality rather than hype.
