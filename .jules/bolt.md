## 2024-05-18 - Precalculate expensive math loops for Embedded Apps
**Learning:** Found an embedded/Toit system doing expensive float operations `math.pow`, `math.sin`, `math.cos` at a high frequency (100Hz) to drive a breathing LED animation.
**Action:** Extract the static calculations to a lazily-initialized lookup list (`BREATHE-TABLE_`) mapping ticks to intensity. In Toit this removes significant runtime CPU overhead on standard loops.
