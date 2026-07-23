import sys
import time
import math
import socket
import struct
import signal
import argparse
import evdev
from evdev import UInput, ecodes as e


# ==============================================================================
# DEFAULT PIPELINE CONFIGURATION & TUNING CONSTANTS
# Edit any filter, deadzone, sensitivity, or reposition parameter right here.
# ==============================================================================

# ------------------------------------------------------------------------------
# GROUP 1: BASE SENSITIVITY & DEADZONE
# ------------------------------------------------------------------------------
# DEFAULT_BASE_SENSITIVITY (Range: 1.0 to 50.0)
#   Higher = faster pointer / less wrist effort; Lower = slower pointer / fine precision targeting.
DEFAULT_BASE_SENSITIVITY          = 10.0

# DEFAULT_DEADZONE_THRESHOLD (Range: 0.00 to 0.05 rad/s)
#   Higher = eliminates resting hand tremors, but adds start-motion stickiness; Lower = raw sensitivity to micro-tremors.
DEFAULT_DEADZONE_THRESHOLD        = 0.015

# ------------------------------------------------------------------------------
# GROUP 2: ACTIVE MODE 1-EURO FILTER (Low Latency / Smooth Pointer Tracking)
# ------------------------------------------------------------------------------
# DEFAULT_MIN_CUTOFF_FREQUENCY (Range: 0.5 to 10.0 Hz)
#   Higher = lower latency & raw responsiveness; Lower = smoother, buttery tracking with slight slow-speed lag.
DEFAULT_MIN_CUTOFF_FREQUENCY      = 3.0

# DEFAULT_SPEED_COEFFICIENT (Range: 0.0 to 1.0)
#   Higher = fast moves bypass filtering to eliminate lag; Lower = pure low-pass filtering (fast moves lag).
DEFAULT_SPEED_COEFFICIENT         = 0.5

# DEFAULT_DERIVATIVE_CUTOFF (Range: 1.0 to 10.0 Hz)
#   Higher = instant filter adaptation to fast swipes; Lower = smoother velocity slope estimation.
DEFAULT_DERIVATIVE_CUTOFF         = 6.0

# ------------------------------------------------------------------------------
# GROUP 3: REPOSITION MODE (Low Sens / De-acceleration when Clutch Off)
# ------------------------------------------------------------------------------
# DEFAULT_REPOSITION_SENS_FACTOR (Range: 0.0 to 0.5)
#   Higher = soft clutch (mouse still moves at 40-50% speed); Lower (0.0) = hard clutch (zero cursor movement).
DEFAULT_REPOSITION_SENS_FACTOR    = 0.2

# DEFAULT_REPOSITION_MIN_CUTOFF (Range: 1.0 to 5.0 Hz)
#   Higher = minimal filtering during repositioning; Lower = heavy smoothing to absorb hand reset jitter.
DEFAULT_REPOSITION_MIN_CUTOFF     = 2.5

# DEFAULT_REPOSITION_DEADZONE (Range: 0.01 to 0.10 rad/s)
#   Higher = ignores involuntary hand movement when resetting position; Lower = responsive to micro-nudges.
DEFAULT_REPOSITION_DEADZONE       = 0.03

# DEFAULT_REPOSITION_SLOWDOWN_SPEED (Range: 0.0 to 1.0 rad/s)
#   Higher = expands low-speed dampening zone for hand resets; Lower (0.0) = disables reposition slowdown curve.
DEFAULT_REPOSITION_SLOWDOWN_SPEED = 0.3

# DEFAULT_REPOSITION_SLOWDOWN_EXP (Range: 1.0 to 2.0)
#   Higher = aggressive exponential dampening on small reposition nudges; Lower = linear sensitivity reduction.
DEFAULT_REPOSITION_SLOWDOWN_EXP   = 1.35

