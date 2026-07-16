import ..ble_server show BleServer
import .rgb_led show RgbLed

class RgbIndicator:
  led /RgbLed
  ble /BleServer

  constructor .ble .led:

  start -> none:
    task:: run_

  run_ -> none:
    
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
        r = 0; g = 0; b = 255 // Solid Blue
      else if state == BleServer.STATE-CONNECTED:
        r = 0; g = 255; b = 0 // Green
      else if state == BleServer.STATE-ERROR:
        r = 255; g = 0; b = 0 // Red

      // Only write to physical PWM registers if color index actually changes
      if r != last-r or g != last-g or b != last-b:
        led.set-color r g b
        last-r = r
        last-g = g
        last-b = b

      sleep --ms=10
