# Installation

## Prerequisites

- Sovol Zero **already running mainline Klipper** (not the Sovol firmware fork)
- Your own working `printer.cfg` with steppers, heaters, MCUs, and Moonraker
- CAN MCUs configured and communicating
- `[force_move]` with `enable_force_move: True` (needed for `EDDY_CALIBRATE_PREP`)

## Important: merge templates, do not overwrite

`config/printer.cfg` and `config/Macro.cfg` in this repo are **merge templates**, not complete configs. They contain only what is specific to eddy + load cell probing. You must **merge** them into your existing files — do not replace your whole `printer.cfg` or you will lose machine-specific settings (UUIDs, PID, input shaper, display, etc.).

## 1. Install Klipper extras

```bash
git clone https://github.com/0dysseusRex/Rex-Sovol-Zero-Mainline.git
cd Rex-Sovol-Zero-Mainline
./scripts/install-probe-pressure.sh ~/klipper
```

This copies `probe_pressure.py` and `axis_twist_pressure.py` into your Klipper tree.

## 2. Deploy included config snippets

```bash
cp config/sovol_eddy.cfg config/probe_pressure.cfg ~/printer_data/config/
cp config/GP3D_Macro.cfg config/Rex_Macros.cfg config/display_macros.cfg ~/printer_data/config/
```

Add to your include list in `printer.cfg` (order matters):

```ini
[include GP3D_Macro.cfg]
[include Rex_Macros.cfg]
[include display_macros.cfg]
```

`display_macros.cfg` extends the stock UC1701 menus with load cell / eddy calibration, Z offset save, chamber preheat, and lights. It must load **after** `GP3D_Macro.cfg` and `Rex_Macros.cfg`.

## 3. Merge `printer.cfg`

Open **your** `~/printer_data/config/printer.cfg` and use `config/printer.cfg` from this repo as a checklist:

| Action | What |
|---|---|
| Add includes | `[include sovol_eddy.cfg]`, `[include probe_pressure.cfg]` |
| Update `[stepper_z]` | `endstop_pin: probe:z_virtual_endstop` |
| Add `[safe_z_home]` | If missing — see template for coordinates |
| Add `[force_move]` | `enable_force_move: True` if missing |
| Remove | `[z_offset_calibration]`, Sovol fork eddy modules |
| Keep yours | CAN UUIDs, steppers, heaters, fans, `SAVE_CONFIG` block |

## 4. Merge `Macro.cfg`

Merge from `config/Macro.cfg` into **your** macro file (or `[include Macro.cfg]` after resolving conflicts):

| Macro | Purpose |
|---|---|
| `G28` | Block Z home until eddy `calibrate` exists in SAVE_CONFIG |
| `PRINT_START` | Bed heat → load cell Z offset → eddy mesh |
| `START_PRINT` | Slicer alias for `PRINT_START` |
| `END_PRINT` | Minimal end routine — customize park/cooldown |

Remove Sovol-fork references such as `PROBE_EDDY_NG_SET_TAP_OFFSET` from your end macro if present.

Optional **line purge** and **slicer start g-code**: see README **Extras**.

## 5. Restart and calibrate

```bash
sudo systemctl restart klipper
```

Verify in Moonraker / Mainsail:

- `probe_eddy_current eddy`
- `probe_pressure`
- `gcode_macro BED_LOADCELL_Z_OFFSET`
- `gcode_macro EDDY_CALIBRATE_PREP`

Follow [docs/CALIBRATION.md](docs/CALIBRATION.md) for first-time eddy and axis twist calibration.

## What NOT to install

| Item | Reason |
|---|---|
| `[load_cell]` upstream module | Wrong API — PD10 is digital trigger, not HX711 |
| `[z_offset_calibration]` | Requires Sovol fork eddy probe methods |
| `eddyng.cfg` / `[probe_eddy_ng]` | Not used — mainline `probe_eddy_current` path |

## probe_pressure.py patch

This repo includes a fix: `RUN_PROBE_PRESSURE` stores `last_z_result` (required by `BED_LOADCELL_Z_OFFSET`). Stock Sovol v1.3.7 omitted this.
