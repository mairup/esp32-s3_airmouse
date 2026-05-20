## 2026-05-20 - High frequency polling in Wait states wastes battery
**Learning:** In microcontroller code, tight polling loops during idle states (like waiting for a BLE connection in `while state == STATE-ADVERTISING`) cause the CPU to constantly wake up, defeating deep sleep/idle optimizations and wasting power. A 10ms sleep polls 100 times per second.
**Action:** Increase polling delays in idle/waiting loops to the maximum acceptable latency (e.g., changing 10ms to 100ms reduces wakeups by 90%) when absolute immediacy isn't required by the user experience.
