#!/usr/bin/env bash
set -euo pipefail

# title: Install REAPER audio editor
# summary: Install the official Linux x86_64 REAPER build locally for audio-advert editing.

source_path="${BASH_SOURCE[0]}"
if command -v readlink >/dev/null 2>&1; then
  source_path="$(readlink -f "$source_path")"
fi
root="$(cd "$(dirname "$source_path")/.." && pwd)"

version="${REAPER_VERSION:-7.73}"
major="${version%%.*}"
version_digits="${version//./}"
archive="reaper${version_digits}_linux_x86_64.tar.xz"
url="${REAPER_URL:-https://www.reaper.fm/files/${major}.x/${archive}}"

cache_dir="$root/local/downloads/reaper"
install_base="${REAPER_INSTALL_BASE:-$HOME/.local/opt}"
install_dir="$install_base/reaper-$version"
current_link="$install_base/reaper-current"
bin_dir="$HOME/.local/bin"
desktop_dir="$HOME/.local/share/applications"

echo "== REAPER local install =="
echo "Version: $version"
echo "Download: $url"
echo "Install: $install_dir"
echo

for tool in curl tar file ldd; do
  if ! command -v "$tool" >/dev/null 2>&1; then
    echo "Missing required tool: $tool" >&2
    exit 1
  fi
done

mkdir -p "$cache_dir" "$install_base" "$bin_dir" "$desktop_dir"
archive_path="$cache_dir/$archive"
if [[ ! -s "$archive_path" ]]; then
  curl -fL --retry 3 --output "$archive_path" "$url"
fi

tmp_dir="$(mktemp -d)"
trap 'rm -rf "$tmp_dir"' EXIT

tar -xf "$archive_path" -C "$tmp_dir"
src_dir="$tmp_dir/reaper_linux_x86_64"
if [[ ! -x "$src_dir/REAPER/reaper" ]]; then
  echo "Downloaded archive did not contain REAPER/reaper." >&2
  exit 1
fi

rm -rf "$install_dir"
cp -a "$src_dir" "$install_dir"
ln -sfn "$install_dir" "$current_link"
ln -sfn "$current_link/REAPER/reaper" "$bin_dir/reaper"

cat > "$desktop_dir/reaper-continuum.desktop" <<EOF
[Desktop Entry]
Type=Application
Name=REAPER
Comment=Audio production and editing
Exec=$bin_dir/reaper %F
Terminal=false
Categories=AudioVideo;Audio;AudioVideoEditing;
MimeType=audio/wav;audio/x-wav;audio/mpeg;audio/ogg;
EOF

if command -v update-desktop-database >/dev/null 2>&1; then
  update-desktop-database "$desktop_dir" >/dev/null 2>&1 || true
fi

echo "Binary:"
file "$current_link/REAPER/reaper"
echo

missing_libs="$(ldd "$current_link/REAPER/reaper" | awk '/not found/ {print $1}')"
if [[ -n "$missing_libs" ]]; then
  echo "REAPER installed, but these libraries are missing:" >&2
  echo "$missing_libs" >&2
  exit 1
fi

echo "Installed:"
echo "  $bin_dir/reaper"
echo
echo "Try:"
echo "  reaper"

if ! command -v pw-jack >/dev/null 2>&1; then
  echo
  echo "Audio note:"
  echo "  This PipeWire system does not have pw-jack installed."
  echo "  If REAPER reports that JACK is not running, run:"
  echo "    do-now install-reaper-audio"
fi
