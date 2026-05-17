
class Heartbeat:
  send-to /Lambda
  interval-ms /int
  run-thread /Task? := null
  counter /int := 0

  constructor --.send-to --.interval-ms=1000:

  start -> none:
    if run-thread: return
    run-thread = task::
      while true:
        send-to.call "$counter"
        counter++
        sleep --ms=interval-ms

  stop -> none:
    if run-thread:
      run-thread.cancel
      run-thread = null
