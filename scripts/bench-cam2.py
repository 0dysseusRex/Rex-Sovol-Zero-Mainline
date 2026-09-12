#!/usr/bin/env python3
"""Sweep every advertised v4l2 mode on Sovol Zero Cam 2 (DH Camera).

Prioritizes measured FPS. Stops crowsnest for the run so Cam 1 (MGS1) does
not steal USB bandwidth, then starts it again on exit.

Run on the printer:
    python3 bench-cam2.py
    python3 bench-cam2.py --keep-crowsnest-stopped
"""
from __future__ import annotations

import argparse
import csv
import os
import re
import shutil
import signal
import subprocess
import sys
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, Optional


DEVICE_NAME = "DH Camera"
STREAM_SECONDS = 4.0
STREAM_COUNT_CAP = 180
EXPOSURE_TIMES = (50, 100, 150, 200, 400)
TOP_MODES_FOR_EXPOSURE = 8


@dataclass(order=True)
class Mode:
    fmt: str
    width: int
    height: int
    fps: float
    interval: str = ""


@dataclass
class Result:
    mode: Mode
    measured_fps: float
    ok: bool
    notes: str = ""
    auto_exposure: str = ""
    exposure_dynamic_framerate: str = ""
    exposure_time_absolute: str = ""
    ustreamer_fps: Optional[float] = None


def run(
    cmd: list[str],
    timeout: Optional[float] = None,
    check: bool = False,
    text: bool = True,
) -> subprocess.CompletedProcess:
    return subprocess.run(
        cmd,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        timeout=timeout,
        check=check,
        text=text,
    )


def require_v4l2() -> str:
    path = shutil.which("v4l2-ctl")
    if not path:
        sys.exit("v4l2-ctl not found. Install v4l-utils on the CB1.")
    return path


def list_devices_text() -> str:
    return run(["v4l2-ctl", "--list-devices"]).stdout


def find_dh_camera_nodes(listing: str) -> list[str]:
    nodes: list[str] = []
    blocks = re.split(r"\n\s*\n", listing.strip())
    for block in blocks:
        if DEVICE_NAME.lower() not in block.lower() and "dh camera" not in block.lower():
            if not re.search(r"\bDH\b.*Camera", block, re.I):
                continue
        for m in re.finditer(r"(/dev/video\d+)", block):
            nodes.append(m.group(1))
    # Fallback: by-id path
    by_id = Path("/dev/v4l/by-id")
    if by_id.is_dir():
        for p in sorted(by_id.iterdir()):
            name = p.name.lower()
            if "dh_camera" in name or "dh-camera" in name or "dh_camera" in name:
                if p.name.endswith("-index0") or "index0" in p.name:
                    try:
                        nodes.insert(0, str(p.resolve()))
                    except OSError:
                        nodes.insert(0, str(p))
    seen = set()
    out = []
    for n in nodes:
        if n not in seen:
            seen.add(n)
            out.append(n)
    return out


def is_capture_node(dev: str) -> bool:
    info = run(["v4l2-ctl", "-d", dev, "--all"], timeout=10).stdout
    if "Video Capture" not in info:
        # Some UVC nodes still stream; require at least one pixelformat.
        fmts = run(["v4l2-ctl", "-d", dev, "--list-formats"], timeout=10).stdout
        return "VIDIOC_ENUM_FMT" in fmts and ("MJPG" in fmts or "YUYV" in fmts or "H264" in fmts)
    fmts = run(["v4l2-ctl", "-d", dev, "--list-formats"], timeout=10).stdout
    return bool(re.search(r"\['?[A-Z0-9]{4}'?\]|'[A-Z0-9]{4}'", fmts))


