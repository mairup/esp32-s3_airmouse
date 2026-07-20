import gpio

REDUNDANCY-COUNT    ::= 3
REDUNDANCY-DELAY-MS ::= 5

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
          REDUNDANCY-COUNT.repeat:
            send-to.call "BTN_DOWN\n"
            sleep --ms=REDUNDANCY-DELAY-MS
        else:
          pin.wait-for 1
          last-state = 1
          REDUNDANCY-COUNT.repeat:
            send-to.call "BTN_UP\n"
            sleep --ms=REDUNDANCY-DELAY-MS
        
        // Debounce period
        sleep --ms=30

  stop -> none:
    if run-thread:
      run-thread.cancel
      run-thread = null
      catch: pin.close
