#!/usr/bin/env bash
#
# Build an installable COMPAS-Masonry package whose toolbar is the DESIGNED one
# (resources/COMPAS-Masonry.rui), not the one rhinocode generates from the rhproj
# icons.
#
# Why this exists
# ---------------
# `rhinocode project build` always emits its own COMPAS-Masonry.rui, and there is
# no flag to suppress it -- the only options are --buildversion, --buildtarget and
# --buildpath. Both files carry the same NAME, so the designed one has to be copied
# over the generated one AFTER the build and BEFORE `yak build` repackages the
# archive: `yak install --source <dir>` reads the .yak, not the loose files sitting
# next to it.
#
# Getting that order wrong fails silently, and stays invisible on a machine where
# resources/COMPAS-Masonry.rui is also registered by hand -- both copies carry the
# same pinned collection guid and the same bytes, so the toolbar looks right while
# the package carries the generated one (temp/wiki_icons.md 6a.5). The md5
# assertion in step 6 is the only check that actually catches it.
#
# Usage
# -----
#   ./resources/rui/build_plugin.sh 0.1.56-beta
#   ./resources/rui/build_plugin.sh 0.1.56-beta --bump-rhproj
#   ./resources/rui/build_plugin.sh 0.1.56-beta --skip-icons
#
# Stops before installing. `yak install` needs Rhino closed, so the script prints
# the exact command -- with the version read out of the generated manifest.yml,
# which is NOT the string passed to --buildversion -- rather than guessing when
# Rhino is safe to touch.
#
set -euo pipefail

# RHINOCODE and YAK are overridable on their own, not just through RHINO_APP:
# Rhino lays its tools out differently per platform, so deriving both from one
# app path only works on macOS. On Windows (Git Bash / WSL) point them straight
# at the executables, which live in `System/` rather than `Contents/Resources/bin/`:
#
#   RHINOCODE="/c/Program Files/Rhino 8/System/rhinocode.exe" \
#   YAK="/c/Program Files/Rhino 8/System/yak.exe" \
#   ./resources/rui/build_plugin.sh 0.1.58-beta --skip-icons \
#       --target "8.*-win" --builddir build/rh8-win
RHINO_APP="${RHINO_APP:-/Applications/Rhino 8.app}"
RHINOCODE="${RHINOCODE:-$RHINO_APP/Contents/Resources/bin/rhinocode}"
YAK="${YAK:-$RHINO_APP/Contents/Resources/bin/yak}"

VERSION=""
TARGET="8.*"
BUILDDIR="build/rh8"
SKIP_ICONS=0
BUMP_RHPROJ=0

while [ $# -gt 0 ]; do
    case "$1" in
        --skip-icons)   SKIP_ICONS=1; shift ;;
        --bump-rhproj)  BUMP_RHPROJ=1; shift ;;
        --target)       TARGET="$2"; shift 2 ;;
        --builddir)     BUILDDIR="$2"; shift 2 ;;
        -h|--help)      sed -n '2,34p' "$0"; exit 0 ;;
        -*)             echo "unknown option: $1" >&2; exit 2 ;;
        *)              VERSION="$1"; shift ;;
    esac
done

if [ -z "$VERSION" ]; then
    echo "usage: $0 <buildversion> [--skip-icons] [--bump-rhproj] [--target T] [--builddir D]" >&2
    echo "  bump the version on EVERY rebuild -- Rhino keys packages by version and" >&2
    echo "  installs them side by side, so reusing one invites a stale load." >&2
    exit 2
fi

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$ROOT"

RUI="resources/COMPAS-Masonry.rui"
RHPROJ="COMPAS-Masonry.rhproj"

for tool in "$RHINOCODE" "$YAK"; do
    [ -x "$tool" ] || { echo "not executable: $tool  (set RHINO_APP)" >&2; exit 1; }
done

echo "==> 1/7  regenerate the icon sheet and compile the RUI"
if [ "$SKIP_ICONS" -eq 1 ]; then
    echo "    skipped (--skip-icons); $RUI is used as it stands"
else
    # Defaults reproduce the shipped look: --color "" (the artwork AS DRAWN) and
    # --min-stroke 0.6. This comment said `--color "#E6E6E6"` until 2026-08-31 --
    # that was the old default, chosen when the icons were black-on-dark, and it
    # repainted the current light-toolbar set near-white until it vanished.
    # To use different values, run make_icons.py by hand and pass --skip-icons here.
    python resources/rui/set_rhproj_icons.py     # System A: rhproj, per command
    python resources/rui/make_icons.py           # System B: icons.png + ui.json wiring
    python resources/rui/generate_rui.py         # ui.json + icons.png -> the .rui
fi

echo "==> 2/7  verify both icon systems"
# Exits 1 on a missing icon, an out-of-range index, an unfilled button size, or a
# .rui compiled from a different sheet -- all of which would otherwise only show up
# as "my icons did not update" after an install.
python resources/rui/verify_icons.py

