import math
try:
    from .filters import (
        OneEuroFilter,
        MadgwickFilter,
        AutoZeroBiasCalibrator,
        apply_deadzone_filter,
    )
    from .config import (
        GYRO_SCALE_RAD_PER_SEC,
        ACCEL_SCALE_G,
        DEFAULT_BASE_SENSITIVITY,
        DEFAULT_DEADZONE_THRESHOLD,
        DEFAULT_MIN_CUTOFF_FREQUENCY,
        DEFAULT_SPEED_COEFFICIENT,
        DEFAULT_DERIVATIVE_CUTOFF,
        DEFAULT_ACTIVE_SLOWDOWN_SPEED,
        DEFAULT_ACTIVE_SLOWDOWN_EXP,
        DEFAULT_CLICK_SLOWDOWN_ENABLED,
        DEFAULT_CLICK_INITIAL_FACTOR,
        DEFAULT_CLICK_TARGET_FACTOR,
        DEFAULT_CLICK_DECAY_INTERVAL,
        DEFAULT_CLICK_DECAY_STEP,
        DEFAULT_REPOSITION_SENS_FACTOR,
        DEFAULT_REPOSITION_MIN_CUTOFF,
        DEFAULT_REPOSITION_DEADZONE,
        DEFAULT_REPOSITION_SLOWDOWN_SPEED,
        DEFAULT_REPOSITION_SLOWDOWN_EXP,
        DEFAULT_ACCEL_FACTOR,
        DEFAULT_ACCEL_EXPONENT,
        DEFAULT_ACCEL_THRESHOLD,
        DEFAULT_INVERT_CLUTCH,
        DEFAULT_ACCEL_REJECTION_THRESHOLD,
        DEFAULT_MAX_ROLL_DEGREES,
    )
except ImportError:
    from filters import (
        OneEuroFilter,
        MadgwickFilter,
        AutoZeroBiasCalibrator,
        apply_deadzone_filter,
    )
    from config import (
        GYRO_SCALE_RAD_PER_SEC,
        ACCEL_SCALE_G,
        DEFAULT_BASE_SENSITIVITY,
        DEFAULT_DEADZONE_THRESHOLD,
        DEFAULT_MIN_CUTOFF_FREQUENCY,
        DEFAULT_SPEED_COEFFICIENT,
        DEFAULT_DERIVATIVE_CUTOFF,
        DEFAULT_ACTIVE_SLOWDOWN_SPEED,
        DEFAULT_ACTIVE_SLOWDOWN_EXP,
        DEFAULT_CLICK_SLOWDOWN_ENABLED,
        DEFAULT_CLICK_INITIAL_FACTOR,
        DEFAULT_CLICK_TARGET_FACTOR,
        DEFAULT_CLICK_DECAY_INTERVAL,
        DEFAULT_CLICK_DECAY_STEP,
        DEFAULT_REPOSITION_SENS_FACTOR,
        DEFAULT_REPOSITION_MIN_CUTOFF,
        DEFAULT_REPOSITION_DEADZONE,
        DEFAULT_REPOSITION_SLOWDOWN_SPEED,
        DEFAULT_REPOSITION_SLOWDOWN_EXP,
        DEFAULT_ACCEL_FACTOR,
        DEFAULT_ACCEL_EXPONENT,
        DEFAULT_ACCEL_THRESHOLD,
        DEFAULT_INVERT_CLUTCH,
        DEFAULT_ACCEL_REJECTION_THRESHOLD,
        DEFAULT_MAX_ROLL_DEGREES,
    )


