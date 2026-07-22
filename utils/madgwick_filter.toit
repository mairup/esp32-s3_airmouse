import math

/// Fuses gyro and accelerometer data with the Madgwick AHRS algorithm.
///
/// The filter keeps an internal quaternion state, uses gradient descent to
/// correct gyro drift from the accelerometer gravity vector, and exposes roll,
/// pitch, and yaw in radians for the IMU pipeline.
class MadgwickFilter:
  beta /float

  q0_ /float := 1.0
  q1_ /float := 0.0
  q2_ /float := 0.0
  q3_ /float := 0.0

  roll-rad_ /float := 0.0
  pitch-rad_ /float := 0.0
  yaw-rad_ /float := 0.0

  /// Creates a Madgwick filter with the configured gradient-descent gain.
  ///
  /// Higher `beta` values increase accelerometer correction strength and make
  /// the filter respond faster, but they can also add more noise.
  constructor --.beta/float=0.1:

  /// Updates the quaternion state from one IMU sample.
  ///
  /// The accelerometer vector is normalized to a unit gravity estimate, the
  /// quaternion gradient is computed from the current error, and the result is
  /// integrated forward by `delta-seconds` before the Euler angles are
  /// refreshed.
  update --gyro-x/float --gyro-y/float --gyro-z/float --accel-x/float --accel-y/float --accel-z/float --delta-seconds/float -> none:
    ax := accel-x
    ay := accel-y
    az := accel-z

    norm := math.sqrt (ax * ax + ay * ay + az * az)
    if norm == 0.0:
      return

    ax /= norm
    ay /= norm
    az /= norm

    q0 := q0_
    q1 := q1_
    q2 := q2_
    q3 := q3_

    two-q0 := 2.0 * q0
    two-q1 := 2.0 * q1
    two-q2 := 2.0 * q2
    two-q3 := 2.0 * q3
    four-q0 := 4.0 * q0
    four-q1 := 4.0 * q1
    four-q2 := 4.0 * q2
    eight-q1 := 8.0 * q1
    eight-q2 := 8.0 * q2

    q0q0 := q0 * q0
    q1q1 := q1 * q1
    q2q2 := q2 * q2
    q3q3 := q3 * q3

    s0 := four-q0 * q2q2 + two-q2 * ax + four-q0 * q1q1 - two-q1 * ay
    s1 := four-q1 * q3q3 - two-q3 * ax + 4.0 * q0q0 * q1 - two-q0 * ay - four-q1 + eight-q1 * q1q1 + eight-q1 * q2q2 + four-q1 * az
    s2 := 4.0 * q0q0 * q2 + two-q0 * ax + four-q2 * q3q3 - two-q3 * ay - four-q2 + eight-q2 * q1q1 + eight-q2 * q2q2 + four-q2 * az
    s3 := 4.0 * q1q1 * q3 - two-q1 * ax + 4.0 * q2q2 * q3 - two-q2 * ay

    norm = math.sqrt (s0 * s0 + s1 * s1 + s2 * s2 + s3 * s3)
    if norm == 0.0:
      return

    s0 /= norm
    s1 /= norm
    s2 /= norm
    s3 /= norm

    half-dt := 0.5 * delta-seconds
    qDot0 := 0.5 * (-q1 * gyro-x - q2 * gyro-y - q3 * gyro-z) - beta * s0
    qDot1 := 0.5 * (q0 * gyro-x + q2 * gyro-z - q3 * gyro-y) - beta * s1
    qDot2 := 0.5 * (q0 * gyro-y - q1 * gyro-z + q3 * gyro-x) - beta * s2
    qDot3 := 0.5 * (q0 * gyro-z + q1 * gyro-y - q2 * gyro-x) - beta * s3

    q0_ = q0 + qDot0 * half-dt
    q1_ = q1 + qDot1 * half-dt
    q2_ = q2 + qDot2 * half-dt
    q3_ = q3 + qDot3 * half-dt

    norm = math.sqrt (q0_ * q0_ + q1_ * q1_ + q2_ * q2_ + q3_ * q3_)
    if norm == 0.0:
      return

    q0_ /= norm
    q1_ /= norm
    q2_ /= norm
    q3_ /= norm

    update-euler_

  /// Returns the current roll angle in radians.
  roll-rad -> float: return roll-rad_

  /// Returns the current pitch angle in radians.
  pitch-rad -> float: return pitch-rad_

  /// Returns the current yaw angle in radians.
  yaw-rad -> float: return yaw-rad_

  /// Converts the current quaternion state into roll, pitch, and yaw.
  ///
  /// The pitch term is clamped before `asin` so numerical noise cannot push
  /// the value outside the valid domain.
  update-euler_ -> none:
    sin-pitch := 2.0 * (q0_ * q2_ - q3_ * q1_)
    if sin-pitch > 1.0:
      sin-pitch = 1.0
    if sin-pitch < -1.0:
      sin-pitch = -1.0

    roll-rad_ = math.atan2 2.0 * (q0_ * q1_ + q2_ * q3_) 1.0 - 2.0 * (q1_ * q1_ + q2_ * q2_)
    pitch-rad_ = math.asin sin-pitch
    yaw-rad_ = math.atan2 2.0 * (q0_ * q3_ + q1_ * q2_) 1.0 - 2.0 * (q2_ * q2_ + q3_ * q3_)