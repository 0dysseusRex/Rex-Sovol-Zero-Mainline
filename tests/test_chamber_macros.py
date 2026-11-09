"""Run the chamber macros through a small Klipper-like executor.

Run: python -m unittest discover -s tests -v (requires Jinja2).
CHAMBER_CONFIG_DIR may point at an older config/ to reproduce the regressions.
These are offline macro checks, not printer tests: temperatures are set by
the test, and fans and heaters only record their last command.
"""
import ast
import configparser
import os
from pathlib import Path
import re
import unittest

import jinja2


CONFIG_DIR = Path(os.environ.get(
    "CHAMBER_CONFIG_DIR", Path(__file__).resolve().parents[1] / "config"))


class MacroError(Exception):
    pass


class Printer:
    """Just enough of Klipper's gcode_macro, delayed_gcode and save_variables."""

    def __init__(self, files=("chamber_macros.cfg", "pid_macros.cfg"), heater=False):
        # Klipper's own parser settings (klippy/configfile.py).
        config = configparser.RawConfigParser(strict=False, inline_comment_prefixes=(";", "#"))
        for name in files:
            config.read(CONFIG_DIR / name, encoding="utf-8")
        self.env = jinja2.Environment("{%", "%}", "{", "}")
        self.macros, self.delayed = {}, {}
        self.status = {
            "save_variables": {"variables": {}},
            "temperature_sensor chamber_temp": {"temperature": 25.0},
            "fan_generic exhaust_fan": {"speed": 0.0, "rpm": None},
            "fan_generic part_cooling_fan": {"speed": 0.0},
            "heater_bed": {"target": 0.0, "temperature": 25.0},
            "extruder": {"target": 0.0, "temperature": 25.0},
            "idle_timeout": {"state": "Ready"},
        }
        if heater:
            self.status["heater_generic chamber_heater"] = {"target": 0.0}
        for section in config.sections():
            kind, _, name = section.partition(" ")
            if kind == "gcode_macro":
                self.macros[name.upper()] = self.env.from_string(config[section]["gcode"])
                self.status[section] = {
                    key[len("variable_"):]: ast.literal_eval(value)
                    for key, value in config[section].items() if key.startswith("variable_")}
            elif kind == "delayed_gcode":
                self.delayed[name] = config[section]["gcode"]
        self.now, self.timers, self.active = 0.0, {}, []
        self.saves, self.messages, self.log, self.waits = 0, [], [], []

    @property
    def state(self):
        return self.status["gcode_macro _CH_STATE"]

    @property
    def saved(self):
        return self.status["save_variables"]["variables"]

    def run(self, script):
        for line in script.splitlines():
            line = line.strip()
            if line and not line.startswith("#"):
                self.command(line)

    def command(self, line):
        self.log.append(line)
        cmd, _, rest = line.partition(" ")
        cmd = cmd.upper()
        if re.fullmatch(r"[GM]\d+", cmd):
            params = {word[0].upper(): word[1:] for word in rest.split()}
        else:
            params = {key.upper(): value.strip('"')
                      for key, value in re.findall(r'(\w+)=("[^"]*"|\S+)', rest)}
        if cmd in self.macros:
            if cmd in self.active:
                raise MacroError("Macro %s called recursively" % cmd)
            self.active.append(cmd)
            try:
                self.run(self.macros[cmd].render(
                    printer=self.status, params=params, rawparams=rest))
            finally:
                self.active.pop()
        elif cmd == "SET_GCODE_VARIABLE":
            variables = self.status["gcode_macro " + params["MACRO"]]
            if params["VARIABLE"] not in variables:
                raise MacroError("Unknown gcode_macro variable '%s'" % params["VARIABLE"])
            variables[params["VARIABLE"]] = ast.literal_eval(params["VALUE"])
        elif cmd == "SAVE_VARIABLE":
            self.saved[params["VARIABLE"]] = ast.literal_eval(params["VALUE"])
            self.saves += 1
        elif cmd == "UPDATE_DELAYED_GCODE":
            duration = float(params["DURATION"])
            if duration:
                self.timers[params["ID"]] = self.now + duration
            else:
                self.timers.pop(params["ID"], None)
        elif cmd == "SET_FAN_SPEED":
            self.status["fan_generic " + params["FAN"]]["speed"] = float(params["SPEED"])
        elif cmd == "SET_HEATER_TEMPERATURE":
            self.status["heater_generic " + params["HEATER"]]["target"] = float(params["TARGET"])
        elif cmd == "M140":
            self.status["heater_bed"]["target"] = float(params.get("S", 0))
        elif cmd == "M104":
            self.status["extruder"]["target"] = float(params.get("S", 0))
        elif cmd == "RESPOND":
            self.messages.append(params.get("MSG", ""))
        elif cmd == "TEMPERATURE_WAIT":
            # The wait holds the gcode mutex, so no timer fires during it:
            # record what the printer holds for its whole length.
            heater = self.status.get("heater_generic chamber_heater")
            self.waits.append({
                "params": params,
                "exhaust": self.status["fan_generic exhaust_fan"]["speed"],
                "part_fan": self.status["fan_generic part_cooling_fan"]["speed"],
                "hotend": self.status["extruder"]["target"],
                "heater": heater["target"] if heater else None,
                "timer": "CHAMBER_TIMER" in self.timers,
            })
        elif cmd == "M400":
            pass
        else:
            raise MacroError("Unknown command: " + line)

    def advance(self, seconds):
        """Fire due delayed_gcode timers in order, as the reactor would."""
        end = self.now + seconds
        while self.timers and min(self.timers.values()) <= end:
            name = min(self.timers, key=self.timers.get)
            self.now = self.timers.pop(name)
            self.run(self.delayed[name])
        self.now = end

    def passes(self):
        return sum(1 for line in self.log if line == "CHAMBER_LOOP")

    def heat(self, chamber):
        self.status["temperature_sensor chamber_temp"]["temperature"] = chamber


