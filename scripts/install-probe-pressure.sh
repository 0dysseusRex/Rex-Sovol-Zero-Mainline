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

ATC_SRC="$(cd "$(dirname "$0")/.." && pwd)/klipper/extras/axis_twist_pressure.py"
ATC_DEST="$KLIPPER_DIR/klippy/extras/axis_twist_pressure.py"
cp "$ATC_SRC" "$ATC_DEST"
echo "Installed axis_twist_pressure.py -> $ATC_DEST"

ELC_SRC="$(cd "$(dirname "$0")/.." && pwd)/klipper/extras/eddy_loadcell_calibrate.py"
ELC_DEST="$KLIPPER_DIR/klippy/extras/eddy_loadcell_calibrate.py"
cp "$ELC_SRC" "$ELC_DEST"
echo "Installed eddy_loadcell_calibrate.py -> $ELC_DEST"

echo "Add to printer.cfg: [include probe_pressure.cfg]"
echo "sovol_eddy.cfg includes [eddy_loadcell_calibrate] for experimental eddy cal."
echo "Restart Klipper after copying config files."
