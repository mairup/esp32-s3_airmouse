import log
import ..utils.overload_led show OverloadLed


class CpuMonitor:
  led /OverloadLed
  latency-us_ /int := 0
  run-thread /Task? := null

  constructor --.led:

  update-latency latency/int -> none:
    latency-us_ = latency

  start -> none:
    if run-thread: return
    log.info "Starting CPU Monitor..."
    error := catch:
      run-thread = task::
        while true:
          if latency-us_ > 2400: // 2.4ms budget at 416Hz
            led.on
          else:
            led.off
          sleep --ms=100
    if error:
      log.error "Failed to start CPU Monitor: $error"
      throw error
    else:
      log.info "SUCCESS: CPU Monitor started"
