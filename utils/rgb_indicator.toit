import .rgb_led show RgbLed

class RgbIndicator:
  led /RgbLed
  server /any

  constructor .server .led:

  start -> none:
    task:: run_

  run_ -> none:
    
    last-r := -1
    last-g := -1
    last-b := -1

    while true:
      state := server.state
      
      // Determine target colors
      r := 0
      g := 0
      b := 0
      
      if state == 0: // STATE-STOPPED
        r = 0; g = 0; b = 0
      else if state == 1: // STATE-STARTING
        r = 255; g = 128; b = 0 // Orange
      else if state == 2: // STATE-ADVERTISING / LISTENING
        r = 0; g = 0; b = 255 // Solid Blue
      else if state == 3: // STATE-CONNECTED
        r = 0; g = 255; b = 0 // Green
      else if state == 4: // STATE-ERROR
        r = 255; g = 0; b = 0 // Red

      // Only write to physical PWM registers if color index actually changes
      if r != last-r or g != last-g or b != last-b:
        led.set-color r g b
        last-r = r
        last-g = g
        last-b = b

      sleep --ms=10
