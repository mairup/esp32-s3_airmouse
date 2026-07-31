import gpio
import gpio.adc as gpio_adc
import log
import ..utils.imu_data as imu_data

class PotentiometerManager:
  pin-num /int
  poll-interval-ms /int
  run-thread /Task? := null

  constructor --.pin-num --.poll-interval-ms=50:

  start -> none:
    if run-thread: return
    log.info "Starting PotentiometerManager on GPIO $pin-num..."
    
    pin := gpio.Pin pin-num
    adc := gpio_adc.Adc pin

    run-thread = task::
      while true:
        imu-data.potentiometer_val = adc.get --raw
        sleep --ms=poll-interval-ms

    log.info "SUCCESS: PotentiometerManager started successfully"

  stop -> none:
    if run-thread:
      run-thread.cancel
      run-thread = null
