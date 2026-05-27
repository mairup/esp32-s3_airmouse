## 2023-10-24 - Pre-compute floating-point animations to save CPU cycles
**Learning:** Repetitive mathematical operations, particularly `math.sin`, `math.cos`, and `math.pow`, used for hardware animations (like LED breathing at 100Hz) unconditionally burn precious microcontroller CPU cycles on every tick.
**Action:** Always pre-compute complex bounded repetitive patterns (like a 200-step breathing cycle) into an array/List during initialization to reduce the render loop to a simple O(1) lookup.
