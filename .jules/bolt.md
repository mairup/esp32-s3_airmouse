## 2024-06-25 - [Precomputed Math lookup table]
**Learning:** Precomputing a lookup table on startup for expensive math in tight loops significantly reduces CPU consumption on microcontrollers without compromising on the outcome of the function.
**Action:** Always check the math run inside high frequency loops. Precompute to simple arrays / ByteArrays if possible (sacrificing RAM for CPU on systems like ESP32 where every tick matters).
