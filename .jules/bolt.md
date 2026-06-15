## 2024-06-15 - Replace expensive float math with lookup tables in embedded loops
**Learning:** Performing expensive floating-point trigonometric calculations (`math.pow`, `math.sin`, `math.cos`) on an embedded system at 100Hz inside a busy loop is computationally heavy and can block CPU tasks or unnecessarily consume power, especially on devices like the ESP32.
**Action:** When calculating repeated complex animations or signals, pre-calculate the values and put them in an array lookup table (e.g., `BREATHE-TABLE_`). It turns expensive function calls into O(1) memory lookups.
