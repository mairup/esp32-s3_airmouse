import gpio
import log

REDUNDANCY-COUNT    ::= 5
REDUNDANCY-DELAY-MS ::= 10

BTN-DOWN-BYTES ::= "BTN_DOWN\n".to-byte-array
BTN-UP-BYTES   ::= "BTN_UP\n".to-byte-array

class ButtonService:
  pin /gpio.Pin
  send-to /Lambda
  run-thread /Task? := null

  constructor --pin-num/int --.send-to:
    log.info "Setting up button service on Pin $pin-num..."
    pin = gpio.Pin pin-num --input --pull-up=true
    log.info "SUCCESS: ButtonService initialized on Pin $pin-num"

  start -> none:
    if run-thread: return
    log.info "Starting ButtonService..."
    run-thread = task::
      last-state := 1
      while true:
        if last-state == 1:
          pin.wait-for 0
          last-state = 0
          REDUNDANCY-COUNT.repeat:
            send-to.call BTN-DOWN-BYTES
            sleep --ms=REDUNDANCY-DELAY-MS
        else:
          pin.wait-for 1
          last-state = 1
          REDUNDANCY-COUNT.repeat:
            send-to.call BTN-UP-BYTES
            sleep --ms=REDUNDANCY-DELAY-MS
        
        // Debounce period
        sleep --ms=30
    log.info "SUCCESS: ButtonService started"

  stop -> none:
    if run-thread:
      run-thread.cancel
      run-thread = null
      catch: pin.close
