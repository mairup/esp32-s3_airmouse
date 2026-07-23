import gpio
import log
import ..utils.imu_data as imu_data

BIT-CLUTCH      ::= 1 << 0
BIT-LEFT-CLICK  ::= 1 << 1
BIT-RIGHT-CLICK ::= 1 << 2

class ButtonManager:
  tasks_ /List := []

  constructor 
      --clutch-pin/int 
      --left-click-pin/int 
      --right-click-pin/int
      --left-click-led-pin/int? = null
      --right-click-led-pin/int? = null:
    log.info "Initializing ButtonManager..."
    
    tasks_.add (
      task:: monitor-button_ clutch-pin BIT-CLUTCH
    )
    tasks_.add (
      task:: monitor-button_ left-click-pin BIT-LEFT-CLICK --led-pin=left-click-led-pin
    )
    tasks_.add (
      task:: monitor-button_ right-click-pin BIT-RIGHT-CLICK --led-pin=right-click-led-pin
    )
    
    log.info "SUCCESS: ButtonManager initialized"

  monitor-button_ pin-num/int bit-mask/int --led-pin/int?=null -> none:
    pin := gpio.Pin pin-num --input --pull-up=true
    led/gpio.Pin? := led-pin ? (gpio.Pin led-pin --output) : null
    
    current-state := pin.get
    apply-button-state_ current-state bit-mask led

    while true:
      target-level := current-state == 1 ? 0 : 1
      pin.wait-for target-level
      
      sleep --ms=15

      sampled := pin.get
      if sampled != current-state:
        current-state = sampled
        apply-button-state_ current-state bit-mask led

  apply-button-state_ state/int bit-mask/int led/gpio.Pin? -> none:
    if state == 0:
      imu-data.button_states |= bit-mask
      if led: led.set 1
    else:
      imu-data.button_states &= ~bit-mask
      if led: led.set 0
