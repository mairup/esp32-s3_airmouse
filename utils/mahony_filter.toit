import math

/// Fuses gyro and accelerometer data with the Mahony AHRS algorithm.
///
/// The filter keeps an internal quaternion state, corrects gyro drift using
/// the accelerometer gravity vector, and exposes roll, pitch, and yaw in
/// radians for the rest of the IMU pipeline.
class MahonyFilter:
  kp /float
  ki /float

  q0_ /float := 1.0
  q1_ /float := 0.0
  q2_ /float := 0.0
  q3_ /float := 0.0

  integral-fb-x_ /float := 0.0
  integral-fb-y_ /float := 0.0
  integral-fb-z_ /float := 0.0

  roll-rad_ /float := 0.0
  pitch-rad_ /float := 0.0
  yaw-rad_ /float := 0.0

  /// Creates a Mahony filter with the configured proportional and integral
  /// gains.
  ///
  /// `kp` controls how strongly the accelerometer corrects short-term drift.
  /// `ki` controls how much gyro bias is accumulated over time.
  constructor --.kp/float=0.5 --.ki/float=0.005:

  /// Updates the quaternion state from one IMU sample.
  ///
  /// The accelerometer vector is normalized to a unit gravity estimate, then
  /// compared against the gravity vector predicted by the current quaternion.
  /// The resulting error is fed back into the gyro rates, the quaternion is
  /// integrated forward by `delta-seconds`, and the Euler angles are refreshed.
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

    vx := 2.0 * (q1 * q3 - q0 * q2)
    vy := 2.0 * (q0 * q1 + q2 * q3)
    vz := q0 * q0 - q1 * q1 - q2 * q2 + q3 * q3

    ex := ay * vz - az * vy
    ey := az * vx - ax * vz
    ez := ax * vy - ay * vx

    if ki > 0.0:
      integral-fb-x_ += 2.0 * ki * ex * delta-seconds
      integral-fb-y_ += 2.0 * ki * ey * delta-seconds
      integral-fb-z_ += 2.0 * ki * ez * delta-seconds
      gyro-x += integral-fb-x_
      gyro-y += integral-fb-y_
      gyro-z += integral-fb-z_
    else:
      integral-fb-x_ = 0.0
      integral-fb-y_ = 0.0
      integral-fb-z_ = 0.0

    gyro-x += 2.0 * kp * ex
    gyro-y += 2.0 * kp * ey
    gyro-z += 2.0 * kp * ez

    half-dt := 0.5 * delta-seconds
    q0_ = q0 + (-q1 * gyro-x - q2 * gyro-y - q3 * gyro-z) * half-dt
    q1_ = q1 + (q0 * gyro-x + q2 * gyro-z - q3 * gyro-y) * half-dt
    q2_ = q2 + (q0 * gyro-y - q1 * gyro-z + q3 * gyro-x) * half-dt
    q3_ = q3 + (q0 * gyro-z + q1 * gyro-y - q2 * gyro-x) * half-dt

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