#!/bin/bash
# Install network_status.py into a mainline Klipper tree (display IP menus).
set -euo pipefail

KLIPPER_DIR="${1:-$HOME/klipper}"
SRC="$(cd "$(dirname "$0")/.." && pwd)/klipper/extras/network_status.py"
DEST="$KLIPPER_DIR/klippy/extras/network_status.py"

if [[ ! -d "$KLIPPER_DIR/klippy/extras" ]]; then
  echo "Klipper extras directory not found: $KLIPPER_DIR/klippy/extras" >&2
  exit 1
fi

cp "$SRC" "$DEST"
echo "Installed network_status.py -> $DEST"
echo "Add to printer.cfg (via display_macros.cfg): [network_status]"
echo "Restart Klipper after updating config."
