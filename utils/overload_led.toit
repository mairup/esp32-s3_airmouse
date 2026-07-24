import gpio
import log

class OverloadLed:
  pin_ /gpio.Pin

  constructor --pin-num/int:
    log.info "Initializing Overload LED on Pin $pin-num..."
    pin_ = gpio.Pin pin-num --output
    off
    log.info "SUCCESS: Overload LED initialized successfully"

  on -> none:
    pin_.set 1

  off -> none:
    pin_.set 0