# ------------------------------------------------------------------------------
# GROUP 4: MOUSE ACCELERATION CURVE (Active Mode Fast Swipes)
# ------------------------------------------------------------------------------
# DEFAULT_ACCEL_FACTOR (Range: 0.0 to 1.0)
#   Higher = rapid wrist flicks fling cursor across screen; Lower (0.0) = 1:1 direct linear mapping.
DEFAULT_ACCEL_FACTOR              = 0.25

# DEFAULT_ACCEL_EXPONENT (Range: 1.0 to 2.0)
#   Higher = exponential speed boost on fast hand flicks; Lower = linear speed scaling.
DEFAULT_ACCEL_EXPONENT            = 1.12

# DEFAULT_ACCEL_THRESHOLD (Range: 0.05 to 0.5 rad/s)
#   Higher = acceleration only triggers on rapid wrist flicks; Lower = acceleration engages almost immediately.
DEFAULT_ACCEL_THRESHOLD           = 0.4

# ------------------------------------------------------------------------------
# GROUP 5: HARDWARE & DEBOUNCE
# ------------------------------------------------------------------------------
# DEFAULT_INVERT_CLUTCH (Range: True / False)
#   True = Air mouse is ACTIVE by default (holding clutch pauses); False = Air mouse PAUSED by default (holding clutch activates).
DEFAULT_INVERT_CLUTCH             = True

# DEFAULT_SLOW_ON_CLICK (Range: True / False)
#   True = Apply reposition slowdown mode during left/right click drags; False = Active speed during click drags.
DEFAULT_SLOW_ON_CLICK             = True

# ------------------------------------------------------------------------------
# GROUP 6: ORIENTATION STABILITY & ACCELERATION REJECTION
# ------------------------------------------------------------------------------
# DEFAULT_ACCEL_REJECTION_THRESHOLD (Range: 0.05 to 0.40 g)
#   Higher = loose rejection (fast shaking can ksew tilt); Lower = strict rejection (protects tilt during fast moves).
DEFAULT_ACCEL_REJECTION_THRESHOLD = 0.1

# DEFAULT_MAX_ROLL_DEGREES (Range: 45.0 to 85.0 deg)
#   Higher = wider roll range for steep wrist tilts; Lower = tight clamp (keeps screen movement strictly horizontal).
DEFAULT_MAX_ROLL_DEGREES          = 75.0


# ==============================================================================
# PIPELINE FILTER CLASSES
# ==============================================================================

