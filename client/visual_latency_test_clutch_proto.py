"""
Visual Latency & IMU Telemetry Dashboard - 85% Pointer Display & Fullscreen Prototype
A Pygame GUI client that connects to the ESP32 Wi-Fi server,
renders an 85% main pointer display with center-reset trace tracking,
and provides a 15% telemetry & controls sidebar with Fullscreen toggle (F key).
"""
import sys
import socket
import threading
import pygame
import struct
import time
import math
from collections import deque

# Network Configuration
PORT = 8889
HEARTBEAT_INTERVAL = 0.2  # Client keep-alive heartbeat interval (5 Hz)

# UI Theme Colors (Dark Cyberpunk / Sleek Dashboard)
COLOR_BG           = (15, 17, 26)       # Deep slate
COLOR_PANEL_BG     = (22, 26, 38)       # Dark panel container
COLOR_PANEL_BORDER = (40, 48, 68)       # Border outline
COLOR_TEXT_MAIN    = (235, 240, 255)    # Bright text
COLOR_TEXT_MUTED   = (130, 145, 170)    # Subdued label text
COLOR_GRID         = (32, 38, 54)       # Subtle graph grid lines
COLOR_ZERO_LINE    = (60, 70, 95)       # Graph zero axis

# Graph Trace Colors
COLOR_X_AXIS = (255, 77, 109)   # Neon Crimson (X-axis)
COLOR_Y_AXIS = (0, 245, 212)    # Neon Mint/Teal (Y-axis)
COLOR_Z_AXIS = (0, 180, 216)    # Cyan/Blue (Z-axis)

COLOR_ACCEL_X = (255, 190, 11)  # Amber Yellow
COLOR_ACCEL_Y = (131, 56, 236)  # Electric Purple
COLOR_ACCEL_Z = (58, 134, 255)  # Bright Blue

# Button State Colors
COLOR_BTN_UP   = (220, 50, 70)   # Red glow
COLOR_BTN_DOWN = (40, 220, 120)  # Emerald Green glow

# Global Telemetry State
button_state = "UP"
running = True

connection_status = "Connecting..."
conn_start_time = None
last_heartbeat_seq = -1
dropped_packets = 0
heartbeats_received = 0
btn_presses = 0
heartbeat_hz = 0.0

gyro_vals  = [0.0, 0.0, 0.0]
accel_vals = [0.0, 0.0, 0.0]

# Gravity Alignment & Sensor State
active_stage_name = "SEARCHING"
roll_angle_rad  = 0.0
roll_angle_deg  = 0.0

screen_pitch_rate = 0.0
screen_yaw_rate   = 0.0
roll_comp_enabled = True

# Sensor Data Filtering State (Sequential Pipeline)
deadzone_enabled = False
deadzone_threshold = 0.025

ema_enabled = False
ema_alpha = 0.35

one_euro_enabled = False

madgwick_enabled = True
madgwick_beta = 0.1

mahony_enabled = False
mahony_kp = 0.5
mahony_ki = 0.02    # Integral feedback gain for active gyro drift correction

# Hardware/Software Calibration State
gyro_bias = [0.0, 0.0, 0.0]     # [gx_bias, gy_bias, gz_bias] in rad/s
is_calibrating = False
calib_samples = []
auto_zero_enabled = True         # Auto-adapt zero bias when idle & stationary


class EmaFilter:
    """Exponential Moving Average (IIR Low-Pass) Filter."""
    def __init__(self, alpha=0.35):
        self.alpha = float(alpha)
        self.value = None

    def filter(self, val):
        if self.value is None:
            self.value = float(val)
        else:
            self.value = self.alpha * val + (1.0 - self.alpha) * self.value
        return self.value

    def reset(self):
        self.value = None


class OneEuroFilter:
    """
    1-Euro Filter for adaptive low-latency interactive pointing (Casiez et al.).
    Dynamically adjusts cutoff frequency based on movement velocity:
    High filtering during slow motion (removes tremor), minimal filtering during fast motion (low latency).
    """
    def __init__(self, min_cutoff=1.0, beta=0.007, d_cutoff=1.0):
        self.min_cutoff = float(min_cutoff)
        self.beta = float(beta)
        self.d_cutoff = float(d_cutoff)
        self.x_prev = None
        self.dx_prev = 0.0
        self.t_prev = None

    def _alpha(self, cutoff, dt):
        tau = 1.0 / (2.0 * math.pi * cutoff)
        return 1.0 / (1.0 + tau / dt)

    def filter(self, val, timestamp=None):
        if timestamp is None:
            timestamp = time.monotonic()

        if self.x_prev is None or self.t_prev is None:
            self.x_prev = float(val)
            self.dx_prev = 0.0
            self.t_prev = timestamp
            return float(val)

        dt = timestamp - self.t_prev
        if dt <= 0.0:
            dt = 1e-5

        self.t_prev = timestamp

        # Derivative (velocity) estimation
        d_val = (val - self.x_prev) / dt
        alpha_d = self._alpha(self.d_cutoff, dt)
        dx = alpha_d * d_val + (1.0 - alpha_d) * self.dx_prev
        self.dx_prev = dx

        # Speed-adaptive cutoff frequency
        cutoff = self.min_cutoff + self.beta * abs(dx)
        alpha = self._alpha(cutoff, dt)

        x_filtered = alpha * val + (1.0 - alpha) * self.x_prev
        self.x_prev = x_filtered
        return x_filtered

    def reset(self):
        self.x_prev = None
        self.dx_prev = 0.0
        self.t_prev = None


