import asyncio
import os
import sys
import time
import subprocess
from bleak import BleakClient

RX_CHAR = "0000FFE2-0000-1000-8000-00805F9B34FB"
DEFAULT_MAC = "A0:85:E3:E3:57:6E"
CACHE_FILE = os.path.join(os.path.dirname(__file__), ".ble_cache")

def get_cached_address():
    if os.path.exists(CACHE_FILE):
        try:
            with open(CACHE_FILE, "r") as f:
                return f.read().strip()
        except:
            pass
    return DEFAULT_MAC

async def run_worker(address):
    c = BleakClient(address)
    try:
        await c.connect()
        first_packet_event = asyncio.Event()
        
        async def handler(_, data):
            first_packet_event.set()
            
        await c.start_notify(RX_CHAR, handler)
        # Wait for the first notification packet to ensure the connection is active
        await asyncio.wait_for(first_packet_event.wait(), timeout=4.0)
        # Success! Exit instantly to force the OS to drop the connection immediately
        os._exit(0)
    except Exception:
        # Exit with error code if something went wrong
        os._exit(1)

def run_orchestrator(address, iterations=30):
    print(f"Starting Fast Reconnect Benchmark on {address}...")
    print("Spawning workers that exit via os._exit(0) to test peak reconnect frequencies.\n", flush=True)
    
    latencies = []
    for i in range(1, iterations + 1):
        print(f"Cycle {i}/{iterations}: Spawning worker...", end="", flush=True)
        start_time = time.monotonic()
        
        # Spawn the worker process
        proc = subprocess.Popen([sys.executable, __file__, "--worker", address])
        proc.wait()
        
        elapsed = time.monotonic() - start_time
        if proc.returncode == 0:
            latencies.append(elapsed)
            print(f" Success! Connected and dropped in {elapsed:.2f}s", flush=True)
        else:
            print(" Failed!", flush=True)
            
        # Give the ESP32-S3 a tiny window (80ms) to detect the loss and resume advertising
        time.sleep(0.08)
        
    if latencies:
        avg_time = sum(latencies) / len(latencies)
        reconnects_per_sec = 1.0 / avg_time
        reconnects_per_min = 60.0 / avg_time
        print("\n--- Fast Reconnect Benchmark Results ---")
        print(f"Successful cycles: {len(latencies)}/{iterations}")
        print(f"Average cycle time (spawn -> connect -> notify -> instant drop): {avg_time:.2f}s")
        print(f"Achievable reconnects per second: {reconnects_per_sec:.2f}")
        print(f"Achievable reconnects per minute: {reconnects_per_min:.1f}")
    else:
        print("Benchmark failed to capture any successful cycles.")

if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "--worker":
        address = sys.argv[2] if len(sys.argv) > 2 else get_cached_address()
        asyncio.run(run_worker(address))
    else:
        iterations = 30
        if len(sys.argv) > 1:
            try:
                iterations = int(sys.argv[1])
            except ValueError:
                print(f"Warning: Could not parse '{sys.argv[1]}' as number of cycles. Defaulting to 30.\n")
        
        address = get_cached_address()
        run_orchestrator(address, iterations=iterations)
