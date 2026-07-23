import gpio
import gpio.adc as gpio_adc
import log
import ..utils.imu_data as imu_data

class PotentiometerManager:
  pin-num /int
  run-thread /Task? := null

  constructor --.pin-num:

  start -> none:
    if run-thread: return
    log.info "Starting PotentiometerManager on GPIO $pin-num..."
    
    pin := gpio.Pin pin-num
    adc := gpio_adc.Adc pin

    run-thread = task::
      while true:
        voltage-ratio := adc.get
        imu-data.potentiometer_val = (voltage-ratio * 4095.0).to-int
        sleep --ms=50

    log.info "SUCCESS: PotentiometerManager started successfully"

  stop -> none:
    if run-thread:
      run-thread.cancel
      run-thread = null
