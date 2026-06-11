## 2024-06-11 - Precomputing Animations for ESP32
**Learning:** Performing floating-point math (like `math.pow`, `math.sin`, `math.cos`) continuously in a fast loop (e.g., 10ms for LED animations) consumes unnecessary CPU cycles and increases battery drain on microcontrollers like the ESP32.
**Action:** Use Toit's block-based list initialization (`List size: |index| ...`) to precompute animation curves into constant arrays at module load time. Look up the precomputed values in O(1) time inside the hot loop.
