# SSH and Networking Basics

**SSH** (Secure Shell) lets you type Linux commands on the CB1 from your PC. You need it for almost every step after Armbian is installed.

This page assumes **Windows**. Mac/Linux users can use the built-in Terminal instead of PuTTY.

---

## Find your printer's IP address

The CB1 must be on the **same network** as your PC (usually your home Wi-Fi or router).

### Method 1 — Router admin page (easiest)

1. Open your router's web interface (often `192.168.1.1` or `192.168.0.1`).  
2. Look for **Connected devices** / **DHCP clients**.  
3. Find a device named something like:
   - `bigtreetech-cb1`
   - `SPI-XI` (stock Sovol hostname)
   - `sovol-zero` (if you renamed it)

Write down the IP, e.g. `192.168.11.186` (Mainsail: `http://192.168.11.186/`).

**Why:** SSH needs an IP address — there is no "search" button in PuTTY.

### Method 2 — Stock Sovol display

On OEM firmware, the touchscreen may show network info under settings (varies by version).

### Method 3 — Ethernet + monitor (Armbian first boot)

Plug HDMI + keyboard into the CB1. After login:
```bash
hostname -I
```
The first number is your IP.

### Method 4 — mDNS (sometimes works)

```bash
ping bigtreetech-cb1.local
```
This only works if your router supports mDNS — don't rely on it alone.

---

## Default usernames and passwords

Credentials depend on **what is installed today**:

| Setup | Username | Password | When |
|---|---|---|---|
| **Stock Sovol OEM** | `sovol` | `sovol` | Factory firmware |
| **BTT CB1 image** (some guides) | `biqu` | `biqu` | Pre-built CB1 images |
| **Fresh Armbian — first login** | `root` | `1234` | Forces password change + new user creation |
| **Your printer after Armbian setup** | *(you chose it)* | *(you chose it)* | e.g. `rex` — **not a universal default** |

After Armbian first boot you create your own user (e.g. `rex`). **Write down the username and password you choose.**

---

## Connect with PuTTY (Windows)

1. Download and open **PuTTY**.  
2. **Host Name:** `192.168.11.186` (your IP)  
3. **Port:** `22`  
4. **Connection type:** SSH  
5. Click **Open**.  
6. Accept the security warning (first connect only — normal).  
7. Login: `yourusername` → Enter → password → Enter  

Password **will not show** while typing — that is normal.

**Why SSH?** The Klipper host is a Linux computer without a desktop. SSH is the standard remote control method.

---

## Connect from PowerShell (Windows 10/11)

```powershell
ssh yourusername@192.168.11.186
```

---

## Copy files with WinSCP

1. Open **WinSCP** → New Session  
2. **File protocol:** SCP  
3. **Host, username, password** — same as SSH  
4. Connect  

Left side = your PC. Right side = printer.

Common paths on the printer:
| Path | Contents |
|---|---|
| `~/printer_data/config/` | Klipper configuration |
| `~/klipper/` | Klipper source |
| `~/katapult/` | Katapult bootloader source |
| `~/printer_data/gcodes/` | G-code files |

**Why WinSCP?** Easier than typing long commands when uploading config files or downloading logs.

---

## Essential commands (copy/paste reference)

Run these **after** SSH login:

```bash
# Where am I?
whoami
hostname -I

# Is Klipper running?
sudo systemctl status klipper

# Is Moonraker running?
sudo systemctl status moonraker

# View live Klipper log (Ctrl+C to exit)
tail -f ~/printer_data/logs/klippy.log

# Restart Klipper after config change
sudo systemctl restart klipper

# Full firmware restart (MCUs reconnect)
# Run from Mainsail console or:
sudo systemctl restart klipper

# Edit a config file (nano editor)
nano ~/printer_data/config/printer.cfg
# Save: Ctrl+O, Enter. Quit: Ctrl+X

# List config files
ls ~/printer_data/config/
```

### `sudo` — why it asks for your password again

`sudo` means "run as administrator." Klipper service control requires it. Enter **your user password**, not root's.

---

## Finding errors when Klipper won't start

```bash
tail -n 80 ~/printer_data/logs/klippy.log
```

Look for lines containing `error` or `Config error`.

Common pattern:
```
Include file 'sovol_eddy.cfg' does not exist
```
→ File missing from `~/printer_data/config/` — copy it from the Rex repo.

---

## Wi-Fi on Armbian (after first boot)

**Do not** configure Wi-Fi during Armbian's first-login wizard if you plan to follow zero-config (it can complicate setup). Use Ethernet first, then:

```bash
sudo armbian-config
```
Navigate to **Network** → configure Wi-Fi.

**Why Ethernet first?** SSH over Wi-Fi during flashing/recovery is fragile; a dropped connection mid-flash is stressful.

---

## Firewall / "Connection refused"

| Symptom | Likely cause | Fix |
|---|---|---|
| `Connection timed out` | Wrong IP or printer offline | Check router, ping IP, verify Ethernet cable |
| `Connection refused` port 22 | SSH not running or wrong device | Verify you're connecting to CB1, not router |
| `Permission denied` | Wrong password | Caps Lock; try OEM `sovol/sovol` on stock firmware |
| Host key changed warning | Re-flashed OS (expected) | PuTTY: delete old session key or click Yes |

---

## Next step

→ **[Backup and Recovery](Backup-and-Recovery)** — save firmware before flashing  
→ **[Host Setup (CB1 / Armbian)](Host-Setup-CB1-Armbian)** — if you can already SSH in and want to flash Armbian
