import gpio

class ButtonService:
  pin /gpio.Pin
  send-to /Lambda
  run-thread /Task? := null

  constructor --pin-num/int --.send-to:
    pin = gpio.Pin pin-num --input --pull-up=true

  start -> none:
    if run-thread: return
    run-thread = task::
      last-state := 1
      while true:
        if last-state == 1:
          pin.wait-for 0
          last-state = 0
          send-to.call "BTN_DOWN\n"
        else:
          pin.wait-for 1
          last-state = 1
          send-to.call "BTN_UP\n"
        
        // Debounce period: Sleep to ignore rapid contact bounces
        sleep --ms=30

  stop -> none:
    if run-thread:
      run-thread.cancel
      run-thread = null
      catch: pin.close
