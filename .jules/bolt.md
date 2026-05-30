## 2024-06-25 - Avoid floating-point trigonometry in tight render loops
**Learning:** Performing heavy trigonometric floating-point operations (like math.pow, math.sin, math.cos) within a high-frequency (e.g. 10ms) render loop on a microcontroller is an anti-pattern. This significantly increases CPU load and can impact performance or responsiveness.
**Action:** Precompute static animations or cyclic mathematical series into a lookup table (LUT) and use O(1) array access within the render loop instead of recalculating in real-time.
