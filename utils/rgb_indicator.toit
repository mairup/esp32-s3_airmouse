import log
import .rgb_led show RgbLed

class RgbIndicator:
  led /RgbLed
  server /any

  last-r_ := -1
  last-g_ := -1
  last-b_ := -1

  run-thread /Task? := null

  constructor .server .led:

  start -> none:
    if run-thread: return
    log.info "Starting RgbIndicator..."
    error := catch:
      run-thread = task:: run_
    if error:
      log.error "Failed to start RgbIndicator: $error"
      throw error
    else:
      log.info "SUCCESS: RgbIndicator started"

  stop -> none:
    if run-thread:
      run-thread.cancel
      run-thread = null
      catch: led.set-color 0 0 0

  force-update -> none:
    last-r_ = -1
    last-g_ = -1
    last-b_ = -1

  run_ -> none:
    while true:
      state := server.state
      
      r := 0
      g := 0
      b := 0
      
      if state == 0:
        r = 0; g = 0; b = 0
      else if state == 1:
        r = 255; g = 128; b = 0
      else if state == 2:
        r = 0; g = 0; b = 255
      else if state == 3:
        r = 0; g = 255; b = 0
      else if state == 4:
        r = 255; g = 0; b = 0

      if r != last-r_ or g != last-g_ or b != last-b_:
        led.set-color r g b
        last-r_ = r
        last-g_ = g
        last-b_ = b

      sleep --ms=10
