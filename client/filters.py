import math

try:
    from .config import (
        DEFAULT_MIN_CUTOFF_FREQUENCY,
        DEFAULT_SPEED_COEFFICIENT,
        DEFAULT_DERIVATIVE_CUTOFF,
        DEFAULT_ACCEL_REJECTION_THRESHOLD,
        DEFAULT_MAX_ROLL_DEGREES,
        DEFAULT_DEADZONE_THRESHOLD,
    )
except ImportError:
    from config import (
        DEFAULT_MIN_CUTOFF_FREQUENCY,
        DEFAULT_SPEED_COEFFICIENT,
        DEFAULT_DERIVATIVE_CUTOFF,
        DEFAULT_ACCEL_REJECTION_THRESHOLD,
        DEFAULT_MAX_ROLL_DEGREES,
        DEFAULT_DEADZONE_THRESHOLD,
    )


class OneEuroFilter:
    def __init__(
        self,
        minimum_cutoff_frequency=DEFAULT_MIN_CUTOFF_FREQUENCY,
        speed_coefficient=DEFAULT_SPEED_COEFFICIENT,
        derivative_cutoff_frequency=DEFAULT_DERIVATIVE_CUTOFF
    ):
        self.minimum_cutoff_frequency = float(minimum_cutoff_frequency)
        self.speed_coefficient = float(speed_coefficient)
        self.derivative_cutoff_frequency = float(derivative_cutoff_frequency)
        self.previous_value = None
        self.previous_derivative = 0.0
        self.previous_timestamp = None

    def calculate_alpha(self, cutoff_frequency, delta_time):
        time_constant = 1.0 / (2.0 * math.pi * cutoff_frequency)
        return 1.0 / (1.0 + time_constant / delta_time)

    def filter(self, value, timestamp, min_cutoff=None):
        if self.previous_value is None or self.previous_timestamp is None:
            self.previous_value = float(value)
            self.previous_derivative = 0.0
            self.previous_timestamp = timestamp
            return float(value)

        delta_time = timestamp - self.previous_timestamp
        if delta_time <= 0.0:
            delta_time = 1e-5

        self.previous_timestamp = timestamp

        value_derivative = (value - self.previous_value) / delta_time
        alpha_derivative = self.calculate_alpha(self.derivative_cutoff_frequency, delta_time)
        filtered_derivative = alpha_derivative * value_derivative + (1.0 - alpha_derivative) * self.previous_derivative
        self.previous_derivative = filtered_derivative

        effective_min_cutoff = min_cutoff if min_cutoff is not None else self.minimum_cutoff_frequency
        cutoff_frequency = effective_min_cutoff + self.speed_coefficient * abs(filtered_derivative)
        alpha_value = self.calculate_alpha(cutoff_frequency, delta_time)

        filtered_value = alpha_value * value + (1.0 - alpha_value) * self.previous_value
        self.previous_value = filtered_value
        return filtered_value

    def reset(self):
        self.previous_value = None
        self.previous_derivative = 0.0
        self.previous_timestamp = None


