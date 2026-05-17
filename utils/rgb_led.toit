import gpio
import gpio.pwm
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
    flash-ticks := 0
    flash-on := false
    
    last-state := -1
    last-flash-on := false

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
        if flash-ticks % 25 == 0:
          flash-on = not flash-on
        
        if flash-on:
          r = 0; g = 0; b = 255 // Blue
        else:
          r = 0; g = 0; b = 0
        flash-ticks++
      else if state == BleServer.STATE-CONNECTED:
        r = 0; g = 255; b = 0 // Green
      else if state == BleServer.STATE-ERROR:
        r = 255; g = 0; b = 0 // Red

      // Reset flash state when not advertising
      if state != BleServer.STATE-ADVERTISING:
        flash-ticks = 0
        flash-on = false

      // Only write to the physical PWM registers if state or flash tick changes
      if state != last-state or flash-on != last-flash-on:
        led.set-color r g b
        last-state = state
        last-flash-on = flash-on

      sleep --ms=10
