# Rex-Sovol-Zero-Mainline

If your **Sovol Zero** is already on mainline Klipper, this repo provides the config and Python modules to use the stock probing hardware properly. The toolhead eddy probe handles Z homing and bed mesh; the bed load cell fine-tunes nozzle height with a nozzle touch; axis twist compensation calibrates both so your first layer stays consistent across the bed.

## Support

If this config helped you, consider buying me a coffee:

**[ko-fi.com/0dysseusrex](https://ko-fi.com/0dysseusrex)**

---

Working Klipper configuration and addons for the **Sovol Zero** on **mainline Klipper** (~v0.13.0), using:

- **`probe_eddy_current`** — toolhead eddy probe for Z homing, mesh, and scanning
- **`probe_pressure`** — bed load cell (PD9 tare / PD10 trigger) for nozzle-touch Z offset
- **`axis_twist_pressure`** — axis twist calibration using eddy probe + load cell (replaces paper test)

This replaces Sovol stock `[z_offset_calibration]` with mainline `probe_eddy_current` + `probe_pressure`.

## Architecture

| Role | Hardware | Klipper module |
|---|---|---|
| Coarse Z homing | LDC1612 eddy on toolhead | `[probe_eddy_current eddy]` → `stepper_z` virtual endstop |
| Fine Z offset | Bed strain gauge via external HX711 board | `[probe_pressure]` on PD10, tare on PD9 |
| Mesh / scan | Eddy probe | `BED_MESH_CALIBRATE`, `PROBE METHOD=scan` |
| Axis twist compensation | Eddy at probe offset + load cell nozzle touch | `[axis_twist_compensation]` + `[axis_twist_pressure]` |

```
G28 X Y  →  G28 Z (eddy)  →  RUN_PROBE_PRESSURE (load cell)  →  SET_GCODE_OFFSET  →  G28 Z
```

### Axis twist compensation

Axis twist corrects the Z difference between where the **eddy probe** reads the bed and where the **nozzle** actually touches, as you move in X and Y.

| Calibration step | Sensor |
|---|---|
| Probe-side height (at eddy offset) | Eddy (`probe.run_single_probe`) |
| Nozzle-side height (at bed point) | Load cell (`RUN_PROBE_PRESSURE`) |

Both **X** and **Y** axes are supported. Calibrate each axis separately; results are stored as `z_compensations` (X) and `zy_compensations` (Y) in `SAVE_CONFIG`. After calibration, compensation is applied automatically to eddy probe results and load cell touches.

```
G28
AXIS_TWIST_COMPENSATION_CALIBRATE          ; X axis — 4 points (12, ~25, ~37, 50 at Y=20)
SAVE_CONFIG

G28
AXIS_TWIST_COMPENSATION_CALIBRATE AXIS=Y   ; Y axis — 4 points (12, 24, 36, 48 at X=25)
SAVE_CONFIG
```

Default is **4 evenly-spaced points** per axis (macro wrapper). Override with `SAMPLE_COUNT=5` if needed. Points stay within the load-cell zone; extending the range to keep the old 3-point spacing would put the extra point too far from the sensor.

Cal sweep ranges are in `probe_pressure.cfg`. They are **limited to the bed load cell location (~X25 Y20)** — nozzle touches must stay near the sensor. Eddy probe steps still run at the full probe-offset positions along each sweep; twist values extrapolate outside the cal range during mesh and print.

Default sweeps: X 12–50 mm at Y=20; Y 12–48 mm at X=25.

## Repository layout

```
config/
  printer.cfg          Full printer config (includes other macro files on the live machine)
  sovol_eddy.cfg       Eddy probe, bed mesh, eddy helper macros
  probe_pressure.cfg   Load cell probe, axis twist, BED_LOADCELL_Z_OFFSET macro
  line_purge.cfg       Adaptive line purge (optional; see Extras below)
  Macro.cfg            Print lifecycle macros (PRINT_START, G28, etc.)

klipper/extras/
  probe_pressure.py         Sovol bed load cell module (required)
  axis_twist_pressure.py    Load cell nozzle touch for axis twist cal (required)

slicer/
  Sovol-OrcaSlicer-start.gcode
  Sovol-OrcaSlicer-end.gcode

docs/
  INSTALL.md
  CALIBRATION.md

scripts/
  install-probe-pressure.sh
```

## Quick install

```bash
git clone https://github.com/0dysseusRex/Rex-Sovol-Zero-Mainline.git
cd Rex-Sovol-Zero-Mainline
```

1. Install Klipper extras into your Klipper tree (copies `probe_pressure.py` and `axis_twist_pressure.py`):
   ```bash
   ./scripts/install-probe-pressure.sh ~/klipper
   ```

2. Copy config snippets into `~/printer_data/config/`:
   ```bash
   cp config/sovol_eddy.cfg config/probe_pressure.cfg ~/printer_data/config/
   ```

3. Merge into `printer.cfg`:
   ```ini
   [include sovol_eddy.cfg]
   [include probe_pressure.cfg]
   ```
   Ensure `[stepper_z]` uses `endstop_pin: probe:z_virtual_endstop`.

4. Merge relevant macros from `config/Macro.cfg` (at minimum: `G28`, `PRINT_START`, `END_PRINT`).

5. Restart Klipper and follow [docs/CALIBRATION.md](docs/CALIBRATION.md).

See also [docs/KLIPPER_UPDATES.md](docs/KLIPPER_UPDATES.md) for keeping Klipper update-safe.

<details>
<summary><strong>Extras — line purge &amp; slicer start g-code</strong></summary>

Optional quality-of-life additions included in this repo. Not required for eddy + load cell probing.

### Line purge

Adaptive first-layer purge inspired by [pellcorp/creality](https://github.com/pellcorp/creality) (SimpleAF) and KAMP. Places a purge line near the print when the slicer emits `EXCLUDE_OBJECT` bounds.

1. Add to `printer.cfg`:
   ```ini
   [include line_purge.cfg]
   ```
2. `PRINT_START` in `Macro.cfg` already calls `LINE_PURGE` after mesh + skew.
3. Enable **Exclude Objects** in Orca Slicer so Moonraker injects object bounds.

Runtime tuning:
```gcode
SETUP_LINE_PURGE PURGE_AMOUNT=40 FLOW_RATE=12 PURGE_MARGIN=25
LINE_PURGE PURGE=0    ; skip once
```

Defaults (`line_purge.cfg`): 25 mm margin from object bounds, 48 mm purge length, 12 mm³/s flow, fallback corner X15 Y15 when no object data.

### Slicer start / end g-code

Replace the long OEM Sovol block (M140/M190, double G28, manual purge lines, M104/M109) with:

**Start** — copy from `slicer/Sovol-OrcaSlicer-start.gcode`:
```gcode
M117
START_PRINT BED=[bed_temperature_initial_layer_single] HOTEND=[nozzle_temperature_initial_layer] CHAMBER=[chamber_temperature]
SET_PRINT_STATS_INFO TOTAL_LAYER=[total_layer_count]
G90
```

**End**:
```gcode
END_PRINT
```

`START_PRINT` is an alias for `PRINT_START`. The macro handles homing, bed/chamber heat, load-cell Z offset, eddy mesh, skew profile, and `LINE_PURGE`. Do not duplicate heat, home, or purge commands in the slicer.

If your slicer profile has no chamber variable, use `CHAMBER=0`.

</details>

## Klipper shows "dirty" — that's OK

After installing `probe_pressure.py` and `axis_twist_pressure.py`, Moonraker and Klipper may report the repo as **dirty** (e.g. `v0.13.0-708-g7046bd00-dirty`) because those files are **untracked** in the upstream Klipper tree.

This is **normal and expected**. It does **not** block `git pull` or cause update problems, as long as you have **no modified tracked files** (don't patch `bed_mesh.py`, `src/Makefile`, etc.).

Untracked extras = fine. Modified upstream files = update headaches.

## Machine-specific values

These **must be calibrated per printer** and live in the `SAVE_CONFIG` block of `printer.cfg`:

- `[probe_eddy_current eddy]` → `reg_drive_current`, `calibrate`
- `[axis_twist_compensation]` → `z_compensations`, `zy_compensations` (after axis twist cal)
- `[bed_mesh]` mesh points
- `[input_shaper]`, PID, skew, etc.

**Do not copy another machine's `SAVE_CONFIG` block verbatim.**

Also update CAN UUIDs in `printer.cfg` for your MCUs:

```ini
[mcu]
canbus_uuid: <your main mcu>

[mcu extruder_mcu]
canbus_uuid: <your toolhead mcu>
```

## Tested environment

- Host: BigTreeTech CB1 (aarch64)
- Klipper: `v0.13.0-708-g7046bd00`
- MCUs: CAN (`mcu` + `extruder_mcu`)
- Eddy I2C: software I2C on `extruder_mcu:PB10/PB11`

## Credits

- `probe_pressure.py` — derived from Sovol OEM Klipper (GPLv3), based on upstream Klipper probe code
- `axis_twist_pressure.py` — GPLv3; patches mainline axis twist cal to use load cell nozzle touch
- `line_purge.cfg` — adapted from [pellcorp/creality](https://github.com/pellcorp/creality) (SimpleAF) `_LINE_PURGE` and KAMP

## License

Klipper-derived Python files are GPLv3. Config files are provided as-is for community use.
