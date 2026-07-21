import gpio
import gpio.pwm
import log
import math

GAMMA-TABLE ::= List 256: | i | math.pow (i / 255.0) 2.2

class RgbLed:
  // ========================================================================
  // Instance Fields
  // ========================================================================
  generator     /pwm.Pwm
  red-channel   /pwm.PwmChannel
  green-channel /pwm.PwmChannel
  blue-channel  /pwm.PwmChannel

  red        /int := 0
  green      /int := 0
  blue       /int := 0
  brightness /int := 100

  // ========================================================================
  // Constructor
  // ========================================================================
  constructor 
      --red/int 
      --green/int 
      --blue/int 
      --.brightness/int=100:
        
    log.info "Initializing RgbLed on R:$red, G:$green, B:$blue..."
    generator = pwm.Pwm --frequency=1000
    red-channel = generator.start (gpio.Pin red)
    green-channel = generator.start (gpio.Pin green)
    blue-channel = generator.start (gpio.Pin blue)
    update_
    log.info "SUCCESS: RgbLed initialized successfully"

  // ========================================================================
  // Public API
  // ========================================================================
  set-color r/int g/int b/int -> none:
    red = r
    green = g
    blue = b
    update_

  set-brightness value/int -> none:
    brightness = value
    update_

  run-color-test -> none:
    log.info "Starting color diagnostic test loop (switches every 2 seconds)..."
    while true:
      log.info "Setting RED"
      set-color 255 0 0
      sleep --ms=2000

      log.info "Setting GREEN"
      set-color 0 255 0
      sleep --ms=2000

      log.info "Setting BLUE"
      set-color 0 0 255
      sleep --ms=2000

      log.info "Setting ORANGE"
      set-color 255 128 0
      sleep --ms=2000

  // ========================================================================
  // Private Core Logic
  // ========================================================================
  update_ -> none:
    brightness-factor := brightness / 100.0

    r-factor := GAMMA-TABLE[red] * brightness-factor
    g-factor := GAMMA-TABLE[green] * brightness-factor
    b-factor := GAMMA-TABLE[blue] * brightness-factor

    red-channel.set-duty-factor r-factor
    green-channel.set-duty-factor g-factor
    blue-channel.set-duty-factor b-factor
