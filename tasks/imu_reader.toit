import gpio
import log
import ..imu show Imu
import ..utils.mahony_filter show MahonyFilter
import ..utils.madgwick_filter show MadgwickFilter
import ..utils.orientation_data show OrientationData
import ..utils.kinematics show KinematicsEngine
import ..utils.screen_delta show ScreenDelta
import .cpu_monitor show CpuMonitor

/// Reads IMU samples, runs attitude estimation (Mahony/Madgwick),
/// and evaluates the Kinematics transformation chain (Base Mapper + One Euro Filter + Deadband + Sensitivity).
class ImuReader:
  static FILTER-MAHONY ::= 0
  static FILTER-MADGWICK ::= 1
  static FILTER-TYPE ::= FILTER-MAHONY

  imu /Imu
  int-pin /gpio.Pin
  cpu-monitor /CpuMonitor
  mahony-filter /MahonyFilter
  madgwick-filter /MadgwickFilter
  kinematics-engine /KinematicsEngine

  latest-orientation_ /OrientationData? := null
  latest-delta_       /ScreenDelta := ScreenDelta --delta-x=0.0 --delta-y=0.0

  run-thread /Task? := null
  interval /Duration ::= Duration --ms=10
  sample-interval-seconds_ /float ::= 0.01

  /// Creates an IMU reader for the given IMU instance, interrupt pin, CPU monitor,
  /// and optional custom KinematicsEngine instance.
  constructor
      --.imu
      --int-pin-num/int
      --.cpu-monitor
      --kinematics-engine/KinematicsEngine?=(KinematicsEngine):

    int-pin = gpio.Pin int-pin-num --input --pull-down=true
    mahony-filter = MahonyFilter
    madgwick-filter = MadgwickFilter
    this.kinematics-engine = kinematics-engine
    log.info "SUCCESS: ImuReader initialized on Pin $int-pin-num"

  /// Returns the latest calculated orientation data.
  latest-orientation -> OrientationData?:
    return latest-orientation_

  /// Returns the latest smoothed screen delta output.
  latest-delta -> ScreenDelta:
    return latest-delta_

  /// Starts the reader loop if it is not already running.
  start -> none:
    if run-thread: return
    log.info "Starting IMU reader with integrated Kinematics pipeline..."
    if FILTER-TYPE == FILTER-MADGWICK:
      run-thread = task::
        run-filter-loop-madgwick_ --next-time=(Time.now + interval)
    else:
      run-thread = task::
        run-filter-loop-mahony_ --next-time=(Time.now + interval)
    log.info "SUCCESS: IMU reader started successfully"

  /// Runs the IMU loop with Mahony filter and updates Kinematics engine.
  run-filter-loop-mahony_ --next-time/Time -> none:
    while true:
      start-time := Time.monotonic-us
      imu.read-sensors
      mahony-filter.update
        --gyro-x=imu.gyro-x-rad
        --gyro-y=imu.gyro-y-rad
        --gyro-z=imu.gyro-z-rad
        --accel-x=imu.accel-x-g
        --accel-y=imu.accel-y-g
        --accel-z=imu.accel-z-g
        --delta-seconds=sample-interval-seconds_
      elapsed-us := Time.monotonic-us - start-time
      cpu-monitor.update-latency elapsed-us

      data := OrientationData
        --timestamp-us=start-time
        --roll-rad=mahony-filter.roll-rad
        --pitch-rad=mahony-filter.pitch-rad
        --yaw-rad=mahony-filter.yaw-rad
      latest-orientation_ = data

      // Run Kinematics transformation pipeline
      latest-delta_ = kinematics-engine.update
        --orientation=data
        --delta-seconds=sample-interval-seconds_

      now := Time.now
      if next-time > now:
        sleep (now.to next-time)
      else:
        sleep --ms=0
        next-time = now
      next-time += interval

  /// Runs the IMU loop with Madgwick filter and updates Kinematics engine.
  run-filter-loop-madgwick_ --next-time/Time -> none:
    while true:
      start-time := Time.monotonic-us
      imu.read-sensors
      madgwick-filter.update
        --gyro-x=imu.gyro-x-rad
        --gyro-y=imu.gyro-y-rad
        --gyro-z=imu.gyro-z-rad
        --accel-x=imu.accel-x-g
        --accel-y=imu.accel-y-g
        --accel-z=imu.accel-z-g
        --delta-seconds=sample-interval-seconds_
      elapsed-us := Time.monotonic-us - start-time
      cpu-monitor.update-latency elapsed-us

      data := OrientationData
        --timestamp-us=start-time
        --roll-rad=madgwick-filter.roll-rad
        --pitch-rad=madgwick-filter.pitch-rad
        --yaw-rad=madgwick-filter.yaw-rad
      latest-orientation_ = data

      // Run Kinematics transformation pipeline
      latest-delta_ = kinematics-engine.update
        --orientation=data
        --delta-seconds=sample-interval-seconds_

      now := Time.now
      if next-time > now:
        sleep (now.to next-time)
      else:
        sleep --ms=0
        next-time = now
      next-time += interval

  /// Stops the reader loop and closes the interrupt pin.
  stop -> none:
    if run-thread:
      run-thread.cancel
      run-thread = null
      catch: int-pin.close
