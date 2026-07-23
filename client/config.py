"""
Centralized Configuration & Tuning Constants for Air Mouse CLI Client.

Edit any filter, deadzone, sensitivity, acceleration, or hardware parameter here.
"""

# ==============================================================================
# 1. HARDWARE SENSOR CONSTANTS
# ==============================================================================
# Scale factor converting raw LSM6DSOX Gyro LSB to rad/s (±500 dps full scale).
# Fixed sensor property.
GYRO_SCALE_RAD_PER_SEC = 0.000305432619

# Scale factor converting raw LSM6DSOX Accel LSB to g (±4g full scale).
# Fixed sensor property.
ACCEL_SCALE_G = 0.000122


# ==============================================================================
# 2. BASE SENSITIVITY & DEADZONE
# ==============================================================================
# Base mouse sensitivity multiplier when physical potentiometer knob is at 50%.
# Range: 1.0 to 50.0 (Default: 10.0)
DEFAULT_BASE_SENSITIVITY = 25.0

# Minimum angular velocity (rad/s) required to initiate pointer movement.
# Eliminates resting hand tremors; higher values add start-motion resistance.
# Range: 0.00 to 0.05 rad/s (Default: 0.015)
DEFAULT_DEADZONE_THRESHOLD = 0.0005


# ==============================================================================
# 3. ACTIVE MODE 1-EURO FILTER
# ==============================================================================
# Minimum cutoff frequency (Hz) for 1-Euro filter during active tracking.
# Lower = smoother tracking with slight latency; Higher = maximum responsiveness.
# Range: 0.5 to 10.0 Hz (Default: 3.0)
DEFAULT_MIN_CUTOFF_FREQUENCY = 4.0

# Speed coefficient (beta) for 1-Euro filter.
# Controls cutoff frequency scaling with motion speed to eliminate lag during fast moves.
# Range: 0.0 to 1.0 (Default: 0.5)
DEFAULT_SPEED_COEFFICIENT = 0.1

# Cutoff frequency (Hz) for velocity derivative estimation in 1-Euro filter.
# Range: 1.0 to 10.0 Hz (Default: 6.0)
DEFAULT_DERIVATIVE_CUTOFF = 6.0

# Speed threshold (rad/s) below which active mode low-speed slowdown applies.
# 0.0 = disabled (linear tracking at low speeds); >0.0 = smooth low-speed dampening.
# Range: 0.0 to 0.5 rad/s (Default: 0.15)
DEFAULT_ACTIVE_SLOWDOWN_SPEED = 0.15

# Exponential dampening factor on slow precision micro-movements in active mode.
# Range: 1.0 to 2.0 (Default: 1.15)
DEFAULT_ACTIVE_SLOWDOWN_EXP = 1.01



# ==============================================================================
# 4. REPOSITION & SLOWDOWN MODE (Clutch Released / Click Drag)
# ==============================================================================
# Sensitivity multiplier applied when repositioning (clutch off).
# 0.0 = hard clutch (zero cursor movement); >0.0 = soft clutch.
# Range: 0.0 to 0.5 (Default: 0.2)
DEFAULT_REPOSITION_SENS_FACTOR = 0.27

# 1-Euro filter minimum cutoff frequency (Hz) during repositioning.
# Range: 1.0 to 5.0 Hz (Default: 2.5)
DEFAULT_REPOSITION_MIN_CUTOFF = 2.5

# Gyro deadzone threshold (rad/s) during repositioning.
# Range: 0.01 to 0.10 rad/s (Default: 0.03)
DEFAULT_REPOSITION_DEADZONE = 0.03

# Speed threshold (rad/s) below which reposition slowdown curve applies.
# Range: 0.0 to 1.0 rad/s (Default: 0.3)
DEFAULT_REPOSITION_SLOWDOWN_SPEED = 0.3

# Exponential dampening factor on small reposition hand nudges.
# Range: 1.0 to 2.0 (Default: 1.35)
DEFAULT_REPOSITION_SLOWDOWN_EXP = 1.35


