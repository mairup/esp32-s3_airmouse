import gpio

// Drives hardware indicator LEDs (Pan Mode LED and Axis Lock LED) via bitmask commands received from the client.
class PanLed:
  pan-pin_ /gpio.Pin
  axis-lock-pin_ /gpio.Pin

  constructor --pan-pin/int --axis-lock-pin/int:
    pan-pin_ = gpio.Pin pan-pin --output
    pan-pin_.set 0
    axis-lock-pin_ = gpio.Pin axis-lock-pin --output
    axis-lock-pin_.set 0

  set-bitmask bitmask/int -> none:
    pan-pin_.set (bitmask & 0x01)
    axis-lock-pin_.set ((bitmask & 0x02) >> 1)

  close -> none:
    pan-pin_.set 0
    pan-pin_.close
    axis-lock-pin_.set 0
    axis-lock-pin_.close
