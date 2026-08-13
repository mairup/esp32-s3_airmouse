import math
try:
    from .filters import (
        OneEuroFilter,
        MadgwickFilter,
        AutoZeroBiasCalibrator,
        StateTransitionSlowdown,
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
        DEFAULT_CLICK_SLOWDOWN_DURATION,
        DEFAULT_CLICK_SLOWDOWN_EXPONENT,
        DEFAULT_SCROLL_MODE_ENABLED,
        DEFAULT_SCROLL_SENSITIVITY,
        DEFAULT_PAN_SENSITIVITY_X,
        DEFAULT_PAN_SENSITIVITY_Y,
        DEFAULT_SCROLL_DEADZONE,
        DEFAULT_INVERT_VERTICAL_SCROLL,
        DEFAULT_SCROLL_AXIS_LOCK,
        DEFAULT_PAN_AXIS_LOCK_THRESHOLD,
        DEFAULT_PAN_AXIS_LOCK_DECAY_TIME,
        DEFAULT_PAN_LOCK_RAMP_DURATION,
        DEFAULT_PAN_ACTIVATION_DELAY,
        DEFAULT_PAN_STILLNESS_THRESHOLD,
        DEFAULT_POST_PAN_SLOWDOWN_ENABLED,
        DEFAULT_POST_PAN_INITIAL_FACTOR,
        DEFAULT_POST_PAN_SLOWDOWN_DURATION,
        DEFAULT_POST_PAN_SLOWDOWN_EXPONENT,
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
        DEFAULT_POT_MAX,
        DEFAULT_MADGWICK_BETA,
        DEFAULT_MADGWICK_BETA_SENS_SCALE,
        DEFAULT_POT_SENS_RANGE,
        DEFAULT_SMOOTH_SCROLL_ENABLED,
        DEFAULT_SCROLL_HI_RES_SCALE,
        DEFAULT_SCROLL_SMOOTHING_ALPHA,
        DEFAULT_SCROLL_INERTIA_ENABLED,
        DEFAULT_SCROLL_INERTIA_DECAY,
    )
