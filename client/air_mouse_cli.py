import sys
import time
import socket
import struct
import signal
import argparse
import subprocess
from evdev import UInput, ecodes as e

try:
    from .pipeline import AirMousePipeline
    from .config import (
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
        DEFAULT_CLICK_SLOWDOWN_DURATION,
        DEFAULT_CLICK_SLOWDOWN_EXPONENT,
        DEFAULT_SCROLL_MODE_ENABLED,
        DEFAULT_SCROLL_SENSITIVITY,
        DEFAULT_PAN_SENSITIVITY_X,
        DEFAULT_PAN_SENSITIVITY_Y,
        DEFAULT_SCROLL_DEADZONE,
        DEFAULT_INVERT_VERTICAL_SCROLL,
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
    )
except ImportError:
    from pipeline import AirMousePipeline
    from config import (
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
        DEFAULT_CLICK_SLOWDOWN_DURATION,
        DEFAULT_CLICK_SLOWDOWN_EXPONENT,
        DEFAULT_SCROLL_MODE_ENABLED,
        DEFAULT_SCROLL_SENSITIVITY,
        DEFAULT_PAN_SENSITIVITY_X,
        DEFAULT_PAN_SENSITIVITY_Y,
        DEFAULT_SCROLL_DEADZONE,
        DEFAULT_INVERT_VERTICAL_SCROLL,
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
    )





def create_virtual_mouse_device():
    return UInput(
        {
            e.EV_REL: [e.REL_X, e.REL_Y, e.REL_WHEEL, e.REL_HWHEEL],
            e.EV_KEY: [e.BTN_LEFT, e.BTN_RIGHT, e.BTN_MIDDLE]
        },
        name="AirMouse-Virtual-Mouse"
    )


def emit_relative_mouse_movement(virtual_mouse_device, movement_x, movement_y):
    if movement_x != 0 or movement_y != 0:
        virtual_mouse_device.write(e.EV_REL, e.REL_X, movement_x)
        virtual_mouse_device.write(e.EV_REL, e.REL_Y, movement_y)
        virtual_mouse_device.syn()


def emit_scroll_movement(virtual_mouse_device, scroll_x, scroll_y):
    if scroll_y != 0:
        virtual_mouse_device.write(e.EV_REL, e.REL_WHEEL, scroll_y)
    if scroll_x != 0:
        virtual_mouse_device.write(e.EV_REL, e.REL_HWHEEL, scroll_x)
    if scroll_y != 0 or scroll_x != 0:
        virtual_mouse_device.syn()


def initialize_udp_socket(server_ip, server_port):
    client_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    client_socket.setsockopt(socket.SOL_SOCKET, socket.SO_RCVBUF, 1024 * 1024)
    client_socket.settimeout(0.5)
    return client_socket


def send_heartbeat_handshake(client_socket, server_ip, server_port):
    client_socket.sendto(b"HELLO", (server_ip, server_port))


def send_led_command(client_socket, server_ip, server_port, led_on):
    payload = struct.pack("<BB", 0xFF, 1 if led_on else 0)
    client_socket.sendto(payload, (server_ip, server_port))


def set_cursor_hand():
    try:
        subprocess.run(["xsetroot", "-cursor_name", "hand2"], timeout=0.1,
                       capture_output=True, check=False)
    except Exception:
        pass


