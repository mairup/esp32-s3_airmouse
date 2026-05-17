import asyncio
import os
import sys
import termios
import tty
from bleak import BleakClient, BleakScanner

RX_CHAR = "0000FFE2-0000-1000-8000-00805F9B34FB"
TARGET = "ESP32-S3"
CACHE_FILE = os.path.join(os.path.dirname(__file__), ".ble_cache")
DEFAULT_MAC = "A0:85:E3:E3:57:6E"

def get_cached_address():
    if os.path.exists(CACHE_FILE):
        try:
            with open(CACHE_FILE, "r") as f:
                return f.read().strip()
        except:
            pass
    return DEFAULT_MAC

def cache_address(address):
    try:
        with open(CACHE_FILE, "w") as f:
            f.write(address)
    except:
        pass

async def auto_connect():
    deadline = asyncio.get_event_loop().time() + 5
    while asyncio.get_event_loop().time() < deadline:
        devices = await BleakScanner.discover(timeout=0.5)
        match = next((d for d in devices if d.name == TARGET), None)
        if match:
            return match, devices
    return None, devices

def pick(devices):
    for i, d in enumerate(devices):
        print(f"  [{i}] {d.address}  {d.name or '?'}")
    return devices[int(input("Select: "))]

def read_key(stop):
    fd = sys.stdin.fileno()
    old = termios.tcgetattr(fd)
    try:
        tty.setcbreak(fd)
        while not stop.is_set():
            ch = sys.stdin.read(1)
            if ch == 'q':
                stop.set()
                return
    finally:
        termios.tcsetattr(fd, termios.TCSANOW, old)

async def main():
    address = get_cached_address()
    c = None
    notifications_started = False
    
    stop = asyncio.Event()
    last_print_time = 0.0
    
    async def handler(_, data):
        nonlocal last_print_time
        now = asyncio.get_event_loop().time()
        if now - last_print_time >= 0.5:
            last_print_time = now
            parts = []
            for b in data:
                char_repr = f"'{chr(b)}'" if 32 <= b <= 126 else "'.'"
                parts.append(f"0x{b:02X} ({char_repr})")
            hexs = " ".join(parts)
            print(f"RX {hexs}", flush=True)

    if address:
        print(f"Attempting direct connection to cached address: {address}...", flush=True)
        c = BleakClient(address)
        try:
            await asyncio.wait_for(c.connect(), timeout=3.0)
            # Verify the connection is fully active by subscribing to notifications
            await c.start_notify(RX_CHAR, handler)
            print("Connected instantly using cache!", flush=True)
            notifications_started = True
        except Exception as e:
            print(f"Cached address connection failed ({type(e).__name__}). Scanning...", flush=True)
            try:
                await c.disconnect()
            except:
                pass
            address = None
            c = None

    if not address:
        print(f"Scanning for {TARGET}...", flush=True)
        match, devices = await auto_connect()
        dev = match if match else pick(devices)
        if not dev:
            print("No devices found")
            return
        address = dev.address
        cache_address(address)
        print(f"Connecting to {dev.name or address}...", flush=True)
        c = BleakClient(address)
        await c.connect()
        print("Connected!", flush=True)

    print("Press 'q' to quit.\n", flush=True)
    if not notifications_started:
        await c.start_notify(RX_CHAR, handler)
        
    await asyncio.gather(asyncio.to_thread(read_key, stop), stop.wait(), return_exceptions=True)
    print("Disconnected.")

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print()
