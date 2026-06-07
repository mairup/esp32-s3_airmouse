## 2024-06-07 - Precomputing math operations in hot loops
**Learning:** In embedded devices running Toit, calculating complex math functions (`math.pow`, `math.sin`, `math.cos`) inside high-frequency event loops (like an LED breathing animation at 100Hz) consumes unnecessary CPU cycles and power.
**Action:** Always prefer precomputing complex, deterministic mathematical curves into a static array/lookup table to minimize computational overhead during runtime, especially for hardware and UI animations.