def restore_cursor():
    try:
        subprocess.run(["xsetroot", "-cursor_name", "left_ptr"], timeout=0.1,
                       capture_output=True, check=False)
    except Exception:
        pass


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
    parser.add_argument("--active-slowdown-speed", type=float, default=DEFAULT_ACTIVE_SLOWDOWN_SPEED, help=f"Active mode low-speed slowdown threshold rad/s (default: {DEFAULT_ACTIVE_SLOWDOWN_SPEED})")
    parser.add_argument("--active-slowdown-exp", type=float, default=DEFAULT_ACTIVE_SLOWDOWN_EXP, help=f"Active mode low-speed slowdown exponent (default: {DEFAULT_ACTIVE_SLOWDOWN_EXP})")

    # Dynamic click slowdown settings
    parser.add_argument("--click-slowdown-init", type=float, default=DEFAULT_CLICK_INITIAL_FACTOR, help=f"Initial click sensitivity multiplier at t=0ms (default: {DEFAULT_CLICK_INITIAL_FACTOR})")
    parser.add_argument("--click-slowdown-target", type=float, default=DEFAULT_CLICK_TARGET_FACTOR, help=f"Target click sensitivity multiplier cap (default: {DEFAULT_CLICK_TARGET_FACTOR})")
    parser.add_argument("--click-slowdown-duration", type=float, default=DEFAULT_CLICK_SLOWDOWN_DURATION, help=f"Click slowdown recovery duration in seconds (default: {DEFAULT_CLICK_SLOWDOWN_DURATION})")
    parser.add_argument("--click-slowdown-exp", type=float, default=DEFAULT_CLICK_SLOWDOWN_EXPONENT, help=f"Click slowdown recovery curve exponent linearity (default: {DEFAULT_CLICK_SLOWDOWN_EXPONENT})")
    parser.add_argument("--no-click-slowdown", dest="click_slowdown_enabled", action="store_false", default=DEFAULT_CLICK_SLOWDOWN_ENABLED, help="Disable dynamic click slowdown during click holds")

    # Scroll & Pan settings
    parser.add_argument("--scroll-sens", type=float, default=DEFAULT_SCROLL_SENSITIVITY, help=f"Scroll sensitivity multiplier (default: {DEFAULT_SCROLL_SENSITIVITY})")
    parser.add_argument("--pan-sens", type=float, default=None, help="General pan sensitivity multiplier for both X and Y axes")
    parser.add_argument("--pan-sens-x", type=float, default=DEFAULT_PAN_SENSITIVITY_X, help=f"Horizontal pan sensitivity multiplier (default: {DEFAULT_PAN_SENSITIVITY_X})")
    parser.add_argument("--pan-sens-y", type=float, default=DEFAULT_PAN_SENSITIVITY_Y, help=f"Vertical pan sensitivity multiplier (default: {DEFAULT_PAN_SENSITIVITY_Y})")
    parser.add_argument("--scroll-deadzone", type=float, default=DEFAULT_SCROLL_DEADZONE, help=f"Scroll deadzone threshold in rad/s (default: {DEFAULT_SCROLL_DEADZONE})")
    parser.add_argument("--no-scroll-mode", dest="scroll_mode_enabled", action="store_false", default=DEFAULT_SCROLL_MODE_ENABLED, help="Disable scroll/pan mode when gesture button is held")
    parser.add_argument("--normal-vertical-scroll", dest="invert_vertical_scroll", action="store_false", default=DEFAULT_INVERT_VERTICAL_SCROLL, help="Use non-inverted vertical scroll direction")
    parser.add_argument("--pan-activation-delay", type=float, default=DEFAULT_PAN_ACTIVATION_DELAY, help=f"Seconds clutch must be held still before pan activates (default: {DEFAULT_PAN_ACTIVATION_DELAY})")
    parser.add_argument("--pan-stillness-threshold", type=float, default=DEFAULT_PAN_STILLNESS_THRESHOLD, help=f"Max motion speed rad/s considered 'still' during pan activation hold (default: {DEFAULT_PAN_STILLNESS_THRESHOLD})")

    # Post-pan release slowdown settings
    parser.add_argument("--post-pan-init", type=float, default=DEFAULT_POST_PAN_INITIAL_FACTOR, help=f"Initial sensitivity factor upon releasing pan mode (default: {DEFAULT_POST_PAN_INITIAL_FACTOR})")
    parser.add_argument("--post-pan-duration", type=float, default=DEFAULT_POST_PAN_SLOWDOWN_DURATION, help=f"Post-pan slowdown linear recovery duration in seconds (default: {DEFAULT_POST_PAN_SLOWDOWN_DURATION})")
    parser.add_argument("--post-pan-exp", type=float, default=DEFAULT_POST_PAN_SLOWDOWN_EXPONENT, help=f"Post-pan slowdown recovery curve exponent linearity (default: {DEFAULT_POST_PAN_SLOWDOWN_EXPONENT})")
    parser.add_argument("--no-post-pan-slowdown", dest="post_pan_slowdown_enabled", action="store_false", default=DEFAULT_POST_PAN_SLOWDOWN_ENABLED, help="Disable transient slowdown upon releasing gesture/pan button")


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
    
    # Hardware clutch logic
    parser.add_argument("--normal-clutch", dest="invert_clutch", action="store_false", default=DEFAULT_INVERT_CLUTCH, help="Normal clutch logic (hold button to activate mouse)")
    return parser.parse_args()


def drain_udp_socket_buffers(client_socket):
    datagrams_to_process = []
    try:
        datagram_bytes, _ = client_socket.recvfrom(1024)
        if len(datagram_bytes) in (15, 17):
            datagrams_to_process.append(datagram_bytes)
    except socket.timeout:
        return datagrams_to_process

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
    return datagrams_to_process


