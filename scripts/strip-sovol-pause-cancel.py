#!/usr/bin/env python3
"""Remove Sovol OEM PAUSE/CANCEL/END_PRINT from Macro.cfg."""
from pathlib import Path

p = Path.home() / "printer_data/config/Macro.cfg"
lines = p.read_text().splitlines(keepends=True)
out = []
skip = False
repl = (
    "# PAUSE / CANCEL_PRINT / END_PRINT — see pause_cancel_macros.cfg\n"
    "# (removed Sovol OEM duplicates to avoid double-park on pause/cancel)\n\n"
)
inserted = False
for line in lines:
    if line.startswith("[gcode_macro END_PRINT]"):
        skip = True
        if not inserted:
            out.append(repl)
            inserted = True
        continue
    if skip and line.startswith("[delayed_gcode _resume_wait]"):
        skip = False
        out.append(line)
        continue
    if not skip:
        out.append(line)
if not inserted:
    raise SystemExit("END_PRINT block not found")
p.write_text("".join(out))
print("OK")
