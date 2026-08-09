# UC1701 Display and Menus

The Sovol Zero **knob LCD** (UC1701, 128×64, 16×4 characters) stays useful after migrating to mainline Klipper. This page describes the **status screen**, **custom icons**, and **menu layout** used with the Rex repo configs.

**Config files involved:**

| File | Role |
|---|---|
| `printer.cfg` | `[display]` section (pins, contrast) |
| Klipper `menu.cfg` | Stock menus (Control, Temperature, Filament, …) |
| `GP3D_Macro.cfg` | Shutdown, bed soak, Z save menus |
| `display_macros.cfg` | Rex status line, icons, calibration menus, network |

Include order in `printer.cfg`:

```ini
[include GP3D_Macro.cfg]
[include Rex_Macros.cfg]
[include display_macros.cfg]
```

`display_macros.cfg` must load **after** `GP3D_Macro.cfg` and `Rex_Macros.cfg`.

---

## Basic use (knob and button)

| Action | What to do |
|---|---|
| **Open menu** | Press the encoder **click** once while idle (or when the status screen is showing). |
| **Scroll** | Turn the encoder. Rex configs set `menu_reverse_navigation: True` so scroll direction matches typical expectation on the Zero. |
| **Select** | Highlight a line, then **click**. |
| **Go back** | Choose **`..`** at the top of a submenu, or use back navigation if your display wiring provides a back pin. |
| **Adjust a value** | On **input** items (bed temp, move axis, …): click to edit, turn to change, click to apply. |
| **Long lines** | Network and some labels scroll horizontally when highlighted — keep turning or wait for the scroll. |

While a **print is running**, many setup items are hidden (`enable: not Printing`). Use **Tune** for speed, flow, and Z offset during a print.

**After config changes:** `FIRMWARE_RESTART` or `RESTART` so menus and glyphs reload.

---

## Status screen layout

When not in a menu, the display shows four rows of 16 characters:

```
Row 0:  [hotend icon + temp]          [filament icon + Yes/No]
Row 1:  [bed icon + temp]             [chamber icon + temp °]
Row 2:  [print progress bar]          [print time]
Row 3:  [status / IP / XYZ / Ready]
```

### Left side (stock Klipper)

- **Row 0 — Hotend:** Nozzle icon and current temperature (and target arrow when heating).
- **Row 1 — Bed:** Bed icon and bed temperature.
- **Row 2 — Progress:** Print percentage and progress bar while printing.
- **Row 3 — Status:**
  - **Printing:** `M117` message if set, else toolhead **X/Y/Z** position.
  - **Idle:** **`Ready`**, or the printer **IP address** if you enabled it (see below).

### Right side (Rex additions)

#### Filament sensor — row 0, right

| On screen | Meaning |
|---|---|
| **Spool icon** + **`Yes`** | `[filament_switch_sensor filament_sensor]` is enabled and filament is present at the sensor. |
| **Spool icon** + **`No`** | Sensor disabled, runout, or no filament detected. |

The **spool icon** is a custom 16×16 `[display_glyph filament]` (bitmap in `display_macros.cfg`). It replaces the stock **part-fan percentage** on the right side of row 0.

Sensor config (in `printer.cfg`):

```ini
[filament_switch_sensor filament_sensor]
switch_pin: PB2
```

#### Chamber temperature — row 1, right

| On screen | Meaning |
|---|---|
| **Chamber icon** + **`25°`** (example) | Current **chamber air** temperature from `[temperature_sensor chamber_temp]`. |

The **chamber icon** is a custom 16×16 `[display_glyph chamber]` — a small enclosed-chamber graphic, same size as the stock bed and hotend icons. It replaces the idle **feedrate %** on row 1 right.

This is a **read-only sensor** display, not the chamber *heater target*. To heat the chamber for ABS/ASA, use **Temperature → Chamber Preheat** (macro `START_CHAMBER_PREHEAT`).

#### Optional IP — row 3

Off by default. When enabled (**Setup → Network → Show IP: ON**), the bottom line shows the host IP (e.g. `192.168.11.186`) instead of `Ready`. Requires the `network_status` Klipper extra:

```bash
~/Rex-Sovol-Zero-Mainline/scripts/install-network-status.sh
```

The setting persists in `~/variables.cfg` as `show_ip`.

---

## Main menu structure

Press the knob to open **Main**. Submenus show **`..`** first to go back.

### Stock Klipper (always present)

| Menu | Contents |
|---|---|
| **Tune** | *(printing only)* Speed %, Flow %, Z offset |
| **SD Card** | Start / pause / resume / cancel virtual SD jobs |
| **Control** | Home, Z tilt, bed mesh, move axes, fans, … |
| **Temperature** | Hotend/bed targets, preheat presets, cooldown |
| **Filament** | Load/unload filament, extruder temp |
| **Setup** | Save config, restart, PID tune, calibration helpers |

