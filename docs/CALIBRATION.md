# Calibration guide

## First-time eddy calibration (bootstrap)

Mainline Klipper has a chicken-and-egg problem: `G28 Z` needs eddy calibration, but `PROBE_EDDY_CURRENT_CALIBRATE` needs Z moves, and Z moves need homing.

### Step 1 — Bootstrap Z with load cell

```
EDDY_CALIBRATE_PREP
```

This macro:
1. Homes XY
2. Uses `SET_KINEMATIC_POSITION` + `RUN_PROBE_PRESSURE` to sync Z to bed contact
3. Lifts to Z=5 for manual calibration

### Step 2 — LDC drive current (once)

```
G0 X76.2 Y76.2 Z20
LDC_CALIBRATE_DRIVE_CURRENT CHIP=eddy
SAVE_CONFIG
```

**Important:** Do not set `reg_drive_current` in `sovol_eddy.cfg`. If `SAVE_CONFIG` reports a conflict, comment out the hardcoded value and retry.

### Step 3 — Eddy height calibration

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

### Step 4 — Verify homing

```
G28
```

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