if [ "$BUMP_RHPROJ" -eq 1 ]; then
    echo "==> 2b/7  set identity.version in $RHPROJ to $VERSION"
    # Targeted text edit rather than a JSON round-trip: the rhproj carries 28
    # base64 SVGs, and reserialising it would rewrite the whole file.
    python3 - "$RHPROJ" "$VERSION" <<'PY'
import pathlib
import re
import sys

path, version = pathlib.Path(sys.argv[1]), sys.argv[2]
text = path.read_text()
pattern = re.compile(r'("identity"\s*:\s*\{.*?"version"\s*:\s*")([^"]*)(")', re.S)
match = pattern.search(text)
if not match:
    sys.exit("could not find identity.version -- edit it by hand")
print(f"    {match.group(2)} -> {version}")
path.write_text(pattern.sub(lambda m: m.group(1) + version + m.group(3), text, count=1))
PY
fi

echo "==> 3/7  clear $ROOT/build"
# Not optional: setuptools uses the same directory when the sync scripts pip-install
# the package, and it never prunes -- stale modules have survived a build this way.
rm -rf build/

echo "==> 4/7  rhinocode project build ($VERSION, target $TARGET)"
"$RHINOCODE" project build "./$RHPROJ" --buildversion "$VERSION" --buildtarget "$TARGET"
[ -d "$BUILDDIR" ] || { echo "expected $BUILDDIR -- wrong --target/--builddir?" >&2; exit 1; }

echo "==> 5/7  swap in the designed RUI"
cp "$RUI" "$BUILDDIR/COMPAS-Masonry.rui"

echo "==> 6/7  repackage and assert the archive carries it"
# `rhinocode project build` ALREADY wrote a .yak, containing the generated toolbar,
# under a different filename than the one `yak build` writes. Both declare the same
# version in their manifest, so leaving them side by side makes
# `yak install --source <dir>` pick between two archives on undocumented grounds --
# observed 2026-08-06 with 0.1.55-beta+23694, where it happened to choose correctly.
# Delete first so there is nothing to choose between.
rm -f "$BUILDDIR"/*.yak
# `yak build` needs the platform the package is FOR, and it does not read
# --buildtarget. This was hardcoded to `mac` until 2026-08-31, which meant
# --target/--builddir could aim a build at Windows and yak would still stamp it
# as a mac package -- an archive that installs on neither with any confidence.
case "$TARGET" in
    *win*) PLATFORM=win ;;
    *mac*|*macOS*) PLATFORM=mac ;;
    *) PLATFORM=any ;;
esac
echo "    packaging for platform: $PLATFORM  (from --target $TARGET)"
( cd "$BUILDDIR" && "$YAK" build --platform "$PLATFORM" )
python3 - "$RUI" "$BUILDDIR" <<'PY'
import glob
import hashlib
import io
import pathlib
import sys
import xml.etree.ElementTree as ET
import zipfile

rui, builddir = pathlib.Path(sys.argv[1]), pathlib.Path(sys.argv[2])
archives = sorted(builddir.glob("*.yak"))
if len(archives) != 1:
    sys.exit(f"expected exactly one .yak in {builddir}, found {len(archives)}")

mine = rui.read_bytes()
inside = zipfile.ZipFile(archives[0]).read("COMPAS-Masonry.rui")
guid = ET.parse(io.BytesIO(inside)).getroot().get("guid")

print(f"    repo : {hashlib.md5(mine).hexdigest()[:12]}  {len(mine)} bytes")
print(f"    yak  : {hashlib.md5(inside).hexdigest()[:12]}  {len(inside)} bytes  guid {guid}")
if mine != inside:
    sys.exit("    MISMATCH -- the archive carries the GENERATED toolbar, not yours")
print("    MATCH")
PY

echo "==> 7/7  install command"
# The build stamps its own +<build> suffix, so this string is neither the one passed
# to --buildversion nor the one in the .yak filename. A wrong version gives
# "[error] No package found by the name of..." which reads like a network failure.
INSTALLED_VERSION="$(python3 -c "
import pathlib, re, sys
text = pathlib.Path('$BUILDDIR/manifest.yml').read_text()
match = re.search(r'^version:\s*(\S+)', text, re.M)
sys.exit('no version in manifest.yml') if not match else print(match.group(1))
")"

cat <<EOF

Package ready: $BUILDDIR
Toolbar in it: yours ($RUI)

QUIT RHINO, then:

  "$YAK" install --source "$ROOT/$BUILDDIR" COMPAS-Masonry $INSTALLED_VERSION

Then confirm the package really carries the commands in the repo -- a version bump
proves a build happened, not what went into it, and Rhino keeps older versions on
disk beside the new one:

  python3 resources/rui/verify_install.py

On the next start Rhino registers the packaged RUI from the plugin folder. If a
second COMPAS-Masonry tab appears, it is the copy you opened by hand from
resources/ -- close that one in Tools > Toolbar Layout (see temp/wiki_icons.md 6a.5
before you do, it is a useful dev loop).
EOF
