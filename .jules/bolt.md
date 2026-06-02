## 2024-06-02 - Floating Point Math in Embedded Tight Loop
**Learning:** This codebase had floating point math (`math.pow`, `math.sin`, `math.cos`) executing continuously in a 100Hz (10ms sleep) loop for an LED breathing effect while advertising BLE. This is very expensive on embedded devices.
**Action:** Replace dynamic math in periodic/tight loops with pre-computed lookup tables (LUTs), especially for graphical or LED effects that cycle continuously.