class MadgwickFilter:
    """
    Madgwick AHRS 6-DOF (Gyroscope + Accelerometer) Gradient Descent Orientation Filter.
    """
    def __init__(self, beta=0.1):
        self.beta = float(beta)
        self.q = [1.0, 0.0, 0.0, 0.0]

    def update(self, gx, gy, gz, ax, ay, az, dt):
        q1, q2, q3, q4 = self.q

        norm = math.sqrt(ax * ax + ay * ay + az * az)
        if norm == 0.0:
            return self.get_roll()
        ax /= norm
        ay /= norm
        az /= norm

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

        s_norm = math.sqrt(s1 * s1 + s2 * s2 + s3 * s3 + s4 * s4)
        if s_norm > 0.0:
            s1 /= s_norm
            s2 /= s_norm
            s3 /= s_norm
            s4 /= s_norm

        qDot1 = 0.5 * (-q2 * gx - q3 * gy - q4 * gz) - self.beta * s1
        qDot2 = 0.5 * ( q1 * gx + q3 * gz - q4 * gy) - self.beta * s2
        qDot3 = 0.5 * ( q1 * gy - q2 * gz + q4 * gx) - self.beta * s3
        qDot4 = 0.5 * ( q1 * gz + q2 * gy - q3 * gx) - self.beta * s4

        q1 += qDot1 * dt
        q2 += qDot2 * dt
        q3 += qDot3 * dt
        q4 += qDot4 * dt

        q_norm = math.sqrt(q1 * q1 + q2 * q2 + q3 * q3 + q4 * q4)
        if q_norm > 0.0:
            self.q = [q1 / q_norm, q2 / q_norm, q3 / q_norm, q4 / q_norm]

        return self.get_roll()

    def get_roll(self):
        q1, q2, q3, q4 = self.q
        return math.atan2(2.0 * (q1 * q2 + q3 * q4), 1.0 - 2.0 * (q2 * q2 + q3 * q3))

    def reset(self):
        self.q = [1.0, 0.0, 0.0, 0.0]


class MahonyFilter:
    """
    Mahony AHRS 6-DOF Explicit Complementary Filter with proportional & integral feedback.
    """
    def __init__(self, kp=0.5, ki=0.0):
        self.kp = float(kp)
        self.ki = float(ki)
        self.q = [1.0, 0.0, 0.0, 0.0]
        self.e_int = [0.0, 0.0, 0.0]

    def update(self, gx, gy, gz, ax, ay, az, dt):
        q1, q2, q3, q4 = self.q

        norm = math.sqrt(ax * ax + ay * ay + az * az)
        if norm == 0.0:
            return self.get_roll()
        ax /= norm
        ay /= norm
        az /= norm

        vx = 2.0 * (q2 * q4 - q1 * q3)
        vy = 2.0 * (q1 * q2 + q3 * q4)
        vz = q1 * q1 - q2 * q2 - q3 * q3 + q4 * q4

        ex = (ay * vz - az * vy)
        ey = (az * vx - ax * vz)
        ez = (ax * vy - ay * vx)

        if self.ki > 0.0:
            self.e_int[0] += ex * dt
            self.e_int[1] += ey * dt
            self.e_int[2] += ez * dt
            gx += self.ki * self.e_int[0]
            gy += self.ki * self.e_int[1]
            gz += self.ki * self.e_int[2]

        gx += self.kp * ex
        gy += self.kp * ey
        gz += self.kp * ez

        qDot1 = 0.5 * (-q2 * gx - q3 * gy - q4 * gz)
        qDot2 = 0.5 * ( q1 * gx + q3 * gz - q4 * gy)
        qDot3 = 0.5 * ( q1 * gy - q2 * gz + q4 * gx)
        qDot4 = 0.5 * ( q1 * gz + q2 * gy - q3 * gx)

        q1 += qDot1 * dt
        q2 += qDot2 * dt
        q3 += qDot3 * dt
        q4 += qDot4 * dt

        q_norm = math.sqrt(q1 * q1 + q2 * q2 + q3 * q3 + q4 * q4)
        if q_norm > 0.0:
            self.q = [q1 / q_norm, q2 / q_norm, q3 / q_norm, q4 / q_norm]

        return self.get_roll()

    def get_roll(self):
        q1, q2, q3, q4 = self.q
        return math.atan2(2.0 * (q1 * q2 + q3 * q4), 1.0 - 2.0 * (q2 * q2 + q3 * q3))

    def reset(self):
        self.q = [1.0, 0.0, 0.0, 0.0]
        self.e_int = [0.0, 0.0, 0.0]


