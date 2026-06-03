## 2024-05-24 - Precomputing trigonometric and power values in tight loops
**Learning:** In microcontroller environments like Toit running on ESP32, repeatedly calculating floating-point math functions (like sin, cos, pow) in tight loops (e.g. 100Hz LED update loop) can waste CPU cycles and power.
**Action:** Replace complex repetitive floating-point mathematical calculations with a precomputed look-up table array of integers if the input range is bounded and small.
