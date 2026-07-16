"""
Interactive TCP Wi-Fi client for ESP32-S3 AirMouse.
Auto-reconnects on disconnect. Press 'q' to quit.
Usage: python wifi_heartbeat.py <ESP32_IP>
"""
import asyncio
import os
import sys
import termios
import time
import tty

PORT = 8889

CONNECT_TIMEOUT  = 5.0
RECONNECT_DELAY  = 0.3
ERROR_DELAY      = 1.0

async def connect_with_retry(ip: str) -> tuple[asyncio.StreamReader, asyncio.StreamWriter] | None:
    try:
        reader, writer = await asyncio.wait_for(asyncio.open_connection(ip, PORT), timeout=CONNECT_TIMEOUT)
        return reader, writer
    except Exception as e:
        print(f"Connect failed: {e}")
        await asyncio.sleep(ERROR_DELAY)
    return None

async def run_session(reader: asyncio.StreamReader, quit_event: asyncio.Event, avg_downtime: float | None = None, avg_lifespan: float | None = None) -> None:
    conn_start_time = time.monotonic()

    info_parts = ["Press 'q' to quit."]
    if avg_downtime is not None:
        info_parts.append(f"Avg downtime: {avg_downtime:.2f}s")
    if avg_lifespan is not None:
        info_parts.append(f"Avg lifespan: {avg_lifespan:.2f}s")
    print(f"Connected! {', '.join(info_parts)}\n")

    async def read_loop():
        while not quit_event.is_set():
            try:
                line = await reader.readline()
                if not line:
                    break
                text = line.decode("utf-8", errors="replace").strip()
                if not text:
                    continue
                
                elapsed = time.monotonic() - conn_start_time
                try:
                    heartbeats = int(text)
                    alive_seconds = heartbeats * 0.25
                    print(f"\rRX: {text} (Device Uptime: {alive_seconds:.2f}s, Conn Alive: {elapsed:.2f}s)      ", flush=True, end="")
                except ValueError:
                    print(f"\rRX: {text} (Conn Alive: {elapsed:.2f}s)      ", flush=True, end="")
            except Exception as e:
                break
        print("\n[Disconnected]")

    done, pending = await asyncio.wait(
        [asyncio.create_task(read_loop()), asyncio.create_task(quit_event.wait())],
        return_when=asyncio.FIRST_COMPLETED
    )
    for t in pending:
        t.cancel()

async def main() -> None:
    if len(sys.argv) < 2:
        print("Usage: python wifi_heartbeat.py <ESP32_IP>")
        sys.exit(1)
        
    ip = sys.argv[1]

    quit_event = asyncio.Event()
    loop = asyncio.get_event_loop()

    fd = sys.stdin.fileno()
    old_settings = termios.tcgetattr(fd)
    tty.setraw(fd)

    def on_key():
        try:
            ch = os.read(fd, 1)
            if ch in (b"q", b"Q", b"\x03"):
                quit_event.set()
        except Exception:
            pass

    loop.add_reader(fd, on_key)

    try:
        downtimes = []
        lifespans = []
        last_disconnect_time = None

        while not quit_event.is_set():
            print(f"Connecting to {ip}:{PORT}...")
            conn = await connect_with_retry(ip)
            if not conn:
                continue
                
            reader, writer = conn

            avg_downtime = None
            if last_disconnect_time is not None:
                downtime = time.monotonic() - last_disconnect_time
                downtimes.append(downtime)
                avg_downtime = sum(downtimes) / len(downtimes)

            avg_lifespan = sum(lifespans) / len(lifespans) if lifespans else None

            conn_start_time = time.monotonic()
            try:
                await run_session(reader, quit_event, avg_downtime=avg_downtime, avg_lifespan=avg_lifespan)
            finally:
                try:
                    writer.close()
                    await writer.wait_closed()
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