class OneEuroFilter:
    def __init__(self, minimum_cutoff_frequency=DEFAULT_MIN_CUTOFF_FREQUENCY, speed_coefficient=DEFAULT_SPEED_COEFFICIENT, derivative_cutoff_frequency=DEFAULT_DERIVATIVE_CUTOFF):
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
        accelerometer_norm = math.sqrt(accelerometer_x * accelerometer_x + accelerometer_y * accelerometer_y + accelerometer_z * accelerometer_z)
        if accelerometer_norm == 0.0:
            self.reset()
            return
        ax = accelerometer_x / accelerometer_norm
        ay = accelerometer_y / accelerometer_norm
        az = accelerometer_z / accelerometer_norm

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

        accelerometer_norm = math.sqrt(accelerometer_x * accelerometer_x + accelerometer_y * accelerometer_y + accelerometer_z * accelerometer_z)
        if accelerometer_norm == 0.0:
            return self.calculate_roll_radians()

        # Dynamic Linear Acceleration Rejection:
        # Check how much total acceleration norm deviates from 1.0g (gravity)
        accel_err = abs(accelerometer_norm - 1.0)
        if accel_err >= self.accel_rejection_threshold:
            effective_beta = 0.0
        else:
            effective_beta = self.beta * (1.0 - (accel_err / self.accel_rejection_threshold))

        accelerometer_x /= accelerometer_norm
        accelerometer_y /= accelerometer_norm
        accelerometer_z /= accelerometer_norm

        _2q1 = 2.0 * q1
        _2q2 = 2.0 * q2
        _2q3 = 2.0 * q3
        _2q4 = 2.0 * q4

        f1 = _2q2 * q4 - _2q1 * q3 - accelerometer_x
        f2 = _2q1 * q2 + _2q3 * q4 - accelerometer_y
        f3 = 1.0 - _2q2 * q2 - _2q3 * q3 - accelerometer_z

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

        s_norm = math.sqrt(s1 * s1 + s2 * s2 + s3 * s3 + s4 * s4)
        if s_norm > 0.0:
            s1 /= s_norm
            s2 /= s_norm
            s3 /= s_norm
            s4 /= s_norm

        q_dot_1 = 0.5 * (-q2 * gyroscope_x - q3 * gyroscope_y - q4 * gyroscope_z) - effective_beta * s1
        q_dot_2 = 0.5 * ( q1 * gyroscope_x + q3 * gyroscope_z - q4 * gyroscope_y) - effective_beta * s2
        q_dot_3 = 0.5 * ( q1 * gyroscope_y - q2 * gyroscope_z + q4 * gyroscope_x) - effective_beta * s3
        q_dot_4 = 0.5 * ( q1 * gyroscope_z + q2 * gyroscope_y - q3 * gyroscope_x) - effective_beta * s4

        q1 += q_dot_1 * delta_time
        q2 += q_dot_2 * delta_time
        q3 += q_dot_3 * delta_time
        q4 += q_dot_4 * delta_time

        quaternion_norm = math.sqrt(q1 * q1 + q2 * q2 + q3 * q3 + q4 * q4)
        if quaternion_norm > 0.0:
            self.quaternion = [q1 / quaternion_norm, q2 / quaternion_norm, q3 / quaternion_norm, q4 / quaternion_norm]

        return self.calculate_roll_radians()

    def calculate_roll_radians(self):
        q1, q2, q3, q4 = self.quaternion
        roll = math.atan2(2.0 * (q1 * q2 + q3 * q4), 1.0 - 2.0 * (q2 * q2 + q3 * q3))
        return max(-self.max_roll_rad, min(self.max_roll_rad, roll))


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
            self.gyroscope_bias[0] = self.decay_factor * self.gyroscope_bias[0] + self.update_factor * gyroscope_uncalibrated_x
            self.gyroscope_bias[1] = self.decay_factor * self.gyroscope_bias[1] + self.update_factor * gyroscope_uncalibrated_y
            self.gyroscope_bias[2] = self.decay_factor * self.gyroscope_bias[2] + self.update_factor * gyroscope_uncalibrated_z

    def apply_bias_correction(self, gyroscope_uncalibrated_x, gyroscope_uncalibrated_y, gyroscope_uncalibrated_z):
        return (
            gyroscope_uncalibrated_x - self.gyroscope_bias[0],
            gyroscope_uncalibrated_y - self.gyroscope_bias[1],
            gyroscope_uncalibrated_z - self.gyroscope_bias[2]
        )


def apply_deadzone_filter(value, threshold=DEFAULT_DEADZONE_THRESHOLD):
    return 0.0 if abs(value) < threshold else value


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

        gyro_uncalibrated_x = raw_gyro_x * 0.000305432619
        gyro_uncalibrated_y = raw_gyro_y * 0.000305432619
        gyro_uncalibrated_z = raw_gyro_z * 0.000305432619

        accelerometer_x = raw_accel_x * 0.000122
        accelerometer_y = raw_accel_y * 0.000122
        accelerometer_z = raw_accel_z * 0.000122

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


# ==============================================================================
# VIRTUAL DEVICE & NETWORK HELPERS
# ==============================================================================

def create_virtual_mouse_device():
    return UInput(
        {
            e.EV_REL: [e.REL_X, e.REL_Y],
            e.EV_KEY: [e.BTN_LEFT, e.BTN_RIGHT, e.BTN_MIDDLE]
        },
        name="AirMouse-Virtual-Mouse"
    )


