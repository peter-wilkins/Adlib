#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../../.." && pwd)"
VOICE_DIR="$ROOT/data/raw/audio-ads/jobdone-dog-callback"
VOICE="$VOICE_DIR/voice.wav"

mkdir -p "$VOICE_DIR"

ffmpeg -y -hide_banner -loglevel error \
  -f lavfi \
  -i "aevalsrc='0.12*sin(2*PI*180*t)+0.04*sin(2*PI*360*t)':d=28:s=48000" \
  -af "afade=t=in:st=0:d=0.2,afade=t=out:st=27.6:d=0.4" \
  -ac 2 \
  "$VOICE"

sha256sum "$VOICE"
