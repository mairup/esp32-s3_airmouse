## 2024-05-24 - Pre-calculating Complex Animation Math
**Learning:** Doing continuous heavy floating-point math (like `math.sin`, `math.cos`, `math.pow`) for static LED animations inside a fast loop (e.g. 100Hz) is an expensive anti-pattern on microcontrollers like the ESP32-S3.
**Action:** Always pre-calculate static repeating animations into an array (`ByteArray`) lookup table at module initialization/load time to turn complex runtime math into O(1) memory lookups.
