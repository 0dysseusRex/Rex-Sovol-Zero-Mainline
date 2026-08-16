# Configuration and Rex Repo

Once Klipper connects to MCUs, you need **configuration files** telling it about the Zero's hardware. This page covers the baseline from [asnajder/zero-config](https://github.com/asnajder/zero-config) plus the **[Rex-Sovol-Zero-Mainline](https://github.com/0dysseusRex/Rex-Sovol-Zero-Mainline)** layer.

> **This page is Path A (default): eddy probe + bed load cell for fine Z offset.**  
> Some printers shipped **without** a bed load cell → follow **[Eddy-Only Configuration](Eddy-Only-Configuration)** instead (eddy homing, mesh, and tap-cal Z offset only).

---

## Two config layers

| Layer | Repo | When |
|---|---|---|
| **Base mainline Zero** | [asnajder/zero-config](https://github.com/asnajder/zero-config) configs | First Klipper start after MCU flash |
| **Eddy + load cell tuning** | [Rex-Sovol-Zero-Mainline](https://github.com/0dysseusRex/Rex-Sovol-Zero-Mainline) | After base Klipper runs — **requires bed load cell** |
| **Eddy only (no load cell)** | Rex `sovol_eddy.cfg` + zero-config baseline | See [Eddy-Only Configuration](Eddy-Only-Configuration) |

**Do not overwrite** your entire `printer.cfg` with any single repo — merge sections and keep your `SAVE_CONFIG` block.

---

## Architecture (Path A — load cell for fine Z)

This is the **default Rex config**. It uses the bed load cell for a nozzle touch at print start to set fine Z offset; the eddy probe still handles homing and mesh.

```
G28 X Y  →  G28 Z (eddy, non-contact)  →  PRINT_START  →  load cell touch  →  G28 Z  →  mesh
```

| Function | Module | Hardware |
|---|---|---|
| Z homing + mesh | `probe_eddy_current` | Toolhead LDC1612 eddy |
| Fine first-layer Z | `probe_pressure` | Bed strain gauge (PD9/PD10) — **not on all printers** |
| Axis twist cal | `axis_twist_pressure` | Eddy at offset + load cell touch |

**G28 never uses the load cell** — same pattern as Cartographer-style scan homing.

**No load cell?** You only need the eddy column — see [Eddy-Only Configuration](Eddy-Only-Configuration).

Details: [Rex README](https://github.com/0dysseusRex/Rex-Sovol-Zero-Mainline#architecture)

---

## Install Rex Klipper extras (load cell path only)

SSH into printer:

```bash
cd ~
git clone https://github.com/0dysseusRex/Rex-Sovol-Zero-Mainline.git
cd Rex-Sovol-Zero-Mainline
./scripts/install-probe-pressure.sh ~/klipper
```

**Why Python extras?** Mainline Klipper doesn't include Sovol's bed load cell module. This script copies `probe_pressure.py` and `axis_twist_pressure.py` into `~/klipper/klippy/extras/`.

**Skip this entire step** if you have no load cell — you don't need `probe_pressure.py`. See [Eddy-Only Configuration](Eddy-Only-Configuration).

Klipper may show **"dirty"** version — normal with untracked extras ([KLIPPER_UPDATES.md](https://github.com/0dysseusRex/Rex-Sovol-Zero-Mainline/blob/master/docs/KLIPPER_UPDATES.md)).

---

## Copy config snippets (Path A)

```bash
cp ~/Rex-Sovol-Zero-Mainline/config/sovol_eddy.cfg ~/printer_data/config/
cp ~/Rex-Sovol-Zero-Mainline/config/probe_pressure.cfg ~/printer_data/config/
cp ~/Rex-Sovol-Zero-Mainline/config/GP3D_Macro.cfg ~/printer_data/config/
cp ~/Rex-Sovol-Zero-Mainline/config/Rex_Macros.cfg ~/printer_data/config/
cp ~/Rex-Sovol-Zero-Mainline/config/display_macros.cfg ~/printer_data/config/
cp ~/Rex-Sovol-Zero-Mainline/config/pause_cancel_macros.cfg ~/printer_data/config/
```

**Eddy-only:** copy only `sovol_eddy.cfg` — omit `probe_pressure.cfg`. Details: [Eddy-Only Configuration](Eddy-Only-Configuration).

Optional:
```bash
cp ~/Rex-Sovol-Zero-Mainline/config/line_purge.cfg ~/printer_data/config/
```

---

## Includes in printer.cfg

Add near top of `~/printer_data/config/printer.cfg` (order matters):

```ini
[include mainsail.cfg]
[include Macro.cfg]
[include pause_cancel_macros.cfg]
[include GP3D_Macro.cfg]
[include Rex_Macros.cfg]
[include display_macros.cfg]
[include sovol_eddy.cfg]
[include probe_pressure.cfg]
# [include line_purge.cfg]    ; optional
```

**Why order?** `pause_cancel_macros.cfg` must load **after** `Macro.cfg` and defines `PAUSE`, `CANCEL_PRINT`, and `END_PRINT`. Do **not** duplicate those three in `Macro.cfg`. Later includes override earlier macros for everything else.

---

## Critical printer.cfg changes

Merge from [Rex printer.cfg template](https://github.com/0dysseusRex/Rex-Sovol-Zero-Mainline/blob/master/config/printer.cfg):

| Setting | Value | Why |
|---|---|---|
| `[stepper_z] endstop_pin` | `probe:z_virtual_endstop` | Z homes on eddy, not load cell |
| `[safe_z_home]` | See template | Safe XY before Z homing |
| `[force_move] enable_force_move` | `True` | Required for `EDDY_CALIBRATE_PREP` |
| **Remove** | `[z_offset_calibration]` | Sovol fork only |
| **Remove** | `[probe_eddy_ng]`, eddyng includes | Not used on mainline path |
| **Update** | All `canbus_uuid` | Your flashed UUIDs |

Verify:
```ini
[stepper_z]
endstop_pin: probe:z_virtual_endstop
```

**Do NOT set** `endstop_pin: probe_pressure:z_virtual_endstop`.

---

## Merge macros (Macro.cfg)

From [Rex Macro.cfg template](https://github.com/0dysseusRex/Rex-Sovol-Zero-Mainline/blob/master/config/Macro.cfg):

| Macro | Purpose |
|---|---|
| `G28` | Safe Z homing until eddy calibrated |
| `PRINT_START` / `START_PRINT` | Bed heat → nozzle clean → load cell Z → mesh |
| `CLEAN_NOZZLE` | OEM silicone wiper before probing (optional `CLEAN_NOZZLE_BRASS` for brush mod) |

**Pause / cancel / end:** use `[include pause_cancel_macros.cfg]` after `Macro.cfg` — do **not** also define `PAUSE`, `CANCEL_PRINT`, or `END_PRINT` in `Macro.cfg`.

If migrating from stock Sovol `Macro.cfg`, **remove** those three macros from `Macro.cfg` and keep `RESUME` / load-filament macros there. Do not duplicate `PAUSE`/`RESUME`/`CANCEL_PRINT` unless you intend to override [mainsail.cfg](https://github.com/mainsail-crew/mainsail-config) versions without using `pause_cancel_macros.cfg`.

---

## Display menus (UC1701 knob screen)

Full reference: **[UC1701 Display and Menus](UC1701-Display-and-Menus)** — status screen layout, chamber and filament icons, menu tree, and basic knob use.

Quick summary — `display_macros.cfg` adds:

**Idle status line:** optional IP (off by default; **Setup → Network → Show IP** to toggle)  
**Status rows:** filament spool + **Yes/No** (row 0 right); chamber icon + temp (row 1 right)  
**Control (top):** Front And Center, Clean Nozzle  
**Temperature (top):** Chamber Preheat, Stop Preheat  
**Filament:** load / unload 60 mm (fast and slow)  
**Prepare → Calibration:** Load Cell Z Touch, Eddy Cal Prep, Axis Twist Cal, Test Load Cell  
**Tune:** Save Z Offset, End Print + Save Z  
**Setup → Network:** Ethernet IP, Wi-Fi IP, SSID, Wi-Fi signal, mDNS hostname  
**Setup → Chamber LED:** On / Off / Brightness %  

The stock Klipper **OctoPrint** menu is **hidden** by default (optional commented block in `display_macros.cfg`).

Install the network plugin once on the host:

```bash
~/Rex-Sovol-Zero-Mainline/scripts/install-network-status.sh
```

Requires stock `[display]` section in `printer.cfg` (UC1701).

**Display knob reversed?** See [UC1701 Display and Menus — Troubleshooting](UC1701-Display-and-Menus#troubleshooting).

**KlipperScreen alternative:** [lexfrei sovol_codes plugin](https://github.com/lexfrei/sovol-zero-mainline/tree/main/klipper-plugin) reproduces vendor numeric codes on HDMI — optional.

---

## Slicer G-code

Replace long OEM start sequence in Orca:

**Start G-code** ([template](https://github.com/0dysseusRex/Rex-Sovol-Zero-Mainline/blob/master/slicer/Sovol-OrcaSlicer-start.gcode)):
```gcode
M117
START_PRINT BED=[bed_temperature_initial_layer_single] HOTEND=[nozzle_temperature_initial_layer] CHAMBER=[chamber_temperature]
SET_PRINT_STATS_INFO TOTAL_LAYER=[total_layer_count]
G90
```

**End G-code:**
```gcode
END_PRINT
```

**Why short g-code?** `PRINT_START` macro handles homing, heating, probing, mesh — duplicating in slicer causes double-homing and wrong probe order.

---

## Start from zero-config baseline (alternative)

If you don't have a working merged config yet, start from [asnajder/zero-config configs](https://github.com/asnajder/zero-config) and add Rex includes on top. Remove unsupported Sovol fork sections iteratively until Klipper starts — see zero-config "Finishing Up".

---

## Restart and verify

```bash
sudo systemctl restart klipper
```

Mainsail → Machine tab → verify objects exist (Path A):

- `probe_eddy_current eddy`
- `probe_pressure`
- `gcode_macro BED_LOADCELL_Z_OFFSET`
- `gcode_macro EDDY_CALIBRATE_PREP`

**Eddy-only:** only `probe_eddy_current eddy` is required — no `probe_pressure` objects.

---

## Next step

→ **[Calibration](Calibration)** — Path A (load cell)  
→ **[Eddy-Only Configuration](Eddy-Only-Configuration)** — Path B (no load cell)