except ImportError:
    from filters import (
        OneEuroFilter,
        MadgwickFilter,
        AutoZeroBiasCalibrator,
        StateTransitionSlowdown,
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
        DEFAULT_CLICK_SLOWDOWN_DURATION,
        DEFAULT_CLICK_SLOWDOWN_EXPONENT,
        DEFAULT_SCROLL_MODE_ENABLED,
        DEFAULT_SCROLL_SENSITIVITY,
        DEFAULT_PAN_SENSITIVITY_X,
        DEFAULT_PAN_SENSITIVITY_Y,
        DEFAULT_SCROLL_DEADZONE,
        DEFAULT_INVERT_VERTICAL_SCROLL,
        DEFAULT_SCROLL_AXIS_LOCK,
        DEFAULT_PAN_AXIS_LOCK_THRESHOLD,
        DEFAULT_PAN_AXIS_LOCK_DECAY_TIME,
        DEFAULT_PAN_LOCK_RAMP_DURATION,
        DEFAULT_PAN_ACTIVATION_DELAY,
        DEFAULT_PAN_STILLNESS_THRESHOLD,
        DEFAULT_POST_PAN_SLOWDOWN_ENABLED,
        DEFAULT_POST_PAN_INITIAL_FACTOR,
        DEFAULT_POST_PAN_SLOWDOWN_DURATION,
        DEFAULT_POST_PAN_SLOWDOWN_EXPONENT,
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
        DEFAULT_POT_MAX,
        DEFAULT_MADGWICK_BETA,
        DEFAULT_MADGWICK_BETA_SENS_SCALE,
        DEFAULT_POT_SENS_RANGE,
        DEFAULT_SMOOTH_SCROLL_ENABLED,
        DEFAULT_SCROLL_HI_RES_SCALE,
        DEFAULT_SCROLL_SMOOTHING_ALPHA,
        DEFAULT_SCROLL_INERTIA_ENABLED,
        DEFAULT_SCROLL_INERTIA_DECAY,
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
        click_duration=DEFAULT_CLICK_SLOWDOWN_DURATION,
        click_exponent=DEFAULT_CLICK_SLOWDOWN_EXPONENT,
        scroll_mode_enabled=DEFAULT_SCROLL_MODE_ENABLED,
        scroll_sensitivity=DEFAULT_SCROLL_SENSITIVITY,
        pan_sensitivity_x=None,
        pan_sensitivity_y=None,
        scroll_deadzone=DEFAULT_SCROLL_DEADZONE,
        invert_vertical_scroll=DEFAULT_INVERT_VERTICAL_SCROLL,
        scroll_axis_lock=DEFAULT_SCROLL_AXIS_LOCK,
        pan_axis_lock_threshold=DEFAULT_PAN_AXIS_LOCK_THRESHOLD,
        pan_axis_lock_decay_time=DEFAULT_PAN_AXIS_LOCK_DECAY_TIME,
        pan_lock_ramp_duration=DEFAULT_PAN_LOCK_RAMP_DURATION,
        pan_activation_delay=DEFAULT_PAN_ACTIVATION_DELAY,
        pan_stillness_threshold=DEFAULT_PAN_STILLNESS_THRESHOLD,
        post_pan_slowdown_enabled=DEFAULT_POST_PAN_SLOWDOWN_ENABLED,
        post_pan_initial_factor=DEFAULT_POST_PAN_INITIAL_FACTOR,
        post_pan_duration=DEFAULT_POST_PAN_SLOWDOWN_DURATION,
        post_pan_exponent=DEFAULT_POST_PAN_SLOWDOWN_EXPONENT,
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
        max_roll_degrees=DEFAULT_MAX_ROLL_DEGREES,
        pot_max=DEFAULT_POT_MAX,
        madgwick_beta=DEFAULT_MADGWICK_BETA,
        madgwick_beta_sens_scale=DEFAULT_MADGWICK_BETA_SENS_SCALE,
        pot_sens_range=DEFAULT_POT_SENS_RANGE,
        smooth_scroll_enabled=DEFAULT_SMOOTH_SCROLL_ENABLED,
        scroll_hi_res_scale=DEFAULT_SCROLL_HI_RES_SCALE,
        scroll_smoothing_alpha=DEFAULT_SCROLL_SMOOTHING_ALPHA,
        scroll_inertia_enabled=DEFAULT_SCROLL_INERTIA_ENABLED,
        scroll_inertia_decay=DEFAULT_SCROLL_INERTIA_DECAY,
    ):
        self.base_sensitivity = sensitivity
        self.sensitivity = sensitivity
        self.deadzone_threshold = deadzone_threshold
        self.minimum_cutoff_frequency = minimum_cutoff_frequency
        self.active_slowdown_speed = active_slowdown_speed
        self.active_slowdown_exp = active_slowdown_exp
        self.click_slowdown_enabled = click_slowdown_enabled
        self.click_slowdown = StateTransitionSlowdown(
            initial_factor=click_initial_factor,
            target_factor=1.0,
            duration_seconds=click_duration,
            exponent=click_exponent
        )
        self.scroll_mode_enabled = scroll_mode_enabled
        self.scroll_sensitivity = scroll_sensitivity
        self.pan_sensitivity_x = pan_sensitivity_x if pan_sensitivity_x is not None else scroll_sensitivity
        self.pan_sensitivity_y = pan_sensitivity_y if pan_sensitivity_y is not None else scroll_sensitivity
        self.scroll_deadzone = scroll_deadzone
        self.invert_vertical_scroll = invert_vertical_scroll
        self.scroll_axis_lock = scroll_axis_lock
        self.pan_axis_lock_threshold = pan_axis_lock_threshold
        self.pan_axis_lock_decay_time = pan_axis_lock_decay_time
        self.pan_lock_ramp_duration = pan_lock_ramp_duration
        self.pan_lock_start_timestamp = None
        self.pan_activation_delay = pan_activation_delay
        self.pan_stillness_threshold = pan_stillness_threshold
        self.post_pan_slowdown_enabled = post_pan_slowdown_enabled
        self.smooth_scroll_enabled = smooth_scroll_enabled
        self.scroll_hi_res_scale = scroll_hi_res_scale
        self.scroll_smoothing_alpha = scroll_smoothing_alpha
        self.scroll_inertia_enabled = scroll_inertia_enabled
        self.scroll_inertia_decay = scroll_inertia_decay

        self.scroll_smooth_vel_x = 0.0
        self.scroll_smooth_vel_y = 0.0
        self.scroll_hi_res_accum_x = 0.0
        self.scroll_hi_res_accum_y = 0.0
        self.scroll_wheel_accum_x = 0.0
        self.scroll_wheel_accum_y = 0.0


        self.post_pan_slowdown = StateTransitionSlowdown(
            initial_factor=post_pan_initial_factor,
            target_factor=1.0,
            duration_seconds=post_pan_duration,
            exponent=post_pan_exponent
        )

        self.clutch_hold_start_timestamp = None
        self.is_pan_mode_active = False
        self.pan_activation_failed_for_press = False
        self.locked_pan_axis = None
        self.pan_init_accum_x = 0.0
        self.pan_init_accum_y = 0.0
        self.previous_pan_mode_active = False
        self.previous_click_held = False
        self.previous_clutch_pressed = False

        self.acceleration_factor = acceleration_factor
        self.acceleration_exponent = acceleration_exponent
        self.acceleration_threshold = acceleration_threshold
        self.invert_clutch = invert_clutch
        self.reposition_sens_factor = reposition_sens_factor
        self.reposition_min_cutoff = reposition_min_cutoff
        self.reposition_deadzone = reposition_deadzone
        self.reposition_slowdown_speed = reposition_slowdown_speed
        self.reposition_slowdown_exp = reposition_slowdown_exp

        self.scroll_accumulator_x = 0.0
        self.scroll_accumulator_y = 0.0

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
            beta=madgwick_beta,
            accel_rejection_threshold=accel_rejection_threshold,
            max_roll_degrees=max_roll_degrees
        )
        self.madgwick_beta_sens_scale = madgwick_beta_sens_scale
        self.pot_sens_range = pot_sens_range
        self.previous_clutch_active = None
        self.subpixel_accumulator_x = 0.0
        self.subpixel_accumulator_y = 0.0
        self.raw_potentiometer = 0
        self.potentiometer_ratio = 0.5
        self.pot_max = pot_max


        def calculate_effective_sensitivity(self, screen_pitch_rate, screen_yaw_rate):
            motion_speed = math.sqrt(screen_pitch_rate * screen_pitch_rate + screen_yaw_rate * screen_yaw_rate)
            if motion_speed > self.acceleration_threshold and self.acceleration_threshold > 0.0:
                acceleration_multiplier = (motion_speed / self.acceleration_threshold) ** (self.acceleration_exponent - 1.0)
                return self.sensitivity * (1.0 + self.acceleration_factor * acceleration_multiplier)
            return self.sensitivity

    def _apply_reposition_slowdown(self, effective_sensitivity, screen_pitch_rate, screen_yaw_rate):
        motion_speed = math.sqrt(screen_pitch_rate * screen_pitch_rate + screen_yaw_rate * screen_yaw_rate)
        if motion_speed < self.reposition_slowdown_speed and self.reposition_slowdown_speed > 0.0:
            slowdown_factor = (motion_speed / self.reposition_slowdown_speed) ** self.reposition_slowdown_exp
            return effective_sensitivity * self.reposition_sens_factor * slowdown_factor
        return effective_sensitivity * self.reposition_sens_factor

    def _apply_active_slowdown(self, effective_sensitivity, screen_pitch_rate, screen_yaw_rate):
        if self.active_slowdown_speed <= 0.0:
            return effective_sensitivity
        motion_speed = math.sqrt(screen_pitch_rate * screen_pitch_rate + screen_yaw_rate * screen_yaw_rate)
        if motion_speed < self.active_slowdown_speed:
            slowdown_factor = (motion_speed / self.active_slowdown_speed) ** self.active_slowdown_exp
            return effective_sensitivity * slowdown_factor
        return effective_sensitivity

    def _process_scroll_and_pan(self, is_pan_active, screen_pitch_rate, screen_yaw_rate, delta_time, timestamp):
        pitch_rate = apply_deadzone_filter(screen_pitch_rate, self.scroll_deadzone)
        yaw_rate = apply_deadzone_filter(screen_yaw_rate, self.scroll_deadzone)

        vertical_direction = -1.0 if self.invert_vertical_scroll else 1.0

        if is_pan_active:
            target_vel_y = pitch_rate * self.pan_sensitivity_y * vertical_direction
            target_vel_x = yaw_rate * self.pan_sensitivity_x

            if self.scroll_axis_lock:
                if self.locked_pan_axis is None:
                    decay = math.exp(-delta_time / max(self.pan_axis_lock_decay_time, 1e-4)) if self.pan_axis_lock_decay_time > 0.0 else 1.0
                    self.pan_init_accum_x = self.pan_init_accum_x * decay + (yaw_rate * delta_time)
                    self.pan_init_accum_y = self.pan_init_accum_y * decay + (pitch_rate * delta_time)

                    abs_x = abs(self.pan_init_accum_x)
                    abs_y = abs(self.pan_init_accum_y)
                    if max(abs_x, abs_y) >= self.pan_axis_lock_threshold:
                        if abs_y >= abs_x:
                            self.locked_pan_axis = 'vertical'
                        else:
                            self.locked_pan_axis = 'horizontal'
                        self.pan_lock_start_timestamp = timestamp

                if self.locked_pan_axis == 'vertical':
                    target_vel_x = 0.0
                elif self.locked_pan_axis == 'horizontal':
                    target_vel_y = 0.0
                else:
                    target_vel_x = 0.0
                    target_vel_y = 0.0

                if self.locked_pan_axis is not None and self.pan_lock_start_timestamp is not None and self.pan_lock_ramp_duration > 0.0:
                    lock_elapsed = timestamp - self.pan_lock_start_timestamp
                    ramp_factor = min(1.0, max(0.0, lock_elapsed / self.pan_lock_ramp_duration))
                    target_vel_x *= ramp_factor
                    target_vel_y *= ramp_factor

            if self.smooth_scroll_enabled:
                alpha = max(0.01, min(1.0, self.scroll_smoothing_alpha))
                self.scroll_smooth_vel_x = (1.0 - alpha) * self.scroll_smooth_vel_x + alpha * target_vel_x
                self.scroll_smooth_vel_y = (1.0 - alpha) * self.scroll_smooth_vel_y + alpha * target_vel_y
            else:
                self.scroll_smooth_vel_x = target_vel_x
                self.scroll_smooth_vel_y = target_vel_y
        else:
            self.pan_init_accum_x = 0.0
            self.pan_init_accum_y = 0.0
            self.locked_pan_axis = None
            self.pan_lock_start_timestamp = None

            if self.scroll_inertia_enabled and (abs(self.scroll_smooth_vel_x) > 0.001 or abs(self.scroll_smooth_vel_y) > 0.001):
                decay_factor = math.exp(-delta_time / max(self.scroll_inertia_decay, 1e-4))
                self.scroll_smooth_vel_x *= decay_factor
                self.scroll_smooth_vel_y *= decay_factor
                if abs(self.scroll_smooth_vel_x) < 0.001:
                    self.scroll_smooth_vel_x = 0.0
                if abs(self.scroll_smooth_vel_y) < 0.001:
                    self.scroll_smooth_vel_y = 0.0
            else:
                self.scroll_smooth_vel_x = 0.0
                self.scroll_smooth_vel_y = 0.0

        if self.smooth_scroll_enabled:
            hi_res_delta_y = self.scroll_smooth_vel_y * 12000.0 * delta_time
            hi_res_delta_x = self.scroll_smooth_vel_x * 12000.0 * delta_time

            self.scroll_hi_res_accum_y += hi_res_delta_y
            self.scroll_hi_res_accum_x += hi_res_delta_x

            hi_res_steps_y = int(self.scroll_hi_res_accum_y)
            hi_res_steps_x = int(self.scroll_hi_res_accum_x)

            self.scroll_hi_res_accum_y -= hi_res_steps_y
            self.scroll_hi_res_accum_x -= hi_res_steps_x

            self.scroll_wheel_accum_y += hi_res_steps_y
            self.scroll_wheel_accum_x += hi_res_steps_x

            wheel_steps_y = int(self.scroll_wheel_accum_y / self.scroll_hi_res_scale)
            wheel_steps_x = int(self.scroll_wheel_accum_x / self.scroll_hi_res_scale)

            self.scroll_wheel_accum_y -= wheel_steps_y * self.scroll_hi_res_scale
            self.scroll_wheel_accum_x -= wheel_steps_x * self.scroll_hi_res_scale

            return hi_res_steps_x, hi_res_steps_y, wheel_steps_x, wheel_steps_y
        else:
            self.scroll_accumulator_y += self.scroll_smooth_vel_y
            self.scroll_accumulator_x += self.scroll_smooth_vel_x

            wheel_steps_y = int(self.scroll_accumulator_y)
            wheel_steps_x = int(self.scroll_accumulator_x)

            self.scroll_accumulator_y -= wheel_steps_y
            self.scroll_accumulator_x -= wheel_steps_x

            return 0, 0, wheel_steps_x, wheel_steps_y

    def _accumulate_subpixel_movement(self, delta_x, delta_y):
        self.subpixel_accumulator_x += delta_x
        self.subpixel_accumulator_y += delta_y

        movement_x = int(self.subpixel_accumulator_x)
        movement_y = int(self.subpixel_accumulator_y)

        self.subpixel_accumulator_x -= movement_x
        self.subpixel_accumulator_y -= movement_y

        return movement_x, movement_y