class ChamberLoopTest(unittest.TestCase):
    def primed_print(self, heater=False):
        """M141 S40 during a print, then the chamber reaches its target."""
        printer = Printer(heater=heater)
        printer.command("M140 S100")
        printer.command("M141 S40")
        printer.heat(40.0)
        printer.advance(60)                 # primes within 1 C of target
        self.assertIn("CHAMBER_TIMER", printer.timers)
        return printer

    def test_auto_off_stops_after_the_print(self):
        printer = self.primed_print()
        printer.command("M140 S0")          # END_PRINT's TURN_OFF_HEATERS
        printer.heat(36.5)                  # 3.5 C under target
        printer.advance(60)
        self.assertNotIn("CHAMBER_TIMER", printer.timers)
        self.assertEqual(printer.status["fan_generic exhaust_fan"]["speed"], 0.0)
        passes = printer.passes()
        printer.advance(3600)
        self.assertEqual(printer.passes(), passes)

    def test_auto_off_when_target_was_never_reached(self):
        printer = Printer()
        printer.command("M140 S100")
        printer.command("M141 S40")
        printer.heat(30.0)                  # never within 1 C, so never primed
        printer.advance(600)
        self.assertIn("CHAMBER_TIMER", printer.timers)
        printer.command("M140 S0")
        printer.advance(60)
        self.assertNotIn("CHAMBER_TIMER", printer.timers)

    def test_dip_while_bed_heats_keeps_running(self):
        printer = self.primed_print()
        printer.heat(30.0)                  # door opened mid-print
        printer.advance(120)
        self.assertIn("CHAMBER_TIMER", printer.timers)

    def test_dip_keeps_chamber_heater_on(self):
        printer = self.primed_print(heater=True)
        self.assertEqual(printer.status["heater_generic chamber_heater"]["target"], 40.0)
        printer.command("M140 S0")          # the heater alone holds the chamber
        printer.heat(30.0)
        printer.advance(120)
        self.assertEqual(printer.status["heater_generic chamber_heater"]["target"], 40.0)
        self.assertIn("CHAMBER_TIMER", printer.timers)

    def test_heater_off_then_auto_off(self):
        printer = self.primed_print(heater=True)
        printer.command("M140 S0")
        printer.command("SET_HEATER_TEMPERATURE HEATER=chamber_heater TARGET=0")
        printer.heat(36.0)
        printer.advance(60)
        self.assertNotIn("CHAMBER_TIMER", printer.timers)

    def test_loop_saves_nothing(self):
        printer = self.primed_print()
        saves = printer.saves
        for chamber in (41.0, 43.0, 45.0, 44.0):
            printer.heat(chamber)
            printer.advance(60)
        self.assertEqual(printer.saves, saves)
        self.assertGreater(printer.status["fan_generic exhaust_fan"]["speed"], 0.0)

    def test_config_fallbacks_match_loop_defaults(self):
        # The gains CHAMBER_LOOP has always used when nothing is saved.
        loop = {"kp": 0.15, "ki": 0.020, "minfan": 0.15, "maxfan": 1.0, "i_max": 0.6}
        printer = Printer()
        printer.command("CHAMBER_CONFIG TARGET=40")
        self.assertEqual(printer.saved["ch_target"], 40.0)
        self.assertEqual({key: printer.saved["ch_" + key] for key in loop}, loop)

    def test_config_keeps_saved_values(self):
        printer = Printer()
        printer.command("CHAMBER_CONFIG KP=0.25 KI=0.01")
        printer.command("CHAMBER_CONFIG TARGET=45")
        self.assertEqual((printer.saved["ch_kp"], printer.saved["ch_ki"]), (0.25, 0.01))

    def test_pid_chamber_reports_what_it_saved(self):
        printer = Printer()
        printer.command("PID_CHAMBER TARGET=40")
        saved = printer.saved
        self.assertIn("KP=%s KI=%s MINFAN=%s MAXFAN=%s" % (
            saved["ch_kp"], saved["ch_ki"], saved["ch_minfan"], saved["ch_maxfan"]),
            printer.messages[0])

    def test_off_and_reset(self):
        printer = self.primed_print()
        printer.heat(44.0)
        printer.advance(60)
        self.assertNotEqual(printer.state["integral"], 0.0)
        printer.command("CH_RESET_I")
        self.assertEqual(printer.state["integral"], 0.0)
        printer.command("M141 S0")
        self.assertNotIn("CHAMBER_TIMER", printer.timers)
        self.assertEqual(printer.state["running"], 0)

    def test_m191_heat_up_stops_the_exhaust_for_the_wait(self):
        printer = self.primed_print()
        printer.heat(44.0)
        printer.advance(60)                 # the loop opens the exhaust
        self.assertGreater(printer.status["fan_generic exhaust_fan"]["speed"], 0.0)
        printer.heat(30.0)                  # the next job starts colder
        printer.command("M191 S45")
        wait = printer.waits[-1]
        self.assertEqual(wait["exhaust"], 0.0)
        self.assertFalse(wait["timer"])
        self.assertEqual(printer.state["running"], 1)
        self.assertIn("CHAMBER_TIMER", printer.timers)

    def test_m191_keeps_the_chamber_heater_for_the_wait(self):
        printer = Printer(heater=True)
        printer.command("M140 S100")
        printer.command("M191 S45")
        self.assertEqual(printer.waits[-1]["heater"], 45.0)
        self.assertEqual(printer.status["heater_generic chamber_heater"]["target"], 45.0)

    def test_m191_range_wait_leaves_the_loop_running(self):
        printer = self.primed_print()
        printer.command("M191 R40")
        self.assertIn("MAXIMUM", printer.waits[-1]["params"])
        self.assertTrue(printer.waits[-1]["timer"])

    def test_m141_alone_does_not_stir(self):
        printer = Printer()
        printer.command("M140 S100")
        printer.command("M141 S40")
        self.assertEqual(printer.status["fan_generic part_cooling_fan"]["speed"], 0.0)
        self.assertEqual(printer.status["extruder"]["target"], 0.0)

    def test_m191_stirs_only_while_waiting(self):
        printer = Printer()
        printer.command("M140 S100")
        printer.command("M191 S45")
        self.assertEqual((printer.waits[-1]["part_fan"], printer.waits[-1]["hotend"]), (1.0, 46.0))
        self.assertEqual(printer.status["fan_generic part_cooling_fan"]["speed"], 0.0)

    def test_m191_leaves_a_running_part_fan_alone(self):
        printer = Printer()
        printer.command("SET_FAN_SPEED FAN=part_cooling_fan SPEED=0.5")
        printer.command("M191 S45")
        self.assertEqual(printer.waits[-1]["part_fan"], 0.5)
        self.assertEqual(printer.status["fan_generic part_cooling_fan"]["speed"], 0.5)

    def print_start_chamber_lines(self, rawparams):
        """PRINT_START reads only its params, so rendering it shows what it sends."""
        config = configparser.RawConfigParser(strict=False, inline_comment_prefixes=(";", "#"))
        config.read(CONFIG_DIR / "Macro.cfg", encoding="utf-8")
        params = {key.upper(): value for key, value in re.findall(r"(\w+)=(\S+)", rawparams)}
        out = jinja2.Environment("{%", "%}", "{", "}").from_string(
            config["gcode_macro PRINT_START"]["gcode"]).render(params=params, rawparams=rawparams)
        return [line.strip() for line in out.splitlines() if re.match(r"\s*M1[49]1\b", line)]

    def test_print_start_chamber_zero_turns_control_off(self):
        self.assertEqual(self.print_start_chamber_lines("BED=60 HOTEND=220 CHAMBER=0"), ["M141 S0"])

    def test_print_start_without_chamber_leaves_control_alone(self):
        self.assertEqual(self.print_start_chamber_lines("BED=60 HOTEND=220"), [])

    def test_print_start_chamber_target_heats_and_waits(self):
        self.assertEqual(self.print_start_chamber_lines("BED=100 HOTEND=250 CHAMBER=40"),
                         ["M141 S40.0", "M191 S40.0"])

    def test_status_reports_state(self):
        printer = self.primed_print()
        printer.command("CH_STATUS")
        self.assertRegex(printer.messages[-1], r"^running=1 T=40\.0 A=40\.0 P=0\.000 I=0\.000 duty=0% rpm=n/a$")


if __name__ == "__main__":
    unittest.main()
