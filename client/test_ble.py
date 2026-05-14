import asyncio
from bleak import BleakClient, BleakScanner

CHAR = "0000FFE1-0000-1000-8000-00805F9B34FB"

async def main():
    print("Scanning...")
    devices = await BleakScanner.discover(timeout=5)
    if not devices:
        print("No devices found")
        return
    for i, d in enumerate(devices):
        print(f"  [{i}] {d.address}  {d.name or '?'}")
    n = int(input("Select: "))
    dev = devices[n]
    print(f"Connecting to {dev.name or dev.address}...")
    async with BleakClient(dev) as c:
        print("Connected! Listening...")
        async def handler(_, data):
            print(data.decode())
        await c.start_notify(CHAR, handler)
        await asyncio.Event().wait()

asyncio.run(main())
