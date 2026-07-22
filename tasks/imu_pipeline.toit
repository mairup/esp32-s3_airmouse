import log
import gpio
import ..imu show Imu
import ..utils.mahony_filter show MahonyFilter
import ..utils.one_euro_filter show OneEuroFilter
import ..utils.imu_data as imu-data
import ..utils.packet_encoder as packet_encoder
import .cpu_monitor show CpuMonitor

class ImuPipeline:
  imu /Imu
  cpu-monitor /CpuMonitor
  send-to /Lambda
  stage /string
  run-thread /Task? := null
  sample-interval-seconds_ /float ::= 0.01

  mahony-filter_ /MahonyFilter ::= MahonyFilter
  pitch-filter_ /OneEuroFilter ::= OneEuroFilter --min-cutoff=1.0 --beta=0.005 --d-cutoff=1.0
  yaw-filter_   /OneEuroFilter ::= OneEuroFilter --min-cutoff=1.0 --beta=0.005 --d-cutoff=1.0
  roll-filter_  /OneEuroFilter ::= OneEuroFilter --min-cutoff=1.0 --beta=0.005 --d-cutoff=1.0

  constructor --.imu --.cpu-monitor --.send-to --.stage:
    counter := 0

  start -> none:
    if run-thread: return
    log.info "Starting IMU pipeline..."
    
    int-pin := gpio.Pin imu.int-pin-num --input --pull-down=true

    run-thread = task::
      counter := 0
      while true:
        int-pin.wait-for 1

        start-time := Time.monotonic-us

        imu.read-sensors

        mahony-filter_.update
          --gyro-x=imu.gyro-x-rad
          --gyro-y=imu.gyro-y-rad
          --gyro-z=imu.gyro-z-rad
          --accel-x=imu.accel-x-g
          --accel-y=imu.accel-y-g
          --accel-z=imu.accel-z-g
          --delta-seconds=sample-interval-seconds_

        raw-pitch := mahony-filter_.pitch-rad
        raw-yaw   := mahony-filter_.yaw-rad
        raw-roll  := mahony-filter_.roll-rad

        imu-data.pitch = pitch-filter_.filter --val=raw-pitch --delta-seconds=sample-interval-seconds_
        imu-data.yaw   = yaw-filter_.filter   --val=raw-yaw   --delta-seconds=sample-interval-seconds_
        imu-data.roll  = roll-filter_.filter  --val=raw-roll  --delta-seconds=sample-interval-seconds_
        
        packet := encode-packet_ (counter++)
            
        if packet:
          send-to.call packet

        elapsed-us := Time.monotonic-us - start-time
        cpu-monitor.update-latency elapsed-us

    log.info "SUCCESS: IMU pipeline started successfully"

  stop -> none:
    if run-thread:
      run-thread.cancel
      run-thread = null

  encode-packet_ seq/int -> ByteArray?:
    if stage == "raw":
      return packet_encoder.encode-raw-packet
        --seq=seq
        --buttons=imu-data.button_states
        --gx=imu-data.gyro_x
        --gy=imu-data.gyro_y
        --gz=imu-data.gyro_z
        --ax=imu-data.accel_x
        --ay=imu-data.accel_y
        --az=imu-data.accel_z
    else if stage == "fusion":
      return packet_encoder.encode-fusion-packet
        --seq=seq
        --buttons=imu-data.button_states
        --pitch=imu-data.pitch
        --yaw=imu-data.yaw
        --roll=imu-data.roll
    else if stage == "kinematics":
      return packet_encoder.encode-kinematics-packet
        --seq=seq
        --buttons=imu-data.button_states
        --delta-x=imu-data.delta_x
        --delta-y=imu-data.delta_y
    return null
