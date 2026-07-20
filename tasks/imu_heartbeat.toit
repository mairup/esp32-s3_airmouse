import ..imu show Imu

class ImuHeartbeat:
  imu /Imu
  interval /Duration
  run-thread /Task? := null

  constructor --.imu --.interval/Duration:

  start -> none:
    if run-thread: return
    run-thread = task::
      while true:
        imu.read-gyro
        sleep interval

  stop -> none:
    if run-thread:
      run-thread.cancel
      run-thread = null