## 2026-05-20 - Avoid Math operations in fast loops on MCU
**Learning:** Floating-point math functions like `math.pow`, `math.sin`, and `math.cos` are very expensive when calculated inside tight loops (like 100Hz render loops) on microcontrollers (MCUs) like ESP32.
**Action:** Pre-compute animation curves or other predictable math operations into lookup tables (lists/arrays) when possible to save CPU cycles and power on MCUs.
