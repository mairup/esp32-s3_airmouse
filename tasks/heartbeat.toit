
class Heartbeat:
  send-to /Lambda
  generator /Lambda
  interval /Duration
  run-thread /Task? := null

  constructor --.send-to --.generator --.interval/Duration:

  start -> none:
    if run-thread: return
    run-thread = task::
      while true:
        val := generator.call
        send-to.call val
        sleep interval

  stop -> none:
    if run-thread:
      run-thread.cancel
      run-thread = null
