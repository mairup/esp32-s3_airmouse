## 2024-06-09 - Precomputing Math for Animations
**Learning:** Running floating-point math functions (`math.sin`, `math.cos`, `math.pow`) inside a high-frequency loop (e.g., 100Hz animation tick) on a microcontroller is an anti-pattern. The CPU overhead can be surprisingly large, affecting battery life and smooth task scheduling.
**Action:** Always prefer precomputed lookup tables over dynamic complex math functions for periodic patterns or animations in low-level/embedded code when memory allows.
