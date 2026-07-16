import net
import net.tcp as tcp
import monitor show Channel
import log

class WifiServer:
  static STATE-STOPPED     ::= 0
  static STATE-STARTING    ::= 1
  static STATE-ADVERTISING ::= 2
  static STATE-CONNECTED   ::= 3
  static STATE-ERROR       ::= 4

  static PORT ::= 8889

  /// Default state-change logger
  static print-state state/int context/any -> none:
    if state == STATE-ADVERTISING:
      log.info "[Wi-Fi] Ready and listening"
    else if state == STATE-CONNECTED:
      log.info "[Wi-Fi] Client connected"
    else if state == STATE-ERROR:
      log.error "[Wi-Fi] Error" --tags={"context": context}
    else if state == STATE-STOPPED:
      log.info "[Wi-Fi] Service stopped"

  name /string
  tx-bus /Channel
  
  state /int := STATE-STOPPED

  main-task /Task? := null
  network /net.Interface? := null
  server-socket /tcp.ServerSocket? := null
  client-socket /tcp.Socket? := null

  constructor
      --.name/string
      --tx-queue-size=10:
    tx-bus = Channel tx-queue-size

  /// Update state
  set-state new-state/int --context=null -> none:
    if state != new-state:
      state = new-state
      print-state state context

      if state == STATE-ERROR:
        task::
          sleep --ms=100
          stop
          log.info "[RECOVERY] Waiting 2s before restart..."
          sleep --ms=2000
          start
    else: log.warn "Tried to reset the state" --tags={"state": state}

  /// Start Wi-Fi adapter and TX loop in background
  start -> none:
    if main-task:
      set-state STATE-ERROR --context="START_REQUESTED_WHILE_RUNNING"
      return

    set-state STATE-STARTING
    main-task = task::
      error := catch:
        network = net.open
        server-socket = network.tcp-listen PORT
        log.info "Wi-Fi Server '$name' listening on $(network.address):$PORT"
        
        while true:
          set-state STATE-ADVERTISING
          // Wait for client to connect
          client-socket = server-socket.accept
          set-state STATE-CONNECTED
          log.info "[Wi-Fi] Client connected from $(client-socket.peer-address)"
          
          run-tx-loop
          
          catch: client-socket.close
          client-socket = null
          log.info "[Wi-Fi] Client disconnected"
            
      if error != "CANCELED":
        set-state STATE-ERROR --context=error

  /// Stream TX channel data to hardware while connected
  run-tx-loop -> none:
    clear-tx-queue_
    while state == STATE-CONNECTED:
      data/ByteArray := tx-bus.receive
      if not transmit_ data: return

  /// Transmit data to connected client.
  /// Returns false on hardware or connection error.
  transmit_ data/ByteArray -> bool:
    error := catch: client-socket.out.write data
    if error:
      log.debug "[Wi-Fi] TX failed" --tags={"error": error}
      return false
    return true

  /// Cancel tasks and release hardware resources
  stop -> none:
    if main-task:
      main-task.cancel
      main-task = null

    if client-socket:
      catch: client-socket.close
      client-socket = null
    if server-socket:
      catch: server-socket.close
      server-socket = null
    if network:
      catch: network.close
      network = null
      
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
