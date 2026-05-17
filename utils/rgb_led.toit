import gpio
import gpio.pwm
import math
import ..ble_server show BleServer

class RgbLed:
  red-channel   /pwm.PwmChannel
  green-channel /pwm.PwmChannel
  blue-channel  /pwm.PwmChannel

  red        /int := 0
  green      /int := 0
  blue       /int := 0
  brightness /int := 100 // 0 -- 100

  constructor --red/int --green/int --blue/int --.brightness/int=100:
    generator := pwm.Pwm --frequency=1000
    red-channel = generator.start (gpio.Pin red)
    green-channel = generator.start (gpio.Pin green)
    blue-channel = generator.start (gpio.Pin blue)
    update_

  set-color r/int g/int b/int -> none:
    red = r
    green = g
    blue = b
    update_

  set-brightness value/int -> none:
    brightness = value
    update_

  update_ -> none:
    // Scale current R, G, B by the 0-100 brightness percentage
    r-factor := (red * brightness) / (255.0 * 100.0)
    g-factor := (green * brightness) / (255.0 * 100.0)
    b-factor := (blue * brightness) / (255.0 * 100.0)

    red-channel.set-duty-factor r-factor
    green-channel.set-duty-factor g-factor
    blue-channel.set-duty-factor b-factor


class RgbIndicator:
  led /RgbLed
  ble /BleServer

  constructor .led .ble:

  start -> none:
    task:: run_

  run_ -> none:
    flash-angle := 0.0
    
    last-r := -1
    last-g := -1
    last-b := -1

    while true:
      state := ble.state
      
      // Determine target colors
      r := 0
      g := 0
      b := 0
      
      if state == BleServer.STATE-STOPPED:
        r = 0; g = 0; b = 0
      else if state == BleServer.STATE-STARTING:
        r = 255; g = 128; b = 0 // Orange
      else if state == BleServer.STATE-ADVERTISING:
        // Slow biological breathing cycle (period = 3.0s -> 300 steps at 100Hz)
        flash-angle += (2.0 * math.PI / 300.0)
        sin-val := math.sin flash-angle
        
        // Apple Gaussian Breathing Curve: e^sin(t) normalized to [0.0, 1.0]
        breathe-factor := (math.exp sin-val - 0.367879) / 2.350402
        
        r = 0
        g = 0
        b = (255.0 * breathe-factor).to-int
      else if state == BleServer.STATE-CONNECTED:
        r = 0; g = 255; b = 0 // Green
      else if state == BleServer.STATE-ERROR:
        r = 255; g = 0; b = 0 // Red

      // Reset breathing angle when not advertising
      if state != BleServer.STATE-ADVERTISING:
        flash-angle = 0.0

      // Only write to physical PWM registers if color index actually changes
      if r != last-r or g != last-g or b != last-b:
        led.set-color r g b
        last-r = r
        last-g = g
        last-b = b

      sleep --ms=10
