#!/usr/bin/env bash
# Packs mod/ into a real BG3 .pak using LSLib's Divine tool.
#
# Running Divine.dll natively via `dotnet` on Linux hits a confirmed upstream bug
# (https://github.com/Norbyte/lslib/issues/220): its path-validation code assumes
# Windows-style paths and crashes on absolute Linux paths ("This operation is not
# supported for a relative URI"). So we run it through a DEDICATED Wine prefix
# instead (NOT your game's actual Proton prefix — this stays fully isolated from
# your BG3 install).
#
# One-time setup for that prefix, if you haven't already:
#   WINEPREFIX="$HOME/Documents/BG3_SE_GUI/.wineprefix" winetricks -q dotnet8
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
DIVINE_EXE="$SCRIPT_DIR/tools/Divine.exe"
SRC="$SCRIPT_DIR/mod"
OUT_DIR="$SCRIPT_DIR/dist"
OUT="$OUT_DIR/BG3GuiBridge.pak"
export WINEPREFIX="${WINEPREFIX:-$SCRIPT_DIR/.wineprefix}"

if [ ! -f "$DIVINE_EXE" ]; then
    echo "error: $DIVINE_EXE not found. See tools/README.md." >&2
    exit 1
fi

if [ ! -d "$WINEPREFIX" ]; then
    echo "error: Wine prefix not found at $WINEPREFIX" >&2
    echo "Run this once first:" >&2
    echo "  WINEPREFIX=\"$WINEPREFIX\" winetricks -q dotnet8" >&2
    exit 1
fi

mkdir -p "$OUT_DIR"
echo "Packing $SRC -> $OUT ..."
echo "(using Wine prefix: $WINEPREFIX)"

# Divine's path validation (a Uri.IsFile check) only recognizes Windows-style
# absolute paths. Plain Unix paths — even run through Wine — read as "relative"
# to it and crash. winepath -w gives the Z:\... form it actually expects.
WIN_SRC="$(winepath -w "$SRC")"
WIN_OUT="$(winepath -w "$OUT")"

wine "$DIVINE_EXE" --game bg3 --action create-package --source "$WIN_SRC" --destination "$WIN_OUT"
echo "Done: $OUT"
