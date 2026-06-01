## 2024-05-14 - Replace heavy loop float math with Lookup Table (LUT)
**Learning:** Using high-frequency (100Hz) float operations like `math.pow`, `math.sin`, and `math.cos` within an infinite `while true` loop is extremely CPU-intensive on microcontrollers like the ESP32-S3 and drastically reduces battery life.
**Action:** When working on tight visual update loops, precalculate the float geometry into a Lookup Table (LUT) array during initialization and use O(1) index lookups in the loop body to save CPU cycles.
