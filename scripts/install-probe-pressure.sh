#!/bin/bash
# Install Sovol probe_pressure.py into a mainline Klipper tree.
set -euo pipefail

KLIPPER_DIR="${1:-$HOME/klipper}"
SRC="$(cd "$(dirname "$0")/.." && pwd)/klipper/extras/probe_pressure.py"
DEST="$KLIPPER_DIR/klippy/extras/probe_pressure.py"

if [[ ! -d "$KLIPPER_DIR/klippy/extras" ]]; then
  echo "Klipper extras directory not found: $KLIPPER_DIR/klippy/extras" >&2
  exit 1
fi

cp "$SRC" "$DEST"
echo "Installed probe_pressure.py -> $DEST"
echo "Add to printer.cfg: [include probe_pressure.cfg]"
echo "Restart Klipper after copying config files."