**OctoPrint** (stock Klipper submenu for `action:pause` / OctoPrint plugins) is **hidden** in Rex configs. Use Mainsail **Pause / Resume / Cancel** instead. Optional OctoPrint items are preserved as a commented block at the bottom of `display_macros.cfg`.

### GP3D additions (`GP3D_Macro.cfg`)

| Location | Item |
|---|---|
| **Prepare** | Bed temp (input), Heat soak |
| **Tune → Save & Exit?** | End-Save Z-offs, End print + save Z (via `display_macros.cfg`) |
| **Tune** | Move Z (input) |
| **Setup** | **Shutdown** (cool hotend, then host shutdown) |

### Rex additions (`display_macros.cfg`)

| Location | Item | Macro / action |
|---|---|---|
| **Control** *(top)* | Front And Center | `FRONT_AND_CENTER` — home, park at front for photos/maintenance |
| **Control** *(top)* | Clean Nozzle | `CLEAN_NOZZLE` — brass brush + silicone wipe sequence |
| **Temperature** *(top)* | Chamber Preheat | `START_CHAMBER_PREHEAT CHAMBER=50` |
| **Temperature** *(top)* | Stop Preheat | `STOP_CHAMBER_PREHEAT` |
| **Prepare → Calibration** | Load Cell Z Touch | `BED_LOADCELL_Z_OFFSET` |
| **Prepare → Calibration** | Test Load Cell | `PROBE_LOAD_CELL` |
| **Prepare → Calibration** | Eddy Cal Prep | `EDDY_CALIBRATE_PREP` |
| **Prepare → Calibration** | Axis Twist Cal | `AXIS_TWIST_COMPENSATION_CALIBRATE` |
| **Tune** | Save Z Offset Now | `Z_OFFSET_APPLY_PROBE1` + `SAVE_CONFIG` |
| **Tune → Save & Exit?** | End Print + Save Z | `END_PRINT_G` |
| **Filament** | Load / Unload fast & slow | **60 mm** extrude (stock Klipper uses 50 mm) |
| **Setup → Network** | Show IP, Eth, Wi‑Fi, SSID, mDNS | Toggle and view addresses |
| **Setup → Lights** | Light On / Off / Breathe | Nozzle LED macros |

---

## Common tasks from the display

### Before printing (Path A — load cell)

1. **Control → Front And Center** or home from Mainsail if needed.
2. **Control → Clean Nozzle** if the tip needs wiping (same as `PRINT_START` clean step).
3. **Temperature → Chamber Preheat** for enclosed high-temp filaments; **Stop Preheat** when done or if you abort.
4. Confirm **filament icon** shows **Yes** before starting a job.

### During a print

- **Tune** → adjust speed, flow, or babystep Z.
- Pause/resume/cancel from **Mainsail** (not the hidden OctoPrint menu).

### After a print / Z offset

- **Tune → Save Z Offset Now** if you babystepped and want to keep the offset.
- **Tune → Save & Exit? → End Print + Save Z** to run end sequence and save load-cell Z if flagged.

### Network / IP

- **Setup → Network → Show IP** — toggle idle IP on row 3.
- Scroll other network lines while highlighted to read full addresses.

### Shutdown

- **Setup → Shutdown** — cools hotend below 70 °C with fans, then shuts down the CB1 host (same as GP3D `SHUTDOWN` macro).

---

## Icons and text limits

- The LCD uses an **8×14 bitmap font** — **ASCII only** on the status lines. Emojis and Unicode (✔, ❌, smart quotes) do **not** render; use plain text (`Yes` / `No`) or custom `[display_glyph]` bitmaps.
- Each row is **16 characters** wide. IP addresses fit without a prefix; long menu names scroll when selected.
- Custom glyphs must be **16×16** dot grids using only `.` and `*` (see `chamber` and `filament` in `display_macros.cfg`).

---

## Troubleshooting

| Issue | Fix |
|---|---|
| Knob scroll feels reversed | Toggle `menu_reverse_navigation` in `display_macros.cfg`, or swap `encoder_pins` in `[display]`. |
| No chamber / filament on screen | Confirm `[include display_macros.cfg]` and `FIRMWARE_RESTART`. |
| Filament always **No** | Check `[filament_switch_sensor filament_sensor]` wiring and `switch_pin`. |
| Chamber shows **`N/A`** or wrong | Verify `[temperature_sensor chamber_temp]` in `printer.cfg`. |
| IP menu missing | Run `install-network-status.sh` and add `[network_status]` (included in `display_macros.cfg`). |
| `SET_DISPLAY_TEXT already registered` | Do not define `[gcode_macro SET_DISPLAY_TEXT]` — Klipper provides it. |

See also [Configuration and Rex Repo](Configuration-and-Rex-Repo) and [Troubleshooting](Troubleshooting).

---

## Related

- [Configuration and Rex Repo](Configuration-and-Rex-Repo) — install `display_macros.cfg` and dependencies
- [SSH and Networking Basics](SSH-and-Networking-Basics) — find printer IP for Mainsail
- [Calibration](Calibration) — when to use display calibration menu items
