# ST-LINK Step by Step

An **ST-LINK** is a small USB debugger that connects to hidden **SWD** pads on each MCU board. You use it to read, backup, and flash firmware when CAN-based updates fail.

This guide is for **complete beginners**. Based on [Rappetor/Sovol-SV08-Mainline Step 6–7](https://github.com/Rappetor/Sovol-SV08-Mainline?tab=readme-ov-file#step-6---stock-firmware-backup) and [asnajder/zero-config recovery section](https://github.com/asnajder/zero-config#if-something-goes-wrong).

---

## What is ST-LINK?

| Term | Meaning |
|---|---|
| **MCU** | Microcontroller — tiny computer on mainboard, toolhead, chamber board |
| **SWD** | Serial Wire Debug — 2-wire protocol for programming |
| **ST-LINK** | ST Micro's USB adapter that speaks SWD |
| **STM32CubeProgrammer** | Free software to flash STM32 chips |

**Why not flash everything over CAN?** The first migration from Sovol stock often needs ST-LINK once per board to install **Katapult** (bootloader). After that, most updates use CAN from the CB1.

---

## Buy / identify your ST-LINK

Common options:
- ST-LINK V2 clone (blue pill style) — cheap, works if firmware updated  
- ST-LINK V3 — faster, more reliable  

Update clone firmware via STM32CubeProgrammer **Help → Firmware update** if connect fails.

---

## Wiring (same for all Zero boards)

**Printer MUST be OFF and unplugged from wall power.**

Connect board pads → ST-LINK:

| Board pad label | ST-LINK pin |
|---|---|
| **3V3** | 3.3V |
| **IO** | SWDIO |
| **CK** | SWCLK |
| **G** | GND |

Pinout diagrams (photos): [zero-config README — recovery section](https://github.com/asnajder/zero-config#if-something-goes-wrong)

**Why printer off?** ST-LINK supplies 3.3V to the MCU. Mains power + ST-LINK can damage hardware.

**Clone ST-LINK pin order varies** — read the silkscreen on *your* adapter; don't assume colors.

---

## Install STM32CubeProgrammer

1. Create free account at [st.com](https://www.st.com).  
2. Download [STM32CubeProgrammer](https://www.st.com/en/development-tools/stm32cubeprog.html).  
3. Install with default options.  
4. Connect ST-LINK to PC (printer still off).  
5. Open programmer → top right **Firmware upgrade** if prompted.

---

## Step A — Connect and verify

1. Wire ST-LINK to **mainboard** SWD (start with mainboard — easiest access).  
2. Open STM32CubeProgrammer.  
3. Top right: interface **ST-LINK**, port **USB**, **Connect**.  
4. Green **Connected** — memory map appears in center panel.

**Troubleshooting connect:**

| Problem | Fix |
|---|---|
| No device detected | Re-seat USB; try another port; update ST-LINK firmware |
| Can't connect to target | Check 3V3/GND swapped; verify printer is OFF |
| Connect then instant disconnect | Bad clone — try shorter wires (<15 cm) |

---

## Step B — Backup current firmware (do this first!)

1. **Read** menu → **Read all** — wait until complete.  
2. **Read** menu → **Save As** → `mainboard_backup_YYYY-MM-DD.bin`  
3. Check file size: mainboard should be **≥ 512 KB**.

Repeat for **toolhead** (open toolhead cover) and **chamber board** if present.

Store backups on your PC **and** cloud/USB stick.

**Why:** Personal backup restores *your* exact state. zero-config `.hex` files restore *known* Sovol v1.3.7.

---

## Step C — Full chip erase (when installing Katapult fresh)

1. Connected in STM32CubeProgrammer.  
2. **Erasing & Programming** tab.  
3. Check **Full chip erase** (or use OB menu for mass erase).  
4. Click **Erase**.

**Why erase?** Old Sovol firmware and new Katapult/Klipper must not overlap at wrong flash offsets.

---

## Step D — Flash Katapult `.bin` (mainboard example)

1. **Erasing & Programming** → **Browse** → select:  
   [`Katapult_Zero_Host_H743_128kb.bin`](https://github.com/asnajder/zero-config/tree/main/bins)  
   (from zero-config `bins/` folder — **not** the Deployer file)  
2. Start address: `0x08000000` (default for STM32).  
3. Click **Start Programming** / **Download**.  
4. Disconnect ST-LINK, power printer on, proceed to CAN/USB Klipper flash.

For **toolhead/chamber** (STM32F103, 8 KiB offset): use F103 Katapult bin built with [menuconfig values](CAN-Bus-and-MCU-Flashing) or toolhead bin from zero-config.

---

## Step E — Restore stock Sovol `.hex` (recovery)

1. Connect ST-LINK (printer off).  
2. Open file from [zero-config/recovery](https://github.com/asnajder/zero-config/tree/main/recovery):  
   - Mainboard → `zero_motherboard_1.3.7.hex`  
   - Toolhead → `zero_extuder_1.3.7.hex`  
   - Chamber → `zero_chamber_hot.hex`  
3. Program → Download.  
4. Power cycle printer.

---

## Which board am I on?

| Location | MCU | Typical access |
|---|---|---|
| Base — main controller | STM32H743-class | Under base cover, near CB1 |
| Toolhead | STM32F103 | Under toolhead shroud |
| Chamber heater | STM32F103 | Chamber heater module |

Flash **one board at a time**. Label your wires.

---

## After ST-LINK: flash Klipper over CAN

ST-LINK installs Katapult. Normal Klipper updates then happen from SSH:

```bash
sudo service klipper stop
python3 ~/katapult/scripts/flashtool.py -i can0 -q
python3 ~/katapult/scripts/flashtool.py -i can0 -f ~/klipper/out/klipper.bin -u <UUID>
sudo service klipper start
```

Full procedure: **[CAN Bus and MCU Flashing](CAN-Bus-and-MCU-Flashing)**

---

## Alternative: openocd (advanced)

[lexfrei/sovol-zero-mainline](https://github.com/lexfrei/sovol-zero-mainline) documents SWD flashing via `openocd` without ST-LINK — useful for advanced users with CMSIS-DAP or GPIO bit-banging. Beginners should use STM32CubeProgrammer.

---

## Next step

→ **[Host Setup (CB1 / Armbian)](Host-Setup-CB1-Armbian)** — replace host OS  
→ **[CAN Bus and MCU Flashing](CAN-Bus-and-MCU-Flashing)** — if ST-LINK Katapult is installed
