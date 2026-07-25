# Troubleshooting

Symptoms → causes → fixes. Cross-references to community sources included.

---

## CAN / MCU

### `flashtool.py -q` shows no devices

| Check | Action |
|---|---|
| CAN interface down | `ip link show can0` — should be UP |
| Wrong bitrate | Verify `25-can.network` has `BitRate=1M`, reboot |
| Wiring | CANH/CANL to toolhead — seated connectors |
| Power | Mainboard must power toolhead CAN transceiver |
| Klipper holding bus | `sudo service klipper stop` before query |

### Wrong UUID after flash

**Expected** — UUID changes when Katapult/Klipper reflashed. Run `-q` again, update `printer.cfg`, restart Klipper.

### Toolhead UUID missing after Klipper update

Common when Katapult corrupt ([Klipper Discourse](https://klipper.discourse.group/t/unable-to-update-klipper-on-sovol-zero-toolhead-mcu/24864)).

**Fix:**
1. ST-LINK flash toolhead Katapult ([ST-LINK Step by Step](ST-LINK-Step-by-Step))  
2. Or flash stock [`zero_extuder_1.3.7.hex`](https://github.com/asnajder/zero-config/blob/main/recovery/zero_extuder_1.3.7.hex) then re-migrate  
3. Re-flash Klipper over CAN  

**Boot vs runtime UUID:** Toolhead may show `61755fe321ac` in Katapult boot mode — different from running Klipper UUID ([Blenky56 guide](https://github.com/Blenky56/Flashing-Klipper-to-Sovol-ZERO-Toolhead-on-the-SV08)).

### Fans at 100% after MCU flash

Missing GPIO startup in menuconfig. Must include:
```
GPIO pins at startup: !PE11,!PB0
```
Rebuild and reflash. Credit: [vvuk wiki](https://github.com/vvuk/printer-configs/wiki/Kalico-on-the-Sovol-Zero)

---

## Klipper config errors

### `Include file 'X.cfg' does not exist`

File not copied to `~/printer_data/config/`. Copy from Rex repo or zero-config.

### `gcode command SET_DISPLAY_TEXT already registered`

Do **not** define `[gcode_macro SET_DISPLAY_TEXT]` — Klipper's `[display]` provides it via `display_status`. Remove duplicate from custom configs.

### `gcode_macro CANCEL_PRINT already exists`

Both `mainsail.cfg` and your `Macro.cfg` define it. Include order matters — later file wins. Remove duplicate or use only one.

### `Option 'X' is not valid in section 'Y'`

Usually Sovol fork config on mainline Klipper. Remove:
- `[z_offset_calibration]`
- `[probe_eddy_ng]`
- Custom Sovol `klippy/extras` references

Research reference: [Gekkio/sovol-zero-klipper](https://github.com/Gekkio/sovol-zero-klipper)

---

## Eddy probe

### `I2C request to addr 42 reports error START_NACK`

Hardware I2C unreliable on Zero toolhead — use **software I2C** in eddy config (PB10/PB11 on extruder MCU). Rex `sovol_eddy.cfg` enables this.

Also try Klipper service nice level ([zero-config](https://github.com/asnajder/zero-config#finishing-up)):
```bash
sudo nano /etc/systemd/system/klipper.service
# Under [Service], add: Nice=-10
sudo systemctl daemon-reload
sudo systemctl restart klipper
```

### `Error during homing probe: Trigger analog error: RAW_RANGE`

`reg_drive_current` too low (often 15). Recalibrate at 16:
```
SET_KINEMATIC_POSITION X=96 Y=76.2 Z=2
PROBE_EDDY_CURRENT_CALIBRATE CHIP=eddy
SAVE_CONFIG
```
**Do not G28** between changing current and recalibrating.

### G28 only homes XY / Z crashes

| Cause | Fix |
|---|---|
| No eddy calibrate data | Run [Calibration](Calibration) Steps 1–3 |
| Bad G28 macro | Use Rex `G28` — blocks Z until calibrated |
| Filament blob on nozzle | Run `CLEAN_NOZZLE` before load cell touch |

### `Must home axis first` during TESTZ

Run `EDDY_CALIBRATE_PREP` or `SET_KINEMATIC_POSITION Z=<known>`

---

## Load cell / probe_pressure (Path A only)

Skip this section if you have **no bed load cell** — see [Eddy-Only Configuration](Eddy-Only-Configuration).

### `Unknown command: RUN_PROBE_PRESSURE` / `GET_PRESSURE_TARE`

You are on the **eddy-only** path but still have load cell configs or macros. Remove `[include probe_pressure.cfg]`, load cell blocks from `PRINT_START`, and reinstall Klipper extras only if needed.

### `QUERY_PROBE1` always TRIGGERED

- Run `GET_PRESSURE_TARE`  
- Ensure nothing on bed  
- Check PD10 wiring to bed load cell board  
- Verify `[probe_pressure]` pin config matches hardware  

### First layer too close / too far

Tune `[probe_pressure] z_offset` — not eddy cal. See [Calibration Step 6](Calibration#step-6--load-cell-z-offset-first-layer).

Use `Z_OFFSET_APPLY_PROBE1` + `SAVE_CONFIG` (not `Z_OFFSET_APPLY_PROBE` — wrong module).

### Axis twist cal crashes at last point

Nozzle too far from load cell (~X25 Y20). Shrink cal range in `probe_pressure.cfg`; keep cross-axis coordinate at Y=20 (X cal) or X=25 (Y cal).

---

## Host / network

### Armbian boot hangs minutes

```bash
sudo systemctl mask systemd-networkd-wait-online.service
```

### Mainsail loads but Klipper disconnected

```bash
tail -n 50 ~/printer_data/logs/klippy.log
```
Fix config error, `sudo systemctl restart klipper`.

### Webcam choppy / disconnects

CB1 on 2.4 GHz Wi-Fi + USB Wi-Fi dongle interference. Use Ethernet or 5 GHz AP near printer. Crowsnest may bind localhost only — use Mainsail proxy URL.

---

## Display

### Knob rotates wrong direction

Swap encoder pins in `[display]`:
```ini
encoder_pins: ^EXP2_3, ^EXP2_5
```

### Stock display shows garbage during PRINT_START

Remove undefined macros (`save_last_file`, undefined `PRINT_END`). Use Rex `display_macros.cfg` + fixed `GP3D_Macro.cfg`.

---

## Klipper updates

### Klipper shows "dirty"

Normal with untracked `probe_pressure.py`. Avoid modifying **tracked** Klipper files.

Details: [KLIPPER_UPDATES.md](https://github.com/0dysseusRex/Rex-Sovol-Zero-Mainline/blob/master/docs/KLIPPER_UPDATES.md)

### MCU version mismatch after `git pull`

Reflash MCUs with same Klipper version:
```bash
~/update_klipper_mcus_svzero.sh   # from zero-config, UUIDs configured
```
Or manual `make` + `flashtool.py` per [CAN Bus and MCU Flashing](CAN-Bus-and-MCU-Flashing).

---

## Emergency recovery

| Situation | Action |
|---|---|
| MCU bricked / no CAN | ST-LINK + [zero-config/recovery](https://github.com/asnajder/zero-config/tree/main/recovery) `.hex` |
| Want full OEM back | Restore all three `.hex` files + stock eMMC if saved |
| Armbian broken | Re-flash eMMC with Armbian Imager |

→ **[Backup and Recovery](Backup-and-Recovery)**

---

## Get help

1. Read `~/printer_data/logs/klippy.log` (last 100 lines)  
2. Search [Klipper Discourse](https://klipper.discourse.group/)  
3. Sovol Zero threads on [Sovol forum](https://forum.sovol3d.com/)  
4. [asnajder/zero-config issues](https://github.com/asnajder/zero-config/issues)  
5. [Rex-Sovol-Zero-Mainline issues](https://github.com/0dysseusRex/Rex-Sovol-Zero-Mainline/issues)

Include: Klipper version, error text, relevant config sections (not full secrets).
