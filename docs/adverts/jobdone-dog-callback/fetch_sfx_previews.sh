#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../../.." && pwd)"
SFX_DIR="$ROOT/data/raw/audio-ads/external-sfx/dog-bark"

OPENING_BARK="$SFX_DIR/haulaway-630648-single-bark-small-to-medium-dog.mp3"
CALLBACK_BARK="$SFX_DIR/joviansounds-502655-single-dog-bark-king-charles-spaniel.mp3"

mkdir -p "$SFX_DIR"

curl -L --fail --silent --show-error \
  -o "$OPENING_BARK" \
  "https://cdn.freesound.org/previews/630/630648_7228277-hq.mp3"

curl -L --fail --silent --show-error \
  -o "$CALLBACK_BARK" \
  "https://cdn.freesound.org/previews/502/502655_9561949-hq.mp3"

sha256sum "$OPENING_BARK" "$CALLBACK_BARK"
