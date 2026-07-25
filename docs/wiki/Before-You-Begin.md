# Before You Begin

This page lists everything you need **before** opening the printer or erasing the eMMC.

---

## What you are about to do

Sovol ships the Zero with a **custom Klipper fork** on the CB1 (single-board computer inside the base). Mainline migration means:

1. **Replacing the host operating system** on the CB1 eMMC with Armbian Linux  
2. **Re-flashing all microcontroller (MCU) boards** with Katapult + mainline Klipper firmware  
3. **Replacing configuration files** so Klipper talks to the eddy probe and bed load cell using standard modules  

**Why?** Mainline Klipper receives security fixes, new features, and community support. The Rex config layer uses `probe_eddy_current` + `probe_pressure` — modules that work on stock hardware but require mainline Klipper (or restored Sovol Python extras).

---

## Time and skill estimate

| Stage | Time (first time) |
|---|---|
| Backup + ST-LINK backup (optional) | 1–2 hours |
| Armbian flash + first boot | 30–60 min |
| KIAUH install | 30–60 min |
| MCU flashing (all boards) | 1–2 hours |
| Config merge + calibration | 2–4 hours |
| **Total** | **~6–10 hours** spread over a day |

You do **not** need to be a programmer. You **do** need patience, the ability to follow steps exactly, and willingness to learn basic SSH.

---

## Hardware checklist

| Item | Why you need it |
|---|---|
| **USB eMMC reader** | Remove CB1 eMMC module and flash Armbian from your PC |
| **32 GB eMMC module** (recommended) | [asnajder/zero-config](https://github.com/asnajder/zero-config) recommends 32 GB. Stock 8 GB *can* work with a special overlay ([lexfrei](https://sovol.lexfrei.dev)) — beginners should use 32 GB to avoid that extra step |
| **Ethernet cable** (recommended for first boot) | More reliable than Wi-Fi during setup |
| **USB keyboard + HDMI monitor** (optional) | Alternative to SSH for Armbian first login |
| **ST-LINK V2** (or compatible clone) | Flash/recover MCU firmware when CAN flash fails |
| **STM32CubeProgrammer** (free, ST Micro) | GUI for ST-LINK read/flash — easier than command line for beginners |
| **Small Phillips screwdriver** | Open base panel, toolhead cover for SWD access |
| **PC with Windows/Mac/Linux** | Armbian Imager, PuTTY, WinSCP |

---

## Software checklist (install on your PC)

| Software | Download | Purpose |
|---|---|---|
| [Armbian Imager](https://www.armbian.com/download/) | armbian.com | Write Armbian to eMMC |
| [PuTTY](https://www.putty.org/) or Windows OpenSSH | — | SSH terminal to CB1 |
| [WinSCP](https://winscp.net/) | — | Copy files to/from printer (drag-and-drop) |
| [STM32CubeProgrammer](https://www.st.com/en/development-tools/stm32cubeprog.html) | st.com (free account) | ST-LINK firmware read/flash |
| [Orca Slicer](https://github.com/SoftFever/OrcaSlicer) or Sovol Orca | — | Update start/end G-code later |

---

## Back up before you change anything

### 1. Copy Klipper configs (while still on OEM)

If Mainsail/Fluidd still works, use WinSCP:

- Connect to printer IP (see [SSH and Networking Basics](SSH-and-Networking-Basics))
- Download entire folder: `/home/sovol/printer_data/config/` (OEM user is often `sovol`)  
  — or `/home/<your-user>/printer_data/config/` if you already migrated partially

**Why:** Contains PID values, mesh data, slicer macros, and settings you may want to reference.

Also download:
- `/home/sovol/primer_data/gcodes/` — your saved prints (path may be `printer_data/gcodes`)
- Moonraker database if present: `~/printer_data/database/`

### 2. Note your CAN UUIDs (if Klipper still starts)

In SSH:
```bash
sudo service klipper stop
python3 ~/katapult/scripts/flashtool.py -i can0 -q
```
Save the output — UUIDs **will change** after reflash, but this confirms CAN works before you start.

### 3. ST-LINK firmware backup (strongly recommended)

See **[Backup and Recovery](Backup-and-Recovery)** and **[ST-LINK Step by Step](ST-LINK-Step-by-Step)**.

**Why:** If MCU flashing goes wrong, you can restore your exact stock firmware instead of hunting for files.

### 4. Optional — clone entire eMMC

If you have a USB eMMC reader, make a raw image of the stock module before overwriting. Advanced users only; Armbian flash is usually enough.

---

## Safety rules

1. **Unplug the printer** before opening panels or touching the CB1 eMMC.  
2. **Printer OFF when using ST-LINK** — the debugger powers the MCU; mains power can damage the ST-LINK or board.  
3. **Keep ST-LINK wiring short and correct** — wrong wiring can brick the MCU (see ST-LINK page).  
4. **Do not flash `Deployer_*.bin` via ST-LINK** — deployer bins are for CAN/USB flash only ([zero-config note](https://github.com/asnajder/zero-config#firmware-binaries)).  
5. **One MCU at a time** when first learning ST-LINK — mainboard, then toolhead, then chamber heater board.

---

## When things go wrong

You are **not** stuck if you prepared:

| Problem | Escape hatch |
|---|---|
| Bad Armbian flash | Re-flash eMMC; OEM eMMC backup if you kept one |
| MCU won't respond on CAN | ST-LINK + recovery `.hex` from [zero-config/recovery](https://github.com/asnajder/zero-config/tree/main/recovery) |
| Klipper won't start | Fix config errors one section at a time; comment out includes |
| Want to go back to Sovol entirely | Flash stock `.hex` to all MCUs + restore OEM eMMC image |

---

## Next step

→ **[SSH and Networking Basics](SSH-and-Networking-Basics)** if you need help connecting to the printer  
→ **[Backup and Recovery](Backup-and-Recovery)** to save ST-LINK backups and download recovery files  
→ **[Host Setup (CB1 / Armbian)](Host-Setup-CB1-Armbian)** if you already have backups and want to start flashing
