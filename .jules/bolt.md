## 2024-05-22 - Replace Float Math in Fast Loops with Lookup Tables
**Learning:** Floating point math operations (`math.pow`, `math.sin`, `math.cos`) executed inside high-frequency loops (e.g. 100Hz LED animations) are computationally expensive and can be a bottleneck on microcontrollers like the ESP32-S3.
**Action:** Always pre-compute fixed animation patterns or expensive repetitive mathematical functions into static byte array (`ByteArray`) lookup tables to transform O(N) calculations into O(1) array accesses during runtime.
