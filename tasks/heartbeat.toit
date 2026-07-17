
class Heartbeat:
  send-to /Lambda
  generator /Lambda
  interval /Duration
  run-thread /Task? := null

  constructor --.send-to --.generator --.interval/Duration:

  start -> none:
    if run-thread: return
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

  stop -> none:
    if run-thread:
      run-thread.cancel
      run-thread = null
