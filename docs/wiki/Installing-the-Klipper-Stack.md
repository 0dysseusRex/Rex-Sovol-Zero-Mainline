# Installing the Klipper Stack

**KIAUH** (Klipper Installation And Update Helper) installs Klipper, Moonraker, and Mainsail with menus instead of manual git clones.

Reference: **[asnajder/zero-config — Install Core Software](https://github.com/asnajder/zero-config#install-core-software)**

---

## Clone and run KIAUH

```bash
cd ~
git clone https://github.com/dw-0/kiauh.git
./kiauh/kiauh.sh
```

Text menu appears in SSH.

---

## Install in this order

| # | KIAUH option | Why |
|---|---|---|
| 1 | **Klipper** | Motion firmware host software |
| 2 | **Moonraker** | API server for web UIs |
| 3 | **Mainsail** | Web interface (recommended) |
| 4 | **Crowsnest** | Webcam streaming (optional) |

After each major install, reboot when KIAUH suggests:

```bash
sudo reboot now
```

**Why Moonraker?** Mainsail/Fluidd cannot talk to Klipper directly — Moonraker sits in between.

---

## Python dependencies for eddy probe

Eddy mesh uses scipy for processing:

```bash
~/klippy-env/bin/pip install scipy
```

**Why scipy?** Mainline `probe_eddy_current` bed mesh calibration requires it.

---

## Input Shaper (optional but recommended)

In KIAUH: **Advanced → Extra Dependencies → Input Shaper**

Or install accelerometer support later when running `SHAPER_CALIBRATE`.

---

## Install Katapult (bootloader tools)

Katapult flashed MCUs receive updates over CAN:

```bash
cd ~
git clone https://github.com/Arksine/katapult
```

No build needed yet — flashing scripts used later.

---

## Moonraker Timelapse (optional)

```bash
cd ~
git clone https://github.com/mainsail-crew/moonraker-timelapse.git
cd ~/moonraker-timelapse
make install
```

Add the `[include timelapse.cfg]` snippet the installer prints to `moonraker.conf`.

In Orca Slicer: add `TIMELAPSE_TAKE_FRAME` to **Before layer change G-code** if using timelapse.

---

## Verify services

```bash
sudo systemctl status klipper
sudo systemctl status moonraker
```

Klipper will **error** until MCU configs exist — expected at this stage.

Open Mainsail: `http://<printer-ip>` — should load even if Klipper is red/disconnected.

---

## Folder layout (after install)

```
~/klipper/                 Klipper source
~/moonraker/               Moonraker source
~/mainsail/                Mainsail static files
~/printer_data/
  config/                  YOUR printer.cfg lives here
  logs/                    klippy.log
  gcodes/                  print files
~/katapult/                Bootloader flasher
~/klippy-env/              Python virtual environment
```

**Why know these paths?** Every guide references `~/printer_data/config/printer.cfg`.

---

## Next step

→ **[CAN Bus and MCU Flashing](CAN-Bus-and-MCU-Flashing)** — mandatory before Klipper connects to motors
