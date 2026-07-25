# Use bed load cell (probe_pressure) for axis twist nozzle-touch step.
#
# Replaces the paper-test ManualProbeHelper in AXIS_TWIST_COMPENSATION_CALIBRATE
# with RUN_PROBE_PRESSURE while keeping the eddy probe step at probe offsets.

from . import probe


class AxisTwistPressure:
    def __init__(self, config):
        self.printer = config.get_printer()
        self.printer.register_event_handler("klippy:connect",
                                            self._handle_connect)

    def _handle_connect(self):
        atc = self.printer.lookup_object('axis_twist_compensation', None)
        if atc is None:
            return
        self.printer.lookup_object('probe_pressure')
        calibrater = atc.calibrater
        calibrater._calibration = self._make_calibration(calibrater)
        calibrater.cmd_AXIS_TWIST_COMPENSATION_CALIBRATE_help = (
            "Axis twist calibration using eddy probe + bed load cell touch")

    def _make_calibration(self, calibrater):
        def _calibration(probe_points, nozzle_points, interval):
            gcmd = calibrater.gcmd
            gcmd.respond_info(
                "AXIS_TWIST_COMPENSATION_CALIBRATE: "
                "Probing point %d of %d (eddy + load cell)"
                % (calibrater.current_point_index + 1, len(probe_points)))

            calibrater._move_helper((None, None, calibrater.horizontal_move_z))
            calibrater._move_helper((
                probe_points[calibrater.current_point_index][0],
                probe_points[calibrater.current_point_index][1], None))

            pos = probe.run_single_probe(calibrater.probe, gcmd)
            calibrater.current_measured_z = pos.bed_z

            calibrater._move_helper((None, None, calibrater.horizontal_move_z))
            calibrater._move_helper(
                (nozzle_points[calibrater.current_point_index]))

            pressure = calibrater.printer.lookup_object('probe_pressure')
            calibrater.gcode.run_script_from_command('GET_PRESSURE_TARE')
            ppos = pressure.run_probe(gcmd)
            nozzle_bed_z = ppos[2]
            z_offset = calibrater.current_measured_z - nozzle_bed_z
            calibrater.results.append(z_offset)

            is_end = (calibrater.current_point_index
                      == len(probe_points) - 1)
            if is_end:
                calibrater._finalize_calibration()
            else:
                calibrater.current_point_index += 1
                _calibration(probe_points, nozzle_points, interval)

        return _calibration


def load_config(config):
    return AxisTwistPressure(config)