def parse_formats_ext(text: str) -> list[Mode]:
    modes: list[Mode] = []
    fmt = ""
    width = height = 0
    for line in text.splitlines():
        m = re.search(r"\[(\d+)\]:\s+'([A-Z0-9]{4})'", line)
        if m:
            fmt = m.group(2)
            continue
        m = re.search(r"Size:\s+Discrete\s+(\d+)x(\d+)", line)
        if m:
            width, height = int(m.group(1)), int(m.group(2))
            continue
        m = re.search(r"Size:\s+Stepwise\s+(\d+)x(\d+)\s+-\s+(\d+)x(\d+)", line)
        if m:
            # Sample min, a mid 16:9-ish, and max for stepwise devices.
            pairs = [
                (int(m.group(1)), int(m.group(2))),
                (int(m.group(3)), int(m.group(4))),
            ]
            mid_w = (int(m.group(1)) + int(m.group(3))) // 2
            mid_h = (int(m.group(2)) + int(m.group(4))) // 2
            pairs.append((mid_w, mid_h))
            # Also try common 12MP / 4K / 1080p if in range.
            for cand in ((4000, 3000), (3840, 2160), (1920, 1080), (1280, 720)):
                if int(m.group(1)) <= cand[0] <= int(m.group(3)) and int(m.group(2)) <= cand[1] <= int(m.group(4)):
                    pairs.append(cand)
            for w, h in pairs:
                width, height = w, h
            continue
        m = re.search(r"Interval:\s+Discrete\s+([0-9.]+)s\s+\(([0-9.]+)\s+fps\)", line)
        if m and fmt and width and height:
            fps = float(m.group(2))
            modes.append(Mode(fmt=fmt, width=width, height=height, fps=fps, interval=m.group(1)))
            continue
        m = re.search(r"Interval:\s+Stepwise\s+([0-9.]+)s\s+-\s+([0-9.]+)s", line)
        if m and fmt and width and height:
            lo, hi = float(m.group(1)), float(m.group(2))
            for iv in {lo, hi, (lo + hi) / 2}:
                if iv <= 0:
                    continue
                modes.append(Mode(fmt=fmt, width=width, height=height, fps=1.0 / iv, interval=f"{iv:.4f}"))
    # Dedup
    uniq = {}
    for mode in modes:
        key = (mode.fmt, mode.width, mode.height, round(mode.fps, 3))
        uniq[key] = mode
    return sorted(uniq.values(), key=lambda m: (-m.fps, -m.width * m.height, m.fmt))


def measure_v4l2_fps(dev: str, mode: Mode, extra_ctrl: Optional[str] = None) -> Result:
    set_fmt = [
        "v4l2-ctl",
        "-d",
        dev,
        f"--set-fmt-video=width={mode.width},height={mode.height},pixelformat={mode.fmt}",
        f"--set-parm={mode.fps:.3f}",
    ]
    if extra_ctrl:
        set_fmt.append(f"--set-ctrl={extra_ctrl}")
    prep = run(set_fmt, timeout=15)
    notes = ""
    if prep.returncode != 0:
        err = (prep.stderr or prep.stdout or "").strip().replace("\n", " ")
        return Result(mode, 0.0, False, notes=err[:240])

    count = max(30, min(STREAM_COUNT_CAP, int(mode.fps * STREAM_SECONDS) + 15))
    stream = run(
        [
            "v4l2-ctl",
            "-d",
            dev,
            f"--set-fmt-video=width={mode.width},height={mode.height},pixelformat={mode.fmt}",
            "--stream-mmap=4",
            f"--stream-count={count}",
            "--stream-to=/dev/null",
        ],
        timeout=STREAM_SECONDS + 20,
    )
    blob = (stream.stderr or "") + "\n" + (stream.stdout or "")
    fps_hits = [float(x) for x in re.findall(r"([0-9]+(?:\.[0-9]+)?)\s+fps", blob, re.I)]
    if not fps_hits:
        # Some builds print "fps: 12.34"
        fps_hits = [float(x) for x in re.findall(r"fps[:=]\s*([0-9]+(?:\.[0-9]+)?)", blob, re.I)]
    if stream.returncode != 0 and not fps_hits:
        err = blob.strip().replace("\n", " ")
        return Result(mode, 0.0, False, notes=(err[:240] or "stream failed"))
    measured = fps_hits[-1] if fps_hits else 0.0
    if abs(measured - mode.fps) > 1.0:
        notes = f"advertised {mode.fps:.2f}"
    return Result(mode, measured, measured > 0.1, notes=notes)


