## 2024-05-24 - Pre-calculate Math Functions for Microcontroller Animations
**Learning:** Performing heavy floating-point and transcendental mathematical calculations (`pow`, `sin`, `cos`) in a tight, 100Hz animation loop (like `RgbIndicator.run_`) consumes excessive CPU cycles and energy on microcontrollers.
**Action:** Replace dynamic calculations in animation loops with static, pre-calculated look-up tables (LUTs) initialized during class compilation or startup to trade a small amount of memory for significant computational savings and better power efficiency.
