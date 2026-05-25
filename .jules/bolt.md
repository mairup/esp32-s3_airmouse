## 2024-05-24 - Precompute Trigonometry/Floating Math on Microcontrollers
**Learning:** Doing heavy `math.sin`, `math.cos`, and `math.pow` floating-point math inside a tight 10ms loop (like a breathing LED animation) is a significant CPU burden on ESP32/microcontrollers, wasting battery and blocking other tasks.
**Action:** Always precompute fixed-length periodic sequences (like animations) into lookup tables (`ByteArray` or `List`) during initialization, replacing floating point math in the render loop with an O(1) array lookup.
