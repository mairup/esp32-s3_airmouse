import math
try:
    from .filters import (
        OneEuroFilter,
        MadgwickFilter,
        AutoZeroBiasCalibrator,
        apply_deadzone_filter,
        GYRO_SCALE_RAD_PER_SEC,
        ACCEL_SCALE_G,
        DEFAULT_MIN_CUTOFF_FREQUENCY,
        DEFAULT_SPEED_COEFFICIENT,
        DEFAULT_DERIVATIVE_CUTOFF,
        DEFAULT_ACCEL_REJECTION_THRESHOLD,
        DEFAULT_MAX_ROLL_DEGREES,
        DEFAULT_DEADZONE_THRESHOLD,
    )
except ImportError:
    from filters import (
        OneEuroFilter,
        MadgwickFilter,
        AutoZeroBiasCalibrator,
        apply_deadzone_filter,
        GYRO_SCALE_RAD_PER_SEC,
        ACCEL_SCALE_G,
        DEFAULT_MIN_CUTOFF_FREQUENCY,
        DEFAULT_SPEED_COEFFICIENT,
        DEFAULT_DERIVATIVE_CUTOFF,
        DEFAULT_ACCEL_REJECTION_THRESHOLD,
        DEFAULT_MAX_ROLL_DEGREES,
        DEFAULT_DEADZONE_THRESHOLD,
    )

# ------------------------------------------------------------------------------
# DEFAULT PIPELINE CONFIGURATION & TUNING CONSTANTS
# ------------------------------------------------------------------------------
DEFAULT_BASE_SENSITIVITY          = 10.0
DEFAULT_REPOSITION_SENS_FACTOR    = 0.2
DEFAULT_REPOSITION_MIN_CUTOFF     = 2.5
DEFAULT_REPOSITION_DEADZONE       = 0.03
DEFAULT_REPOSITION_SLOWDOWN_SPEED = 0.3
DEFAULT_REPOSITION_SLOWDOWN_EXP   = 1.35
DEFAULT_ACCEL_FACTOR              = 0.25
DEFAULT_ACCEL_EXPONENT            = 1.12
DEFAULT_ACCEL_THRESHOLD           = 0.4
DEFAULT_INVERT_CLUTCH             = True
DEFAULT_SLOW_ON_CLICK             = True


