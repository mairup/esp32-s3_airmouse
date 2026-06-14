## 2026-06-14 - Precomputing Math for Toit IoT Applications
**Learning:** In resource-constrained environments like Toit on ESP32, placing heavy float operations (`math.pow`, `math.sin`, `math.cos`) inside a high-frequency loop (100Hz animation tick) is a performance bottleneck.
**Action:** When writing or optimizing animations or continuous sensor polling loops in Toit, use a top-level lazily-initialized static `List` to precompute static repetitive patterns.
