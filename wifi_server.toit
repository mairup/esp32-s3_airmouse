import net
import net.udp as udp
import monitor show Channel Latch
import log

class WifiServer:
  static STATE-STOPPED     ::= 0
  static STATE-STARTING    ::= 1
  static STATE-ADVERTISING ::= 2
  static STATE-CONNECTED   ::= 3
  static STATE-ERROR       ::= 4

  static PORT ::= 8889
  static HEARTBEAT-TIMEOUT ::= Duration --ms=500
  static RECOVERY-DELAY    ::= Duration --ms=500

  name /string
  tx-bus /Channel
  
  state /int := STATE-STOPPED

  main-task /Task? := null
  rx-task /Task? := null
  tx-task /Task? := null
  heartbeat-task /Task? := null
  network /net.Interface? := null
  server-socket /udp.Socket? := null
  target-address /net.SocketAddress? := null
  last-heartbeat-time /Time := Time.now

  constructor
      --.name/string
      --tx-queue-size=10:
    tx-bus = Channel tx-queue-size

  /// Log state transitions.
  static log-state-change state/int --context=null -> none:
    if state == STATE-ADVERTISING:
      log.info "[Wi-Fi] UDP server advertising on port $PORT"
    else if state == STATE-CONNECTED:
      log.info "[Wi-Fi] Client registered"
    else if state == STATE-ERROR:
      log.error "[Wi-Fi] Error" --tags={"context": context}
    else if state == STATE-STOPPED:
      log.info "[Wi-Fi] Service stopped"

  set-state new-state/int --context=null -> none:
    if state == new-state: return
    state = new-state
    log-state-change state --context=context


  start -> none:
    if main-task:
      log.warn "[Wi-Fi] start called while already running, ignoring"
      return

    set-state STATE-STARTING
    main-task = task::
      while true:
        error-latch := Latch
        error := catch:
          network = net.open
          server-socket = network.udp-open --port=PORT
          log.info "Wi-Fi Server '$name' listening on $(network.address):$PORT"
          set-state STATE-ADVERTISING

          tx-task = task:: run-tx-loop
          rx-task = task:: run-rx-loop error-latch

          throw error-latch.get

        if error == "CANCELED": break
        set-state STATE-ERROR --context=error
        release-resources_
        sleep RECOVERY-DELAY
        set-state STATE-STARTING

  /// Register or update the connected client address.
  register-client address/net.SocketAddress -> none:
    if not target-address or target-address != address:
      target-address = address
      log.info "[Wi-Fi] Client registered from $target-address"
    if state != STATE-CONNECTED:
      set-state STATE-CONNECTED
      if heartbeat-task: heartbeat-task.cancel
      heartbeat-task = task:: run-heartbeat-timeout-check

  /// Poll for heartbeat timeout while connected.
  run-heartbeat-timeout-check -> none:
    while state == STATE-CONNECTED:
      sleep --ms=50
      elapsed := last-heartbeat-time.to Time.now
      if elapsed > HEARTBEAT-TIMEOUT:
        handle-client-timeout
        return

  /// Drop the current client on heartbeat timeout.
  handle-client-timeout -> none:
    if target-address:
      log.info "[Wi-Fi] Client $target-address disconnected (timeout)"
      target-address = null
      if state == STATE-CONNECTED:
        set-state STATE-ADVERTISING

  run-rx-loop error-latch/Latch -> none:
    error := catch:
      while true:
        datagram := server-socket.receive
        last-heartbeat-time = Time.now
        register-client datagram.address
    if error and error != "CANCELED":
      error-latch.set error

  /// Forward TX-bus data to the registered client.
  run-tx-loop -> none:
    clear-tx-queue_
    while state == STATE-ADVERTISING or state == STATE-CONNECTED:
      data/ByteArray := tx-bus.receive
      if target-address:
        transmit_ data

  /// Send a single datagram to the registered client.
  transmit_ data/ByteArray -> none:
    error := catch: 
      datagram := udp.Datagram data target-address
      server-socket.send datagram
    if error:
      log.warn "[Wi-Fi] TX failed" --tags={"error": error}

  /// Cancel main task and release hardware resources.
  stop -> none:
    if main-task:
      main-task.cancel
      main-task = null
    release-resources_
    set-state STATE-STOPPED

  /// Close socket and network without cancelling the main task.
  release-resources_ -> none:
    if rx-task:
      rx-task.cancel
      rx-task = null
    if heartbeat-task:
      heartbeat-task.cancel
      heartbeat-task = null
    if server-socket:
      catch: server-socket.close
      server-socket = null
    if network:
      catch: network.close
      network = null
    target-address = null

  /// Enqueue data to TX bus. Returns false if not connected or buffer full.
  send data/string -> bool:
    if state == STATE-CONNECTED:
      return tx-bus.try-send data.to-byte-array
    return false

  /// Drain any stale data from the TX queue.
  clear-tx-queue_ -> none:
    while (tx-bus.receive --blocking=false):
      null  // discard