def apply_deadzone(val, threshold=0.025):
    """Zeroes out readings smaller than threshold to eliminate idle drift."""
    return 0.0 if abs(val) < threshold else val


# Filter Instances
ema_gx = EmaFilter(alpha=ema_alpha)
ema_gy = EmaFilter(alpha=ema_alpha)
ema_gz = EmaFilter(alpha=ema_alpha)

one_euro_gx = OneEuroFilter(min_cutoff=1.5, beta=0.020, d_cutoff=2.0)
one_euro_gy = OneEuroFilter(min_cutoff=1.5, beta=0.020, d_cutoff=2.0)
one_euro_gz = OneEuroFilter(min_cutoff=1.5, beta=0.020, d_cutoff=2.0)

madgwick_filter = MadgwickFilter(beta=madgwick_beta)
mahony_filter = MahonyFilter(kp=mahony_kp, ki=mahony_ki)

ema_roll = EmaFilter(alpha=0.2)



# Dynamic Canvas Dimensions (shared between threads)
canvas_dimensions = [800.0, 600.0]

# Graph rolling histories (300 points = 3 sec window at 100Hz)
HISTORY_LEN = 300
gyro_hist_x = deque([0.0]*HISTORY_LEN, maxlen=HISTORY_LEN)
gyro_hist_y = deque([0.0]*HISTORY_LEN, maxlen=HISTORY_LEN)
gyro_hist_z = deque([0.0]*HISTORY_LEN, maxlen=HISTORY_LEN)

accel_hist_x = deque([0.0]*HISTORY_LEN, maxlen=HISTORY_LEN)
accel_hist_y = deque([0.0]*HISTORY_LEN, maxlen=HISTORY_LEN)
accel_hist_z = deque([0.0]*HISTORY_LEN, maxlen=HISTORY_LEN)

roll_hist = deque([0.0]*HISTORY_LEN, maxlen=HISTORY_LEN)

# 2D Air Mouse Pointer State
pointer_pos   = [400.0, 300.0]
pointer_trail = deque(maxlen=300)

_hz_count = 0
_hz_last_time = 0.0