def emit_relative_mouse_movement(virtual_mouse_device, movement_x, movement_y):
    if movement_x != 0 or movement_y != 0:
        virtual_mouse_device.write(e.EV_REL, e.REL_X, movement_x)
        virtual_mouse_device.write(e.EV_REL, e.REL_Y, movement_y)
        virtual_mouse_device.syn()


def initialize_udp_socket(server_ip, server_port):
    client_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    client_socket.setsockopt(socket.SOL_SOCKET, socket.SO_RCVBUF, 1024 * 1024)
    client_socket.settimeout(0.5)
    return client_socket


def send_heartbeat_handshake(client_socket, server_ip, server_port):
    client_socket.sendto(b"HELLO", (server_ip, server_port))


def parse_command_line_arguments():
    parser = argparse.ArgumentParser(description="Ultra-Low Latency Air Mouse CLI Client with Adjustable Acceleration")
    parser.add_argument("ip_address", type=str, help="ESP32 Wi-Fi Server IP Address")
    parser.add_argument("--port", type=int, default=8889, help="UDP Server Port (default: 8889)")
    
    # Active mode settings
    parser.add_argument("--sensitivity", type=float, default=DEFAULT_BASE_SENSITIVITY, help=f"Base Mouse Sensitivity (default: {DEFAULT_BASE_SENSITIVITY})")
    parser.add_argument("--deadzone", type=float, default=DEFAULT_DEADZONE_THRESHOLD, help=f"Gyro Deadzone Threshold (default: {DEFAULT_DEADZONE_THRESHOLD})")
    parser.add_argument("--min-cutoff", type=float, default=DEFAULT_MIN_CUTOFF_FREQUENCY, help=f"1-Euro Minimum Cutoff Frequency Hz (default: {DEFAULT_MIN_CUTOFF_FREQUENCY})")
    parser.add_argument("--beta", type=float, default=DEFAULT_SPEED_COEFFICIENT, help=f"1-Euro Speed Slope Beta (default: {DEFAULT_SPEED_COEFFICIENT})")
    parser.add_argument("--d-cutoff", type=float, default=DEFAULT_DERIVATIVE_CUTOFF, help=f"1-Euro Derivative Cutoff Hz (default: {DEFAULT_DERIVATIVE_CUTOFF})")
    
    # Acceleration settings
    parser.add_argument("--accel-factor", type=float, default=DEFAULT_ACCEL_FACTOR, help=f"Acceleration Factor (default: {DEFAULT_ACCEL_FACTOR})")
    parser.add_argument("--accel-exponent", type=float, default=DEFAULT_ACCEL_EXPONENT, help=f"Acceleration Exponent Curve (default: {DEFAULT_ACCEL_EXPONENT})")
    parser.add_argument("--accel-threshold", type=float, default=DEFAULT_ACCEL_THRESHOLD, help=f"Acceleration Speed Threshold rad/s (default: {DEFAULT_ACCEL_THRESHOLD})")
    
    # Reposition mode settings
    parser.add_argument("--reposition-sens", type=float, default=DEFAULT_REPOSITION_SENS_FACTOR, help=f"Sensitivity scale factor in reposition mode (default: {DEFAULT_REPOSITION_SENS_FACTOR})")
    parser.add_argument("--reposition-min-cutoff", type=float, default=DEFAULT_REPOSITION_MIN_CUTOFF, help=f"1-Euro min cutoff Hz in reposition mode (default: {DEFAULT_REPOSITION_MIN_CUTOFF})")
    parser.add_argument("--reposition-deadzone", type=float, default=DEFAULT_REPOSITION_DEADZONE, help=f"Deadzone threshold in reposition mode (default: {DEFAULT_REPOSITION_DEADZONE})")
    parser.add_argument("--reposition-slowdown-speed", type=float, default=DEFAULT_REPOSITION_SLOWDOWN_SPEED, help=f"Reposition slowdown speed threshold rad/s (default: {DEFAULT_REPOSITION_SLOWDOWN_SPEED})")
    parser.add_argument("--reposition-slowdown-exp", type=float, default=DEFAULT_REPOSITION_SLOWDOWN_EXP, help=f"Reposition slowdown power exponent (default: {DEFAULT_REPOSITION_SLOWDOWN_EXP})")
    
    # Orientation & Stability settings
    parser.add_argument("--accel-rejection-thresh", type=float, default=DEFAULT_ACCEL_REJECTION_THRESHOLD, help=f"Max g-force deviation before ignoring accel gravity correction (default: {DEFAULT_ACCEL_REJECTION_THRESHOLD})")
    parser.add_argument("--max-roll-deg", type=float, default=DEFAULT_MAX_ROLL_DEGREES, help=f"Max roll angle clamp in degrees (default: {DEFAULT_MAX_ROLL_DEGREES})")
    
    # Hardware clutch & click logic
    parser.add_argument("--normal-clutch", dest="invert_clutch", action="store_false", default=DEFAULT_INVERT_CLUTCH, help="Normal clutch logic (hold button to activate mouse)")
    parser.add_argument("--no-slow-on-click", dest="slow_on_click", action="store_false", default=DEFAULT_SLOW_ON_CLICK, help="Disable reposition slowdown mode during click drags")
    return parser.parse_args()