class AirMousePipeline:
    def __init__(
        self,
        sensitivity=DEFAULT_BASE_SENSITIVITY,
        deadzone_threshold=DEFAULT_DEADZONE_THRESHOLD,
        minimum_cutoff_frequency=DEFAULT_MIN_CUTOFF_FREQUENCY,
        speed_coefficient=DEFAULT_SPEED_COEFFICIENT,
        derivative_cutoff_frequency=DEFAULT_DERIVATIVE_CUTOFF,
        active_slowdown_speed=DEFAULT_ACTIVE_SLOWDOWN_SPEED,
        active_slowdown_exp=DEFAULT_ACTIVE_SLOWDOWN_EXP,
        click_slowdown_enabled=DEFAULT_CLICK_SLOWDOWN_ENABLED,
        click_initial_factor=DEFAULT_CLICK_INITIAL_FACTOR,
        click_target_factor=DEFAULT_CLICK_TARGET_FACTOR,
        click_decay_interval=DEFAULT_CLICK_DECAY_INTERVAL,
        click_decay_step=DEFAULT_CLICK_DECAY_STEP,
        acceleration_factor=DEFAULT_ACCEL_FACTOR,
        acceleration_exponent=DEFAULT_ACCEL_EXPONENT,
        acceleration_threshold=DEFAULT_ACCEL_THRESHOLD,
        invert_clutch=DEFAULT_INVERT_CLUTCH,
        reposition_sens_factor=DEFAULT_REPOSITION_SENS_FACTOR,
        reposition_min_cutoff=DEFAULT_REPOSITION_MIN_CUTOFF,
        reposition_deadzone=DEFAULT_REPOSITION_DEADZONE,
        reposition_slowdown_speed=DEFAULT_REPOSITION_SLOWDOWN_SPEED,
        reposition_slowdown_exp=DEFAULT_REPOSITION_SLOWDOWN_EXP,
        accel_rejection_threshold=DEFAULT_ACCEL_REJECTION_THRESHOLD,
        max_roll_degrees=DEFAULT_MAX_ROLL_DEGREES
    ):
        self.base_sensitivity = sensitivity
        self.sensitivity = sensitivity
        self.deadzone_threshold = deadzone_threshold
        self.minimum_cutoff_frequency = minimum_cutoff_frequency
        self.active_slowdown_speed = active_slowdown_speed
        self.active_slowdown_exp = active_slowdown_exp
        self.click_slowdown_enabled = click_slowdown_enabled
        self.click_initial_factor = click_initial_factor
        self.click_target_factor = click_target_factor
        self.click_decay_interval = click_decay_interval
        self.click_decay_step = click_decay_step
        self.acceleration_factor = acceleration_factor
        self.acceleration_exponent = acceleration_exponent
        self.acceleration_threshold = acceleration_threshold
        self.invert_clutch = invert_clutch
        self.reposition_sens_factor = reposition_sens_factor
        self.reposition_min_cutoff = reposition_min_cutoff
        self.reposition_deadzone = reposition_deadzone
        self.reposition_slowdown_speed = reposition_slowdown_speed
        self.reposition_slowdown_exp = reposition_slowdown_exp

        self.click_start_timestamp = None
        self.previous_click_held = False




        self.calibrator = AutoZeroBiasCalibrator()
        self.one_euro_filter_gyroscope_x = OneEuroFilter(
            minimum_cutoff_frequency=minimum_cutoff_frequency,
            speed_coefficient=speed_coefficient,
            derivative_cutoff_frequency=derivative_cutoff_frequency
        )
        self.one_euro_filter_gyroscope_y = OneEuroFilter(
            minimum_cutoff_frequency=minimum_cutoff_frequency,
            speed_coefficient=speed_coefficient,
            derivative_cutoff_frequency=derivative_cutoff_frequency
        )
        self.one_euro_filter_gyroscope_z = OneEuroFilter(
            minimum_cutoff_frequency=minimum_cutoff_frequency,
            speed_coefficient=speed_coefficient,
            derivative_cutoff_frequency=derivative_cutoff_frequency
        )
        self.madgwick_filter = MadgwickFilter(
            beta=0.1,
            accel_rejection_threshold=accel_rejection_threshold,
            max_roll_degrees=max_roll_degrees
        )
        self.previous_clutch_active = None
        self.subpixel_accumulator_x = 0.0
        self.subpixel_accumulator_y = 0.0
        self.raw_potentiometer = 0
        self.potentiometer_ratio = 0.5
        self.max_observed_pot = 4095

    def calculate_effective_sensitivity(self, screen_pitch_rate, screen_yaw_rate):
        if self.acceleration_factor <= 0.0:
            return self.sensitivity

        motion_speed = math.sqrt(screen_pitch_rate * screen_pitch_rate + screen_yaw_rate * screen_yaw_rate)
        if motion_speed <= self.acceleration_threshold:
            return self.sensitivity

        excess_speed = motion_speed - self.acceleration_threshold
        acceleration_multiplier = 1.0 + self.acceleration_factor * (excess_speed ** self.acceleration_exponent)
        return self.sensitivity * acceleration_multiplier

    def process_frame(self, unpacked_packet, timestamp, delta_time):
        button_bitmask, raw_gyro, raw_accel, raw_potentiometer = self._parse_packet_fields(unpacked_packet)
        self._update_potentiometer_sensitivity(raw_potentiometer)

        is_clutch_active, is_left_click, is_right_click, is_slowdown_mode, is_click_held = self._resolve_button_states(button_bitmask, timestamp)

        gyroscope_uncalibrated, accelerometer = self._scale_sensor_readings(raw_gyro, raw_accel)
        self._handle_clutch_gravity_alignment(is_clutch_active, accelerometer)

        gyroscope = self._calibrate_and_filter_gyroscope(
            gyroscope_uncalibrated, timestamp, is_clutch_active, is_slowdown_mode
        )

        roll_radians = self.madgwick_filter.update(
            gyroscope[0], gyroscope[1], gyroscope[2],
            accelerometer[0], accelerometer[1], accelerometer[2],
            delta_time
        )
        screen_pitch_rate, screen_yaw_rate = self._project_gyroscope_rates(gyroscope[0], gyroscope[2], roll_radians)

        effective_sensitivity = self.calculate_effective_sensitivity(screen_pitch_rate, screen_yaw_rate)
        if is_slowdown_mode:
            effective_sensitivity = self._apply_reposition_slowdown(effective_sensitivity, screen_pitch_rate, screen_yaw_rate)
        else:
            effective_sensitivity = self._apply_active_slowdown(effective_sensitivity, screen_pitch_rate, screen_yaw_rate)

        if is_click_held and self.click_slowdown_enabled:
            effective_sensitivity = self._apply_dynamic_click_slowdown(effective_sensitivity, timestamp)

        movement_x, movement_y = self._accumulate_subpixel_movement(
            delta_x=-screen_yaw_rate * effective_sensitivity,
            delta_y=-screen_pitch_rate * effective_sensitivity
        )

        return movement_x, movement_y, is_clutch_active, is_left_click, is_right_click


    def _parse_packet_fields(self, unpacked_packet):
        if len(unpacked_packet) == 9:
            _, button_bitmask, gx, gy, gz, ax, ay, az, pot = unpacked_packet
        else:
            _, button_bitmask, gx, gy, gz, ax, ay, az = unpacked_packet
            pot = 0
        return button_bitmask, (gx, gy, gz), (ax, ay, az), pot

    def _update_potentiometer_sensitivity(self, raw_potentiometer):
        self.raw_potentiometer = raw_potentiometer
        if raw_potentiometer > self.max_observed_pot:
            self.max_observed_pot = raw_potentiometer

        if self.max_observed_pot > 0:
            self.potentiometer_ratio = min(1.0, max(0.0, raw_potentiometer / float(self.max_observed_pot)))
        else:
            self.potentiometer_ratio = 0.5

        centered_knob_position = 2.0 * self.potentiometer_ratio - 1.0
        cubic_curve = centered_knob_position * centered_knob_position * centered_knob_position
        exponent_scale = cubic_curve * 2.0
        self.sensitivity = self.base_sensitivity * (2.0 ** exponent_scale)

    def _resolve_button_states(self, button_bitmask, timestamp):
        raw_clutch_pressed = bool(button_bitmask & 0x01)
        is_left_click = bool(button_bitmask & 0x02)
        is_right_click = bool(button_bitmask & 0x04)

        is_clutch_active = not raw_clutch_pressed if self.invert_clutch else raw_clutch_pressed
        is_click_held = is_left_click or is_right_click

        if is_click_held and self.click_slowdown_enabled:
            if not self.previous_click_held or self.click_start_timestamp is None:
                self.click_start_timestamp = timestamp
        else:
            self.click_start_timestamp = None

        self.previous_click_held = is_click_held
        is_slowdown_mode = not is_clutch_active

        return is_clutch_active, is_left_click, is_right_click, is_slowdown_mode, is_click_held



    def _scale_sensor_readings(self, raw_gyro, raw_accel):
        gyro_uncalibrated = (
            raw_gyro[0] * GYRO_SCALE_RAD_PER_SEC,
            raw_gyro[1] * GYRO_SCALE_RAD_PER_SEC,
            raw_gyro[2] * GYRO_SCALE_RAD_PER_SEC
        )
        accelerometer = (
            raw_accel[0] * ACCEL_SCALE_G,
            raw_accel[1] * ACCEL_SCALE_G,
            raw_accel[2] * ACCEL_SCALE_G
        )
        return gyro_uncalibrated, accelerometer

    def _handle_clutch_gravity_alignment(self, is_clutch_active, accelerometer):
        if self.previous_clutch_active is not None and is_clutch_active != self.previous_clutch_active:
            self.madgwick_filter.align_to_gravity(accelerometer[0], accelerometer[1], accelerometer[2])
        self.previous_clutch_active = is_clutch_active

    def _calibrate_and_filter_gyroscope(self, gyro_uncalibrated, timestamp, is_clutch_active, is_slowdown_mode):
        self.calibrator.update_bias_if_stationary(
            gyro_uncalibrated[0], gyro_uncalibrated[1], gyro_uncalibrated[2], is_clutch_active
        )
        gx, gy, gz = self.calibrator.apply_bias_correction(
            gyro_uncalibrated[0], gyro_uncalibrated[1], gyro_uncalibrated[2]
        )

        deadzone = self.deadzone_threshold if not is_slowdown_mode else max(self.deadzone_threshold, self.reposition_deadzone)
        min_cutoff = self.minimum_cutoff_frequency if not is_slowdown_mode else self.reposition_min_cutoff

        gx = apply_deadzone_filter(gx, deadzone)
        gy = apply_deadzone_filter(gy, deadzone)
        gz = apply_deadzone_filter(gz, deadzone)

        gx = self.one_euro_filter_gyroscope_x.filter(gx, timestamp, min_cutoff=min_cutoff)
        gy = self.one_euro_filter_gyroscope_y.filter(gy, timestamp, min_cutoff=min_cutoff)
        gz = self.one_euro_filter_gyroscope_z.filter(gz, timestamp, min_cutoff=min_cutoff)

        return gx, gy, gz

    def _project_gyroscope_rates(self, gyroscope_x, gyroscope_z, roll_radians):
        screen_pitch_rate = gyroscope_x * math.cos(roll_radians) - gyroscope_z * math.sin(roll_radians)
        screen_yaw_rate = gyroscope_x * math.sin(roll_radians) + gyroscope_z * math.cos(roll_radians)
        return screen_pitch_rate, screen_yaw_rate

    def _apply_reposition_slowdown(self, effective_sensitivity, screen_pitch_rate, screen_yaw_rate):
        motion_speed = math.sqrt(screen_pitch_rate * screen_pitch_rate + screen_yaw_rate * screen_yaw_rate)
        if motion_speed < self.reposition_slowdown_speed and self.reposition_slowdown_speed > 0.0:
            slowdown_factor = (motion_speed / self.reposition_slowdown_speed) ** self.reposition_slowdown_exp
        else:
            slowdown_factor = 1.0
        return effective_sensitivity * self.reposition_sens_factor * slowdown_factor

    def _apply_active_slowdown(self, effective_sensitivity, screen_pitch_rate, screen_yaw_rate):
        if self.active_slowdown_speed <= 0.0:
            return effective_sensitivity
        motion_speed = math.sqrt(screen_pitch_rate * screen_pitch_rate + screen_yaw_rate * screen_yaw_rate)
        if motion_speed < self.active_slowdown_speed:
            slowdown_factor = (motion_speed / self.active_slowdown_speed) ** self.active_slowdown_exp
            return effective_sensitivity * slowdown_factor
        return effective_sensitivity

    def _apply_dynamic_click_slowdown(self, effective_sensitivity, timestamp):
        if self.click_start_timestamp is None:
            return effective_sensitivity
        t_elapsed = max(0.0, timestamp - self.click_start_timestamp)
        progress_steps = t_elapsed / self.click_decay_interval if self.click_decay_interval > 0.0 else 1.0
        gap = self.click_target_factor - self.click_initial_factor
        raw_factor = self.click_initial_factor + gap * (progress_steps * self.click_decay_step)
        dynamic_factor = min(self.click_target_factor, raw_factor)
        return effective_sensitivity * dynamic_factor



    def _accumulate_subpixel_movement(self, delta_x, delta_y):
        self.subpixel_accumulator_x += delta_x
        self.subpixel_accumulator_y += delta_y

        movement_x = int(self.subpixel_accumulator_x)
        movement_y = int(self.subpixel_accumulator_y)

        self.subpixel_accumulator_x -= movement_x
        self.subpixel_accumulator_y -= movement_y

        return movement_x, movement_y

