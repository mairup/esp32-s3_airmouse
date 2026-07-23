import sys
import time
import socket
import struct
import signal
import argparse
from evdev import UInput, ecodes as e

try:
    from .pipeline import (
        AirMousePipeline,
        DEFAULT_BASE_SENSITIVITY,
        DEFAULT_REPOSITION_SENS_FACTOR,
        DEFAULT_REPOSITION_MIN_CUTOFF,
        DEFAULT_REPOSITION_DEADZONE,
        DEFAULT_REPOSITION_SLOWDOWN_SPEED,
        DEFAULT_REPOSITION_SLOWDOWN_EXP,
        DEFAULT_ACCEL_FACTOR,
        DEFAULT_ACCEL_EXPONENT,
        DEFAULT_ACCEL_THRESHOLD,
        DEFAULT_INVERT_CLUTCH,
        DEFAULT_SLOW_ON_CLICK,
    )
    from .filters import (
        DEFAULT_MIN_CUTOFF_FREQUENCY,
        DEFAULT_SPEED_COEFFICIENT,
        DEFAULT_DERIVATIVE_CUTOFF,
        DEFAULT_ACCEL_REJECTION_THRESHOLD,
        DEFAULT_MAX_ROLL_DEGREES,
        DEFAULT_DEADZONE_THRESHOLD,
    )
except ImportError:
    from pipeline import (
        AirMousePipeline,
        DEFAULT_BASE_SENSITIVITY,
        DEFAULT_REPOSITION_SENS_FACTOR,
        DEFAULT_REPOSITION_MIN_CUTOFF,
        DEFAULT_REPOSITION_DEADZONE,
        DEFAULT_REPOSITION_SLOWDOWN_SPEED,
        DEFAULT_REPOSITION_SLOWDOWN_EXP,
        DEFAULT_ACCEL_FACTOR,
        DEFAULT_ACCEL_EXPONENT,
        DEFAULT_ACCEL_THRESHOLD,
        DEFAULT_INVERT_CLUTCH,
        DEFAULT_SLOW_ON_CLICK,
    )
    from filters import (
        DEFAULT_MIN_CUTOFF_FREQUENCY,
        DEFAULT_SPEED_COEFFICIENT,
        DEFAULT_DERIVATIVE_CUTOFF,
        DEFAULT_ACCEL_REJECTION_THRESHOLD,
        DEFAULT_MAX_ROLL_DEGREES,
        DEFAULT_DEADZONE_THRESHOLD,
    )


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
