import log
import ..imu show Imu

class ImuHeartbeat:
  imu /Imu
  interval /Duration
  run-thread /Task? := null

  constructor --.imu --.interval/Duration:

  start -> none:
    if run-thread: return
    log.info "Starting IMU Heartbeat..."
    error := catch:
      run-thread = task::
        while true:
          imu.read-sensors
          sleep interval
    if error:
      log.error "Failed to start IMU Heartbeat: $error"
      throw error
    else:
      log.info "SUCCESS: IMU Heartbeat started"

  stop -> none:
    if run-thread:
      run-thread.cancel
      run-thread = null