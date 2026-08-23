# Calibration guide

## First-time eddy calibration (bootstrap)

Mainline Klipper has a chicken-and-egg problem: `G28 Z` needs eddy calibration, but `PROBE_EDDY_CURRENT_CALIBRATE` needs Z moves, and Z moves need homing.

### Step 1 — Bootstrap Z with load cell

```
EDDY_CALIBRATE_PREP
```

This macro:
1. Homes XY
2. Moves to the **load cell location (X25 Y20)** — not bed center
3. Sets virtual Z with `SET_KINEMATIC_POSITION Z=25` so the load cell probe has enough downward travel even if the nozzle starts ~10–30 mm above the bed (override with `SYNC_Z=30` if needed)
4. Uses `RUN_PROBE_PRESSURE` to sync Z to bed contact
5. Lifts to Z=5 for calibration

**Do not** use bed center (76.2, 76.2) — the load cell only triggers near X25 Y20.

### Step 2 — LDC drive current (once)

```
G0 X76.2 Y76.2 Z20
LDC_CALIBRATE_DRIVE_CURRENT CHIP=eddy
SAVE_CONFIG
```

**Important:** Do not set `reg_drive_current` in `sovol_eddy.cfg`. If `SAVE_CONFIG` reports a conflict, comment out the hardcoded value and retry.

### Step 3 — Eddy height calibration

**Option A — Paper test (stock mainline):**

```
PROBE_EDDY_CURRENT_CALIBRATE CHIP=eddy
```

Use small `TESTZ` steps (0.05–0.1 mm), not `-1`:

```
TESTZ Z=-0.1
TESTZ Z=-0.1
...
ACCEPT
SAVE_CONFIG
```

**Option B — Experimental load cell reference (no paper):**

Requires `eddy_loadcell_calibrate.py` from `install-probe-pressure.sh`.

```
EDDY_CALIBRATE_LOADCELL
SAVE_CONFIG
```

Or with explicit temperatures and sample count:

```
PROBE_EDDY_CURRENT_CALIBRATE_LOADCELL BED_TEMP=80 NOZZLE_TEMP=150 LC_SAMPLES=7
SAVE_CONFIG
```

This heats the bed to 80°C and nozzle to **150°C** (same as print-start load cell touch), takes multiple load cell touches at **X25 Y20**, then builds the same `[probe_eddy_current eddy]` `calibrate` table as the paper method (~100 eddy frequency samples across 40 µm Z steps). Use **5–9** load cell touches (`LC_SAMPLES`); tighten `LC_TOLERANCE=0.03` if spread is high.

Clean the nozzle before running — filament residue affects load cell contact height.

### Step 4 — Verify homing

```
G28
```

```
G28 X Y  →  G28 Z (eddy)  →  RUN_PROBE_PRESSURE (load cell, PRINT_START only)  →  SET_GCODE_OFFSET  →  G28 Z
```

## Homing vs load cell touch

Your printer should already match the Cartographer / SimpleAF split:

| Action | Sensor | When |
|---|---|---|
| `G28` / `G28 Z` | Eddy (`probe:z_virtual_endstop`) | Anytime — **no nozzle touch** |
| `BED_LOADCELL_Z_OFFSET` | Load cell nozzle touch | `PRINT_START` only (after wipe + 150°C) |
| `EDDY_CALIBRATE_PREP` | Load cell | First-time eddy calibration bootstrap |
| Axis twist cal | Eddy + load cell | Calibration |

Verify in **your** `printer.cfg`:

```ini
[stepper_z]
endstop_pin: probe:z_virtual_endstop
```

Do **not** set `endstop_pin` to `probe_pressure:z_virtual_endstop`. The load cell is a fine Z0 reference, not a homing endstop.

If the nozzle still hits the bed during `G28 Z`, the eddy is triggering too late (recalibrate eddy) or there is a large filament blob — `CLEAN_NOZZLE` + 150°C before load cell touch addresses the latter.

## Load cell Z offset (every print / as needed)

