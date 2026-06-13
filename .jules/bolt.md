## 2024-06-13 - Math functions in run loop
**Learning:** Found transcendental math functions (sin, cos, pow) being calculated every 10ms (100Hz) inside `RgbIndicator.run_` on an ESP32. This is a CPU bottleneck for an MCU running a VM.
**Action:** Precompute these values into a lookup table to save CPU cycles and reduce power consumption.