def unpack_binary_datagram(datagram_bytes):
    if len(datagram_bytes) == 17:
        return struct.unpack("<HBhhhhhhH", datagram_bytes)
    return struct.unpack("<HBhhhhhh", datagram_bytes)


def calculate_packet_delta_time(current_time, last_packet_timestamp):
    if not last_packet_timestamp:
        return 0.01
    delta_time = current_time - last_packet_timestamp
    if delta_time <= 0.0 or delta_time > 0.5:
        return 0.01
    return delta_time


def update_mouse_button_states(virtual_mouse_device, is_left_click, is_right_click, is_gesture_active, previous_left_click, previous_right_click, pipeline=None, current_time=None):
    if is_left_click != previous_left_click:
        if is_left_click and is_gesture_active:
            virtual_mouse_device.write(e.EV_KEY, e.BTN_LEFT, 1)
            virtual_mouse_device.syn()
            time.sleep(0.02)
            virtual_mouse_device.write(e.EV_KEY, e.BTN_LEFT, 0)
            virtual_mouse_device.syn()
            time.sleep(0.02)
            if pipeline and current_time:
                pipeline.trigger_click_slowdown(current_time)
            virtual_mouse_device.write(e.EV_KEY, e.BTN_LEFT, 1)
            virtual_mouse_device.syn()
            time.sleep(0.02)
            virtual_mouse_device.write(e.EV_KEY, e.BTN_LEFT, 0)
            virtual_mouse_device.syn()
        else:
            virtual_mouse_device.write(e.EV_KEY, e.BTN_LEFT, 1 if is_left_click else 0)
            virtual_mouse_device.syn()

    if is_right_click != previous_right_click:
        if is_right_click and is_gesture_active:
            virtual_mouse_device.write(e.EV_KEY, e.BTN_RIGHT, 1)
            virtual_mouse_device.syn()
            time.sleep(0.02)
            virtual_mouse_device.write(e.EV_KEY, e.BTN_RIGHT, 0)
            virtual_mouse_device.syn()
            time.sleep(0.02)
            if pipeline and current_time:
                pipeline.trigger_click_slowdown(current_time)
            virtual_mouse_device.write(e.EV_KEY, e.BTN_RIGHT, 1)
            virtual_mouse_device.syn()
            time.sleep(0.02)
            virtual_mouse_device.write(e.EV_KEY, e.BTN_RIGHT, 0)
            virtual_mouse_device.syn()
        else:
            virtual_mouse_device.write(e.EV_KEY, e.BTN_RIGHT, 1 if is_right_click else 0)
            virtual_mouse_device.syn()

    return is_left_click, is_right_click


def display_streaming_status(pipeline, packet_counter, start_time, is_active, last_left_click, last_right_click, is_gesture=False, raw_clutch_pressed=False, is_pan_active=False):
    elapsed = time.monotonic() - start_time
    packet_rate = packet_counter / elapsed if elapsed > 0 else 0.0
    pot_val = pipeline.raw_potentiometer
    pot_pct = int(pipeline.potentiometer_ratio * 100)

    if is_pan_active:
        current_mode_str = "PAN/SCROLL"
    elif raw_clutch_pressed:
        current_mode_str = "PAN-HOLD..."
    elif last_left_click or last_right_click:
        current_mode_str = "CLICK-DRAG"
    elif is_gesture:
        current_mode_str = "DBL-CLICK-MOD"
    else:
        current_mode_str = "ACTIVE"

    status_text = (
        f"\r[AirMouse CLI] Streaming @ {packet_rate:.1f} Hz | Pot: {pot_val} ({pot_pct}%) | "
        f"Sens: {pipeline.sensitivity:.2f} | Mode: {current_mode_str} | "
        f"L: {'DOWN' if last_left_click else 'UP'} | R: {'DOWN' if last_right_click else 'UP'} | G: {'DOWN' if is_gesture else 'UP'}   "
    )
    sys.stdout.write(status_text)
    sys.stdout.flush()



