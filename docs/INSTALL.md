# Installation

## Prerequisites

- Sovol Zero on **mainline Klipper** (not Sovol fork)
- CAN MCUs configured and communicating
- `[force_move]` with `enable_force_move: True` (needed for `SET_KINEMATIC_POSITION` during first eddy cal)

## 1. Install probe_pressure.py

```bash
git clone https://github.com/0dysseusRex/Rex-Sovol-Zero-Mainline.git
cd Rex-Sovol-Zero-Mainline
./scripts/install-probe-pressure.sh ~/klipper
```

Or manually:

```bash
cp klipper/extras/probe_pressure.py ~/klipper/klippy/extras/
```

## 2. Deploy config files

```bash
cp config/sovol_eddy.cfg ~/printer_data/config/
cp config/probe_pressure.cfg ~/printer_data/config/
```

## 3. Update printer.cfg

Add includes (after your other macro includes):

```ini
[include sovol_eddy.cfg]
[include probe_pressure.cfg]
```

Confirm Z homing uses the eddy virtual endstop:

```ini
[stepper_z]
endstop_pin: probe:z_virtual_endstop
```

Add safe Z home (if not present):

```ini
[safe_z_home]
home_xy_position: 76.2,76.2
speed: 90.0
z_hop: 5
z_hop_speed: 10.0
```

**Do not** hardcode `reg_drive_current` in `sovol_eddy.cfg` — let `SAVE_CONFIG` manage it after `LDC_CALIBRATE_DRIVE_CURRENT`.

## 4. Update macros (Macro.cfg)

Required changes from this repo's `config/Macro.cfg`:

| Macro | Change |
|---|---|
| `G28` | Check `'calibrate' in eddy config` (not `printer.probe.is_calibrated` — mainline lacks that) |
| `PRINT_START` | `SET_GCODE_OFFSET Z=0` → `BED_LOADCELL_Z_OFFSET` → `G28 Z` → `LINE_PURGE` |
| `END_PRINT` | Remove `PROBE_EDDY_NG_SET_TAP_OFFSET` |

## Slicer start / end g-code

Copy from `slicer/Sovol-OrcaSlicer-start.gcode` and `slicer/Sovol-OrcaSlicer-end.gcode`, or paste:

**Start g-code** (replaces the long OEM heat/home/purge block):

```gcode
M117
START_PRINT BED=[bed_temperature_initial_layer_single] HOTEND=[nozzle_temperature_initial_layer] CHAMBER=[chamber_temperature]
SET_PRINT_STATS_INFO TOTAL_LAYER=[total_layer_count]
G90
```

`START_PRINT` is an alias for `PRINT_START`. The macro handles homing, bed/chamber heat, load-cell Z offset, eddy mesh, skew profile, and adaptive `LINE_PURGE`. Do not duplicate M140/M190, G28, M104/M109, or manual purge lines here.

Enable **Exclude Objects** in the slicer so Moonraker injects object bounds for adaptive purge placement. If your slicer profile has no chamber variable, use `CHAMBER=0`.

**End g-code:**

```gcode
END_PRINT
```

## Line purge (SimpleAF-style KAMP)

Tune at runtime: `SETUP_LINE_PURGE PURGE_AMOUNT=40 FLOW_RATE=12`  
Skip once: `LINE_PURGE PURGE=0`

## 5. Restart

```bash
sudo systemctl restart klipper
```

Verify objects exist in Moonraker:

- `probe_eddy_current eddy`
- `probe_pressure`
- `gcode_macro BED_LOADCELL_Z_OFFSET`
- `gcode_macro EDDY_CALIBRATE_PREP`

## What NOT to install

| Item | Reason |
|---|---|
| `[load_cell]` upstream module | Wrong API — PD10 is digital trigger, not HX711 |
| `[z_offset_calibration]` | Requires Sovol fork eddy probe methods |
| `eddyng.cfg` / `[probe_eddy_ng]` | Not used — mainline `probe_eddy_current` path chosen |

## probe_pressure.py patch

This repo includes a small fix: `RUN_PROBE_PRESSURE` stores `last_z_result` (required by `BED_LOADCELL_Z_OFFSET`). Stock Sovol v1.3.7 omitted this.
