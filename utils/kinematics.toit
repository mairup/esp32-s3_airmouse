import math
import .one_euro_filter show OneEuroFilter
import .orientation_data show OrientationData
import .screen_delta show ScreenDelta

/// Translates 3D orientation data into 2D screen movement deltas.
///
/// Implements a multi-stage kinematics transformation chain:
/// 1. Base Screen Mapper: Converts angular pitch/yaw changes to screen space deltas.
/// 2. One Euro Filter: Suppresses low-speed hand jitter and micro-shakes.
/// 3. Deadband Threshold: Clamps micro-tremors below `deadzone-threshold` to zero.
/// 4. Master Sensitivity Scaler: Applies global scaling multiplier `master-sensitivity`.
class KinematicsEngine:
  base-x-multiplier /float
  base-y-multiplier /float

  deadzone-threshold_ /float := 0.5
  master-sensitivity_ /float := 1.0

  filter-x_ /OneEuroFilter
  filter-y_ /OneEuroFilter

  prev-pitch_ /float := 0.0
  prev-yaw_   /float := 0.0
  has-prev-orientation_ /bool := false

  /// Creates a KinematicsEngine instance.
  ///
  /// `base-x-multiplier` and `base-y-multiplier` scale angular rotation (radians) to screen pixel deltas.
  /// `min-cutoff`, `beta`, and `d-cutoff` configure the underlying One Euro Filters.
  /// `deadzone-threshold` sets the minimum pixel threshold below which movement is forced to zero.
  /// `master-sensitivity` scales the final output deltas (e.g. 0.5x to 3.0x).
  constructor
      --.base-x-multiplier/float=1000.0
      --.base-y-multiplier/float=1000.0
      --min-cutoff/float=1.0
      --beta/float=0.005
      --d-cutoff/float=1.0
      --deadzone-threshold/float=0.5
      --master-sensitivity/float=1.0:
    deadzone-threshold_ = deadzone-threshold
    master-sensitivity_ = master-sensitivity
    filter-x_ = OneEuroFilter --min-cutoff=min-cutoff --beta=beta --d-cutoff=d-cutoff
    filter-y_ = OneEuroFilter --min-cutoff=min-cutoff --beta=beta --d-cutoff=d-cutoff

  /// Returns the current deadzone threshold in pixels.
  deadzone-threshold -> float: return deadzone-threshold_

  /// Sets the deadzone threshold in pixels.
  set-deadzone-threshold val/float -> none:
    deadzone-threshold_ = val

  /// Returns the current master sensitivity multiplier.
  master-sensitivity -> float: return master-sensitivity_

  /// Sets the master sensitivity multiplier.
  set-master-sensitivity val/float -> none:
    master-sensitivity_ = val

  /// Processes an `OrientationData` sample and returns the transformed `ScreenDelta`.
  ///
  /// Calculates angular difference since the last sample, maps to screen deltas,
  /// applies One Euro filtering, enforces deadband thresholding, and scales by master sensitivity.
  update --orientation/OrientationData --delta-seconds/float -> ScreenDelta:
    if not has-prev-orientation_:
      prev-pitch_ = orientation.pitch-rad
      prev-yaw_ = orientation.yaw-rad
      has-prev-orientation_ = true
      return ScreenDelta --delta-x=0.0 --delta-y=0.0

    // 1. Calculate raw angular deltas
    dyaw := orientation.yaw-rad - prev-yaw_
    dpitch := orientation.pitch-rad - prev-pitch_

    // Handle yaw angle wrap-around (-PI to +PI boundary)
    if dyaw > math.PI:
      dyaw -= 2.0 * math.PI
    else if dyaw < -math.PI:
      dyaw += 2.0 * math.PI

    prev-yaw_ = orientation.yaw-rad
    prev-pitch_ = orientation.pitch-rad

    // 2. Base mapping from angular delta (radians) to screen space
    raw-delta-x := dyaw * base-x-multiplier
    raw-delta-y := dpitch * base-y-multiplier

    // 3. Smooth deltas using One Euro Filter
    filtered-x := filter-x_.filter --val=raw-delta-x --delta-seconds=delta-seconds
    filtered-y := filter-y_.filter --val=raw-delta-y --delta-seconds=delta-seconds

    // 4. Deadband thresholding (force micro-tremors below threshold to zero)
    if filtered-x.abs < deadzone-threshold_:
      filtered-x = 0.0
    if filtered-y.abs < deadzone-threshold_:
      filtered-y = 0.0

    // 5. Master sensitivity scaling
    final-x := filtered-x * master-sensitivity_
    final-y := filtered-y * master-sensitivity_

    return ScreenDelta --delta-x=final-x --delta-y=final-y

  /// Resets the internal state of the kinematics engine and underlying filters.
  reset -> none:
    has-prev-orientation_ = false
    prev-pitch_ = 0.0
    prev-yaw_ = 0.0
    filter-x_.reset
    filter-y_.reset
