import gpio
import gpio.pwm
import math
import ..ble_server show BleServer

BREATHE-TABLE_ ::= build-breathe-table_

build-breathe-table_ -> List:
  table := List 200
  200.repeat: |ticks|
    x := ticks / 200.0
    breathe-factor := 0.0
    if x < 0.60:
      t := x / 0.60
      breathe-factor = (math.pow 2.0 (-8.0 * t)) * (math.sin (t * 22.0)) + 1.0
    else:
      t := (x - 0.60) / 0.40
      breathe-factor = 0.5 * (math.cos (t * math.PI) + 1.0)
    table[ticks] = (255.0 * breathe-factor).to-int
  return table

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
        // Playful Flutter-style spring-breathing cycle (period = 2.0s -> 200 steps at 100Hz)
        ticks := flash-ticks % 200
        r = 0
        g = 0
        b = BREATHE-TABLE_[ticks]
        flash-ticks++
      else if state == BleServer.STATE-CONNECTED:
        r = 0; g = 255; b = 0 // Green
      else if state == BleServer.STATE-ERROR:
        r = 255; g = 0; b = 0 // Red

      // Reset breathing ticks when not advertising
      if state != BleServer.STATE-ADVERTISING:
        flash-ticks = 0

      // Only write to physical PWM registers if color index actually changes
      if r != last-r or g != last-g or b != last-b:
        led.set-color r g b
        last-r = r
        last-g = g
        last-b = b

      sleep --ms=10
