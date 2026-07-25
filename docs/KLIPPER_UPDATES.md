# Klipper updates

## Keep the Klipper tree clean

After setup, your `~/klipper` repo should have:

- **No modified tracked files** — never patch `bed_mesh.py`, `src/Makefile`, etc. for eddy-ng on mainline
- **Untracked extras only** — `probe_pressure.py` (and optional third-party extras like ShakeTune)

Check status:

```bash
cd ~/klipper
git status
```

Good output:

```
?? klippy/extras/probe_pressure.py
```

Bad output (blocks easy updates):

```
 M klippy/extras/bed_mesh.py
 M src/Makefile
```

If you have modified tracked files, restore them:

```bash
git restore klippy/extras/bed_mesh.py src/Makefile
```

## Update procedure

```bash
cd ~/klipper
git pull --ff-only
sudo systemctl restart klipper
```

Moonraker may show **dirty** if untracked extras exist (`probe_pressure.py`). That is normal and does not block `git pull`.

## Do not install eddy-ng on mainline

If you use `[probe_eddy_current eddy]` (this repo's path), you do **not** need:

- `~/eddy-ng/` clone
- `probe_eddy_ng.py`, `ldc1612_ng.py`, `sensor_ldc1612_ng.c`
- Patches to `bed_mesh.py` or `src/Makefile`

Remove any of the above if present from an old hybrid setup.

## MCU firmware

This Klipper update (707 → 708) changed host Python/C helper code only. **No MCU reflash required** unless a future update changes MCU firmware for your boards.
