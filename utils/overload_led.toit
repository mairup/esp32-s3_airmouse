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

  toggle -> none:
    pin_.set (pin_.get == 0 ? 1 : 0)

  blink-test -> none:
    10.repeat:
      toggle
      sleep --ms=100
    off
