## 2024-05-14 - Pre-computation of Math Operations
**Learning:** In IoT embedded systems like ESP32 using Toit, performing heavy math calculations (sin, cos, pow) at 100Hz inside an LED PWM loop wastes CPU cycles, potentially starving BLE communication or other processes.
**Action:** Pre-compute static wave patterns into lookup tables during initialization instead of calculating them per-tick.