def read_ctrls(dev: str) -> dict[str, str]:
    text = run(["v4l2-ctl", "-d", dev, "--list-ctrls"], timeout=10).stdout
    ctrls = {}
    for line in text.splitlines():
        m = re.search(r"^\s*([a-z0-9_]+)\s+.*value=([-\d]+)", line)
        if m:
            ctrls[m.group(1)] = m.group(2)
    return ctrls


def restore_ctrls(dev: str, ctrls: dict[str, str], names: Iterable[str]) -> None:
    parts = [f"{n}={ctrls[n]}" for n in names if n in ctrls]
    if parts:
        run(["v4l2-ctl", "-d", dev, f"--set-ctrl={','.join(parts)}"], timeout=10)


def crowsnest_active() -> bool:
    p = run(["systemctl", "is-active", "crowsnest"], timeout=10)
    return p.stdout.strip() == "active"


def stop_crowsnest() -> bool:
    was = crowsnest_active()
    if was:
        print("Stopping crowsnest (Cam 1 off)…", flush=True)
        run(["sudo", "systemctl", "stop", "crowsnest"], timeout=30)
        time.sleep(1.5)
    return was


def start_crowsnest() -> None:
    print("Starting crowsnest (restore Cam 1)…", flush=True)
    run(["sudo", "systemctl", "start", "crowsnest"], timeout=30)


def score(res: Result) -> tuple:
    pixels = res.mode.width * res.mode.height
    # FPS first, then prefer MJPEG (what crowsnest/ustreamer wants), then pixels.
    fmt_bonus = 2 if res.mode.fmt in {"MJPG", "H264"} else 0
    return (res.measured_fps, fmt_bonus, pixels)


def recommend_block(dev: str, winner: Result, by_id: Optional[str]) -> str:
    device = by_id or dev
    fps = max(1, int(round(winner.measured_fps)))
    ctrl_parts = []
    if winner.auto_exposure:
        ctrl_parts.append(f"auto_exposure={winner.auto_exposure}")
    if winner.exposure_time_absolute:
        ctrl_parts.append(f"exposure_time_absolute={winner.exposure_time_absolute}")
    if winner.exposure_dynamic_framerate:
        ctrl_parts.append(f"exposure_dynamic_framerate={winner.exposure_dynamic_framerate}")
    # Keep FPS from collapsing in a dim chamber — same lesson as Cam 1.
    if "exposure_dynamic_framerate" not in "".join(ctrl_parts):
        ctrl_parts.append("exposure_dynamic_framerate=0")
    v4l2 = ",".join(ctrl_parts)
    fmt_flag = ""
    if winner.mode.fmt == "MJPG":
        fmt_flag = "custom_flags: --format=MJPEG --encoder=HW\n"
    elif winner.mode.fmt == "H264":
        fmt_flag = "custom_flags: --format=H264\n"
    return (
        f"[cam 2]\n"
        f"mode: ustreamer\n"
        f"port: 8081\n"
        f"device: {device}\n"
        f"resolution: {winner.mode.width}x{winner.mode.height}\n"
        f"max_fps: {fps}\n"
        f"{fmt_flag}"
        f"v4l2ctl: {v4l2}\n"
    )


def find_by_id(dev: str) -> Optional[str]:
    by_id = Path("/dev/v4l/by-id")
    if not by_id.is_dir():
        return None
    try:
        target = Path(dev).resolve()
    except OSError:
        target = Path(dev)
    for p in by_id.iterdir():
        try:
            if p.resolve() == target and "index0" in p.name:
                return str(p)
        except OSError:
            continue
    for p in by_id.iterdir():
        if "dh" in p.name.lower() and "index0" in p.name:
            return str(p)
    return None