class MadgwickFilter:
    def __init__(
        self,
        beta=0.1,
        accel_rejection_threshold=DEFAULT_ACCEL_REJECTION_THRESHOLD,
        max_roll_degrees=DEFAULT_MAX_ROLL_DEGREES
    ):
        self.beta = float(beta)
        self.accel_rejection_threshold = float(accel_rejection_threshold)
        self.max_roll_rad = math.radians(float(max_roll_degrees))
        self.quaternion = [1.0, 0.0, 0.0, 0.0]

    def reset(self):
        self.quaternion = [1.0, 0.0, 0.0, 0.0]

    def align_to_gravity(self, accelerometer_x, accelerometer_y, accelerometer_z):
        normalized_accel, norm = self._normalize_vector3(accelerometer_x, accelerometer_y, accelerometer_z)
        if norm == 0.0:
            self.reset()
            return
        ax, ay, az = normalized_accel

        pitch = math.atan2(-ax, math.sqrt(ay * ay + az * az))
        roll = math.atan2(ay, az)
        yaw = 0.0

        cy = math.cos(yaw * 0.5)
        sy = math.sin(yaw * 0.5)
        cp = math.cos(pitch * 0.5)
        sp = math.sin(pitch * 0.5)
        cr = math.cos(roll * 0.5)
        sr = math.sin(roll * 0.5)

        q1 = cr * cp * cy + sr * sp * sy
        q2 = sr * cp * cy - cr * sp * sy
        q3 = cr * sp * cy + sr * cp * sy
        q4 = cr * cp * sy - sr * sp * cy

        self.quaternion = [q1, q2, q3, q4]

    def update(self, gyroscope_x, gyroscope_y, gyroscope_z, accelerometer_x, accelerometer_y, accelerometer_z, delta_time):
        q1, q2, q3, q4 = self.quaternion

        normalized_accel, accel_norm = self._normalize_vector3(accelerometer_x, accelerometer_y, accelerometer_z)
        if accel_norm == 0.0:
            return self.calculate_roll_radians()

        effective_beta = self._compute_effective_beta(accel_norm)
        ax, ay, az = normalized_accel

        _2q1 = 2.0 * q1
        _2q2 = 2.0 * q2
        _2q3 = 2.0 * q3
        _2q4 = 2.0 * q4

        f1 = _2q2 * q4 - _2q1 * q3 - ax
        f2 = _2q1 * q2 + _2q3 * q4 - ay
        f3 = 1.0 - _2q2 * q2 - _2q3 * q3 - az

        j_11or24 = _2q3
        j_12or23 = _2q4
        j_13or22 = _2q1
        j_14or21 = _2q2
        j_32 = 2.0 * j_14or21
        j_33 = 2.0 * j_13or22

        s1 = -j_13or22 * f1 + j_14or21 * f2
        s2 = j_14or21 * f1 + j_13or22 * f2 - j_32 * f3
        s3 = -j_11or24 * f1 + j_12or23 * f2 - j_33 * f3
        s4 = j_12or23 * f1 + j_11or24 * f2

        normalized_s, s_norm = self._normalize_vector4(s1, s2, s3, s4)
        if s_norm > 0.0:
            s1, s2, s3, s4 = normalized_s

        q_dot_1 = 0.5 * (-q2 * gyroscope_x - q3 * gyroscope_y - q4 * gyroscope_z) - effective_beta * s1
        q_dot_2 = 0.5 * ( q1 * gyroscope_x + q3 * gyroscope_z - q4 * gyroscope_y) - effective_beta * s2
        q_dot_3 = 0.5 * ( q1 * gyroscope_y - q2 * gyroscope_z + q4 * gyroscope_x) - effective_beta * s3
        q_dot_4 = 0.5 * ( q1 * gyroscope_z + q2 * gyroscope_y - q3 * gyroscope_x) - effective_beta * s4

        q1 += q_dot_1 * delta_time
        q2 += q_dot_2 * delta_time
        q3 += q_dot_3 * delta_time
        q4 += q_dot_4 * delta_time

        normalized_q, q_norm = self._normalize_vector4(q1, q2, q3, q4)
        if q_norm > 0.0:
            self.quaternion = list(normalized_q)

        return self.calculate_roll_radians()

    def calculate_roll_radians(self):
        q1, q2, q3, q4 = self.quaternion
        roll = math.atan2(2.0 * (q1 * q2 + q3 * q4), 1.0 - 2.0 * (q2 * q2 + q3 * q3))
        return max(-self.max_roll_rad, min(self.max_roll_rad, roll))

    def _compute_effective_beta(self, accel_norm):
        accel_err = abs(accel_norm - 1.0)
        if accel_err >= self.accel_rejection_threshold:
            return 0.0
        return self.beta * (1.0 - (accel_err / self.accel_rejection_threshold))

    def _normalize_vector3(self, vx, vy, vz):
        norm = math.sqrt(vx * vx + vy * vy + vz * vz)
        if norm == 0.0:
            return (0.0, 0.0, 0.0), 0.0
        return (vx / norm, vy / norm, vz / norm), norm

    def _normalize_vector4(self, v1, v2, v3, v4):
        norm = math.sqrt(v1 * v1 + v2 * v2 + v3 * v3 + v4 * v4)
        if norm == 0.0:
            return (0.0, 0.0, 0.0, 0.0), 0.0
        return (v1 / norm, v2 / norm, v3 / norm, v4 / norm), norm


class AutoZeroBiasCalibrator:
    def __init__(self, decay_factor=0.992, update_factor=0.008, motion_threshold=0.025):
        self.decay_factor = decay_factor
        self.update_factor = update_factor
        self.motion_threshold = motion_threshold
        self.gyroscope_bias = [0.0, 0.0, 0.0]

    def update_bias_if_stationary(self, gyroscope_uncalibrated_x, gyroscope_uncalibrated_y, gyroscope_uncalibrated_z, is_clutch_pressed):
        if is_clutch_pressed:
            return
        motion_magnitude = math.sqrt(
            gyroscope_uncalibrated_x * gyroscope_uncalibrated_x +
            gyroscope_uncalibrated_y * gyroscope_uncalibrated_y +
            gyroscope_uncalibrated_z * gyroscope_uncalibrated_z
        )
        if motion_magnitude < self.motion_threshold:
            uncalibrated = (gyroscope_uncalibrated_x, gyroscope_uncalibrated_y, gyroscope_uncalibrated_z)
            self.gyroscope_bias = [
                self.decay_factor * bias + self.update_factor * raw
                for bias, raw in zip(self.gyroscope_bias, uncalibrated)
            ]

    def apply_bias_correction(self, gyroscope_uncalibrated_x, gyroscope_uncalibrated_y, gyroscope_uncalibrated_z):
        return (
            gyroscope_uncalibrated_x - self.gyroscope_bias[0],
            gyroscope_uncalibrated_y - self.gyroscope_bias[1],
            gyroscope_uncalibrated_z - self.gyroscope_bias[2]
        )


def apply_deadzone_filter(value, threshold=DEFAULT_DEADZONE_THRESHOLD):
    return 0.0 if abs(value) < threshold else value


class StateTransitionSlowdown:
    def __init__(self, initial_factor=0.3, target_factor=1.0, duration_seconds=0.7, exponent=1.0):
        self.initial_factor = float(initial_factor)
        self.target_factor = float(target_factor)
        self.duration_seconds = float(duration_seconds)
        self.exponent = float(exponent)
        self.start_timestamp = None
        self.is_active = False

    def trigger(self, timestamp):
        self.start_timestamp = timestamp
        self.is_active = True

    def reset(self):
        self.start_timestamp = None
        self.is_active = False

    def calculate_multiplier(self, timestamp):
        if not self.is_active or self.start_timestamp is None:
            return 1.0

        elapsed = timestamp - self.start_timestamp
        if elapsed < 0.0:
            return self.initial_factor

        if elapsed >= self.duration_seconds or self.duration_seconds <= 0.0:
            self.reset()
            return 1.0

        progress = elapsed / self.duration_seconds
        curved_progress = progress ** self.exponent
        gap = self.target_factor - self.initial_factor
        return self.initial_factor + gap * curved_progress