def run_air_mouse_cli():
    arguments = parse_command_line_arguments()

    virtual_mouse_device = create_virtual_mouse_device()
    client_socket = initialize_udp_socket(arguments.ip_address, arguments.port)

    pan_x = arguments.pan_sens if arguments.pan_sens is not None else arguments.pan_sens_x
    pan_y = arguments.pan_sens if arguments.pan_sens is not None else arguments.pan_sens_y

    pipeline = AirMousePipeline(
        sensitivity=arguments.sensitivity,
        deadzone_threshold=arguments.deadzone,
        minimum_cutoff_frequency=arguments.min_cutoff,
        speed_coefficient=arguments.beta,
        derivative_cutoff_frequency=arguments.d_cutoff,
        active_slowdown_speed=arguments.active_slowdown_speed,
        active_slowdown_exp=arguments.active_slowdown_exp,
        click_slowdown_enabled=arguments.click_slowdown_enabled,
        click_initial_factor=arguments.click_slowdown_init,
        click_target_factor=arguments.click_slowdown_target,
        click_duration=arguments.click_slowdown_duration,
        click_exponent=arguments.click_slowdown_exp,
        scroll_mode_enabled=arguments.scroll_mode_enabled,
        scroll_sensitivity=arguments.scroll_sens,
        pan_sensitivity_x=pan_x,
        pan_sensitivity_y=pan_y,
        scroll_deadzone=arguments.scroll_deadzone,
        invert_vertical_scroll=arguments.invert_vertical_scroll,
        pan_activation_delay=arguments.pan_activation_delay,
        pan_stillness_threshold=arguments.pan_stillness_threshold,
        post_pan_slowdown_enabled=arguments.post_pan_slowdown_enabled,
        post_pan_initial_factor=arguments.post_pan_init,
        post_pan_duration=arguments.post_pan_duration,
        post_pan_exponent=arguments.post_pan_exp,

        acceleration_factor=arguments.accel_factor,
        acceleration_exponent=arguments.accel_exponent,
        acceleration_threshold=arguments.accel_threshold,
        invert_clutch=arguments.invert_clutch,
        reposition_sens_factor=arguments.reposition_sens,
        reposition_min_cutoff=arguments.reposition_min_cutoff,
        reposition_deadzone=arguments.reposition_deadzone,
        reposition_slowdown_speed=arguments.reposition_slowdown_speed,
        reposition_slowdown_exp=arguments.reposition_slowdown_exp,
        accel_rejection_threshold=arguments.accel_rejection_thresh,
        max_roll_degrees=arguments.max_roll_deg
    )

    print(f"[AirMouse CLI] Target: {arguments.ip_address}:{arguments.port} | Virtual Mouse Active (Press Ctrl+C to exit)\n")


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
    is_active = False
    is_gesture = False
    raw_clutch = False
    is_pan_active = False
    previous_pan_active = False

    try:
        while running:
            current_time = time.monotonic()

            if current_time - last_heartbeat_time >= 0.2:
                send_heartbeat_handshake(client_socket, arguments.ip_address, arguments.port)
                last_heartbeat_time = current_time

            datagrams_to_process = drain_udp_socket_buffers(client_socket)
            if not datagrams_to_process:
                continue

            for datagram in datagrams_to_process:
                unpacked_packet = unpack_binary_datagram(datagram)
                delta_time = calculate_packet_delta_time(current_time, last_packet_timestamp)
                last_packet_timestamp = current_time

                movement_x, movement_y, is_active, is_left, is_right, is_gesture, scroll_x, scroll_y, raw_clutch, is_pan_active = pipeline.process_frame(unpacked_packet, current_time, delta_time)

                if is_pan_active != previous_pan_active:
                    if is_pan_active:
                        set_cursor_hand()
                        send_led_command(client_socket, arguments.ip_address, arguments.port, True)
                    else:
                        restore_cursor()
                        send_led_command(client_socket, arguments.ip_address, arguments.port, False)
                    previous_pan_active = is_pan_active

                last_left_click, last_right_click = update_mouse_button_states(
                    virtual_mouse_device, is_left, is_right, is_gesture, last_left_click, last_right_click, pipeline, current_time
                )

                if scroll_x != 0 or scroll_y != 0:
                    emit_scroll_movement(virtual_mouse_device, scroll_x, scroll_y)
                emit_relative_mouse_movement(virtual_mouse_device, movement_x, movement_y)
                packet_counter += 1

            if current_time - status_print_time >= 2.0:
                display_streaming_status(pipeline, packet_counter, start_time, is_active, last_left_click, last_right_click, is_gesture, raw_clutch, is_pan_active)
                status_print_time = current_time




    finally:
        sys.stdout.write("\n[AirMouse CLI] Shutting down...\n")
        sys.stdout.flush()
        restore_cursor()
        send_led_command(client_socket, arguments.ip_address, arguments.port, False)
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

