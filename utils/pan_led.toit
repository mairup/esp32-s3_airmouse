import gpio

// Drives a single output LED pin in response to pan mode commands received from the client.
class PanLed:
  pin_ /gpio.Pin

  constructor --pin-num/int:
    pin_ = gpio.Pin pin-num --output
    pin_.set 0

  set state/int -> none:
    pin_.set state

  close -> none:
    pin_.set 0
    pin_.close
