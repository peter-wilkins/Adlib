# Product Truth: Phone Control Surface

Date: 2026-06-02

## One Sentence

Phone Control Surface is Peter's local-first Android conduit for talking to agents, preserving phone-side capture, seeing system status, and controlling media without turning the phone into another opaque brain.

## User And Job

- User: Peter using his day phone and dev phones while away from the Linux keyboard.
- Job: capture thoughts, send/receive agent messages, keep pending work safe, and glance at useful status with minimal UI load.

## Truth Levels

### Proven

- The Android project exists at `phone-control-surface-android`.
- The app builds, tests, and installs through `scripts/install_phone_control.py`.
- The day-phone install path is guarded by `--confirm-day-phone`; the latest debug build was installed on `day-phone` serial `RFCN20BKRGW` from commit `76d29ea`.
- The active snap rail has been narrowed to Session, Continuum, JobDone, DevOps, and Listen.
- Unit tests cover Bridge copy/projection, pending messages, route metadata, VPN labels, scroll policy, keyboard clearance, file/link/photo intake stores, DevOps copy, Codex runway copy, and Listen logic.
- The app displays a build commit hash through `BuildInfo`.

### Working But Unproven

- DevOps status now orders Codex Runway, CEO Briefing, Agents, then DevOps, but Peter still needs to dogfood the installed build.
- The app can show VPN/Bridge hints, but route correctness still depends on the day phone's Tailscale/VPN state.
- File, link, and photo intake have local store tests; full end-to-end import review still needs live acceptance.
- Phone identity is still partly confused because event payloads can default to `deviceId=dev-phone`.

### Aspirational

- Snappy appendable dictation with non-blocking transcription, cursor-aware insertions, and no silent audio loss.
- WhatsApp-style reactions and anchored replies.
- Field Capture as a low-fiddle farm/field mode.
- A clean phone projection over all useful agents without exposing raw private state.
- Strong device identity and account isolation.

### False Or Stale

- Older docs still describe Night Note and SignalSource snaps as active product surface, but the current active rail excludes them.
- Field Capture is documented as high priority, but it is not currently an active snap.
- The app is not yet a generic public mobile client.
- It is not a trusted production security boundary; it is a local dogfood conduit.

### Private Only

- Phone Bridge events, raw captures, photo artifacts, agent routes, Tailscale URLs, and device state are private evidence.
- Public demos must use redacted or synthetic content.

## Smallest Honest Pitch

Phone Control Surface is a private Android control surface for Peter's local AI workflow. It lets the phone act as a capture and routing conduit to local agents, with status and media snaps kept intentionally small. The current build is useful for dogfooding, but it is still a private, local-first prototype rather than a public mobile product.

## Docs/Copy To Change

1. `docs/phone-control-surface.md` - add a current active snap lineup near the top.
2. `phone-control-surface-android/README.md` - move Night Note, Field, CEO Status, and SignalSource into dormant/history sections.
3. `docs/backlog.md` - keep Phone Device Identity visible until `deviceId` stops conflating physical phones.

## Next Product Move

Dogfood the installed day-phone build. Verify: visible Android controls stay visible, DevOps refreshes on focus, Codex runway changes, no swipe-triggered copy toast, and the active snap rail feels small enough.
