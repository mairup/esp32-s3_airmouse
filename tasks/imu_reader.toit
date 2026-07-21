import gpio
import log
import ..imu show Imu
import .cpu_monitor show CpuMonitor

class ImuReader:
  imu /Imu
  int-pin /gpio.Pin
  cpu-monitor /CpuMonitor
  run-thread /Task? := null

  constructor --.imu --int-pin-num/int --.cpu-monitor:
    log.info "Initializing ImuReader on Pin $int-pin-num..."
    int-pin = gpio.Pin int-pin-num --input --pull-down=true
    log.info "SUCCESS: ImuReader initialized on Pin $int-pin-num"

  start -> none:
    if run-thread: return
    log.info "Starting IMU reader..."
    run-thread = task::
      while true:
        int-pin.wait-for 1
        start-time := Time.monotonic-us
        imu.read-gyro
        elapsed-us := Time.monotonic-us - start-time
        cpu-monitor.update-latency elapsed-us
        if int-pin.get == 1:
          int-pin.wait-for 0
    log.info "SUCCESS: IMU reader started successfully"

  stop -> none:
    if run-thread:
      run-thread.cancel
      run-thread = null
      catch: int-pin.close
