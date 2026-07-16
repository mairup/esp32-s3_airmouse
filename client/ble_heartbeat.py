"""
Interactive BLE client for ESP32-S3 AirMouse.
Auto-reconnects on disconnect. Press 'q' to quit.
"""
import asyncio
import os
import sys
import termios
import time
import tty
from bleak import BleakClient, BleakScanner

DEVICE_NAME = "ESP32-S3"
RX_CHAR     = "0000FFE2-0000-1000-8000-00805F9B34FB"
CACHE_FILE  = os.path.join(os.path.dirname(__file__), ".ble_cache")

CONNECT_TIMEOUT  = 5.0
SCAN_TIMEOUT     = 8.0
RECONNECT_DELAY  = 0.3
ERROR_DELAY      = 1.0
MAX_CONNECT_ATTEMPTS = 3


def load_cached_address() -> str | None:
    try:
        addr = open(CACHE_FILE).read().strip()
        return addr if addr else None
    except (OSError, FileNotFoundError):
        return None


def save_cached_address(address: str) -> None:
    try:
        with open(CACHE_FILE, "w") as f:
            f.write(address)
    except OSError:
        pass


async def scan_for_device() -> str:
    print(f"Scanning for {DEVICE_NAME}...")
    device = await BleakScanner.find_device_by_name(DEVICE_NAME, timeout=SCAN_TIMEOUT)
    if not device:
        raise RuntimeError(f"Device '{DEVICE_NAME}' not found")
    print(f"Found: {device.name} ({device.address})")
    save_cached_address(device.address)
    return device.address


async def connect_with_retry(address: str, on_disconnect) -> BleakClient | None:
    for attempt in range(MAX_CONNECT_ATTEMPTS):
        try:
            client = BleakClient(address, timeout=CONNECT_TIMEOUT, disconnected_callback=on_disconnect)
            await client.connect()
            return client
        except Exception as e:
            print(f"Connect attempt {attempt + 1}/{MAX_CONNECT_ATTEMPTS} failed: {e}")
            if attempt < MAX_CONNECT_ATTEMPTS - 1:
                await asyncio.sleep(ERROR_DELAY)
    return None


async def run_session(client: BleakClient, quit_event: asyncio.Event, disconnect_event: asyncio.Event, avg_downtime: float | None = None, avg_lifespan: float | None = None) -> None:
    conn_start_time = time.monotonic()

    def on_rx(_, data: bytearray) -> None:
        elapsed = time.monotonic() - conn_start_time
        text = data.decode("utf-8", errors="replace").strip()
        try:
            heartbeats = int(text)
            alive_seconds = heartbeats * 0.25
            print(f"\rRX: {text} (Device Uptime: {alive_seconds:.2f}s, Conn Alive: {elapsed:.2f}s)      ", flush=True)
        except ValueError:
            print(f"\rRX: {text} (Conn Alive: {elapsed:.2f}s)      ", flush=True)

    await client.start_notify(RX_CHAR, on_rx)
    info_parts = ["Press 'q' to quit."]
    if avg_downtime is not None:
        info_parts.append(f"Avg downtime: {avg_downtime:.2f}s")
    if avg_lifespan is not None:
        info_parts.append(f"Avg lifespan: {avg_lifespan:.2f}s")
    print(f"Connected! {', '.join(info_parts)}\n")

    done = asyncio.wait(
        [asyncio.ensure_future(quit_event.wait()),
         asyncio.ensure_future(disconnect_event.wait())],
        return_when=asyncio.FIRST_COMPLETED,
    )
    finished, pending = await done
    for t in pending:
        t.cancel()

    if disconnect_event.is_set():
        print("\n[Disconnected]")


async def main() -> None:
    quit_event = asyncio.Event()
    loop = asyncio.get_event_loop()

    fd = sys.stdin.fileno()
    old_settings = termios.tcgetattr(fd)
    tty.setraw(fd)

    def on_key():
        ch = os.read(fd, 1)
        if ch in (b"q", b"Q", b"\x03"):
            quit_event.set()

    loop.add_reader(fd, on_key)

    try:
        address = load_cached_address()
        if not address:
            address = await scan_for_device()

        downtimes = []
        lifespans = []
        last_disconnect_time = None

        while not quit_event.is_set():
            disconnect_event = asyncio.Event()
            client = await connect_with_retry(address, lambda _: disconnect_event.set())
            if not client:
                print("Cache stale, rescanning...")
                try:
                    address = await scan_for_device()
                except Exception as e:
                    print(f"Scan failed: {e}")
                    await asyncio.sleep(ERROR_DELAY)
                continue

            avg_downtime = None
            if last_disconnect_time is not None:
                downtime = time.monotonic() - last_disconnect_time
                downtimes.append(downtime)
                avg_downtime = sum(downtimes) / len(downtimes)

            avg_lifespan = sum(lifespans) / len(lifespans) if lifespans else None

            conn_start_time = time.monotonic()
            try:
                await run_session(client, quit_event, disconnect_event, avg_downtime=avg_downtime, avg_lifespan=avg_lifespan)
            except Exception as e:
                print(f"\n[Session error: {e}]")
            finally:
                try:
                    await client.disconnect()
                except Exception:
                    pass
                last_disconnect_time = time.monotonic()
                lifespan = last_disconnect_time - conn_start_time
                lifespans.append(lifespan)

            if not quit_event.is_set():
                print(f"Reconnecting in {RECONNECT_DELAY}s...")
                await asyncio.sleep(RECONNECT_DELAY)
    finally:
        loop.remove_reader(fd)
        termios.tcsetattr(fd, termios.TCSADRAIN, old_settings)
        print()


if __name__ == "__main__":
    asyncio.run(main())