def network_thread(ip):
    global button_state, running, conn_start_time, connection_status
    global last_heartbeat_seq, dropped_packets, heartbeats_received, btn_presses
    global heartbeat_hz, _hz_count, _hz_last_time
    global gyro_vals, accel_vals, pointer_pos, pointer_trail
    global roll_angle_rad, roll_angle_deg, screen_pitch_rate, screen_yaw_rate
    global active_stage_name
    global deadzone_enabled, deadzone_threshold
    global ema_enabled, one_euro_enabled, madgwick_enabled, mahony_enabled
    global gyro_bias, is_calibrating, calib_samples, auto_zero_enabled

    last_packet_time = None

    while running:
        try:
            connection_status = "Connecting..."
            with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
                s.setsockopt(socket.SOL_SOCKET, socket.SO_RCVBUF, 1024 * 1024)
                s.settimeout(2.0)

                # Send registration handshake
                s.sendto(b"HELLO", (ip, PORT))
                connection_status = "Waiting for stream..."
                conn_start_time = time.monotonic()
                _hz_last_time = time.monotonic()
                _hz_count = 0

                inner_running = True
                def keepalive():
                    while running and inner_running:
                        try:
                            s.sendto(b"HELLO", (ip, PORT))
                        except Exception:
                            pass
                        time.sleep(HEARTBEAT_INTERVAL)
                threading.Thread(target=keepalive, daemon=True).start()

                first_packet_received = False
                while running:
                    try:
                        data, addr = s.recvfrom(1024)
                        if not first_packet_received:
                            connection_status = "CONNECTED"
                            first_packet_received = True
                    except socket.timeout:
                        connection_status = "DISCONNECTED (Timeout)"
                        inner_running = False
                        break

                    if len(data) == 15:
                        seq, buttons, gx_raw, gy_raw, gz_raw, ax_raw, ay_raw, az_raw = struct.unpack('<HBhhhhhh', data)
                        heartbeats_received += 1

                        # Extract button bitmask (Bit 0: Clutch)
                        new_is_down = bool(buttons & 0x01)
                        if new_is_down and button_state != "DOWN":
                            btn_presses += 1
                        button_state = "DOWN" if new_is_down else "UP"

                        now = time.monotonic()
                        dt = (now - last_packet_time) if last_packet_time else 0.01
                        if dt <= 0.0 or dt > 0.5:
                            dt = 0.01
                        last_packet_time = now

                        gx_uncal = gx_raw * 0.000305432619
                        gy_uncal = gy_raw * 0.000305432619
                        gz_uncal = gz_raw * 0.000305432619
                        ax = ax_raw * 0.000122
                        ay = ay_raw * 0.000122
                        az = az_raw * 0.000122

                        # 0A. Handle Active Calibration Sampling (1-second / 100-packet capture)
                        if is_calibrating:
                            calib_samples.append((gx_uncal, gy_uncal, gz_uncal))
                            if len(calib_samples) >= 100:
                                n = float(len(calib_samples))
                                gyro_bias[0] = sum(s[0] for s in calib_samples) / n
                                gyro_bias[1] = sum(s[1] for s in calib_samples) / n
                                gyro_bias[2] = sum(s[2] for s in calib_samples) / n
                                is_calibrating = False
                                print(f"[Calibration Complete] Gyro Bias Offsets (rad/s): X={gyro_bias[0]:+.4f}, Y={gyro_bias[1]:+.4f}, Z={gyro_bias[2]:+.4f}")

                        # 0B. Auto Zero-Velocity Update (ZUPT) when Clutch is UP and stationary
                        elif auto_zero_enabled and button_state == "UP":
                            motion_mag = math.sqrt(gx_uncal*gx_uncal + gy_uncal*gy_uncal + gz_uncal*gz_uncal)
                            if motion_mag < 0.06:
                                gyro_bias[0] = 0.992 * gyro_bias[0] + 0.008 * gx_uncal
                                gyro_bias[1] = 0.992 * gyro_bias[1] + 0.008 * gy_uncal
                                gyro_bias[2] = 0.992 * gyro_bias[2] + 0.008 * gz_uncal

                        # Apply zero-bias offset correction
                        gx_raw_val = gx_uncal - gyro_bias[0]
                        gy_raw_val = gy_uncal - gyro_bias[1]
                        gz_raw_val = gz_uncal - gyro_bias[2]

                        gx, gy, gz = gx_raw_val, gy_raw_val, gz_raw_val
                        pipeline_stages = []

                        # Stage 1: Deadzone Filter
                        if deadzone_enabled:
                            gx = apply_deadzone(gx, deadzone_threshold)
                            gy = apply_deadzone(gy, deadzone_threshold)
                            gz = apply_deadzone(gz, deadzone_threshold)
                            pipeline_stages.append("DZ")

                        # Stage 2: Exponential Moving Average Filter
                        if ema_enabled:
                            gx = ema_gx.filter(gx)
                            gy = ema_gy.filter(gy)
                            gz = ema_gz.filter(gz)
                            pipeline_stages.append("EMA")

                        # Stage 3: 1-Euro Adaptive Low-Pass Filter
                        if one_euro_enabled:
                            gx = one_euro_gx.filter(gx, now)
                            gy = one_euro_gy.filter(gy, now)
                            gz = one_euro_gz.filter(gz, now)
                            pipeline_stages.append("1-EUR")

                        # Base accelerometer roll angle
                        raw_roll_rad = math.atan2(ax, az)
                        roll_rad = raw_roll_rad

                        # Stage 4 / 5: Madgwick or Mahony AHRS Orientation Fusion
                        if madgwick_enabled:
                            roll_rad = madgwick_filter.update(gx, gy, gz, ax, ay, az, dt)
                            pipeline_stages.append("MADGWICK")
                        elif mahony_enabled:
                            roll_rad = mahony_filter.update(gx, gy, gz, ax, ay, az, dt)
                            pipeline_stages.append("MAHONY")
                        else:
                            roll_rad = ema_roll.filter(raw_roll_rad)

                        active_stage_name = " > ".join(pipeline_stages) if pipeline_stages else "RAW"

                        gyro_vals[0], gyro_vals[1], gyro_vals[2] = gx, gy, gz
                        accel_vals[0], accel_vals[1], accel_vals[2] = ax, ay, az

                        roll_deg = math.degrees(roll_rad)
                        roll_angle_rad, roll_angle_deg = roll_rad, roll_deg

                        if roll_comp_enabled:
                            gx_screen =  gx * math.cos(roll_rad) - gz * math.sin(roll_rad)
                            gz_screen =  gx * math.sin(roll_rad) + gz * math.cos(roll_rad)
                        else:
                            gx_screen = gx
                            gz_screen = gz

                        screen_pitch_rate = gx_screen
                        screen_yaw_rate   = gz_screen

                        gyro_hist_x.append(gx)
                        gyro_hist_y.append(gy)
                        gyro_hist_z.append(gz)
                        accel_hist_x.append(ax)
                        accel_hist_y.append(ay)
                        accel_hist_z.append(az)
                        roll_hist.append(roll_deg)

                        cw, ch = canvas_dimensions[0], canvas_dimensions[1]
                        center_x = cw / 2.0
                        center_y = ch / 2.0

                        if button_state == "DOWN":
                            pointer_pos[0] -= gz_screen * 14.0
                            pointer_pos[1] -= gx_screen * 14.0
                            pointer_pos[0] = max(10.0, min(cw - 10.0, pointer_pos[0]))
                            pointer_pos[1] = max(10.0, min(ch - 10.0, pointer_pos[1]))
                            pointer_trail.append((pointer_pos[0], pointer_pos[1]))
                        else:
                            # Reset pointer to center of canvas immediately when button is released
                            pointer_pos[0] = center_x
                            pointer_pos[1] = center_y
                            pointer_trail.clear()

                        # Drop detection check
                        if last_heartbeat_seq != -1 and seq > (last_heartbeat_seq + 1) % 65536:
                            diff = (seq - last_heartbeat_seq) % 65536 - 1
                            if diff < 1000:
                                dropped_packets += diff
                        last_heartbeat_seq = seq

                        # Frequency computation
                        _hz_count += 1
                        now = time.monotonic()
                        elapsed = now - _hz_last_time
                        if elapsed >= 1.0:
                            heartbeat_hz = _hz_count / elapsed
                            _hz_count = 0
                            _hz_last_time = now
        except Exception as e:
            if running:
                import traceback
                print(f"[Client Error] network_thread exception: {e}")
                traceback.print_exc()
                connection_status = "Error. Retrying..."
                time.sleep(1.0)


