# Rex-Sovol-Zero-Mainline

Sovol Zero on **mainline Klipper** — eddy probe Z homing + bed load cell Z offset.

Working Klipper configuration and addons for the **Sovol Zero** on **mainline Klipper** (~v0.13.0), using:

- **`probe_eddy_current`** — toolhead eddy probe for Z homing, mesh, and scanning
- **`probe_pressure`** — bed load cell (PD9 tare / PD10 trigger) for nozzle-touch Z offset

This replaces Sovol stock `[z_offset_calibration]` and the broken eddy-ng hybrid that was partially configured but not active.

## Architecture

| Role | Hardware | Klipper module |
|---|---|---|
| Coarse Z homing | LDC1612 eddy on toolhead | `[probe_eddy_current eddy]` → `stepper_z` virtual endstop |
| Fine Z offset | Bed strain gauge via external HX711 board | `[probe_pressure]` on PD10, tare on PD9 |
| Mesh / scan | Eddy probe | `BED_MESH_CALIBRATE`, `PROBE METHOD=scan` |

```
G28 X Y  →  G28 Z (eddy)  →  RUN_PROBE_PRESSURE (load cell)  →  SET_GCODE_OFFSET  →  G28 Z
```

## Repository layout

```
config/
  printer.cfg          Full printer config (includes other macro files on the live machine)
  sovol_eddy.cfg       Eddy probe, bed mesh, eddy helper macros
  probe_pressure.cfg   Load cell probe + BED_LOADCELL_Z_OFFSET macro
  Macro.cfg            Print lifecycle macros (PRINT_START, G28, etc.)

klipper/extras/
  probe_pressure.py    Sovol bed load cell module (required)
  probe_eddy_ng.py     Optional reference — NOT used by this config (mainline eddy path)

docs/
  INSTALL.md
  CALIBRATION.md

scripts/
  install-probe-pressure.sh
```

## Quick install

1. Copy `klipper/extras/probe_pressure.py` into your Klipper tree:
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

## Machine-specific values

These **must be calibrated per printer** and live in the `SAVE_CONFIG` block of `printer.cfg`:

- `[probe_eddy_current eddy]` → `reg_drive_current`, `calibrate`
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
- Klipper: `v0.13.0-707-gf604aeee`
- MCUs: CAN (`mcu` + `extruder_mcu`)
- Eddy I2C: software I2C on `extruder_mcu:PB10/PB11`

## Credits

- `probe_pressure.py` — derived from Sovol OEM Klipper (GPLv3), based on upstream Klipper probe code
- `probe_eddy_ng.py` — included for reference only ([vvuk/eddy-ng](https://github.com/vvuk/eddy-ng)); active config uses mainline `probe_eddy_current`

## License

Klipper-derived Python files are GPLv3. Config files are provided as-is for community use.
