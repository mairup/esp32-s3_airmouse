import asyncio
import time
from bleak import BleakClient, BleakScanner

RX_CHAR = "0000FFE2-0000-1000-8000-00805F9B34FB"
TARGET = "ESP32-S3"
ITERATIONS = 5

async def benchmark():
    print(f"Scanning to resolve {TARGET} address...", flush=True)
    devices = await BleakScanner.discover(timeout=5)
    dev = next((d for d in devices if d.name == TARGET), None)
    if not dev:
        print(f"Could not find {TARGET}")
        return

    address = dev.address
    print(f"Resolved address: {address}. Starting benchmark ({ITERATIONS} cycles)...\n", flush=True)

    latencies = []
    for i in range(1, ITERATIONS + 1):
        print(f"Cycle {i}/{ITERATIONS}: Connecting...", end="", flush=True)
        start_time = time.monotonic()
        
        c = BleakClient(address)
        try:
            await c.connect()
            
            # Use an event to wait for the first notification packet
            first_packet_event = asyncio.Event()
            
            async def handler(_, data):
                first_packet_event.set()
                
            await c.start_notify(RX_CHAR, handler)
            
            # Wait for data to flow (validates that connection is fully active)
            await asyncio.wait_for(first_packet_event.wait(), timeout=5.0)
            
            await c.disconnect()
            elapsed = time.monotonic() - start_time
            latencies.append(elapsed)
            print(f" Success! Took {elapsed:.2f}s", flush=True)
        except Exception as e:
            print(f" Failed! Error: {e}", flush=True)
            
        # Give the ESP32 a brief moment to restart advertising
        await asyncio.sleep(0.5)
    if latencies:
        avg_time = sum(latencies) / len(latencies)
        reconnects_per_sec = 1.0 / avg_time
        reconnects_per_min = 60.0 / avg_time
        print("\n--- Benchmark Results ---")
        print(f"Successful cycles: {len(latencies)}/{ITERATIONS}")
        print(f"Average cycle time (connect + notify + disconnect): {avg_time:.2f}s")
        print(f"Achievable reconnects per second: {reconnects_per_sec:.2f}")
        print(f"Achievable reconnects per minute: {reconnects_per_min:.1f}")
    else:
        print("Benchmark failed to capture any successful cycles.")

if __name__ == "__main__":
    asyncio.run(benchmark())