def draw_panel(surface, rect, title=None, font=None):
    """Draws a modern rounded panel with subtle border."""
    pygame.draw.rect(surface, COLOR_PANEL_BG, rect, border_radius=8)
    pygame.draw.rect(surface, COLOR_PANEL_BORDER, rect, width=1, border_radius=8)
    if title and font:
        title_surf = font.render(title, True, COLOR_TEXT_MUTED)
        surface.blit(title_surf, (rect.x + 12, rect.y + 8))


def draw_graph(surface, rect, channels, v_min, v_max, title, font):
    """Renders a multi-channel real-time oscilloscope graph."""
    draw_panel(surface, rect, title, font)

    px = rect.x + 45
    py = rect.y + 28
    pw = rect.width - 55
    ph = rect.height - 38

    if pw <= 10 or ph <= 10:
        return

    plot_rect = pygame.Rect(px, py, pw, ph)
    pygame.draw.rect(surface, (14, 17, 26), plot_rect, border_radius=4)
    pygame.draw.rect(surface, (35, 42, 60), plot_rect, width=1, border_radius=4)

    num_grid = 3
    for i in range(num_grid + 1):
        gy = py + (ph * i / num_grid)
        val = v_max - (i * (v_max - v_min) / num_grid)
        pygame.draw.line(surface, COLOR_GRID, (px, gy), (px + pw, gy), 1)
        label_surf = font.render(f"{val:>4.0f}", True, COLOR_TEXT_MUTED)
        surface.blit(label_surf, (rect.x + 4, gy - 6))

    if v_min < 0 < v_max:
        zero_y = py + ph * (v_max - 0) / (v_max - v_min)
        pygame.draw.line(surface, COLOR_ZERO_LINE, (px, zero_y), (px + pw, zero_y), 1)

    for name, history_data, color in channels:
        if len(history_data) < 2:
            continue
        points = []
        n = len(history_data)
        for i, val in enumerate(history_data):
            x = px + (i * pw / (n - 1))
            clamped = max(v_min, min(v_max, val))
            y = py + ph * (v_max - clamped) / (v_max - v_min)
            points.append((x, y))

        if len(points) >= 2:
            pygame.draw.lines(surface, color, False, points, width=2)