class AirMousePipeline:
    def __init__(
        self,
        sensitivity=DEFAULT_BASE_SENSITIVITY,
        deadzone_threshold=DEFAULT_DEADZONE_THRESHOLD,
        minimum_cutoff_frequency=DEFAULT_MIN_CUTOFF_FREQUENCY,
        speed_coefficient=DEFAULT_SPEED_COEFFICIENT,
        derivative_cutoff_frequency=DEFAULT_DERIVATIVE_CUTOFF,
        acceleration_factor=DEFAULT_ACCEL_FACTOR,
        acceleration_exponent=DEFAULT_ACCEL_EXPONENT,
        acceleration_threshold=DEFAULT_ACCEL_THRESHOLD,
        invert_clutch=DEFAULT_INVERT_CLUTCH,
        slow_on_click=DEFAULT_SLOW_ON_CLICK,
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
        self.acceleration_factor = acceleration_factor
        self.acceleration_exponent = acceleration_exponent
        self.acceleration_threshold = acceleration_threshold
        self.invert_clutch = invert_clutch
        self.slow_on_click = slow_on_click
        self.reposition_sens_factor = reposition_sens_factor
        self.reposition_min_cutoff = reposition_min_cutoff
        self.reposition_deadzone = reposition_deadzone
        self.reposition_slowdown_speed = reposition_slowdown_speed
        self.reposition_slowdown_exp = reposition_slowdown_exp

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
        if len(unpacked_packet) == 9:
            sequence_number, button_bitmask, raw_gyro_x, raw_gyro_y, raw_gyro_z, raw_accel_x, raw_accel_y, raw_accel_z, raw_potentiometer = unpacked_packet
        else:
            sequence_number, button_bitmask, raw_gyro_x, raw_gyro_y, raw_gyro_z, raw_accel_x, raw_accel_y, raw_accel_z = unpacked_packet
            raw_potentiometer = 0

        self.raw_potentiometer = raw_potentiometer
        if raw_potentiometer > self.max_observed_pot:
            self.max_observed_pot = raw_potentiometer

        if self.max_observed_pot > 0:
            self.potentiometer_ratio = min(1.0, max(0.0, raw_potentiometer / float(self.max_observed_pot)))
        else:
            self.potentiometer_ratio = 0.5

        # Floating-point non-linear curve centered at 50% knob (base_sensitivity at center)
        centered_x = 2.0 * self.potentiometer_ratio - 1.0
        cubic_curve = centered_x * centered_x * centered_x
        exponent_scale = cubic_curve * 2.0
        self.sensitivity = self.base_sensitivity * (2.0 ** exponent_scale)
        
        raw_clutch_pressed = bool(button_bitmask & 0x01)
        is_left_click = bool(button_bitmask & 0x02)
        is_right_click = bool(button_bitmask & 0x04)

        is_clutch_active = not raw_clutch_pressed if self.invert_clutch else raw_clutch_pressed
        is_click_held = (is_left_click or is_right_click) if self.slow_on_click else False
        is_slowdown_mode = (not is_clutch_active) or is_click_held

        gyro_uncalibrated_x = raw_gyro_x * GYRO_SCALE_RAD_PER_SEC
        gyro_uncalibrated_y = raw_gyro_y * GYRO_SCALE_RAD_PER_SEC
        gyro_uncalibrated_z = raw_gyro_z * GYRO_SCALE_RAD_PER_SEC

        accelerometer_x = raw_accel_x * ACCEL_SCALE_G
        accelerometer_y = raw_accel_y * ACCEL_SCALE_G
        accelerometer_z = raw_accel_z * ACCEL_SCALE_G

        # Re-align 3D orientation to gravity on clutch state transitions (pressed or released)
        if self.previous_clutch_active is not None and is_clutch_active != self.previous_clutch_active:
            self.madgwick_filter.align_to_gravity(accelerometer_x, accelerometer_y, accelerometer_z)
        self.previous_clutch_active = is_clutch_active

        self.calibrator.update_bias_if_stationary(gyro_uncalibrated_x, gyro_uncalibrated_y, gyro_uncalibrated_z, is_clutch_active)
        gyroscope_x, gyroscope_y, gyroscope_z = self.calibrator.apply_bias_correction(gyro_uncalibrated_x, gyro_uncalibrated_y, gyro_uncalibrated_z)

        if not is_slowdown_mode:
            current_deadzone = self.deadzone_threshold
            filter_min_cutoff = self.minimum_cutoff_frequency
        else:
            current_deadzone = max(self.deadzone_threshold, self.reposition_deadzone)
            filter_min_cutoff = self.reposition_min_cutoff

        gyroscope_x = apply_deadzone_filter(gyroscope_x, current_deadzone)
        gyroscope_y = apply_deadzone_filter(gyroscope_y, current_deadzone)
        gyroscope_z = apply_deadzone_filter(gyroscope_z, current_deadzone)

        gyroscope_x = self.one_euro_filter_gyroscope_x.filter(gyroscope_x, timestamp, min_cutoff=filter_min_cutoff)
        gyroscope_y = self.one_euro_filter_gyroscope_y.filter(gyroscope_y, timestamp, min_cutoff=filter_min_cutoff)
        gyroscope_z = self.one_euro_filter_gyroscope_z.filter(gyroscope_z, timestamp, min_cutoff=filter_min_cutoff)

        roll_radians = self.madgwick_filter.update(gyroscope_x, gyroscope_y, gyroscope_z, accelerometer_x, accelerometer_y, accelerometer_z, delta_time)

        screen_pitch_rate = gyroscope_x * math.cos(roll_radians) - gyroscope_z * math.sin(roll_radians)
        screen_yaw_rate = gyroscope_x * math.sin(roll_radians) + gyroscope_z * math.cos(roll_radians)

        effective_sensitivity = self.calculate_effective_sensitivity(screen_pitch_rate, screen_yaw_rate)

        if is_slowdown_mode:
            motion_speed = math.sqrt(screen_pitch_rate * screen_pitch_rate + screen_yaw_rate * screen_yaw_rate)
            if motion_speed < self.reposition_slowdown_speed and self.reposition_slowdown_speed > 0.0:
                slowdown_factor = (motion_speed / self.reposition_slowdown_speed) ** self.reposition_slowdown_exp
            else:
                slowdown_factor = 1.0
            effective_sensitivity *= self.reposition_sens_factor * slowdown_factor

        delta_x = -screen_yaw_rate * effective_sensitivity
        delta_y = -screen_pitch_rate * effective_sensitivity

        self.subpixel_accumulator_x += delta_x
        self.subpixel_accumulator_y += delta_y

        movement_x = int(self.subpixel_accumulator_x)
        movement_y = int(self.subpixel_accumulator_y)

        self.subpixel_accumulator_x -= movement_x
        self.subpixel_accumulator_y -= movement_y

        return movement_x, movement_y, is_clutch_active, is_left_click, is_right_click
