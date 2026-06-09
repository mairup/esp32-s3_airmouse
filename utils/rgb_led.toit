import gpio
import gpio.pwm
import ..ble_server show BleServer

// Precomputed breathe animation lookup table (200 steps)
BREATHE-TABLE ::= [
  255, 299, 338, 371, 396, 415, 427, 431, 430, 422, 410, 393, 373, 351, 327, 303, 280, 257, 237, 219,
  204, 192, 183, 177, 174, 175, 178, 183, 191, 200, 210, 220, 231, 242, 252, 261, 270, 277, 282, 287,
  289, 291, 291, 289, 287, 284, 280, 276, 271, 266, 261, 256, 252, 248, 245, 242, 240, 239, 238, 238,
  239, 240, 241, 243, 245, 247, 249, 251, 253, 255, 257, 259, 260, 261, 262, 262, 262, 262, 261, 261,
  260, 259, 258, 257, 256, 255, 254, 253, 253, 252, 252, 251, 251, 251, 251, 251, 252, 252, 252, 253,
  253, 254, 254, 255, 255, 255, 256, 256, 256, 256, 256, 256, 256, 256, 256, 255, 255, 255, 255, 255,
  255, 254, 254, 254, 253, 252, 251, 250, 248, 247, 245, 243, 241, 238, 236, 233, 230, 227, 224, 221,
  217, 214, 210, 206, 202, 198, 194, 189, 185, 180, 176, 171, 166, 162, 157, 152, 147, 142, 137, 132,
  127, 122, 117, 112, 107, 102, 97, 92, 88, 83, 78, 74, 69, 65, 60, 56, 52, 48, 44, 40,
  37, 33, 30, 27, 24, 21, 18, 16, 13, 11, 9, 7, 6, 4, 3, 2, 1, 0, 0, 0,
]

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
        b = BREATHE-TABLE[ticks]
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
