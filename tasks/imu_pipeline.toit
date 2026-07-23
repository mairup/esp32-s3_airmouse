import log
import gpio
import ..imu show Imu

import ..utils.imu_data as imu-data
import ..utils.packet_encoder as packet_encoder
import .cpu_monitor show CpuMonitor

class ImuPipeline:
  imu /Imu
  cpu-monitor /CpuMonitor
  send-to /Lambda
  run-thread /Task? := null

  constructor --.imu --.cpu-monitor --.send-to:

  start -> none:
    if run-thread: return
    log.info "Starting IMU pipeline..."
    
    int-pin := gpio.Pin imu.int-pin-num --input --pull-down=true

    log.info "SUCCESS: IMU pipeline started successfully"
    run-thread = task::
      counter := 0
      while true:
        int-pin.wait-for 1

        start-time := Time.monotonic-us

        imu.read-sensors

        packet := packet_encoder.encode-raw-packet
          --seq=(counter++)
          --buttons=imu-data.button_states
          --gx=(imu-data.gyro_x - imu-data.gyro_offset_x)
          --gy=(imu-data.gyro_y - imu-data.gyro_offset_y)
          --gz=(imu-data.gyro_z - imu-data.gyro_offset_z)
          --ax=imu-data.accel_x
          --ay=imu-data.accel_y
          --az=imu-data.accel_z
          --pot=imu-data.potentiometer_val
            
        send-to.call packet

        elapsed-us := Time.monotonic-us - start-time
        cpu-monitor.update-latency elapsed-us

  stop -> none:
    if run-thread:
      run-thread.cancel
      run-thread = null


