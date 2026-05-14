import monitor show Channel

class HeartbeatTask:
  output /Channel
  interval-ms /int
  task_ /Task? := null
  counter /int := 0

  constructor --.output --.interval-ms=1000:

  start -> none:
    task_ = task::
      while true:
        output.send "Hello World! count=$counter"
        counter++
        sleep --ms=interval-ms

  stop -> none:
    if task_ != null:
      task_.cancel

  is-running -> bool:
    if task_ == null: return false
    return not task_.is-canceled
