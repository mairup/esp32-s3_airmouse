import net
import net.udp as udp
import monitor show Channel
import log

class WifiServer:
  static STATE-STOPPED     ::= 0
  static STATE-STARTING    ::= 1
  static STATE-ADVERTISING ::= 2
  static STATE-CONNECTED   ::= 3
  static STATE-ERROR       ::= 4

  static PORT ::= 8889
  static HEARTBEAT-TIMEOUT ::= Duration --ms=200

  /// Default state-change logger
  static print-state state/int context/any -> none:
    if state == STATE-ADVERTISING:
      log.info "[Wi-Fi] UDP server ready on port $PORT"
    else if state == STATE-CONNECTED:
      log.info "[Wi-Fi] Client registered"
    else if state == STATE-ERROR:
      log.error "[Wi-Fi] Error" --tags={"context": context}
    else if state == STATE-STOPPED:
      log.info "[Wi-Fi] Service stopped"

  name /string
  tx-bus /Channel
  
  state /int := STATE-STOPPED

  main-task /Task? := null
  network /net.Interface? := null
  server-socket /udp.Socket? := null
  target-address /net.SocketAddress? := null
  last-heartbeat-time /Time := Time.now

  constructor
      --.name/string
      --tx-queue-size=10:
    tx-bus = Channel tx-queue-size

  set-state new-state/int --context=null -> none:
    if state != new-state:
      state = new-state
      print-state state context

      if state == STATE-ERROR:
        task::
          sleep --ms=100
          stop
          log.info "[RECOVERY] Waiting 0.5s before restart..."
          sleep --ms=500
          start
    else: log.warn "Tried to reset the state" --tags={"state": state}

  /// Start Wi-Fi adapter and TX loop
  start -> none:
    if main-task:
      log.warn "[Wi-Fi] start called while already running, ignoring"
      return

    set-state STATE-STARTING
    main-task = task::
      error := catch:
        network = net.open
        server-socket = network.udp-open --port=PORT
        log.info "Wi-Fi Server '$name' listening on $(network.address):$PORT"
        set-state STATE-ADVERTISING
        
        task:: run-tx-loop
        
        while true:
          // Wait for client to send a hello/heartbeat packet
          datagram := server-socket.receive
          last-heartbeat-time = Time.now
          if not target-address or target-address != datagram.address:
            target-address = datagram.address
            log.info "[Wi-Fi] Client registered from $target-address"
            if state != STATE-CONNECTED:
              set-state STATE-CONNECTED
              task:: run-heartbeat-timeout-check
            
      if error != "CANCELED":
        set-state STATE-ERROR --context=error

  disconnect_ -> none:
    if target-address:
      log.info "[Wi-Fi] Client $target-address disconnected (timeout)"
      target-address = null
      if state == STATE-CONNECTED:
        set-state STATE-ADVERTISING

  run-heartbeat-timeout-check -> none:
    while state == STATE-CONNECTED:
      sleep --ms=50
      if (last-heartbeat-time.to Time.now) > HEARTBEAT-TIMEOUT:
        disconnect_
        return

  /// Stream TX channel data to hardware while connected
  run-tx-loop -> none:
    clear-tx-queue_
    while state == STATE-ADVERTISING or state == STATE-CONNECTED:
      data/ByteArray := tx-bus.receive
      if target-address:
        transmit_ data

  /// Transmit data to connected client.
  transmit_ data/ByteArray -> none:
    datagram := udp.Datagram data target-address
    catch: server-socket.send datagram

  /// Cancel tasks and release hardware resources
  stop -> none:
    if main-task:
      main-task.cancel
      main-task = null

    if server-socket:
      catch: server-socket.close
      server-socket = null
    if network:
      catch: network.close
      network = null
      
    target-address = null
    set-state STATE-STOPPED

  /// Enqueue data chunk to TX channel. 
  /// Returns false if not ready or buffer full
  send data/string -> bool:
    if state == STATE-CONNECTED:
      return tx-bus.try-send data.to-byte-array
    return false

  /// Clear any pending stale data in the TX queue
  clear-tx-queue_ -> none:
    while (tx-bus.receive --blocking=false):
      // Discard stale queued data