```
G28 X Y
BED_LOADCELL_Z_OFFSET
G28 Z
```

Or rely on `PRINT_START`, which runs this automatically:

```
SET_GCODE_OFFSET Z=0
BED_LOADCELL_Z_OFFSET
G28 Z
```

`BED_LOADCELL_Z_OFFSET` defaults to **X25 Y20** (bed load cell location). Override with `X=` / `Y=` if needed.

## Load cell Z offset tuning

The load cell finds **contact**; your preferred **first-layer squish** is set separately via `[probe_pressure] z_offset` in `probe_pressure.cfg`. That value is added in `BED_LOADCELL_Z_OFFSET` when applying `SET_GCODE_OFFSET`.

1. Run a test print.
2. If the first layer is too close or too far, note the baby-step correction (e.g. **+0.240** mm = nozzle too close, raise offset).
3. Set `z_offset` to that value and restart Klipper (or `FIRMWARE_RESTART`).

Check repeatability before chasing larger code changes:

```
G28 X Y
G0 X25 Y20 F6000
G28 Z
RUN_PROBE_PRESSURE
```

Run several times — spread should stay within ~0.02–0.05 mm. If not, check tare (`GET_PRESSURE_TARE`), probe speed, and bed isolation. With stable repeats, `z_offset` is the right knob; `PROBE_CALIBRATE1` is optional for fine-tuning the same value into `SAVE_CONFIG`.

## Axis twist compensation

The load cell is under **~X25 Y20**. Nozzle touches during calibration must stay near that point — points at bed center or far edges will not trigger reliably and can crash into the bed.

```
G28
AXIS_TWIST_COMPENSATION_CALIBRATE          ; X sweep — 4 points at Y=20
SAVE_CONFIG

G28
AXIS_TWIST_COMPENSATION_CALIBRATE AXIS=Y   ; Y sweep — 4 points at X=25
SAVE_CONFIG
```

Default **4 evenly-spaced points** per axis (was 3). Override with `SAMPLE_COUNT=5` etc. if needed.

Eddy probe steps still run at probe offsets along each sweep. Twist compensation extrapolates outside the calibrated range for mesh and print moves.

If a touch point still pushes too hard, shrink `calibrate_end_x` / `calibrate_end_y` in `probe_pressure.cfg` further toward the sensor.

## Load cell sanity check

```
GET_PRESSURE_TARE
QUERY_PROBE1
```

At rest with nothing on the bed: **`open`**

If **`TRIGGERED`** at rest: check wiring, re-tare, ensure bed is unloaded.

## Troubleshooting

| Symptom | Cause | Fix |
|---|---|---|
| `Must home axis first` during TESTZ | Z not marked homed | Run `EDDY_CALIBRATE_PREP` or `SET_KINEMATIC_POSITION Z=<current>` |
| G28 only homes XY | Old G28 macro or missing calibrate data | Fix G28 macro; run eddy cal + SAVE_CONFIG |
| SAVE_CONFIG reg_drive_current conflict | Hardcoded in included cfg | Comment out in `sovol_eddy.cfg` |
| G28 Z reboots | Uncalibrated eddy or bad cal data | Re-run PROBE_EDDY_CURRENT_CALIBRATE |
| QUERY_PROBE1 always TRIGGERED | Load cell stuck / bed loaded | Re-tare, check PD10 wiring |
| Axis twist cal crashes at last point | Nozzle too far from load cell (~X25 Y20) | Shrink cal range in `probe_pressure.cfg`; keep cross-axis at Y=20 or X=25 |

## G28 macro (mainline-safe)

```jinja
{% set eddy = printer.configfile.settings['probe_eddy_current eddy'] %}
{% set want_z = params.Z is defined or (params.X is not defined and params.Y is not defined) %}
{% if want_z and 'calibrate' not in eddy %}
    ... XY-only fallback with message ...
{% else %}
    M9928 {rawparams}
{% endif %}
```

Do **not** use `printer.probe.is_calibrated` — that property exists on Sovol's fork only.
