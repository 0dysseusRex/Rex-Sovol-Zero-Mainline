# Backup and Recovery

If MCU flashing goes wrong, **recovery files** let you restore Sovol stock firmware. This page explains what to back up, where the files live, and how to use them.

Primary source: **[asnajder/zero-config/recovery](https://github.com/asnajder/zero-config/tree/main/recovery)**

---

## Two types of backup

| Type | What it saves | How | When |
|---|---|---|---|
| **Config backup** | `printer.cfg`, macros, PID, mesh | WinSCP / copy folder | Before any migration step |
| **MCU firmware backup** | Exact flash contents of each board | ST-LINK read in STM32CubeProgrammer | Before first MCU reflash |
| **Stock recovery files** | Known-good Sovol v1.3.7 firmware | Download from zero-config | When ST-LINK backup failed or MCU is bricked |

---

## Download stock recovery files (zero-config)

Clone or download from GitHub:

**Folder:** https://github.com/asnajder/zero-config/tree/main/recovery

| File | Board | Use |
|---|---|---|
| [`zero_motherboard_1.3.7.hex`](https://github.com/asnajder/zero-config/blob/main/recovery/zero_motherboard_1.3.7.hex) | Main controller (H743-class) | Restore OEM mainboard firmware |
| [`zero_extuder_1.3.7.hex`](https://github.com/asnajder/zero-config/blob/main/recovery/zero_extuder_1.3.7.hex) | Toolhead (F103) | Restore OEM toolhead firmware |
| [`zero_chamber_hot.hex`](https://github.com/asnajder/zero-config/blob/main/recovery/zero_chamber_hot.hex) | Chamber heater MCU (F103) | Restore chamber board (if installed) |
| [`stm32h750_katapult.bin`](https://github.com/asnajder/zero-config/blob/main/recovery/stm32h750_katapult.bin) | Mainboard | Emergency Katapult for ST-LINK recovery |

**Why `.hex` for stock restore?** STM32CubeProgrammer accepts Intel HEX format directly for full-chip programming back to Sovol OEM state.

Save these files on your PC **before** you start MCU flashing — not only on the printer.

---

## Prebuilt mainline bins (not recovery — for migration)

**Folder:** https://github.com/asnajder/zero-config/tree/main/bins

| File pattern | Purpose |
|---|---|
| `Deployer_Zero_Host_H743_128kb.bin` | Installs Katapult **over CAN/USB** from stock bootloader — **NOT for ST-LINK** |
| `Katapult_Zero_Host_H743_128kb.bin` | Katapult for mainboard via **ST-LINK** |
| `Klipper_Zero_Host_H743_128kb.bin` | Mainline Klipper for mainboard |
| Toolhead/chamber `.bin` files | Flash via Katapult after ST-LINK or CAN bootloader is working |

**Critical distinction:**
- **Deployer** = bridge from Sovol stock → Katapult (flash tool over CAN)  
- **Katapult bin via ST-LINK** = when CAN/USB path is broken  

---

## ST-LINK personal backup (best practice)

Before flashing anything, read the current firmware off each board and save it.

### Procedure summary

1. Printer **OFF**, unplugged from wall.  
2. Wire ST-LINK to board SWD pads (see [ST-LINK Step by Step](ST-LINK-Step-by-Step)).  
3. Open **STM32CubeProgrammer** → **Connect**.  
4. **Read** → **Read all** (sets correct size).  
5. **Read** → **Save As** → e.g. `my_mainboard_backup.bin`.  

### Verify backup size

| Board | Minimum good backup size |
|---|---|
| Toolhead (F103) | **≥ 128 KB** |
| Mainboard (H743) | **≥ 512 KB** |

If your file is only ~1 KB, the read failed — do not trust it.

Credit: [Rappetor/Sovol-SV08-Mainline — Step 6/7](https://github.com/Rappetor/Sovol-SV08-Mainline?tab=readme-ov-file#step-6---stock-firmware-backup) (same ST-LINK workflow applies to Zero).

---

## Restore stock Sovol firmware (emergency)

Use when:
- MCU is unresponsive on CAN  
- Klipper flash left board in boot loop  
- You want to return to OEM firmware temporarily  

### Steps

1. Printer **OFF**. Connect ST-LINK to the affected board.  
2. STM32CubeProgrammer → **Connect**.  
3. **Erasing & Programming** → Open the correct `.hex` from [zero-config/recovery](https://github.com/asnajder/zero-config/tree/main/recovery).  
4. **Download** (flash).  
5. Disconnect ST-LINK, reassemble, power on.  

Repeat for **each** board you changed (mainboard, toolhead, chamber).

**Why three boards?** The Zero has separate MCUs on CAN: main board, toolhead (eddy + extruder), and optional chamber heater.

After stock restore, the host CB1 may still run Armbian — only the motion MCUs return to Sovol firmware. Full OEM experience requires the stock eMMC image too.

---

## Restore Katapult only (mainboard)

If mainboard Klipper is corrupt but you want to stay on mainline:

Flash [`stm32h750_katapult.bin`](https://github.com/asnajder/zero-config/blob/main/recovery/stm32h750_katapult.bin) or [`Katapult_Zero_Host_H743_128kb.bin`](https://github.com/asnajder/zero-config/tree/main/bins) via ST-LINK, then re-flash Klipper over USB/CAN using Katapult tools.

---

## CAN-based restore (advanced)

If Katapult still runs on CAN but Klipper app is corrupt, [vvuk's Kalico wiki](https://github.com/vvuk/printer-configs/wiki/Kalico-on-the-Sovol-Zero) describes flashing original `.bin` back via `flash_can.py` in two steps (reboot to bootloader, then flash).

Toolhead note from community: Katapult UUID (`61755fe321ac` in boot mode) may differ from runtime Klipper UUID — see [Klipper Discourse — Zero toolhead update](https://klipper.discourse.group/t/unable-to-update-klipper-on-sovol-zero-toolhead-mcu/24864).

---

## Config backup checklist

Download via WinSCP before migration:

```
~/printer_data/config/          (entire folder)
~/printer_data/gcodes/          (optional)
~/printer_data/database/        (Moonraker history)
```

Store on your PC with date in folder name: `zero-backup-2026-07-25/`.

---

## Next step

→ **[ST-LINK Step by Step](ST-LINK-Step-by-Step)** — wiring and STM32CubeProgrammer walkthrough  
→ **[CAN Bus and MCU Flashing](CAN-Bus-and-MCU-Flashing)** — if backups are done and you're ready to flash mainline
