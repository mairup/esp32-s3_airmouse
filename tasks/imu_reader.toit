import gpio
import log
import ..imu show Imu
import ..utils.mahony_filter show MahonyFilter
import ..utils.madgwick_filter show MadgwickFilter
import ..utils.orientation_data show OrientationData
import .cpu_monitor show CpuMonitor

  /// Reads IMU samples, runs the configured orientation filter, and exposes the
  /// resulting attitude values to the rest of the airmouse pipeline.
class ImuReader:
  static FILTER-MAHONY ::= 0
  static FILTER-MADGWICK ::= 1
  static FILTER-TYPE ::= FILTER-MAHONY

  imu /Imu
  int-pin /gpio.Pin
  cpu-monitor /CpuMonitor
  mahony-filter /MahonyFilter
  madgwick-filter /MadgwickFilter
  run-thread /Task? := null
  interval /Duration ::= Duration --ms=10
  sample-interval-seconds_ /float ::= 0.01

 /// Creates an IMU reader for the given IMU instance, interrupt pin, and CPU
    /// monitor.
    ///
    /// The active orientation filter is selected through `FILTER-TYPE`.
  constructor --.imu --int-pin-num/int --.cpu-monitor:

    int-pin = gpio.Pin int-pin-num --input --pull-down=true
    mahony-filter = MahonyFilter
    madgwick-filter = MadgwickFilter
    log.info "SUCCESS: ImuReader initialized on Pin $int-pin-num"

  /// Starts the reader loop if it is not already running.
    ///
    /// The loop uses either the Mahony or Madgwick filter depending on the
    /// static `FILTER-TYPE` selector.
  start -> none:
    
    if run-thread: return
    log.info "Starting IMU reader..."
    if FILTER-TYPE == FILTER-MADGWICK:
      run-thread = task::
        run-filter-loop-madgwick_ --next-time=(Time.now + interval)
    else:
      run-thread = task::
        run-filter-loop-mahony_ --next-time=(Time.now + interval)
    log.info "SUCCESS: IMU reader started successfully"

    /// Runs the IMU loop with the Mahony filter and publishes roll, pitch, and
    /// yaw from that filter.
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

      now := Time.now
      if next-time > now:
        sleep (now.to next-time)
      else:
        sleep --ms=0
        next-time = now
      next-time += interval

    /// Runs the IMU loop with the Madgwick filter and publishes roll, pitch,
    /// and yaw from that filter.
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

      now := Time.now
      if next-time > now:
        sleep (now.to next-time)
      else:
        sleep --ms=0
        next-time = now
      next-time += interval

  stop -> none:
    /// Stops the reader loop and closes the interrupt pin.
    if run-thread:
      run-thread.cancel
      run-thread = null
      catch: int-pin.close
