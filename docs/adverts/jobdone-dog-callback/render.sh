#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../../.." && pwd)"
PLAN_DIR="$ROOT/docs/adverts/jobdone-dog-callback"

VOICE="${VOICE:-$ROOT/data/raw/audio-ads/jobdone-dog-callback/voice.wav}"
OPENING_BARK="${OPENING_BARK:-$ROOT/data/raw/audio-ads/external-sfx/dog-bark/haulaway-630648-single-bark-small-to-medium-dog.mp3}"
CALLBACK_BARK="${CALLBACK_BARK:-$ROOT/data/raw/audio-ads/external-sfx/dog-bark/joviansounds-502655-single-dog-bark-king-charles-spaniel.mp3}"
OUT_DIR="${OUT_DIR:-$ROOT/data/processed/audio-ads/renders}"
OUT="${1:-${OUT:-$OUT_DIR/jobdone-dog-callback-v0.wav}}"

missing=0
for path in "$VOICE" "$OPENING_BARK" "$CALLBACK_BARK"; do
  if [[ ! -f "$path" ]]; then
    printf 'missing input: %s\n' "$path" >&2
    missing=1
  fi
done
if [[ "$missing" -ne 0 ]]; then
  printf '\nThis render recipe is ready, but the local ignored audio assets are not present yet.\n' >&2
  printf 'See %s\n' "$PLAN_DIR/README.md" >&2
  exit 2
fi

mkdir -p "$(dirname "$OUT")"
ffmpeg -version | head -1
ffmpeg -hide_banner -loglevel error -y \
  -i "$VOICE" \
  -i "$OPENING_BARK" \
  -i "$CALLBACK_BARK" \
  -/filter_complex "$PLAN_DIR/filter_complex.ffgraph" \
  -map "[out]" \
  -ar 48000 \
  -ac 2 \
  "$OUT"

printf 'wrote: %s\n' "$OUT"
