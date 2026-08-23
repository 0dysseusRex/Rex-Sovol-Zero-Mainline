# Experimental eddy height calibration using bed load cell as Z reference.
#
# Replaces the paper-test step of PROBE_EDDY_CURRENT_CALIBRATE when a load cell
# is installed. Run after EDDY_CALIBRATE_PREP and LDC_CALIBRATE_DRIVE_CURRENT.
#
# Copyright (C) 2026 Rex-Sovol-Zero-Mainline contributors
# Licensed under the GNU GPLv3 (Klipper-derived)

import math


class _EddyCalHelper:
    """Mirrors EddyCalibrationTool helpers from mainline probe_eddy_current."""
    def __init__(self, eddy_probe, calibration, config_name):
        self.eddy_probe = eddy_probe
        self.calibration = calibration
        self.config_name = config_name

    def do_calibration_moves(self, move_speed):
        toolhead = self.eddy_probe.printer.lookup_object('toolhead')
        kin = toolhead.get_kinematics()
        move = toolhead.manual_move
        msgs = []
        is_finished = False

        def handle_batch(msg):
            if is_finished:
                return False
            msgs.append(msg)
            return True

        self.eddy_probe.add_client(handle_batch)
        toolhead.dwell(1.)
        self.calibration.note_z_calibration_start()
        max_z = 4.0
        samp_dist = 0.040
        req_zpos = [i * samp_dist for i in range(int(max_z / samp_dist) + 1)]
        start_pos = toolhead.get_position()
        times = []
        for zpos in req_zpos:
            hop_pos = list(start_pos)
            hop_pos[2] += zpos + 0.500
            move(hop_pos, move_speed)
            next_pos = list(start_pos)
            next_pos[2] += zpos
            move(next_pos, move_speed)
            start_query_time = toolhead.get_last_move_time() + 0.050
            end_query_time = start_query_time + 0.100
            toolhead.dwell(0.200)
            toolhead.flush_step_generation()
            kin_spos = {s.get_name(): s.get_commanded_position()
                        for s in kin.get_steppers()}
            kin_pos = kin.calc_position(kin_spos)
            times.append((start_query_time, end_query_time, kin_pos[2]))
        toolhead.dwell(1.0)
        toolhead.wait_moves()
        self.calibration.note_z_calibration_finish()
        is_finished = True
        cal = {}
        step = 0
        for msg in msgs:
            for query_time, freq, old_z in msg['data']:
                while step < len(times) and query_time > times[step][1]:
                    step += 1
                if step < len(times) and query_time >= times[step][0]:
                    cal.setdefault(times[step][2], []).append(freq)
        if len(cal) != len(times):
            raise self.eddy_probe.printer.command_error(
                "Failed calibration - incomplete sensor data")
        return cal

    @staticmethod
    def _median(values):
        values = sorted(values)
        n = len(values)
        if n % 2 == 0:
            return (values[n // 2 - 1] + values[n // 2]) / 2.0
        return values[n // 2]

    def calc_freqs(self, meas):
        positions = {}
        for pos, freqs in meas.items():
            count = len(freqs)
            freq_avg = float(sum(freqs)) / count
            mads = [abs(f - freq_avg) for f in freqs]
            mad = self._median(mads)
            positions[pos] = (freq_avg, mad, count)
        return positions

    def validate_calibration_data(self, positions, gcmd):
        last_freq = 40000000.
        last_pos = last_mad = .0
        filtered = []
        mad_hz_total = mad_mm_total = .0
        samples_count = 0
        for pos, (freq_avg, mad_hz, count) in sorted(positions.items()):
            if freq_avg > last_freq:
                gcmd.respond_info(
                    "Frequency stops decreasing at step %.3f" % (pos))
                break
            diff_mad = math.sqrt(last_mad**2 + mad_hz**2)
            freq_diff = last_freq - freq_avg
            last_freq = freq_avg
            if freq_diff < 2.5 * diff_mad:
                gcmd.respond_info(
                    "Frequency too noisy at step %.3f -> %.3f" % (
                        last_pos, pos))
                break
            last_mad = mad_hz
            delta_dist = pos - last_pos
            last_pos = pos
            mad_mm = mad_hz * delta_dist / freq_diff
            filtered.append((pos, freq_avg, mad_hz, mad_mm))
            mad_hz_total += mad_hz
            mad_mm_total += mad_mm
            samples_count += count
        if not filtered:
            raise gcmd.error("Failed calibration - No usable data")
        avg_mad = mad_hz_total / len(filtered)
        avg_mad_mm = mad_mm_total / len(filtered)
        gcmd.respond_info(
            "probe_eddy_current: noise %.6fmm, MAD_Hz=%.3f in %d queries"
            % (avg_mad_mm, avg_mad, samples_count))
        return filtered

    def save_calibration(self, z_freq_pairs, gcmd):
        gcmd.respond_info(
            "The SAVE_CONFIG command will update the printer config file\n"
            "and restart the printer.")
        cal_contents = []
        for i, (pos, freq) in enumerate(z_freq_pairs):
            if not i % 3:
                cal_contents.append('\n')
            cal_contents.append("%.6f:%.3f" % (pos, freq))
            cal_contents.append(',')
        cal_contents.pop()
        configfile = self.eddy_probe.printer.lookup_object('configfile')
        configfile.set(self.config_name, 'calibrate', ''.join(cal_contents))


class EddyLoadcellCalibrate:
    def __init__(self, config):
        self.printer = config.get_printer()
        self.chip_name = config.get('chip', 'eddy')
        self.lc_x = config.getfloat('loadcell_x', 25.)
        self.lc_y = config.getfloat('loadcell_y', 20.)
        self.bed_temp = config.getfloat('bed_temp', 80.)
        self.nozzle_temp = config.getfloat('nozzle_temp', 150.)
        self.lc_samples = config.getint('loadcell_samples', 5, minval=3)
        self.lc_tolerance = config.getfloat('loadcell_tolerance', 0.050,
                                              minval=0.)
        self.probe_speed = config.getfloat('probe_speed', 5., above=0.)
        self.lift_z = config.getfloat('lift_z', 5., above=0.)
        self.gcode = self.printer.lookup_object('gcode')
        self.gcode.register_command(
            'PROBE_EDDY_CURRENT_CALIBRATE_LOADCELL',
            self.cmd_PROBE_EDDY_CURRENT_CALIBRATE_LOADCELL,
            desc=self.cmd_PROBE_EDDY_CURRENT_CALIBRATE_LOADCELL_help)

    cmd_PROBE_EDDY_CURRENT_CALIBRATE_LOADCELL_help = (
        "Experimental: build eddy calibrate table from load cell nozzle touches")

    def _get_eddy(self, gcmd):
        chip = gcmd.get('CHIP', self.chip_name)
        name = 'probe_eddy_current %s' % (chip,)
        eddy = self.printer.lookup_object(name, None)
        if eddy is None:
            raise gcmd.error("Unknown probe_eddy_current chip '%s'" % (chip,))
        return eddy, name

    def _heat_and_wait(self, gcmd, bed_temp, nozzle_temp):
        gcmd.respond_info(
            "Heating bed to %.0fC and nozzle to %.0fC for calibration..."
            % (bed_temp, nozzle_temp))
        script = (
            "M140 S%.0f\n"
            "M104 S%.0f\n"
            "TEMPERATURE_WAIT SENSOR=heater_bed MINIMUM=%.0f\n"
            "TEMPERATURE_WAIT SENSOR=extruder MINIMUM=%.0f\n"
        ) % (bed_temp, nozzle_temp, bed_temp - 1., nozzle_temp - 1.)
        self.gcode.run_script_from_command(script)

    def _ensure_xy_homed(self):
        toolhead = self.printer.lookup_object('toolhead')
        curtime = self.printer.get_reactor().monotonic()
        homed = toolhead.get_status(curtime)['homed_axes']
        if 'x' not in homed or 'y' not in homed:
            self.gcode.run_script_from_command("G28 X Y")

    def _ensure_z_homed(self, gcmd):
        toolhead = self.printer.lookup_object('toolhead')
        curtime = self.printer.get_reactor().monotonic()
        if 'z' not in toolhead.get_status(curtime)['homed_axes']:
            raise gcmd.error(
                "Z axis not homed. Run EDDY_CALIBRATE_PREP first, then retry.")

    def _loadcell_touch_samples(self, gcmd, lc_x, lc_y, samples, tolerance,
                                speed, lift_z):
        probe_pressure = self.printer.lookup_object('probe_pressure')
        toolhead = self.printer.lookup_object('toolhead')
        move = toolhead.manual_move
        positions = []
        for i in range(samples):
            move([lc_x, lc_y, lift_z], speed)
            toolhead.wait_moves()
            self.gcode.run_script_from_command("GET_PRESSURE_TARE")
            touch_gcmd = self.gcode.create_gcode_command(
                "RUN_PROBE_PRESSURE", "RUN_PROBE_PRESSURE", {"SAMPLES": "1"})
            pos = probe_pressure.run_probe(touch_gcmd)
            positions.append(pos)
            z_vals = [p[2] for p in positions]
            spread = max(z_vals) - min(z_vals)
            gcmd.respond_info(
                "Load cell touch %d/%d: Z=%.4f (spread %.4f mm)"
                % (i + 1, samples, pos[2], spread))
        z_vals = [p[2] for p in positions]
        avg_z = sum(z_vals) / float(len(z_vals))
        spread = max(z_vals) - min(z_vals)
        if spread > tolerance:
            raise gcmd.error(
                "Load cell samples spread %.4f mm exceeds tolerance %.4f mm"
                % (spread, tolerance))
        return avg_z, spread

    def _position_for_eddy_cal(self, lc_x, lc_y, z_touch, probe_speed):
        toolhead = self.printer.lookup_object('toolhead')
        move = toolhead.manual_move
        probe = self.printer.lookup_object('probe')
        x_offset, y_offset, z_offset = probe.get_offsets()
        curpos = [lc_x, lc_y, z_touch]
        probe_calibrate_z = z_touch
        curpos[2] += 5.
        move(curpos, probe_speed)
        curpos[0] -= x_offset
        curpos[1] -= y_offset
        move(curpos, probe_speed)
        curpos[2] -= 5. - 0.050
        move(curpos, probe_speed)
        toolhead.wait_moves()
        return probe_calibrate_z

    def cmd_PROBE_EDDY_CURRENT_CALIBRATE_LOADCELL(self, gcmd):
        eddy, eddy_name = self._get_eddy(gcmd)
        calibration = eddy.calibration
        if len(getattr(calibration, 'cal_freqs', [])) > 2:
            gcmd.respond_info(
                "Note: existing eddy calibrate data will be replaced.")
        bed_temp = gcmd.get_float('BED_TEMP', self.bed_temp)
        nozzle_temp = gcmd.get_float('NOZZLE_TEMP', self.nozzle_temp)
        lc_x = gcmd.get_float('LC_X', self.lc_x)
        lc_y = gcmd.get_float('LC_Y', self.lc_y)
        lc_samples = gcmd.get_int('LC_SAMPLES', self.lc_samples, minval=3)
        lc_tolerance = gcmd.get_float('LC_TOLERANCE', self.lc_tolerance,
                                      minval=0.)
        probe_speed = gcmd.get_float('PROBE_SPEED', self.probe_speed, above=0.)
        lift_z = gcmd.get_float('LIFT_Z', self.lift_z, above=0.)

        self._ensure_xy_homed()
        self._ensure_z_homed(gcmd)
        self._heat_and_wait(gcmd, bed_temp, nozzle_temp)

        gcmd.respond_info(
            "Collecting %d load cell touches at X%.1f Y%.1f..."
            % (lc_samples, lc_x, lc_y))
        z_touch, spread = self._loadcell_touch_samples(
            gcmd, lc_x, lc_y, lc_samples, lc_tolerance, probe_speed, lift_z)
        gcmd.respond_info(
            "Load cell reference Z=%.4f mm (spread %.4f mm). "
            "Building eddy frequency map..." % (z_touch, spread))

        probe_calibrate_z = self._position_for_eddy_cal(
            lc_x, lc_y, z_touch, probe_speed)
        cal_helper = _EddyCalHelper(eddy, calibration, eddy_name)
        cal = cal_helper.do_calibration_moves(probe_speed)
        raw_positions = cal_helper.calc_freqs(cal)
        positions = {}
        for k in raw_positions:
            positions[k - probe_calibrate_z] = raw_positions[k]
        filtered = cal_helper.validate_calibration_data(positions, gcmd)
        if len(filtered) <= 8:
            raise gcmd.error("Failed calibration - No usable data")
        z_freq_pairs = [(pos, freq) for pos, freq, _, _ in filtered]
        cal_helper.save_calibration(z_freq_pairs, gcmd)


def load_config(config):
    return EddyLoadcellCalibrate(config)
