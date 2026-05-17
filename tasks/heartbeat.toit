
class Heartbeat:
  send-to /Lambda
  generator /Lambda
  interval-ms /int
  run-thread /Task? := null

  constructor --.send-to --.generator --.interval-ms=1000:

  start -> none:
    if run-thread: return
    run-thread = task::
      while true:
        val := generator.call
        send-to.call val
        sleep --ms=interval-ms

  stop -> none:
    if run-thread:
      run-thread.cancel
      run-thread = null
