import gpio
import gpio.pwm
import math

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
        
    generator = pwm.Pwm --frequency=1000
    red-channel = generator.start (gpio.Pin red)
    green-channel = generator.start (gpio.Pin green)
    blue-channel = generator.start (gpio.Pin blue)
    update_

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

  // ========================================================================
  // Private Core Logic
  // ========================================================================
  update_ -> none:
    r-factor := (red * brightness) / (255.0 * 100.0)
    g-factor := (green * brightness) / (255.0 * 100.0)
    b-factor := (blue * brightness) / (255.0 * 100.0)

    red-channel.set-duty-factor r-factor
    green-channel.set-duty-factor g-factor
    blue-channel.set-duty-factor b-factor
