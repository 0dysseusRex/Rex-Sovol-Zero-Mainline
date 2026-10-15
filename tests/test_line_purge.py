"""Render the actual Klipper macro; assert properties of its emitted moves.

Run: python -m unittest discover -s tests -v (requires Jinja2).
LINE_PURGE_CONFIG may point at an older config to reproduce the regressions.
These are offline template/geometry checks, not printer motion tests.
"""
import ast
import configparser
import os
from pathlib import Path
import re
import unittest

import jinja2


CONFIG = Path(os.environ.get(
    "LINE_PURGE_CONFIG", Path(__file__).resolve().parents[1] / "config/line_purge.cfg"))


class MacroError(Exception):
    pass


def rectangle(x0, y0, x1, y1):
    return {"polygon": [[x0, y0], [x1, y0], [x1, y1], [x0, y1]]}


class LinePurgeTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.config = configparser.RawConfigParser()
        cls.config.read(CONFIG)
        # Klipper's delimiters, without extra Jinja extensions.
        cls.env = jinja2.Environment("{%", "%}", "{", "}")

    def render(self, objects=(), bounds=(0, 0, 153, 153), offset=(0, 0),
               temperature=200, macro="_LINE_PURGE", params=None, **settings):
        tuning = {
            key[len("variable_"):]: ast.literal_eval(value)
            for key, value in self.config["gcode_macro _KAMP_Settings"].items()
            if key.startswith("variable_")
        }
        tuning.update(settings)
        self.bounds, self.offset = bounds, offset
        self.tuning = tuning
        self.messages = []
        printer = {
            "gcode_macro _KAMP_Settings": tuning,
            "toolhead": {"max_velocity": 600,
                         "axis_minimum": dict(zip("xy", bounds[:2])),
                         "axis_maximum": dict(zip("xy", bounds[2:]))},
            "gcode_move": {"position": {"x": 70, "y": 70},
                           "gcode_position": {"x": 70-offset[0], "y": 70-offset[1]}},
            "extruder": {"temperature": temperature},
            "configfile": {"settings": {"extruder": {"min_extrude_temp": 170}}},
            "exclude_object": {"objects": objects},
        }

        def error(message):
            raise MacroError(message)

        def info(message):
            self.messages.append(message)
            return ""

        template = self.env.from_string(self.config["gcode_macro " + macro]["gcode"])
        output = template.render(printer=printer, params=params or {}, rawparams="",
                                 action_raise_error=error, action_respond_info=info)
        return [line.strip() for line in output.splitlines()
                if line.strip() and not line.lstrip().startswith("#")]

    def check_moves(self, lines):
        moves = [{key: float(value) for key, value in re.findall(
            r"([XYZEF])(-?\d+(?:\.\d*)?)", line)} for line in lines
            if re.match(r"G[01] ", line)]
        for move in moves:
            for i, axis in enumerate("XY"):
                if axis in move:
                    machine = move[axis] + self.offset[i]
                    self.assertGreaterEqual(machine, max(0, self.bounds[i]) - 1e-8)
                    self.assertLessEqual(machine, self.bounds[i+2] + 1e-8)
        xy = [m for m in moves if "X" in m or "Y" in m]
        self.assertEqual(len(xy), 3)  # approach, extrusion, wipe
        start, end, wipe = xy
        axis = "X" if "X" in end else "Y"
        self.assertAlmostEqual(end[axis] - start[axis], self.tuning["purge_amount"])
        self.assertAlmostEqual(wipe[axis] - end[axis], 10)
        self.assertEqual([m["E"] for m in moves if "E" in m],
                         [self.tuning["tip_distance"], self.tuning["purge_amount"],
                          -self.tuning["line_purge_retract"]])
        self.assertEqual(end["F"], self.tuning["flow_rate"] / 5 * 60)
        self.assertIn("SAVE_GCODE_STATE NAME=line_purge_state", lines)
        self.assertEqual(lines[-1], "RESTORE_GCODE_STATE NAME=line_purge_state MOVE=0")
        return start, end, wipe

    def test_right_edge_regression(self):
        start, end, wipe = self.check_moves(self.render([rectangle(140, 70, 150, 80)]))
        self.assertEqual((start["X"], end["X"], wipe["X"]), (95, 143, 153))

    def test_rear_edge_vertical_regression(self):
        start, end, wipe = self.check_moves(self.render(
            [rectangle(70, 10, 80, 150)], purge_margin=25))
        self.assertEqual(start["X"], 45)
        # Put the whole model near the rear, selecting the left side with a larger margin.
        start, end, wipe = self.check_moves(self.render(
            [rectangle(150, 140, 152, 150)], purge_margin=145))
        self.assertEqual((start["Y"], end["Y"], wipe["Y"]), (95, 143, 153))

    def test_centered_control(self):
        start, end, wipe = self.check_moves(self.render([rectangle(60, 70, 90, 90)]))
        self.assertEqual((start["X"], start["Y"], end["X"], wipe["X"]),
                         (51, 45, 99, 109))

    def test_left_side_control(self):
        start, end, wipe = self.check_moves(self.render([rectangle(70, 10, 90, 30)]))
        self.assertEqual((start["X"], start["Y"], end["Y"], wipe["Y"]), (45, 0, 48, 58))

    def test_front_margin_exactly_fits(self):
        start, _, _ = self.check_moves(self.render([rectangle(10, 25, 30, 40)]))
        self.assertEqual(start["Y"], 0)

    def test_fixed_fallback_control(self):
        start, end, wipe = self.check_moves(self.render())
        self.assertEqual((start["X"], start["Y"], end["X"], wipe["X"]), (15, 15, 63, 73))

    def test_fixed_fallback_clamped(self):
        for x, y in ((150, 200), (-50, -20)):
            with self.subTest(x=x, y=y):
                self.check_moves(self.render(fallback_x=x, fallback_y=y))

    def test_empty_or_missing_polygons_use_fallback(self):
        for objects in ([{}], [{"polygon": []}], [{}, {"polygon": []}]):
            with self.subTest(objects=objects):
                start, _, _ = self.check_moves(self.render(objects))
                self.assertEqual((start["X"], start["Y"]), (15, 15))

    def test_multiple_objects(self):
        start, _, _ = self.check_moves(self.render(
            [rectangle(5, 70, 15, 80), rectangle(140, 60, 150, 90)]))
        self.assertEqual(start["Y"], 35)

    def test_limits_and_coordinate_offsets(self):
        for bounds in ((-12, -5, 153, 153), (10, 12, 153, 153)):
            for offset in ((0, 0), (8, -6), (-8, 6)):
                with self.subTest(bounds=bounds, offset=offset):
                    self.check_moves(self.render([rectangle(140, 70, 150, 80)],
                                                 bounds=bounds, offset=offset))
                    self.check_moves(self.render(bounds=bounds, offset=offset,
                                                 fallback_x=-50, fallback_y=200))

    def test_exact_line_and_wipe_fit(self):
        _, _, wipe = self.check_moves(self.render(bounds=(0, 0, 58, 153)))
        self.assertEqual(wipe["X"], 58)

    def test_try_left_when_front_axis_too_short(self):
        start, _, _ = self.check_moves(self.render(
            [rectangle(30, 70, 40, 80)], bounds=(0, 0, 50, 153)))
        self.assertEqual(start["X"], 5)

    def test_no_room_rejected(self):
        for objects, bounds in (([], (0, 0, 57.9, 153)),
                                ([rectangle(70, 70, 80, 80)], (0, 0, 50, 50)),
                                ([rectangle(0, 0, 153, 153)], (0, 0, 153, 153)),
                                ([rectangle(10, 10, 140, 140)], (0, 0, 153, 153))):
            with self.subTest(objects=objects, bounds=bounds):
                with self.assertRaisesRegex(MacroError, "no room"):
                    self.render(objects, bounds=bounds)

    def test_invalid_length_or_margin(self):
        for setting in ({"purge_amount": 0}, {"purge_amount": -1}, {"purge_margin": -1}):
            with self.subTest(setting=setting), self.assertRaises(MacroError):
                self.render(**setting)

    def test_cold_skip_and_explicit_skip(self):
        self.assertEqual(self.render(temperature=100), [])
        self.assertIn("below min_extrude_temp", self.messages[0])
        self.assertEqual(self.render(macro="LINE_PURGE", params={"PURGE": "0"}),
                         ['RESPOND MSG="LINE_PURGE skipped"'])


if __name__ == "__main__":
    unittest.main()
