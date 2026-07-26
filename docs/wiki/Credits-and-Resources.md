# Credits and Resources

This wiki and the [Rex-Sovol-Zero-Mainline](https://github.com/0dysseusRex/Rex-Sovol-Zero-Mainline) config stand on work from the Sovol Zero community. Thank you to everyone who tested, documented, and shared failures so others could succeed.

---

## Primary migration guides

| Resource | Author / maintainer | Contribution |
|---|---|---|
| **[asnajder/zero-config](https://github.com/asnajder/zero-config)** | asnajder + community testers | **Main Sovol Zero mainline guide** — Armbian, KIAUH, CAN, MCU menuconfig, prebuilt bins, recovery `.hex`, ST-LINK pinouts, eddy cal, updater script |
| **[Recovery files](https://github.com/asnajder/zero-config/tree/main/recovery)** | asnajder | Stock restore: `zero_motherboard_1.3.7.hex`, `zero_extuder_1.3.7.hex`, `zero_chamber_hot.hex`, `stm32h750_katapult.bin` |
| **[Prebuilt bins](https://github.com/asnajder/zero-config/tree/main/bins)** | asnajder | Katapult deployer, Klipper bins for H743 + F103 |
| **[sovol.lexfrei.dev](https://sovol.lexfrei.dev)** | [lexfrei/sovol-zero-mainline](https://github.com/lexfrei/sovol-zero-mainline) | Deep knowledge base — 8 GB eMMC overlay, openocd SWD path, vendor patch analysis, `sovol_codes.py` display plugin |
| **[Rappetor/Sovol-SV08-Mainline](https://github.com/Rappetor/Sovol-SV08-Mainline)** | Rappetor | ST-LINK backup/flash procedure (adapted for Zero), KIAUH flow, CB1 images — SV08 focused but architecturally similar |

---

## MCU / CAN technical references

| Resource | Contribution |
|---|---|
| **[vvuk/printer-configs — Kalico on Sovol Zero](https://github.com/vvuk/printer-configs/wiki/Kalico-on-the-Sovol-Zero)** | H743 128 KiB / F103 8 KiB offsets, fan GPIO pins, CAN UUID notes |
| **[Esoterical CAN guides](https://canbus.esoterical.online/Getting_Started.html)** | CAN bus fundamentals, toolhead flashing workflow |
| **[Arksine/katapult](https://github.com/Arksine/katapult)** | CAN bootloader used for MCU updates |
| **[bearclaw92/Zero_Toolhead_Guide](https://github.com/bearclaw92/Zero_Toolhead_Guide)** | Zero toolhead on SV08 — Katapult CAN flash patterns |
| **[Blenky56/Flashing-Klipper-to-Sovol-ZERO-Toolhead-on-the-SV08](https://github.com/Blenky56/Flashing-Klipper-to-Sovol-ZERO-Toolhead-on-the-SV08)** | MCU update script, boot vs runtime UUID behavior |

---

## Klipper / probe documentation

| Resource | Contribution |
|---|---|
| **[Klipper Eddy Probe docs](https://www.klipper3d.org/Eddy_Probe.html)** | Official `probe_eddy_current` calibration |
| **[Gekkio/sovol-zero-klipper](https://github.com/Gekkio/sovol-zero-klipper)** | Analysis of Sovol vendor Klipper changes (`probe_pressure`, eddy fork behavior) |
| **[Klipper Discourse — Zero toolhead MCU](https://klipper.discourse.group/t/unable-to-update-klipper-on-sovol-zero-toolhead-mcu/24864)** | Recovery when toolhead won't update over CAN |

---

## Rex-Sovol-Zero-Mainline specific

| Resource | Contribution |
|---|---|
| **[Rex-Sovol-Zero-Mainline](https://github.com/0dysseusRex/Rex-Sovol-Zero-Mainline)** | Mainline `probe_eddy_current` + `probe_pressure` + axis twist configs, macros, display menus |
| **[INSTALL.md](https://github.com/0dysseusRex/Rex-Sovol-Zero-Mainline/blob/master/docs/INSTALL.md)** | Post-migration config install |
| **[CALIBRATION.md](https://github.com/0dysseusRex/Rex-Sovol-Zero-Mainline/blob/master/docs/CALIBRATION.md)** | Eddy bootstrap + load cell calibration |
| **probe_pressure.py** | Derived from Sovol OEM Klipper (GPLv3) |
| **line_purge.cfg** | Adapted from [pellcorp/creality](https://github.com/pellcorp/creality) (SimpleAF) / KAMP |
| **PRINT_START flow credit** | [jontek2/A-better-print_start-macro](https://github.com/jontek2/A-better-print_start-macro) (via zero-config) |

---

## Tools

| Tool | URL |
|---|---|
| Armbian Imager | https://www.armbian.com/download/ |
| KIAUH | https://github.com/dw-0/kiauh |
| STM32CubeProgrammer | https://www.st.com/en/development-tools/stm32cubeprog.html |
| Mainsail | https://mainsail.xyz/ |
| Orca Slicer | https://github.com/SoftFever/OrcaSlicer |

---

## Official Sovol

| Resource | Note |
|---|---|
| **[Sovol3d/SOVOL-ZERO](https://github.com/Sovol3d/SOVOL-ZERO)** | OEM source — third-party firmware may void warranty |
| **[Sovol forum](https://forum.sovol3d.com/)** | Community support |
| **[Sovol Zero brass brush (MakerWorld)](https://makerworld.com/en/models/2225406-sovol-zero-brass-brush)** | Optional nozzle brush mod — use `CLEAN_NOZZLE_BRASS` in Rex `Macro.cfg` |

---

## zero-config acknowledgements (reproduced)

From [asnajder/zero-config README](https://github.com/asnajder/zero-config):

> Leoboi420, Teapot-Apple, matt73210, Atomique13, J&B, jedi 2^10, wildBill, Rappetor, vvuk, and everyone else who shared information and testing results.

Additional zero-config credit:
- [ljg-dev/sovol-sv08-mainline](https://github.com/ljg-dev/sovol-sv08-mainline)
- [asnajder/sv08-config](https://github.com/asnajder/sv08-config) (eddy cal reference)

---

## License notes

- Klipper — GPLv3  
- Rex `probe_pressure.py` / `axis_twist_pressure.py` — GPLv3 (Klipper-derived)  
- Config files in Rex and zero-config repos — community use, verify individual repo licenses  

---

## Support Rex-Sovol-Zero-Mainline

**[ko-fi.com/0dysseusrex](https://ko-fi.com/0dysseusrex)**

---

[← Back to Home](Home)
