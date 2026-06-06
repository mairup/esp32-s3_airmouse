## 2024-05-24 - Precompute Expensive Math on Embedded Systems
**Learning:** In microcontroller environments (like ESP32 running Toit), running floating-point math functions (`math.sin`, `math.cos`) frequently (e.g. 100Hz loop) can be highly inefficient and drain CPU cycles.
**Action:** Extract repetitive math calculations in update loops into a precomputed static list (lookup table) loaded at startup for fast O(1) array lookups.