def write_outputs(outdir: Path, results: list[Result], winner: Optional[Result], rec: str) -> None:
    outdir.mkdir(parents=True, exist_ok=True)
    csv_path = outdir / "cam2-results.csv"
    with csv_path.open("w", newline="") as f:
        w = csv.writer(f)
        w.writerow(
            [
                "format",
                "width",
                "height",
                "advertised_fps",
                "measured_fps",
                "ok",
                "auto_exposure",
                "exposure_dynamic_framerate",
                "exposure_time_absolute",
                "notes",
            ]
        )
        for r in results:
            w.writerow(
                [
                    r.mode.fmt,
                    r.mode.width,
                    r.mode.height,
                    f"{r.mode.fps:.3f}",
                    f"{r.measured_fps:.3f}",
                    int(r.ok),
                    r.auto_exposure,
                    r.exposure_dynamic_framerate,
                    r.exposure_time_absolute,
                    r.notes,
                ]
            )
    rec_path = outdir / "recommended-cam2.conf"
    rec_path.write_text(rec)
    summary = outdir / "SUMMARY.txt"
    lines = ["Cam 2 (DH Camera) FPS sweep — ranked by measured FPS\n", ""]
    ranked = sorted([r for r in results if r.ok], key=score, reverse=True)
    for i, r in enumerate(ranked[:25], 1):
        extra = ""
        if r.auto_exposure:
            extra = (
                f"  ae={r.auto_exposure} edf={r.exposure_dynamic_framerate} "
                f"exp={r.exposure_time_absolute}"
            )
        lines.append(
            f"{i:2d}. {r.mode.fmt} {r.mode.width}x{r.mode.height}  "
            f"measured {r.measured_fps:.2f} fps  (adv {r.mode.fps:.2f}){extra}"
        )
    if winner:
        lines += ["", "Winner (FPS first, then MJPEG/H264, then resolution):", rec]
    summary.write_text("\n".join(lines) + "\n")
    print(summary.read_text())
    print(f"Wrote {csv_path}")
    print(f"Wrote {rec_path}")


