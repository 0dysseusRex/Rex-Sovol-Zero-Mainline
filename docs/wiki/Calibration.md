# Calibration

> **Path A (this page):** printers **with** a bed load cell — fine Z offset via nozzle touch.  
> **Path B (no load cell):** → **[Eddy-Only Configuration](Eddy-Only-Configuration)** — eddy tap cal and mesh only.

Mainline eddy probing has a **bootstrap problem**: `G28 Z` needs calibration data, but calibration needs Z moves. The Rex **load cell path** uses the bed sensor for one-time bootstrap and per-print fine Z; eddy handles everyday homing and mesh.

Full reference: [Rex CALIBRATION.md](https://github.com/0dysseusRex/Rex-Sovol-Zero-Mainline/blob/master/docs/CALIBRATION.md)

Official eddy docs: [klipper3d.org — Eddy Probe](https://www.klipper3d.org/Eddy_Probe.html)

---

## Calibration order — Path A with load cell (do not skip steps)

```
1. EDDY_CALIBRATE_PREP        (load cell bootstrap — once)
2. LDC_CALIBRATE_DRIVE_CURRENT (once per machine)
3. PROBE_EDDY_CURRENT_CALIBRATE (height map — per temp)
4. G28 verify                 (eddy homing works)
5. AXIS_TWIST_COMPENSATION_CALIBRATE  (X then Y)
6. Load cell z_offset tune    (first print baby-step)
7. PID / input shaper         (normal Klipper tuning)
```

Run from **Mainsail console** unless using display menus (Prepare → Calibration).

---

## Step 1 — Bootstrap Z with load cell

Requires bed load cell hardware (PD9/PD10). **No load cell?** Use `SET_KINEMATIC_POSITION` bootstrap on the [Eddy-Only](Eddy-Only-Configuration#step-1--bootstrap-z-no-load-cell) page instead of this step.

```
EDDY_CALIBRATE_PREP
```

**What it does:**
1. Homes XY  
2. Positions over bed load cell area  
3. `RUN_PROBE_PRESSURE` — nozzle touches bed gently  
4. Sets kinematic Z from touch result  
5. Lifts to safe height for eddy calibration  

**Why:** Mainline Klipper won't Z-move until it believes Z is valid — load cell touch establishes that without eddy cal data.

**Display menu:** Prepare → Calibration → **Eddy Cal Prep**

---

## Step 2 — LDC drive current (once)

Heat bed to your typical print temperature first (eddy readings drift with temperature).

```
G0 X76.2 Y76.2 Z20
LDC_CALIBRATE_DRIVE_CURRENT CHIP=eddy
SAVE_CONFIG
```

**Why:** The LDC1612 eddy chip needs correct drive current for reliable triggering.

**Important:** Do **not** hardcode `reg_drive_current` in `sovol_eddy.cfg` — let `SAVE_CONFIG` own it.

If `reg_drive_current: 15` causes `RAW_RANGE` errors during homing, recalibrate at **16** ([zero-config note](https://github.com/asnajder/zero-config#finishing-up)):

```
SET_KINEMATIC_POSITION X=96 Y=76.2 Z=2
PROBE_EDDY_CURRENT_CALIBRATE CHIP=eddy
```

Do **not** home between changing drive current and recalibrating — crash risk.

---

## Step 3 — Eddy height calibration

```
PROBE_EDDY_CURRENT_CALIBRATE CHIP=eddy
```

Follow prompts — use **small** steps:

```
TESTZ Z=-0.1
TESTZ Z=-0.1
...
ACCEPT
SAVE_CONFIG
```

**Why small steps?** `-1` mm jumps can drive nozzle into bed.

Calibrate at the **bed temperature you print at** (e.g. 90°C for ASA).

---

## Step 4 — Verify homing

```
G28
```

Expected:
- XY home to endstops  
- Z homes **without nozzle touching bed** (eddy senses bed inductively)  

If Z only homes XY:
- Eddy not calibrated — repeat Step 3 + `SAVE_CONFIG`  
- Check `G28` macro blocks Z until `calibrate` exists in SAVE_CONFIG  

```
G28 X Y
G28 Z
```

---

## Step 5 — Axis twist compensation

Corrects height difference between **eddy probe position** and **nozzle position** as head moves in X/Y.

**Constraint:** Load cell is under **~X25 Y20** — nozzle touches during cal must stay near that point.

```
G28
AXIS_TWIST_COMPENSATION_CALIBRATE
SAVE_CONFIG

G28
AXIS_TWIST_COMPENSATION_CALIBRATE AXIS=Y
SAVE_CONFIG
```

**Display menu:** Prepare → Calibration → **Axis Twist Cal**

Default: **4 points** per axis (Rex wrapper). Override: `SAMPLE_COUNT=5`

---

## Step 6 — Load cell Z offset (first layer)

Every print, `PRINT_START` runs:

```
SET_GCODE_OFFSET Z=0
BED_LOADCELL_Z_OFFSET
G28 Z
```

Manual test:
```
G28 X Y
BED_LOADCELL_Z_OFFSET
G28 Z
```

**Tuning squish:** After test print, if first layer too close, note baby-step correction (e.g. +0.240 mm). Set in `probe_pressure.cfg`:

```ini
[probe_pressure]
z_offset: 0.240
```

Or save via display: **Tune → Save Z Offset Now** (`Z_OFFSET_APPLY_PROBE1` + `SAVE_CONFIG`).

**Display menu:** Prepare → Calibration → **Load Cell Z Touch**

---

## Step 7 — Load cell sanity check

```
GET_PRESSURE_TARE
QUERY_PROBE1
```

At rest, empty bed: should show **`open`**

If **`TRIGGERED`** at rest: wiring issue, bed loaded, or bad tare — fix before printing.

**Display menu:** Prepare → Calibration → **Test Load Cell**

---

## Step 8 — Standard Klipper tuning

After probing works:

```
PID_CALIBRATE HEATER=extruder TARGET=240
PID_CALIBRATE HEATER=heater_bed TARGET=60
SAVE_CONFIG

SHAPER_CALIBRATE
SAVE_CONFIG
```

Optional: skew correction, chamber PID (if using Rex chamber macros).

---

## Nozzle clean before probing

`PRINT_START` calls `CLEAN_NOZZLE` — the **stock Sovol silicone wiper** macro (heat to 200°C, wipe, cool to 130°C). Reduces false load cell triggers from plastic blobs.

**Optional brass wire brush mod:** If you install the [Sovol Zero brass brush](https://makerworld.com/en/models/2225406-sovol-zero-brass-brush) on the left side of the bed, uncomment `CLEAN_NOZZLE_BRASS` in `Macro.cfg` and swap it in place of `CLEAN_NOZZLE` (see repo README).

**Display menu:** Prepare → Calibration → **Clean Nozzle**

---

## First print checklist

- [ ] `G28` works (eddy Z, no crash)  
- [ ] `BED_MESH_CALIBRATE` completes in `PRINT_START`  
- [ ] Load cell touch repeatability ±0.02–0.05 mm at X25 Y20  
- [ ] Slicer uses short `START_PRINT` g-code only  
- [ ] `z_offset` tuned from first print baby-steps  

---

## Next step

Use the knob screen for day-to-day tasks → **[UC1701 Display and Menus](UC1701-Display-and-Menus)**

Problems? → **[Troubleshooting](Troubleshooting)**

Happy printing? Star [Rex-Sovol-Zero-Mainline](https://github.com/0dysseusRex/Rex-Sovol-Zero-Mainline) and consider [ko-fi.com/0dysseusrex](https://ko-fi.com/0dysseusrex)
