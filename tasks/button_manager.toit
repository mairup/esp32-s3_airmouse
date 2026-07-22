import gpio
import log
import ..utils.imu_data as imu_data

// Bit masks
BIT-CLUTCH      ::= 1 << 0
BIT-LEFT-CLICK  ::= 1 << 1
BIT-RIGHT-CLICK ::= 1 << 2

class ButtonManager:
  tasks_ /List := []

  constructor --clutch-pin/int:
    log.info "Initializing ButtonManager (Clutch Pin: $clutch-pin)..."
    
    // We can add more buttons here later
    tasks_.add (
      task:: monitor-button_ clutch-pin BIT-CLUTCH
    )
    
    log.info "SUCCESS: ButtonManager initialized"

  monitor-button_ pin-num/int bit-mask/int -> none:
    pin := gpio.Pin pin-num --input --pull-up=true
    
    last-state := 1
    while true:
      if last-state == 1:
        pin.wait-for 0
        last-state = 0
        imu-data.button_states |= bit-mask // Set bit
      else:
        pin.wait-for 1
        last-state = 1
        imu-data.button_states &= ~bit-mask // Clear bit
      
      // Debounce period
      sleep --ms=30