def main():
    global running, roll_comp_enabled, pointer_pos, canvas_dimensions
    global deadzone_enabled, ema_enabled, one_euro_enabled, madgwick_enabled, mahony_enabled
    global gyro_bias, is_calibrating, calib_samples, auto_zero_enabled

    if len(sys.argv) < 2:
        print("Usage: python visual_latency_test_clutch_proto.py <ESP32_IP>")
        sys.exit(1)

    ip = sys.argv[1]

    t = threading.Thread(target=network_thread, args=(ip,), daemon=True)
    t.start()

    pygame.init()
    pygame.font.init()

    window_w, window_h = 1280, 768
    flags = pygame.RESIZABLE | pygame.DOUBLEBUF
    try:
        screen = pygame.display.set_mode((window_w, window_h), flags, vsync=1)
    except Exception:
        screen = pygame.display.set_mode((window_w, window_h), flags)

    pygame.display.set_caption("AIR MOUSE // Fullscreen Pointer & Telemetry Dashboard")
    clock = pygame.time.Clock()

    try:
        font_title = pygame.font.SysFont("monospace", 16, bold=True)
        font_main  = pygame.font.SysFont("monospace", 12, bold=True)
        font_small = pygame.font.SysFont("monospace", 10)
        font_large = pygame.font.SysFont("monospace", 24, bold=True)
    except Exception:
        font_title = pygame.font.SysFont(None, 20)
        font_main  = pygame.font.SysFont(None, 16)
        font_small = pygame.font.SysFont(None, 12)
        font_large = pygame.font.SysFont(None, 30)

    is_fullscreen = False

    while running:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE and is_fullscreen:
                    is_fullscreen = False
                    screen = pygame.display.set_mode((window_w, window_h), flags)
                elif event.key in (pygame.K_f, pygame.K_F11):
                    is_fullscreen = not is_fullscreen
                    if is_fullscreen:
                        screen = pygame.display.set_mode((0, 0), pygame.FULLSCREEN | flags)
                    else:
                        screen = pygame.display.set_mode((window_w, window_h), flags)
                elif event.key == pygame.K_g:
                    roll_comp_enabled = not roll_comp_enabled
                elif event.key == pygame.K_r:
                    cw, ch = canvas_dimensions[0], canvas_dimensions[1]
                    pointer_pos = [cw / 2.0, ch / 2.0]
                    pointer_trail.clear()
                elif event.key == pygame.K_c:
                    is_calibrating = True
                    calib_samples = []
                    print("[Calibration] Capturing 100 stationary gyro samples for zero-offset calculation...")
                elif event.key == pygame.K_z:
                    auto_zero_enabled = not auto_zero_enabled
                elif event.key == pygame.K_d:
                    deadzone_enabled = not deadzone_enabled
                elif event.key == pygame.K_e:
                    ema_enabled = not ema_enabled
                elif event.key in (pygame.K_1, pygame.K_KP1):
                    one_euro_enabled = not one_euro_enabled
                elif event.key == pygame.K_m:
                    madgwick_enabled = not madgwick_enabled
                    if madgwick_enabled:
                        mahony_enabled = False
                elif event.key == pygame.K_h:
                    mahony_enabled = not mahony_enabled
                    if mahony_enabled:
                        madgwick_enabled = False
                elif event.key in (pygame.K_0, pygame.K_KP0):
                    deadzone_enabled = False
                    ema_enabled = False
                    one_euro_enabled = False
                    madgwick_enabled = False
                    mahony_enabled = False

        sw, sh = screen.get_size()
        screen.fill(COLOR_BG)

        # ====================================================================
        # Top Header Bar
        # ====================================================================
        header_rect = pygame.Rect(10, 8, sw - 20, 42)
        draw_panel(screen, header_rect)

        title_surf = font_title.render(f"AIR MOUSE // PIPELINE: {active_stage_name}", True, COLOR_TEXT_MAIN)
        screen.blit(title_surf, (20, 18))

        is_conn = (connection_status == "CONNECTED")
        badge_bg = (20, 60, 40) if is_conn else (60, 20, 30)
        badge_border = (40, 180, 100) if is_conn else (220, 60, 80)
        badge_rect = pygame.Rect(340, 15, 150, 28)
        pygame.draw.rect(screen, badge_bg, badge_rect, border_radius=14)
        pygame.draw.rect(screen, badge_border, badge_rect, width=1, border_radius=14)

        badge_txt = font_main.render(connection_status, True, badge_border)
        badge_txt_rect = badge_txt.get_rect(center=badge_rect.center)
        screen.blit(badge_txt, badge_txt_rect)

        conn_time = (time.monotonic() - conn_start_time) if conn_start_time else 0.0
        metrics_str = f"FREQ: {heartbeat_hz:>5.1f} Hz | RX: {heartbeats_received:<6} | DROPS: {dropped_packets:<3} | UPTIME: {conn_time:.1f}s"
        metrics_surf = font_main.render(metrics_str, True, COLOR_TEXT_MUTED)
        screen.blit(metrics_surf, (510, 21))

        # ====================================================================
        # Layout Calculations (85% Main Canvas / 15% Telemetry Sidebar)
        # ====================================================================
        margin = 10
        top_offset = 58
        avail_w = sw - (margin * 3)
        avail_h = sh - top_offset - margin

        canvas_w = int(avail_w * 0.85)
        sidebar_w = avail_w - canvas_w

        canvas_panel_rect = pygame.Rect(margin, top_offset, canvas_w, avail_h)
        sidebar_panel_rect = pygame.Rect(margin + canvas_w + margin, top_offset, sidebar_w, avail_h)

        # Update global canvas dimensions for physics thread
        c_x = canvas_panel_rect.x + 12
        c_y = canvas_panel_rect.y + 28
        c_w = canvas_panel_rect.width - 24
        c_h = canvas_panel_rect.height - 38
        canvas_dimensions[0] = float(c_w)
        canvas_dimensions[1] = float(c_h)

        # ====================================================================
        # 85% Pointer Display Canvas
        # ====================================================================
        draw_panel(screen, canvas_panel_rect, "AIR MOUSE 2D MOTION CANVAS (85% DISPLAY AREA)", font_small)

        canvas_box = pygame.Rect(c_x, c_y, c_w, c_h)
        pygame.draw.rect(screen, (12, 14, 22), canvas_box, border_radius=6)
        pygame.draw.rect(screen, (35, 42, 60), canvas_box, width=1, border_radius=6)

        mid_x = c_x + c_w // 2
        mid_y = c_y + c_h // 2
        pygame.draw.line(screen, COLOR_GRID, (mid_x, c_y), (mid_x, c_y + c_h), 1)
        pygame.draw.line(screen, COLOR_GRID, (c_x, mid_y), (c_x + c_w, mid_y), 1)
        pygame.draw.circle(screen, COLOR_GRID, (mid_x, mid_y), int(min(c_w, c_h) * 0.15), width=1)

        # Draw Pointer Trace & Cursor ONLY when Clutch Button is DOWN
        if button_state == "DOWN":
            trail_pts = list(pointer_trail)
            if len(trail_pts) >= 2:
                for idx in range(len(trail_pts) - 1):
                    p1 = (c_x + trail_pts[idx][0], c_y + trail_pts[idx][1])
                    p2 = (c_x + trail_pts[idx+1][0], c_y + trail_pts[idx+1][1])
                    alpha = int(255 * (idx + 1) / len(trail_pts))
                    color = (0, alpha, int(alpha * 0.8))
                    pygame.draw.line(screen, color, p1, p2, width=3)

            cur_px = c_x + pointer_pos[0]
            cur_py = c_y + pointer_pos[1]
            pygame.draw.circle(screen, (0, 255, 200), (int(cur_px), int(cur_py)), 10)
            pygame.draw.circle(screen, (255, 255, 255), (int(cur_px), int(cur_py)), 12, width=2)

            pos_txt = font_small.render(f"TRACING ACTIVE | POS: X={pointer_pos[0]:.1f} Y={pointer_pos[1]:.1f} | ROLL: {roll_angle_deg:+6.1f}°", True, (0, 245, 212))
            screen.blit(pos_txt, (c_x + 10, c_y + c_h - 20))
        else:
            idle_txt = font_main.render("CLUTCH RELEASED — PRESS & HOLD CLUTCH BUTTON TO DRAW MOTION TRACE", True, COLOR_TEXT_MUTED)
            idle_rect = idle_txt.get_rect(center=(mid_x, mid_y))
            pygame.draw.rect(screen, (20, 24, 36), idle_rect.inflate(20, 10), border_radius=6)
            screen.blit(idle_txt, idle_rect)

        # ====================================================================
        # 15% Telemetry Sidebar
        # ====================================================================
        draw_panel(screen, sidebar_panel_rect, "INFO SPACES (15%)", font_small)

        sb_x = sidebar_panel_rect.x + 10
        sb_y = sidebar_panel_rect.y + 28
        sb_w = sidebar_panel_rect.width - 20

        # 1. Clutch Button Status Box
        b_box_h = 80
        b_rect = pygame.Rect(sb_x, sb_y, sb_w, b_box_h)
        is_down = (button_state == "DOWN")
        b_color_bg     = (15, 60, 35) if is_down else (55, 18, 25)
        b_color_border = COLOR_BTN_DOWN if is_down else COLOR_BTN_UP

        pygame.draw.rect(screen, b_color_bg, b_rect, border_radius=8)
        pygame.draw.rect(screen, b_color_border, b_rect, width=2, border_radius=8)

        btn_lbl = font_large.render(button_state, True, (255, 255, 255))
        btn_lbl_rect = btn_lbl.get_rect(center=(b_rect.centerx, b_rect.centery - 8))
        screen.blit(btn_lbl, btn_lbl_rect)

        press_lbl = font_small.render(f"PRESSES: {btn_presses}", True, COLOR_TEXT_MUTED)
        press_lbl_rect = press_lbl.get_rect(center=(b_rect.centerx, b_rect.centery + 18))
        screen.blit(press_lbl, press_lbl_rect)

        sb_y += b_box_h + 10

        # 2. Real-time Gyro Oscilloscope Graph
        graph_h = int((sidebar_panel_rect.bottom - sb_y - 320))
        if graph_h > 60:
            graph_rect = pygame.Rect(sb_x, sb_y, sb_w, graph_h)
            gyro_channels = [
                ("GX", list(gyro_hist_x), COLOR_X_AXIS),
                ("GY", list(gyro_hist_y), COLOR_Y_AXIS),
                ("GZ", list(gyro_hist_z), COLOR_Z_AXIS)
            ]
            draw_graph(screen, graph_rect, gyro_channels, -5.0, 5.0, "GYRO (rad/s)", font_small)
            sb_y += graph_h + 10

        # 3. Telemetry Readout & Key Guide Box
        info_box_h = sidebar_panel_rect.bottom - sb_y - 10
        if info_box_h > 50:
            info_box_rect = pygame.Rect(sb_x, sb_y, sb_w, info_box_h)
            draw_panel(screen, info_box_rect)

            comp_status = "ON" if roll_comp_enabled else "OFF"
            comp_color  = (0, 245, 212) if roll_comp_enabled else (255, 77, 109)

            c_on  = (0, 245, 212)
            c_off = (255, 77, 109)

            calib_str = "CALIBRATING..." if is_calibrating else ("AUTO" if auto_zero_enabled else "OFF")
            calib_col = (255, 190, 11) if is_calibrating else (c_on if auto_zero_enabled else c_off)

            info_lines = [
                ("BIAS CALIB", calib_str, calib_col),
                ("BIAS (Z)", f"{gyro_bias[2]:+.4f}", COLOR_TEXT_MUTED),
                ("DEADZONE", "ON" if deadzone_enabled else "OFF", c_on if deadzone_enabled else c_off),
                ("EMA LPF", "ON" if ema_enabled else "OFF", c_on if ema_enabled else c_off),
                ("1-EURO", "ON" if one_euro_enabled else "OFF", c_on if one_euro_enabled else c_off),
                ("MADGWICK", "ON" if madgwick_enabled else "OFF", c_on if madgwick_enabled else c_off),
                ("MAHONY", "ON" if mahony_enabled else "OFF", c_on if mahony_enabled else c_off),
                ("ROLL COMP", comp_status, comp_color),
                ("PITCH RATE", f"{screen_pitch_rate:+5.2f}", COLOR_TEXT_MUTED),
                ("YAW RATE", f"{screen_yaw_rate:+5.2f}", COLOR_TEXT_MUTED),
                ("ROLL DEG", f"{roll_angle_deg:+5.1f}°", COLOR_TEXT_MUTED),
                ("KEY [C]", "CALIB ZERO", (255, 190, 11)),
                ("KEY [Z]", "AUTO-ZUPT", (255, 190, 11)),
                ("KEY [D]", "DEADZONE", (255, 190, 11)),
                ("KEY [E]", "EMA LPF", (255, 190, 11)),
                ("KEY [1]", "1-EURO", (255, 190, 11)),
                ("KEY [M]", "MADGWICK", (255, 190, 11)),
                ("KEY [H]", "MAHONY", (255, 190, 11)),
                ("KEY [0]", "CLEAR ALL", (255, 190, 11)),
                ("KEY [F]", "FULLSCREEN", (255, 190, 11)),
                ("KEY [G]", "ROLL COMP", (255, 190, 11)),
                ("KEY [R]", "RESET CENT", (255, 190, 11)),
            ]

            iy = info_box_rect.y + 10
            for lbl, val, color in info_lines:
                if iy + 14 > info_box_rect.bottom:
                    break
                lbl_surf = font_small.render(lbl, True, COLOR_TEXT_MUTED)
                val_surf = font_small.render(val, True, color)
                screen.blit(lbl_surf, (info_box_rect.x + 8, iy))
                screen.blit(val_surf, (info_box_rect.x + info_box_rect.width - val_surf.get_width() - 8, iy))
                iy += 15

        pygame.display.flip()
        clock.tick(200)

    pygame.quit()
    sys.exit(0)

if __name__ == "__main__":
    main()
