import gpio
import log
import ..imu show Imu
import ..utils.rgb_led show RgbLed
import ..utils.rgb_indicator show RgbIndicator
import ..utils.imu_data as imu_data

MAX-STATIONARY-MOTION-LSB ::= 300
CALIBRATION-SAMPLES        ::= 50

class GestureManager:
  gesture-pin-num /int
  imu /Imu
  rgb-led /RgbLed
  rgb-indicator /RgbIndicator
  run-thread /Task? := null

  constructor --gesture-pin/int --.imu --.rgb-led --.rgb-indicator:
    gesture-pin-num = gesture-pin

  start -> none:
    if run-thread: return
    log.info "Starting GestureManager on GPIO $gesture-pin-num..."
    
    pin := gpio.Pin gesture-pin-num --input --pull-up=true

    run-thread = task::
      while true:
        pin.wait-for 0
        
        sleep --ms=25
        if pin.get == 0:
          handle-gesture-press_ pin
          
        sleep --ms=50

    log.info "SUCCESS: GestureManager started"

  calculate-total-gyro-motion-lsb_ -> int:
    return imu_data.gyro_x.abs + imu_data.gyro_y.abs + imu_data.gyro_z.abs

  handle-gesture-press_ pin/gpio.Pin -> none:
    log.info "Gesture button pressed. Hold stationary for 1s to trigger recalibration..."
    rgb-led.set-color 180 0 255

    hold-valid := true

    for i := 0; i < 10; i++:
      if pin.get != 0:
        log.warn "Gesture aborted: button released before 1 second hold ($((i + 1) * 100)ms)"
        hold-valid = false
        break
      
      gyro-magnitude := calculate-total-gyro-motion-lsb_
      if gyro-magnitude > MAX-STATIONARY-MOTION-LSB:
        log.warn "Gesture aborted: motion detected during hold (magnitude: $gyro-magnitude > $MAX-STATIONARY-MOTION-LSB)"
        hold-valid = false
        break
      
      sleep --ms=100

    if hold-valid and pin.get == 0:
      log.info "VALID GESTURE: Starting hardware gyro zero-bias recalibration..."
      success := recalibrate-gyroscope_
      if success:
        blink-8hz-green-confirmation-led_
      else:
        log.warn "Recalibration aborted due to motion during calibration window"

    rgb-indicator.force-update
    pin.wait-for 1
    sleep --ms=100

  recalibrate-gyroscope_ -> bool:
    sum-x := 0
    sum-y := 0
    sum-z := 0
    
    for i := 0; i < CALIBRATION-SAMPLES; i++:
      gyro-magnitude := calculate-total-gyro-motion-lsb_
      if gyro-magnitude > MAX-STATIONARY-MOTION-LSB:
        return false

      sum-x += imu_data.gyro_x
      sum-y += imu_data.gyro_y
      sum-z += imu_data.gyro_z
      sleep --ms=10

    imu_data.gyro_offset_x = sum-x / CALIBRATION-SAMPLES
    imu_data.gyro_offset_y = sum-y / CALIBRATION-SAMPLES
    imu_data.gyro_offset_z = sum-z / CALIBRATION-SAMPLES

    log.info "SUCCESS: Hardware recalibration completed! Gyro Offsets -> X: $imu_data.gyro_offset_x, Y: $imu_data.gyro_offset_y, Z: $imu_data.gyro_offset_z"
    return true

  blink-8hz-green-confirmation-led_ -> none:
    for i := 0; i < 5; i++:
      rgb-led.set-color 0 255 0
      sleep --ms=62
      rgb-led.set-color 0 0 0
      sleep --ms=63