# ==============================================================================
# MAIN RUNNER
# ==============================================================================

def run_air_mouse_cli():
    arguments = parse_command_line_arguments()

    virtual_mouse_device = create_virtual_mouse_device()
    client_socket = initialize_udp_socket(arguments.ip_address, arguments.port)
    pipeline = AirMousePipeline(
        sensitivity=arguments.sensitivity,
        deadzone_threshold=arguments.deadzone,
        minimum_cutoff_frequency=arguments.min_cutoff,
        speed_coefficient=arguments.beta,
        derivative_cutoff_frequency=arguments.d_cutoff,
        acceleration_factor=arguments.accel_factor,
        acceleration_exponent=arguments.accel_exponent,
        acceleration_threshold=arguments.accel_threshold,
        invert_clutch=arguments.invert_clutch,
        slow_on_click=arguments.slow_on_click,
        reposition_sens_factor=arguments.reposition_sens,
        reposition_min_cutoff=arguments.reposition_min_cutoff,
        reposition_deadzone=arguments.reposition_deadzone,
        reposition_slowdown_speed=arguments.reposition_slowdown_speed,
        reposition_slowdown_exp=arguments.reposition_slowdown_exp,
        accel_rejection_threshold=arguments.accel_rejection_thresh,
        max_roll_degrees=arguments.max_roll_deg
    )

    print(f"[AirMouse CLI] Target: {arguments.ip_address}:{arguments.port}")
    print(f"[AirMouse CLI] Active Mode: DZ({arguments.deadzone}) > 1-EUR(fcmin={arguments.min_cutoff}, beta={arguments.beta}) > MADGWICK")
    print(f"[AirMouse CLI] Reposition Mode: Sens={arguments.reposition_sens} | DZ={arguments.reposition_deadzone} | Cutoff={arguments.reposition_min_cutoff}Hz | SlowSpeed={arguments.reposition_slowdown_speed} | Exp={arguments.reposition_slowdown_exp}")
    print(f"[AirMouse CLI] Acceleration: Factor={arguments.accel_factor}, Exponent={arguments.accel_exponent}, Threshold={arguments.accel_threshold} rad/s")
    print(f"[AirMouse CLI] Orientation Guard: AccelRejection={arguments.accel_rejection_thresh}g | MaxRoll={arguments.max_roll_deg}° | Auto Gravity Re-align on Clutch")
    print(f"[AirMouse CLI] Click Slowdown: {'ENABLED' if arguments.slow_on_click else 'DISABLED'} (reposition slowdown applies when dragging)")
    print(f"[AirMouse CLI] Virtual mouse device initialized via evdev uinput")
    print("[AirMouse CLI] Press Ctrl+C to stop.\n")

    running = True

    def signal_handler(signal_number, frame):
        nonlocal running
        running = False

    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    last_heartbeat_time = 0.0
    last_packet_timestamp = None
    packet_counter = 0
    start_time = time.monotonic()

    status_print_time = 0.0
    last_left_click = False
    last_right_click = False

    try:
        while running:
            current_time = time.monotonic()

            if current_time - last_heartbeat_time >= 0.2:
                send_heartbeat_handshake(client_socket, arguments.ip_address, arguments.port)
                last_heartbeat_time = current_time

            datagrams_to_process = []
            try:
                datagram_bytes, address = client_socket.recvfrom(1024)
                if len(datagram_bytes) in (15, 17):
                    datagrams_to_process.append(datagram_bytes)
            except socket.timeout:
                continue

            client_socket.setblocking(False)
            while True:
                try:
                    next_datagram, _ = client_socket.recvfrom(1024)
                    if len(next_datagram) in (15, 17):
                        datagrams_to_process.append(next_datagram)
                except (BlockingIOError, socket.error):
                    break
            client_socket.setblocking(True)
            client_socket.settimeout(0.5)

            if not datagrams_to_process:
                continue

            for datagram in datagrams_to_process:
                if len(datagram) == 17:
                    unpacked_packet = struct.unpack("<HBhhhhhhH", datagram)
                else:
                    unpacked_packet = struct.unpack("<HBhhhhhh", datagram)

                delta_time = (current_time - last_packet_timestamp) if last_packet_timestamp else 0.01
                if delta_time <= 0.0 or delta_time > 0.5:
                    delta_time = 0.01
                last_packet_timestamp = current_time

                movement_x, movement_y, is_active, is_left_click, is_right_click = pipeline.process_frame(unpacked_packet, current_time, delta_time)

                if is_left_click != last_left_click:
                    virtual_mouse_device.write(e.EV_KEY, e.BTN_LEFT, 1 if is_left_click else 0)
                    virtual_mouse_device.syn()
                    last_left_click = is_left_click

                if is_right_click != last_right_click:
                    virtual_mouse_device.write(e.EV_KEY, e.BTN_RIGHT, 1 if is_right_click else 0)
                    virtual_mouse_device.syn()
                    last_right_click = is_right_click

                emit_relative_mouse_movement(virtual_mouse_device, movement_x, movement_y)

                packet_counter += 1

            if current_time - status_print_time >= 2.0:
                elapsed = current_time - start_time
                packet_rate = packet_counter / elapsed
                pot_val = pipeline.raw_potentiometer
                pot_pct = int(pipeline.potentiometer_ratio * 100)
                if not is_active:
                    current_mode_str = "REPOSITION"
                elif (last_left_click or last_right_click) and pipeline.slow_on_click:
                    current_mode_str = "DRAG-SLOW"
                else:
                    current_mode_str = "ACTIVE"
                status_text = f"\r[AirMouse CLI] Streaming @ {packet_rate:.1f} Hz | Pot: {pot_val} ({pot_pct}%) | Sens: {pipeline.sensitivity:.2f} | Mode: {current_mode_str} | L: {'DOWN' if last_left_click else 'UP'} | R: {'DOWN' if last_right_click else 'UP'}   "
                sys.stdout.write(status_text)
                sys.stdout.flush()
                status_print_time = current_time

    finally:
        sys.stdout.write("\n[AirMouse CLI] Shutting down...\n")
        sys.stdout.flush()
        try:
            if last_left_click or last_right_click:
                virtual_mouse_device.write(e.EV_KEY, e.BTN_LEFT, 0)
                virtual_mouse_device.write(e.EV_KEY, e.BTN_RIGHT, 0)
                virtual_mouse_device.syn()
        except Exception:
            pass
        client_socket.close()
        virtual_mouse_device.close()


def main():
    run_air_mouse_cli()


if __name__ == "__main__":
    main()