def main() -> int:
    global STREAM_SECONDS
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--device", help="Override /dev/videoN for DH Camera")
    ap.add_argument("--outdir", default=os.path.expanduser("~/printer_data/logs/cam2-bench"))
    ap.add_argument("--keep-crowsnest-stopped", action="store_true")
    ap.add_argument("--skip-exposure-sweep", action="store_true")
    ap.add_argument("--seconds", type=float, default=4.0)
    args = ap.parse_args()
    STREAM_SECONDS = args.seconds

    require_v4l2()
    listing = list_devices_text()
    print(listing)

    nodes = [args.device] if args.device else find_dh_camera_nodes(listing)
    if not nodes:
        sys.exit(
            "DH Camera not found in v4l2-ctl --list-devices. "
            "Is Cam 2 plugged in? Dump is printed above."
        )

    capture = None
    for n in nodes:
        if is_capture_node(n):
            capture = n
            break
    if not capture:
        capture = nodes[0]
    print(f"Using capture node: {capture}", flush=True)

    ext = run(["v4l2-ctl", "-d", capture, "--list-formats-ext"], timeout=15).stdout
    print(ext)
    modes = parse_formats_ext(ext)
    if not modes:
        sys.exit("No discrete/stepwise modes parsed from --list-formats-ext")
    print(f"Enumerated {len(modes)} format/size/fps combinations", flush=True)

    was_running = False
    restored = False

    def cleanup(*_a) -> None:
        nonlocal restored
        if restored:
            return
        restored = True
        if was_running and not args.keep_crowsnest_stopped:
            start_crowsnest()

    signal.signal(signal.SIGTERM, cleanup)
    signal.signal(signal.SIGINT, cleanup)

    was_running = stop_crowsnest()
    time.sleep(0.5)

    # Re-resolve device after crowsnest release.
    listing = list_devices_text()
    nodes = [args.device] if args.device else find_dh_camera_nodes(listing)
    for n in nodes:
        if is_capture_node(n):
            capture = n
            break

    orig = read_ctrls(capture)
    results: list[Result] = []
    try:
        for i, mode in enumerate(modes, 1):
            print(
                f"[{i}/{len(modes)}] {mode.fmt} {mode.width}x{mode.height} @{mode.fps:.2f} …",
                flush=True,
            )
            r = measure_v4l2_fps(capture, mode)
            print(f"    -> {r.measured_fps:.2f} fps  {r.notes}", flush=True)
            results.append(r)

        if not args.skip_exposure_sweep:
            top = sorted([r for r in results if r.ok], key=score, reverse=True)[:TOP_MODES_FOR_EXPOSURE]
            ctrl_names = set(orig)
            can_ae = "auto_exposure" in ctrl_names
            can_edf = "exposure_dynamic_framerate" in ctrl_names
            can_exp = "exposure_time_absolute" in ctrl_names
            if top and (can_ae or can_edf or can_exp):
                print(
                    f"Exposure sweep on top {len(top)} modes "
                    f"(auto_exposure / exposure_dynamic_framerate / exposure_time_absolute)…",
                    flush=True,
                )
                ae_values = []
                if can_ae:
                    ae_values = ["1", "3"]
                    # Keep current if it is something else (e.g. 0/2).
                    if orig.get("auto_exposure") not in ae_values:
                        ae_values.append(orig["auto_exposure"])
                else:
                    ae_values = [""]
                edf_values = ["0", "1"] if can_edf else [""]
                for base in top:
                    for ae in ae_values:
                        for edf in edf_values:
                            exp_list: list[str]
                            if ae == "1" and can_exp:
                                exp_list = [str(x) for x in EXPOSURE_TIMES]
                            else:
                                exp_list = [""]
                            for exp in exp_list:
                                parts = []
                                if ae:
                                    parts.append(f"auto_exposure={ae}")
                                if edf:
                                    parts.append(f"exposure_dynamic_framerate={edf}")
                                if exp:
                                    parts.append(f"exposure_time_absolute={exp}")
                                ctrl = ",".join(parts)
                                label = ctrl or "default"
                                print(
                                    f"  {base.mode.fmt} {base.mode.width}x{base.mode.height} "
                                    f"[{label}] …",
                                    flush=True,
                                )
                                r = measure_v4l2_fps(capture, base.mode, extra_ctrl=ctrl or None)
                                r.auto_exposure = ae
                                r.exposure_dynamic_framerate = edf
                                r.exposure_time_absolute = exp
                                r.notes = (r.notes + " exposure-sweep").strip()
                                print(f"    -> {r.measured_fps:.2f} fps", flush=True)
                                results.append(r)
                restore_ctrls(
                    capture,
                    orig,
                    ["auto_exposure", "exposure_dynamic_framerate", "exposure_time_absolute"],
                )

        ok = [r for r in results if r.ok]
        winner = max(ok, key=score) if ok else None
        rec = ""
        if winner:
            rec = recommend_block(capture, winner, find_by_id(capture))
            rec = (
                "#### Generated by scripts/bench-cam2.py — FPS-first sweep of DH Camera\n"
                f"#### Winner: {winner.mode.fmt} {winner.mode.width}x{winner.mode.height} "
                f"@ {winner.measured_fps:.2f} fps measured\n\n"
                + rec
            )
        write_outputs(Path(args.outdir), results, winner, rec)
        return 0 if winner else 2
    finally:
        cleanup()


if __name__ == "__main__":
    sys.exit(main())
