# CAN Bus and MCU Flashing

The Sovol Zero connects its MCUs (mainboard, toolhead, chamber) to the CB1 over **CAN bus** — a automotive-style network at **1 Mbit/s**.

Reference: **[asnajder/zero-config](https://github.com/asnajder/zero-config#set-up-can)** + **[vvuk Kalico wiki](https://github.com/vvuk/printer-configs/wiki/Kalico-on-the-Sovol-Zero)**

CAN primer: [Esoterical CAN bus guides](https://canbus.esoterical.online/Getting_Started.html)

---

## Why CAN matters

Unlike USB serial printers, the Zero's toolhead moves — CAN carries MCU traffic over flexible wiring. Each board has a **UUID** Klipper uses in `printer.cfg`:

```ini
[mcu]
canbus_uuid: abc123...

[mcu extruder_mcu]
canbus_uuid: def456...
```

**UUIDs change** when you flash Katapult/Klipper — you must update `printer.cfg` after migration.

---

## Step 1 — Enable CAN on CB1

### Check systemd-networkd

```bash
systemctl | grep systemd-networkd
```

If inactive:
```bash
sudo systemctl enable systemd-networkd
sudo systemctl start systemd-networkd
```

### udev rule (TX queue length)

Prevents CAN buffer stalls under load:

```bash
echo -e 'SUBSYSTEM=="net", ACTION=="change|add", KERNEL=="can*" ATTR{tx_queue_len}="128"' | sudo tee /etc/udev/rules.d/10-can.rules
```

Verify:
```bash
cat /etc/udev/rules.d/10-can.rules
```

### CAN bitrate config

```bash
echo -e "[Match]\nName=can*\n\n[CAN]\nBitRate=1M\n\n[Link]\nRequiredForOnline=no" | sudo tee /etc/systemd/network/25-can.network
```

**Why 1 Mbit?** Sovol hardware is fixed at 1 Mbps — wrong bitrate = no communication.

### Reboot

```bash
sudo reboot now
```

After reboot, check:
```bash
ip link show can0
```
Should show `UP`.

---

## Step 2 — Prepare for UUID discovery

Upload a **minimal** `printer.cfg` or comment out **all** MCU sections:

```ini
# [mcu]
# canbus_uuid: ...

# [mcu extruder_mcu]
# canbus_uuid: ...
```

**Why comment out?** Klipper won't start with wrong UUIDs — but Katapult query works independently.

Reboot after editing.

---

## Step 3 — Query Katapult / Klipper nodes

```bash
sudo service klipper stop
python3 ~/katapult/scripts/flashtool.py -i can0 -q
```

Example output (stock, before reflash):

```
Detected UUID: 0d1445047cdd, Application: Klipper
Detected UUID: 58a72bb93aa4, Application: Klipper
Detected UUID: 61755fe321ac, Application: Klipper
```

Save this output. Three UUIDs typical = mainboard + chamber + toolhead (order varies).

**No devices?** See [Troubleshooting](Troubleshooting#can--mcu).

---

## Step 4 — Flash mainboard

Two paths:

### Path A — Prebuilt bins (easier)

From [zero-config/bins](https://github.com/asnajder/zero-config/tree/main/bins):

1. **If still on Sovol stock bootloader:** flash Deployer over CAN:
   ```bash
   python3 ~/katapult/scripts/flashtool.py -f Deployer_Zero_Host_H743_128kb.bin -u <HOST_UUID>
   ```
   **Immediately** flash Klipper — deployer is temporary.

2. **If Katapult already installed (ST-LINK):** flash Klipper bin:
   ```bash
   python3 ~/katapult/scripts/flashtool.py -f Klipper_Zero_Host_H743_128kb.bin -u <UUID>
   ```
   Or via USB if in Katapult USB mode:
   ```bash
   python3 ~/katapult/scripts/flashtool.py -f Klipper_Zero_Host_H743_128kb.bin -d /dev/ttyACM0
   ```

### Path B — Build from source

**Katapult menuconfig (mainboard):**
```
Micro-controller: STM32H743
Clock: 25 MHz
Application offset: 128 KiB
Communication: USB on PA11/PA12
GPIO at startup: !PE11,!PB0
```

**Why `!PE11,!PB0`?** Prevents aux/exhaust fans running at 100% before Klipper starts ([vvuk wiki](https://github.com/vvuk/printer-configs/wiki/Kalico-on-the-Sovol-Zero)).

```bash
cd ~/katapult
make menuconfig
make clean && make -j4
python3 scripts/flashtool.py -i can0 -f ~/katapult/out/katapult.bin -u <UUID>
python3 scripts/flashtool.py -i can0 -q   # note NEW uuid
```

**Klipper menuconfig (mainboard):**
```
Micro-controller: STM32H743
Clock: 25 MHz crystal
Application offset: 128 KiB
Communication: USB to CAN bridge (USB PA11/PA12)
CAN bus: PB8/PB9
GPIO at startup: !PE11,!PB0
```

```bash
cd ~/klipper
make menuconfig
make clean && make -j4
python3 ~/katapult/scripts/flashtool.py -i can0 -f ~/klipper/out/klipper.bin -u <MAINBOARD_UUID>
python3 ~/katapult/scripts/flashtool.py -i can0 -q
```

Record the **new** mainboard UUID for `printer.cfg`.

---

## Step 5 — Flash toolhead and chamber (F103)

Same settings for both F103 boards:

**Katapult menuconfig:**
```
STM32F103
8 MHz crystal
8 KiB application offset
CAN bus PB8/PB9
```

**Klipper menuconfig:**
```
STM32F103
8 MHz crystal
8 KiB application offset
CAN bus PB8/PB9
```

Flash **one board at a time**:

```bash
sudo service klipper stop
python3 ~/katapult/scripts/flashtool.py -i can0 -q
python3 ~/katapult/scripts/flashtool.py -i can0 -f ~/klipper/out/klipper.bin -u <UUID>
python3 ~/katapult/scripts/flashtool.py -i can0 -q
```

**Lost track of which UUID is which?**
1. Power off printer.  
2. Disconnect toolhead CAN cable.  
3. Boot, query — remaining UUID = chamber (or mainboard if already done).  
4. Power off, reconnect toolhead, query again — new UUID = toolhead.

**Why 8 KiB offset?** Katapult occupies first 8 KiB of flash; Klipper app starts at `0x08002000`.

---

## Step 6 — Update printer.cfg UUIDs

Uncomment MCU sections and set new UUIDs:

```ini
[mcu]
canbus_uuid: <mainboard>

[mcu extruder_mcu]
canbus_uuid: <toolhead>
```

Chamber MCU section if your config has `hot_mcu` or similar — match zero-config or your backup.

```bash
sudo systemctl restart klipper
```

Check Mainsail — should show **Klipper ready** (may still have config errors until full config deployed).

---

## MCU update script (future updates)

[zero-config/update_klipper_mcus_svzero.sh](https://github.com/asnajder/zero-config/blob/main/update_klipper_mcus_svzero.sh) automates Klipper updates after initial migration.

```bash
chmod +x ~/update_klipper_mcus_svzero.sh
# Edit UUIDs inside script first
~/update_klipper_mcus_svzero.sh
```

---

## Next step

→ **[Configuration and Rex Repo](Configuration-and-Rex-Repo)** — deploy configs for eddy + load cell
