import log

class Heartbeat:
  send-to /Lambda
  generator /Lambda
  interval /Duration
  run-thread /Task? := null

  constructor --.send-to --.generator --.interval/Duration:

  start -> none:
    if run-thread: return
    log.info "Starting Heartbeat service..."
    error := catch:
      run-thread = task::
        next-time := Time.now + interval
        while true:
          val := generator.call
          send-to.call val
          now := Time.now
          if next-time > now:
            sleep (now.to next-time)
          else:
            sleep --ms=0
            next-time = now
          next-time += interval
    if error:
      log.error "Failed to start Heartbeat service: $error"
      throw error
    else:
      log.info "SUCCESS: Heartbeat started"

  stop -> none:
    if run-thread:
      run-thread.cancel
      run-thread = null
