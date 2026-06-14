#!/usr/bin/env bash
set -euo pipefail

# title: Install REAPER PipeWire audio bridge
# summary: Install PipeWire JACK support so REAPER can open without a separate JACK server.

echo "== REAPER PipeWire audio bridge =="
echo "Installing pipewire-jack so JACK-capable audio apps can talk to PipeWire."
echo

sudo apt-get update
sudo apt-get install -y pipewire-jack pipewire-audio-client-libraries

echo
echo "Installed:"
if command -v pw-jack >/dev/null 2>&1; then
  command -v pw-jack
else
  echo "pw-jack was not found on PATH after install." >&2
  exit 1
fi

echo
echo "Try:"
echo "  jobdone-reaper"
