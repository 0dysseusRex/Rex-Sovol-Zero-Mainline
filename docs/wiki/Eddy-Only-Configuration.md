# Eddy-Only Configuration (No Bed Load Cell)

**Use this branch if your Sovol Zero did not ship with a bed load cell** (no strain-gauge board under the bed, no HX711 / PD9–PD10 wiring to the main MCU).

The default **[Rex-Sovol-Zero-Mainline](https://github.com/0dysseusRex/Rex-Sovol-Zero-Mainline)** path and most of this wiki’s Phase 6–7 steps assume a **load cell for fine Z offset**. If you don’t have one, follow this page instead for probing and print start.

> **Have a load cell?** → [Configuration and Rex Repo](Configuration-and-Rex-Repo) + [Calibration](Calibration)

---

## How to tell which printer you have

| Load cell present | Eddy-only (this page) |
|---|---|
| Strain-gauge PCB under bed (~X25 Y20 area) | No board, or empty pad / no HX711 module |
| Wires to mainboard **PD9** (tare) and **PD10** (trigger) | Those pins unused or not connected |
| `QUERY_PROBE1` responds after `GET_PRESSURE_TARE` | Load cell commands fail or probe always `open` |
| Sovol marketing / later production units with “bed probe” | Some early or regional units shipped **eddy only** |

When in doubt, open the base and look under the bed heater assembly near the front-left zone. No load cell hardware → use this guide.

---

## Architecture comparison

### With load cell (default Rex config)

```
G28 X Y → G28 Z (eddy) → PRINT_START → load cell nozzle touch → G28 Z → eddy mesh
         ↑ homing                          ↑ fine Z0 each print
```

### Eddy-only (this branch)

```
G28 X Y → G28 Z (eddy) → PRINT_START → eddy mesh (+ tap-cal Z offset in SAVE_CONFIG)
         ↑ homing + Z0 reference from eddy calibration only
```

| Task | Load cell path | Eddy-only path |
|---|---|---|
| Z homing | Eddy (`probe:z_virtual_endstop`) | Same — eddy |
| Bed mesh | Eddy scan | Same — eddy |
| Fine first-layer Z | `[probe_pressure]` nozzle touch | Eddy **tap calibration** + `z_offset` / baby-step |
| First-time eddy bootstrap | `EDDY_CALIBRATE_PREP` (load cell touch) | `SET_KINEMATIC_POSITION` (zero-config method) |
| Axis twist | `axis_twist_pressure` (eddy + load cell) | Standard `[axis_twist_compensation]` with eddy probe, or skip initially |

**Why eddy-only still works:** Mainline `probe_eddy_current` handles homing, mesh, and tap-based height map. You lose the repeatable nozzle-touch fine Z at the bed sensor — tuning relies on eddy tap cal and baby-stepping instead.

---

## What to skip from the default Rex install

Do **not** install or include load-cell pieces:

| Skip | Why |
|---|---|
| `./scripts/install-probe-pressure.sh` | Adds `probe_pressure.py` — not needed |
| `[include probe_pressure.cfg]` | Defines `[probe_pressure]`, PD9/PD10, load cell macros |
| `BED_LOADCELL_Z_OFFSET` in `PRINT_START` | Requires load cell |
| `EDDY_CALIBRATE_PREP` | Uses `RUN_PROBE_PRESSURE` — use bootstrap below |
| Display menus: Load Cell Z Touch, Test Load Cell | No hardware |
| `Z_OFFSET_APPLY_PROBE1` | Load cell command — use `SET_GCODE_OFFSET` / eddy cal instead |
| `[axis_twist_pressure]` / custom axis twist macro | Needs load cell nozzle touch — use stock axis twist or omit |

Phases **1–5** of the wiki (backup, Armbian, KIAUH, CAN, MCU flash) are **identical** for both branches.

---

## Eddy-only install steps

### 1. Install configs (eddy only)

```bash
cd ~
git clone https://github.com/0dysseusRex/Rex-Sovol-Zero-Mainline.git
cp ~/Rex-Sovol-Zero-Mainline/config/sovol_eddy.cfg ~/printer_data/config/
# Optional UI macros — omit load-cell-specific display items later
cp ~/Rex-Sovol-Zero-Mainline/config/GP3D_Macro.cfg ~/printer_data/config/ 2>/dev/null || true
cp ~/Rex-Sovol-Zero-Mainline/config/Rex_Macros.cfg ~/printer_data/config/ 2>/dev/null || true
```

**Do not copy** `probe_pressure.cfg`.

### 2. Includes in `printer.cfg`

```ini
[include mainsail.cfg]
[include Macro.cfg]
[include sovol_eddy.cfg]
# NO [include probe_pressure.cfg]
```

You can still use [asnajder/zero-config](https://github.com/asnajder/zero-config) as your base `printer.cfg` — it is already eddy-centric. Add Rex `sovol_eddy.cfg` if you want Rex mesh macros and helpers.

### 3. Critical `[stepper_z]` setting (same as load cell path)

```ini
[stepper_z]
endstop_pin: probe:z_virtual_endstop
```

Z homing always uses the **toolhead eddy probe**, never a bed sensor.

### 4. `[force_move]` — still recommended

```ini
[force_move]
enable_force_move: True
```

Needed for `SET_KINEMATIC_POSITION` bootstrap during first eddy calibration.

---

## Eddy-only `PRINT_START` macro

Replace the load cell block in your `PRINT_START` with an eddy-only sequence. Merge into your `Macro.cfg`:

```ini
[gcode_macro PRINT_START]
description: Start print — eddy homing + mesh (no load cell)
gcode:
    {% set bed = params.BED|default(0)|float %}
    {% set hotend = params.HOTEND|default(0)|float %}

    G28 X Y
    G28 Z

    {% if bed > 0 %}
        M140 S{bed}
        M190 S{bed}
    {% endif %}

    # Optional — OEM silicone wipe; brass brush mod: use CLEAN_NOZZLE_BRASS instead
    CLEAN_NOZZLE

    {% if hotend > 0 %}
        M104 S{hotend}
        M109 S{hotend}
    {% endif %}

    SET_GCODE_OFFSET Z=0
    BED_MESH_CLEAR
    BED_MESH_CALIBRATE
```

**Why no load cell block?** Fine Z is already encoded in eddy `calibrate` / tap data from `PROBE_EDDY_CURRENT_CALIBRATE`. Mesh runs at print temperature after homing.

Slicer start g-code stays the same:

```gcode
START_PRINT BED=[bed_temperature_initial_layer_single] HOTEND=[nozzle_temperature_initial_layer]
```

---

## Eddy-only calibration

Reference: [zero-config — Finishing Up (Eddy cal)](https://github.com/asnajder/zero-config#finishing-up) and [Klipper Eddy Probe](https://www.klipper3d.org/Eddy_Probe.html).

### Step 1 — Bootstrap Z (no load cell)

Instead of `EDDY_CALIBRATE_PREP`, manually set a safe Z so Klipper allows moves before eddy cal exists:

```gcode
G28 X Y
SET_KINEMATIC_POSITION X=96 Y=76.2 Z=20
```

Adjust X/Y/Z if needed so the nozzle is **well above the bed** but the toolhead position is plausible. This is the same workaround [asnajder/zero-config](https://github.com/asnajder/zero-config) uses before first eddy cal.

### Step 2 — LDC drive current

Heat bed to your normal print temperature first.

```gcode
G0 X76.2 Y76.2 Z20
LDC_CALIBRATE_DRIVE_CURRENT CHIP=eddy
SAVE_CONFIG
```

If homing later shows `RAW_RANGE` at drive current 15, recalibrate at 16 and redo eddy cal ([zero-config note](https://github.com/asnajder/zero-config#finishing-up)).

### Step 3 — Eddy height + tap calibration

```gcode
PROBE_EDDY_CURRENT_CALIBRATE CHIP=eddy
```

Use small `TESTZ` steps (`-0.1` mm), then `ACCEPT`, then `SAVE_CONFIG`.

This step includes the **paper-test / tap** portion that sets your effective Z offset for the eddy probe. Calibrate at the **bed temperature you print at**.

Official tap details: [Eddy Probe — tap calibration](https://www.klipper3d.org/Eddy_Probe.html#calibration)

### Step 4 — Verify homing

```gcode
G28
```

Z must home **without** the nozzle touching the bed.

### Step 5 — First-layer tuning (eddy-only)

There is no `probe_pressure z_offset`. After a test print:

1. Note baby-step correction (e.g. +0.10 mm if too close).
2. Apply persistently via one of:
   - Re-run / adjust eddy tap cal at print temp  
   - `SET_GCODE_OFFSET Z=…` in `PRINT_START` after homing  
   - `[probe_eddy_current eddy]` `z_offset` in config + `SAVE_CONFIG` if you use probe offset commands for the eddy chip  

Most users tune tap cal once per filament/temp, then minor baby-steps only.

### Step 6 — Axis twist (optional)

Without a load cell you **cannot** use Rex `axis_twist_pressure` (nozzle touch at bed sensor).

Options:

| Option | Notes |
|---|---|
| **Skip for now** | Many users run eddy-only without axis twist initially |
| **Stock Klipper `[axis_twist_compensation]`** | Uses configured probe (eddy) — see [Klipper axis twist docs](https://www.klipper3d.org/Axis_Twist_Compensation.html) |
| **Manual mesh / slicer compensation** | Fallback if twist cal is frustrating without nozzle touch |

Do **not** include Rex `probe_pressure.cfg` axis twist overrides — they assume load cell touches at ~X25 Y20.

### Step 7 — PID / input shaper

Same as main guide — `PID_CALIBRATE`, `SHAPER_CALIBRATE`, `SAVE_CONFIG`.

---

## Display menus (eddy-only)

If you use `display_macros.cfg`, ignore or remove:

- Load Cell Z Touch  
- Test Load Cell  
- Save Z Offset Now (`Z_OFFSET_APPLY_PROBE1`)  

Keep:

- Clean Nozzle  
- Eddy Cal Prep → **replace** with manual `SET_KINEMATIC_POSITION` workflow above, or define a small macro without `RUN_PROBE_PRESSURE`  

Example eddy-only prep macro (add to your macros file):

```ini
[gcode_macro EDDY_CALIBRATE_PREP]
description: Bootstrap Z for first eddy cal (no load cell)
gcode:
    G28 X Y
    SET_KINEMATIC_POSITION X=96 Y=76.2 Z=20
    RESPOND PREFIX="eddy" MSG="Z synced manually. Run PROBE_EDDY_CURRENT_CALIBRATE CHIP=eddy"
```

---

## Troubleshooting (eddy-only)

| Symptom | Fix |
|---|---|
| `Unknown command: RUN_PROBE_PRESSURE` | You still have load cell macros — remove `probe_pressure.cfg` |
| `Unknown command: GET_PRESSURE_TARE` | Same — drop load cell includes |
| First layer consistently off | Re-run eddy tap cal at print bed temp; adjust `SET_GCODE_OFFSET` |
| `EDDY_CALIBRATE_PREP` crashes | Macro still uses load cell — use eddy-only `EDDY_CALIBRATE_PREP` above |
| Axis twist cal crashes at nozzle points | Using Rex load-cell twist config — switch to stock axis twist or skip |

More: [Troubleshooting](Troubleshooting)

---

## When to add a load cell later

If you install Sovol’s bed load cell kit (or retrofit HX711 + sensor):

1. Wire **PD9** / **PD10** per Sovol schematic  
2. Run `./scripts/install-probe-pressure.sh ~/klipper`  
3. Add `[include probe_pressure.cfg]`  
4. Switch `PRINT_START` to the [load cell version](Configuration-and-Rex-Repo)  
5. Follow full [Calibration](Calibration) (load cell path)  

---

[← Configuration and Rex Repo](Configuration-and-Rex-Repo) · [Home](Home)