# ==============================================================================
# 5. MOUSE ACCELERATION CURVE
# ==============================================================================
# Acceleration factor applied during rapid wrist flicks.
# 0.0 = linear 1:1 mapping; >0.0 = dynamic acceleration boost.
# Range: 0.0 to 1.0 (Default: 0.25)
DEFAULT_ACCEL_FACTOR = 0.15

# Power exponent for fast move acceleration curve.
# Range: 1.0 to 2.0 (Default: 1.12)
DEFAULT_ACCEL_EXPONENT = 1.15

# Speed threshold (rad/s) required to engage acceleration boost.
# Range: 0.05 to 0.5 rad/s (Default: 0.4)
DEFAULT_ACCEL_THRESHOLD = 0.4


# ==============================================================================
# 6. DYNAMIC CLICK SLOWDOWN (Left / Right Click Drag)
# ==============================================================================
# Enable dynamic time-decaying slowdown during left or right click holds.
# Expected: True / False (Default: True)
DEFAULT_CLICK_SLOWDOWN_ENABLED = True

# Initial sensitivity multiplier at the instant of button down (t=0ms).
# Stronger than clutch slowdown to prevent cursor jump on click.
# Range: 0.0 to 0.5 (Default: 0.10)
DEFAULT_CLICK_INITIAL_FACTOR = 0.1

# Maximum target sensitivity multiplier cap during sustained click drags.
# Range: 0.80 to 1.0 (Default: 0.95)
DEFAULT_CLICK_TARGET_FACTOR = 0.95

# Time interval (seconds) per decay step.
# Range: 0.05 to 0.5 s (Default: 0.08 s = 80ms)
DEFAULT_CLICK_DECAY_INTERVAL = 0.08

# Fractional recovery step towards target speed per interval (0.2 = 20% per 80ms).
# Range: 0.10 to 1.0 (Default: 0.2)
DEFAULT_CLICK_DECAY_STEP = 0.2


# ==============================================================================
# 7. SCROLL & PAN MODE (Gesture Button Held + Wrist Motion)
# ==============================================================================
# Enable scroll & pan mode when holding gesture button without clicking.
# Expected: True / False (Default: True)
DEFAULT_SCROLL_MODE_ENABLED = True

# Scroll sensitivity multiplier converting gyro rates to wheel scroll steps.
# Range: 0.1 to 5.0 (Default: 1.0)
DEFAULT_SCROLL_SENSITIVITY = 1.0

# Scroll deadzone threshold (rad/s) to prevent unwanted scrolling during tiny hand tremors.
# Range: 0.005 to 0.05 rad/s (Default: 0.02)
DEFAULT_SCROLL_DEADZONE = 0.02

# Invert vertical scroll direction.
# True = Inverted vertical scrolling (wrist up scrolls down); False = Normal vertical scrolling.
# Expected: True / False (Default: True)
DEFAULT_INVERT_VERTICAL_SCROLL = True



# ==============================================================================
# 8. HARDWARE & CLUTCH LOGIC
# ==============================================================================
# Invert clutch logic.
# True = mouse active by default (holding clutch pauses); False = paused by default.
# Expected: True / False (Default: True)
DEFAULT_INVERT_CLUTCH = True


# ==============================================================================
# 9. ORIENTATION STABILITY & MADGWICK FILTER
# ==============================================================================
# Maximum g-force deviation from 1.0g allowed for accelerometer gravity alignment.
# Rejects linear acceleration during fast movements to prevent tilt drift.
# Range: 0.05 to 0.40 g (Default: 0.1)
DEFAULT_ACCEL_REJECTION_THRESHOLD = 0.1

# Maximum roll angle clamp (degrees) for 3D coordinate transformation to screen.
# Range: 45.0 to 85.0 deg (Default: 75.0)
DEFAULT_MAX_ROLL_DEGREES = 75.0

