"""
Visual Latency & IMU Telemetry Dashboard - Clutch & Gravity Alignment Prototype
A Pygame GUI client that connects to the ESP32 Wi-Fi server,
implements Dynamic Gravity Alignment (Roll Compensation), and provides interactive Clutch controls.
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

# Gravity Alignment & Fusion State
active_stage_name = "SEARCHING"
pitch_angle_rad = 0.0
yaw_angle_rad   = 0.0
roll_angle_rad  = 0.0

pitch_angle_deg = 0.0
yaw_angle_deg   = 0.0
roll_angle_deg  = 0.0

screen_pitch_rate = 0.0
screen_yaw_rate   = 0.0
roll_comp_enabled = True

# Clutch Modes:
# 0: "HOLD TO MOVE" (Pointer moves ONLY when Clutch button is DOWN)
# 1: "HOLD TO FREEZE" (Pointer moves normally, Clutch button FREEZES pointer)
# 2: "ALWAYS ON" (Pointer always moves regardless of clutch button)
clutch_mode = 0
CLUTCH_MODE_NAMES = ["HOLD TO MOVE", "HOLD TO FREEZE", "ALWAYS ON"]

# Graph rolling histories (300 points = 3 sec window at 100Hz)
HISTORY_LEN = 300
gyro_hist_x = deque([0.0]*HISTORY_LEN, maxlen=HISTORY_LEN)
gyro_hist_y = deque([0.0]*HISTORY_LEN, maxlen=HISTORY_LEN)
gyro_hist_z = deque([0.0]*HISTORY_LEN, maxlen=HISTORY_LEN)

accel_hist_x = deque([0.0]*HISTORY_LEN, maxlen=HISTORY_LEN)
accel_hist_y = deque([0.0]*HISTORY_LEN, maxlen=HISTORY_LEN)
accel_hist_z = deque([0.0]*HISTORY_LEN, maxlen=HISTORY_LEN)

# Roll, pitch, yaw angle history for graph visualization
roll_hist  = deque([0.0]*HISTORY_LEN, maxlen=HISTORY_LEN)
pitch_hist = deque([0.0]*HISTORY_LEN, maxlen=HISTORY_LEN)
yaw_hist   = deque([0.0]*HISTORY_LEN, maxlen=HISTORY_LEN)

# 2D Air Mouse Pointer State
pointer_pos   = [260.0, 160.0]
pointer_trail = deque(maxlen=25)

_hz_count = 0
_hz_last_time = 0.0


class OneEuroFilter:
    def __init__(self, min_cutoff=1.0, beta=0.005, d_cutoff=1.0):
        self.min_cutoff = min_cutoff
        self.beta = beta
        self.d_cutoff = d_cutoff
        self.x_prev = None
        self.dx_prev = 0.0

    def filter(self, val, dt):
        if dt <= 0.0:
            return val
        if self.x_prev is None:
            self.x_prev = val
            self.dx_prev = 0.0
            return val

        dx_raw = (val - self.x_prev) / dt
        alpha_d = 1.0 / (1.0 + (1.0 / (2.0 * math.pi * self.d_cutoff)) / dt)
        dx_filtered = alpha_d * dx_raw + (1.0 - alpha_d) * self.dx_prev
        self.dx_prev = dx_filtered

        cutoff = self.min_cutoff + self.beta * abs(dx_filtered)
        alpha = 1.0 / (1.0 + (1.0 / (2.0 * math.pi * cutoff)) / dt)
        x_filtered = alpha * val + (1.0 - alpha) * self.x_prev
        self.x_prev = x_filtered
        return x_filtered

filter_pitch = OneEuroFilter(min_cutoff=1.0, beta=0.005)
filter_yaw   = OneEuroFilter(min_cutoff=1.0, beta=0.005)
filter_roll  = OneEuroFilter(min_cutoff=1.0, beta=0.005)


def network_thread(ip):
    global button_state, running, conn_start_time, connection_status
    global last_heartbeat_seq, dropped_packets, heartbeats_received, btn_presses
    global heartbeat_hz, _hz_count, _hz_last_time
    global gyro_vals, accel_vals, pointer_pos
    global roll_angle_rad, roll_angle_deg, pitch_angle_rad, yaw_angle_rad, pitch_angle_deg, yaw_angle_deg
    global active_stage_name

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

                        active_stage_name = "RAW IMU"
                        gx = gx_raw * 0.000305432619
                        gy = gy_raw * 0.000305432619
                        gz = gz_raw * 0.000305432619
                        ax = ax_raw * 0.000122
                        ay = ay_raw * 0.000122
                        az = az_raw * 0.000122

                        gyro_vals[0], gyro_vals[1], gyro_vals[2] = gx, gy, gz
                        accel_vals[0], accel_vals[1], accel_vals[2] = ax, ay, az

                        roll_rad = math.atan2(ax, az)
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

                        allow_movement = (clutch_mode == 0 and button_state == "DOWN") or \
                                         (clutch_mode == 1 and button_state != "DOWN") or \
                                         (clutch_mode == 2)
                        if allow_movement:
                            pointer_pos[0] -= gz_screen * 12.0
                            pointer_pos[1] -= gx_screen * 12.0

                        # Clamp within 2D canvas box boundaries
                        pointer_pos[0] = max(15.0, min(500.0, pointer_pos[0]))
                        pointer_pos[1] = max(15.0, min(330.0, pointer_pos[1]))
                        pointer_trail.append((pointer_pos[0], pointer_pos[1]))

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
        surface.blit(title_surf, (rect.x + 14, rect.y + 10))


def draw_graph(surface, rect, channels, v_min, v_max, title, font):
    """Renders a multi-channel real-time oscilloscope graph."""
    draw_panel(surface, rect, title, font)

    px = rect.x + 50
    py = rect.y + 35
    pw = rect.width - 65
    ph = rect.height - 50

    plot_rect = pygame.Rect(px, py, pw, ph)
    pygame.draw.rect(surface, (14, 17, 26), plot_rect, border_radius=4)
    pygame.draw.rect(surface, (35, 42, 60), plot_rect, width=1, border_radius=4)

    num_grid = 4
    for i in range(num_grid + 1):
        gy = py + (ph * i / num_grid)
        val = v_max - (i * (v_max - v_min) / num_grid)
        pygame.draw.line(surface, COLOR_GRID, (px, gy), (px + pw, gy), 1)
        label_surf = font.render(f"{val:>5.1f}", True, COLOR_TEXT_MUTED)
        surface.blit(label_surf, (rect.x + 6, gy - 7))

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

    leg_x = px + pw - 140
    leg_y = py + 8
    for name, history_data, color in channels:
        curr_val = history_data[-1] if history_data else 0.0
        val_str = f"{name}: {curr_val:+6.2f}"
        txt = font.render(val_str, True, color)
        bg_r = pygame.Rect(leg_x - 4, leg_y - 2, 135, 18)
        pygame.draw.rect(surface, (12, 14, 22), bg_r, border_radius=3)
        surface.blit(txt, (leg_x, leg_y))
        leg_y += 20


def main():
    global running, roll_comp_enabled, clutch_mode, pointer_pos

    if len(sys.argv) < 2:
        print("Usage: python visual_latency_test_clutch_proto.py <ESP32_IP>")
        sys.exit(1)

    ip = sys.argv[1]

    t = threading.Thread(target=network_thread, args=(ip,), daemon=True)
    t.start()

    pygame.init()
    pygame.font.init()

    window_w, window_h = 1100, 720
    flags = pygame.DOUBLEBUF
    try:
        screen = pygame.display.set_mode((window_w, window_h), flags, vsync=1)
    except Exception:
        screen = pygame.display.set_mode((window_w, window_h), flags)

    pygame.display.set_caption("AIR MOUSE // Gravity Alignment & Clutch Prototype")
    clock = pygame.time.Clock()

    try:
        font_title = pygame.font.SysFont("monospace", 18, bold=True)
        font_main  = pygame.font.SysFont("monospace", 13, bold=True)
        font_small = pygame.font.SysFont("monospace", 11)
        font_large = pygame.font.SysFont("monospace", 28, bold=True)
    except Exception:
        font_title = pygame.font.SysFont(None, 24)
        font_main  = pygame.font.SysFont(None, 18)
        font_small = pygame.font.SysFont(None, 14)
        font_large = pygame.font.SysFont(None, 36)

    is_fullscreen = False

    while running:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_g:
                    roll_comp_enabled = not roll_comp_enabled
                elif event.key == pygame.K_m:
                    clutch_mode = (clutch_mode + 1) % 3
                elif event.key in (pygame.K_f, pygame.K_F11):
                    is_fullscreen = not is_fullscreen
                    if is_fullscreen:
                        screen = pygame.display.set_mode((0, 0), pygame.FULLSCREEN | flags)
                    else:
                        screen = pygame.display.set_mode((window_w, window_h), flags)
                elif event.key == pygame.K_r:
                    pointer_pos = [260.0, 160.0]
                    pointer_trail.clear()

        screen.fill(COLOR_BG)

        # ====================================================================
        # Top Header Bar
        # ====================================================================
        header_rect = pygame.Rect(15, 12, 1070, 50)
        draw_panel(screen, header_rect)

        title_surf = font_title.render(f"AIR MOUSE // STAGE: {active_stage_name}", True, COLOR_TEXT_MAIN)
        screen.blit(title_surf, (30, 26))

        is_conn = (connection_status == "CONNECTED")
        badge_bg = (20, 60, 40) if is_conn else (60, 20, 30)
        badge_border = (40, 180, 100) if is_conn else (220, 60, 80)
        badge_rect = pygame.Rect(540, 22, 160, 30)
        pygame.draw.rect(screen, badge_bg, badge_rect, border_radius=15)
        pygame.draw.rect(screen, badge_border, badge_rect, width=1, border_radius=15)

        badge_txt = font_main.render(connection_status, True, badge_border)
        badge_txt_rect = badge_txt.get_rect(center=badge_rect.center)
        screen.blit(badge_txt, badge_txt_rect)

        conn_time = (time.monotonic() - conn_start_time) if conn_start_time else 0.0
        metrics_str = f"FREQ: {heartbeat_hz:>5.1f} Hz | RX: {heartbeats_received:<6} | DROPS: {dropped_packets:<3} | UPTIME: {conn_time:.1f}s"
        metrics_surf = font_main.render(metrics_str, True, COLOR_TEXT_MUTED)
        screen.blit(metrics_surf, (715, 29))

        # ====================================================================
        # Oscilloscope Graphs (Left Side)
        # ====================================================================
        gyro_rect  = pygame.Rect(15, 75, 525, 305)
        roll_rect  = pygame.Rect(15, 395, 525, 310)

        gyro_channels = [
            ("GX (Pitch)", list(gyro_hist_x), COLOR_X_AXIS),
            ("GY (Roll)",  list(gyro_hist_y), COLOR_Y_AXIS),
            ("GZ (Yaw)",   list(gyro_hist_z), COLOR_Z_AXIS)
        ]
        draw_graph(screen, gyro_rect, gyro_channels, -5.0, 5.0, "BODY GYROSCOPE (rad/s)", font_small)

        if active_stage_name.startswith("FUSION"):
            orient_channels = [
                ("PITCH", list(pitch_hist), COLOR_X_AXIS),
                ("YAW",   list(yaw_hist),   COLOR_Y_AXIS),
                ("ROLL",  list(roll_hist),  (255, 159, 28))
            ]
            draw_graph(screen, roll_rect, orient_channels, -180.0, 180.0, "FUSED ORIENTATION ANGLES (deg)", font_small)
        else:
            roll_channels = [
                ("ROLL (deg)", list(roll_hist), (255, 159, 28))
            ]
            draw_graph(screen, roll_rect, roll_channels, -180.0, 180.0, "ESTIMATED DEVICE ROLL ANGLE (deg)", font_small)

        # ====================================================================
        # 2D Motion & Air Mouse Field (Top Right)
        # ====================================================================
        canvas_panel_rect = pygame.Rect(555, 75, 530, 410)
        draw_panel(screen, canvas_panel_rect, "AIR MOUSE 2D MOTION CANVAS", font_small)

        c_x = canvas_panel_rect.x + 15
        c_y = canvas_panel_rect.y + 35
        c_w = canvas_panel_rect.width - 30
        c_h = canvas_panel_rect.height - 50

        canvas_box = pygame.Rect(c_x, c_y, c_w, c_h)
        pygame.draw.rect(screen, (12, 14, 22), canvas_box, border_radius=6)
        pygame.draw.rect(screen, (35, 42, 60), canvas_box, width=1, border_radius=6)

        mid_x = c_x + c_w // 2
        mid_y = c_y + c_h // 2
        pygame.draw.line(screen, COLOR_GRID, (mid_x, c_y), (mid_x, c_y + c_h), 1)
        pygame.draw.line(screen, COLOR_GRID, (c_x, mid_y), (c_x + c_w, mid_y), 1)
        pygame.draw.circle(screen, COLOR_GRID, (mid_x, mid_y), 60, width=1)

        # Draw Motion Trail
        trail_pts = list(pointer_trail)
        if len(trail_pts) >= 2:
            for idx in range(len(trail_pts) - 1):
                p1 = (c_x + trail_pts[idx][0], c_y + trail_pts[idx][1])
                p2 = (c_x + trail_pts[idx+1][0], c_y + trail_pts[idx+1][1])
                alpha = int(255 * (idx + 1) / len(trail_pts))
                color = (0, alpha, int(alpha * 0.8))
                pygame.draw.line(screen, color, p1, p2, width=2)

        # Draw Current Motion Pointer Cursor
        cur_px = c_x + pointer_pos[0]
        cur_py = c_y + pointer_pos[1]

        pointer_color = (0, 255, 200) if button_state == "DOWN" else (0, 200, 255)
        pygame.draw.circle(screen, pointer_color, (int(cur_px), int(cur_py)), 10)
        pygame.draw.circle(screen, (255, 255, 255), (int(cur_px), int(cur_py)), 12, width=2)

        # Telemetry overlay inside canvas
        pos_txt = font_small.render(f"POS: X={pointer_pos[0]:.1f} Y={pointer_pos[1]:.1f} | ROLL: {roll_angle_deg:+6.1f}°", True, COLOR_TEXT_MUTED)
        screen.blit(pos_txt, (c_x + 10, c_y + c_h - 22))

        # ====================================================================
        # Controls & Gravity Alignment Monitor Panel (Bottom Right)
        # ====================================================================
        btn_panel_rect = pygame.Rect(555, 495, 530, 210)
        draw_panel(screen, btn_panel_rect, "CLUTCH & GRAVITY ALIGNMENT CONTROLS", font_small)

        b_box_x = btn_panel_rect.x + 20
        b_box_y = btn_panel_rect.y + 35
        b_box_w = 180
        b_box_h = 150

        is_down = (button_state == "DOWN")
        b_color_bg     = (15, 60, 35) if is_down else (55, 18, 25)
        b_color_border = COLOR_BTN_DOWN if is_down else COLOR_BTN_UP

        b_rect = pygame.Rect(b_box_x, b_box_y, b_box_w, b_box_h)
        pygame.draw.rect(screen, b_color_bg, b_rect, border_radius=12)
        pygame.draw.rect(screen, b_color_border, b_rect, width=3, border_radius=12)

        btn_lbl = font_large.render(button_state, True, (255, 255, 255))
        btn_lbl_rect = btn_lbl.get_rect(center=(b_rect.centerx, b_rect.centery - 15))
        screen.blit(btn_lbl, btn_lbl_rect)

        mode_lbl = font_small.render(CLUTCH_MODE_NAMES[clutch_mode], True, COLOR_TEXT_MUTED)
        mode_lbl_rect = mode_lbl.get_rect(center=(b_rect.centerx, b_rect.centery + 25))
        screen.blit(mode_lbl, mode_lbl_rect)

        # Interactive Status & Hotkey Help
        info_x = b_box_x + b_box_w + 20
        info_y = b_box_y + 5

        comp_status = "ENABLED [ON]" if roll_comp_enabled else "DISABLED [OFF]"
        comp_color  = (0, 245, 212) if roll_comp_enabled else (255, 77, 109)

        info_lines = [
            ("ROLL COMP : ", comp_status, comp_color),
            ("CLUTCH MODE: ", CLUTCH_MODE_NAMES[clutch_mode], COLOR_TEXT_MAIN),
            ("SCREEN PITCH: ", f"{screen_pitch_rate:+6.2f} rad/s", COLOR_TEXT_MUTED),
            ("SCREEN YAW  : ", f"{screen_yaw_rate:+6.2f} rad/s", COLOR_TEXT_MUTED),
            ("HOTKEYS    : ", "[G] Roll  [M] Mode  [F] Fullscreen  [R] Reset", (255, 190, 11))
        ]

        for label, val, color in info_lines:
            lbl_surf = font_main.render(label, True, COLOR_TEXT_MUTED)
            val_surf = font_main.render(val, True, color)
            screen.blit(lbl_surf, (info_x, info_y))
            screen.blit(val_surf, (info_x + 110, info_y))
            info_y += 28

        pygame.display.flip()
        clock.tick(200)

    pygame.quit()
    sys.exit(0)

if __name__ == "__main__":
    main()
