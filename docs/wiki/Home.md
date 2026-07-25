# Sovol Zero: OEM → Mainline Klipper Migration Guide

**Welcome.** This wiki walks you through replacing Sovol's vendor Klipper fork with **upstream (mainline) Klipper** on the **Sovol Zero**, using the BigTreeTech CB1 host board.

It is written for people who are **new to SSH, Linux, and ST-LINK**. Every major step explains **what you are doing and why**.

> **Scope:** This guide covers the **full migration** (host OS, MCU firmware, CAN, configs, calibration).  
> After mainline Klipper is running, install **[Rex-Sovol-Zero-Mainline](https://github.com/0dysseusRex/Rex-Sovol-Zero-Mainline)** for the recommended eddy + bed load cell configuration used on this wiki.

---

## What changes when you migrate?

| Topic | Stock Sovol OEM | Mainline (this guide) |
|---|---|---|
| Klipper source | Sovol fork with custom modules | Official [Klipper](https://github.com/Klipper3d/klipper) |
| Host OS | Sovol image on CB1 eMMC | [Armbian](https://www.armbian.com/bigtreetech-cb1/) (recommended) |
| Z homing | Vendor `[z_offset_calibration]` | `[probe_eddy_current]` (non-contact eddy probe) |
| Fine Z offset | Vendor tap / load cell flow | `[probe_pressure]` (bed load cell nozzle touch) |
| Web UI | Mainsail (usually) | Mainsail + Moonraker (reinstalled via KIAUH) |
| MCU firmware | Sovol prebuilt | Katapult bootloader + mainline Klipper bins |
| Warranty | Stock firmware only | Sovol warns third-party firmware may void warranty — proceed at your own risk |

---

## Before you start — read this

1. **[Before You Begin](Before-You-Begin)** — tools, backups, safety, time estimate  
2. **[SSH and Networking Basics](SSH-and-Networking-Basics)** — connect to your CB1 without prior Linux experience  
3. **[Backup and Recovery](Backup-and-Recovery)** — save OEM firmware; links to **asnajder/zero-config recovery files**

---

## Migration path (overview)

```
┌─────────────────────────────────────────────────────────────────┐
│  PHASE 1 — Backup OEM data + optional ST-LINK firmware backup   │
└───────────────────────────────┬─────────────────────────────────┘
                                ▼
┌─────────────────────────────────────────────────────────────────┐
│  PHASE 2 — Flash Armbian to CB1 eMMC (replace host OS)          │
└───────────────────────────────┬─────────────────────────────────┘
                                ▼
┌─────────────────────────────────────────────────────────────────┐
│  PHASE 3 — Install Klipper stack (KIAUH: Klipper/Moonraker/…)   │
└───────────────────────────────┬─────────────────────────────────┘
                                ▼
┌─────────────────────────────────────────────────────────────────┐
│  PHASE 4 — Configure CAN bus (1 Mbit, systemd-networkd)         │
└───────────────────────────────┬─────────────────────────────────┘
                                ▼
┌─────────────────────────────────────────────────────────────────┐
│  PHASE 5 — Flash MCU firmware (mainboard + toolhead + chamber)  │
│            Katapult first, then Klipper — via CAN or ST-LINK    │
└───────────────────────────────┬─────────────────────────────────┘
                                ▼
┌─────────────────────────────────────────────────────────────────┐
│  PHASE 6 — Deploy configs + Rex-Sovol-Zero-Mainline addons      │
└───────────────────────────────┬─────────────────────────────────┘
                                ▼
┌─────────────────────────────────────────────────────────────────┐
│  PHASE 7 — Calibrate eddy probe, load cell, axis twist          │
└─────────────────────────────────────────────────────────────────┘
```

---

## Step-by-step pages

| # | Page | What you'll do |
|---|---|---|
| 1 | [Before You Begin](Before-You-Begin) | Gather hardware, back up configs, understand risks |
| 2 | [SSH and Networking Basics](SSH-and-Networking-Basics) | Find printer IP, open PuTTY/WinSCP, run first commands |
| 3 | [Backup and Recovery](Backup-and-Recovery) | ST-LINK backup; restore stock `.hex` files from zero-config |
| 4 | [ST-LINK Step by Step](ST-LINK-Step-by-Step) | Wire SWD pads, use STM32CubeProgrammer (beginner walkthrough) |
| 5 | [Host Setup (CB1 / Armbian)](Host-Setup-CB1-Armbian) | Flash eMMC, first boot, create user, fix boot delays |
| 6 | [Installing the Klipper Stack](Installing-the-Klipper-Stack) | KIAUH, Katapult, Moonraker timelapse, dependencies |
| 7 | [CAN Bus and MCU Flashing](CAN-Bus-and-MCU-Flashing) | UUID discovery, menuconfig values, flash all three MCUs |
| 8 | [Configuration and Rex Repo](Configuration-and-Rex-Repo) | Merge configs, install probe_pressure, display menus |
| 9 | [Calibration](Calibration) | Eddy bootstrap, load cell Z, axis twist, first print |
| 10 | [Troubleshooting](Troubleshooting) | Common errors and fixes |
| 11 | [Credits and Resources](Credits-and-Resources) | Repos, docs, and people who made this possible |

---

## Quick links

- **Primary Zero mainline guide:** [asnajder/zero-config](https://github.com/asnajder/zero-config)
- **Recovery firmware (stock restore):** [zero-config/recovery](https://github.com/asnajder/zero-config/tree/main/recovery)
- **Prebuilt Katapult/Klipper bins:** [zero-config/bins](https://github.com/asnajder/zero-config/tree/main/bins)
- **Post-migration config (this project):** [Rex-Sovol-Zero-Mainline](https://github.com/0dysseusRex/Rex-Sovol-Zero-Mainline)
- **Deep-dive knowledge base:** [sovol.lexfrei.dev](https://sovol.lexfrei.dev)
- **Official Klipper eddy docs:** [klipper3d.org — Eddy Probe](https://www.klipper3d.org/Eddy_Probe.html)

---

## Support this project

If this wiki or the Rex config helped you: **[ko-fi.com/0dysseusrex](https://ko-fi.com/0dysseusrex)**
