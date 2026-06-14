# JobDone Reusable Recall Voice Assets

Status: draft manifest only. Not approved for paid generation.

Purpose: prepare small reusable JobDone voice assets from Product Truth so Peter
can approve exact copy and spend before the remaining ElevenLabs subscription
window closes.

Source truth:

```text
docs/product-truths/2026-06-02-jobdone.md
```

## Product Truth QA

- Uses the `Capture -> Confirmation -> Timeline -> Recall` spine.
- Claims JobDone helps tradespeople capture, confirm, and recall job details.
- Does not claim automatic invoicing, finished CRM/accounting, always-correct AI,
  or no-review automation.
- Uses concrete tradesperson memory moments rather than generic SaaS claims.

## Review

List planned generations without credits:

```bash
python3 scripts/audio_ad_generate_elevenlabs_voice_lines.py \
  --manifest docs/adverts/jobdone-reusable-recall/elevenlabs-david-recall-lines-v1.json \
  --list
```

Generate only after Peter approves the exact text and the manifest is changed to:

```json
"approvedForPaidGeneration": true
```
