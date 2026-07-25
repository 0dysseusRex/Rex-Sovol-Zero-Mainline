# Host Setup (CB1 / Armbian)

The **CB1** is the Linux computer inside the Zero's base. Replacing Sovol's image with **Armbian** gives you a standard, updatable Linux host for mainline Klipper.

Primary reference: **[asnajder/zero-config — Initial Setup](https://github.com/asnajder/zero-config#initial-setup)**

Alternative deep-dive: **[sovol.lexfrei.dev — OS layer](https://sovol.lexfrei.dev)**

---

## Why replace the host OS?

| Stock Sovol image | Armbian |
|---|---|
| Tied to Sovol Klipper fork | Install any Klipper via KIAUH |
| Hard to update cleanly | Standard `apt` packages |
| Unknown long-term support | Active Armbian community |

Your configs are backed up separately — the eMMC flash **wipes** the old OS.

---

## Remove the eMMC module

1. **Unplug printer** from wall.  
2. Remove base cover (Sovol service panel).  
3. Locate CB1 board — eMMC is a small removable module (looks like micro SD but **not** compatible with SD slots).  
4. Push spring clip, slide eMMC out.  

**Why remove it?** USB eMMC readers can't attach while inside the printer.

---

## Flash Armbian with Armbian Imager

1. Insert eMMC into **USB eMMC reader** on your PC.  
2. Open [Armbian Imager](https://www.armbian.com/download/).  
3. Select:
   - **Manufacturer:** BTT (BIQU)  
   - **Board:** BigTreeTech CB1  
   - **Image:** Minimal → **Armbian Trixie CLI** (or current stable minimal)  
4. Choose the eMMC drive — **triple-check drive letter** (wrong drive wipes your PC disk).  
5. Flash + verify.

### eMMC size note

| Module | Guidance |
|---|---|
| **32 GB** (recommended) | Works out of the box per [zero-config](https://github.com/asnajder/zero-config#prerequisites) |
| **Stock 8 GB** | May fail or corrupt without [lexfrei's 40 MHz eMMC overlay](https://sovol.lexfrei.dev) — beginners should buy 32 GB |

---

## Edit `armbianEnv.txt` (before first boot in printer)

After flashing, Windows may show a small **boot partition**. Open `armbianEnv.txt`.

1. **Copy** the `rootdev=UUID=...` line from the file (unique per flash).  
2. Replace file contents with (keep **your** UUID):

```ini
verbosity=1
bootlogo=false
console=both
disp_mode=1920x1080p60
overlay_prefix=sun50i-h616
fdtfile=sun50i-h616-bigtreetech-cb1-emmc.dtb
rootdev=UUID=YOUR_COPIED_UUID_HERE
rootfstype=ext4
overlays=sun50i-h6-uart3 sun50i-h616-ws2812 sun50i-h616-spidev1_1
usbstoragequirks=0x2537:0x1066:u,0x2537:0x1068:u
```

**Why these overlays?** They enable UART, WS2812 LEDs, and SPI devices the Zero hardware expects on CB1.

**Optional (8 GB eMMC only):** add `user_overlays=sovol-zero-emmc-40mhz` — see lexfrei docs.

---

## First boot in printer

1. Reinstall eMMC on CB1.  
2. Connect **Ethernet** to router (recommended).  
3. Power on printer.  
4. Wait 2–5 minutes for first boot (longer first time).

### Login options

| Method | Steps |
|---|---|
| **SSH** | Find IP on router → `ssh root@IP` → password `1234` |
| **HDMI + keyboard** | Connect monitor to CB1 HDMI |

Armbian forces:
1. New **root** password  
2. Create a **normal user** (remember this name — e.g. `rex`)  
3. Optional prompts — for Wi-Fi, choose **No** now (configure later via `sudo armbian-config`)

---

## Fix boot delay (important)

Without this, boot can hang 2+ minutes waiting for network:

```bash
sudo systemctl disable systemd-networkd-wait-online.service
sudo systemctl mask systemd-networkd-wait-online.service
```

Credit: [Rappetor issue #229](https://github.com/Rappetor/Sovol-SV08-Mainline/issues/229#issuecomment-3765616568)

**Why:** Klipper/Moonraker don't need "online" network at boot — this wait is unnecessary on CB1.

---

## Install base packages

```bash
sudo apt update
sudo apt install git python3-pip python3-serial -y
```

---

## Wi-Fi (optional, after Ethernet works)

```bash
sudo armbian-config
```
Network → Wi-Fi → enter SSID/password.

---

## Expand partition (if needed)

First Armbian boot usually auto-expands. If disk shows small size:

```bash
sudo armbian-config
```
System → Storage → expand root partition.

---

## Verify before KIAUH

```bash
uname -a          # Should show aarch64, Armbian
hostname -I       # Your IP
free -h           # RAM check
df -h /           # Disk space — want several GB free
```

---

## Next step

→ **[Installing the Klipper Stack](Installing-the-Klipper-Stack)** — KIAUH, Katapult, Moonraker
