## 2024-05-21 - Replace dynamic math in high-frequency LED loop with precomputed lookup table
**Learning:** Using floating point math functions (`math.pow`, `math.sin`, `math.cos`) repeatedly within a high-frequency (10ms) `run_` loop consumes too many CPU cycles, especially when running on an ESP32-S3 microcontroller.
**Action:** Replace dynamically calculated loop expressions that have fixed cyclic behavior with a pre-computed array look-up table. O(1) indexed reads from a constant array vastly out-perform dynamic cyclic mathematical computations on embedded systems.
