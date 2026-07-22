import net
import net.udp as udp
import monitor show Channel Latch
import log

class WifiServer:
  // ========================================================================
  // Constants
  // ========================================================================
  static STATE-STOPPED     ::= 0
  static STATE-STARTING    ::= 1
  static STATE-ADVERTISING ::= 2
  static STATE-CONNECTED   ::= 3
  static STATE-ERROR       ::= 4

  static PORT ::= 8889
  static HEARTBEAT-TIMEOUT ::= Duration --ms=1000
  static RECOVERY-DELAY    ::= Duration --ms=500

  // ========================================================================
  // Properties
  // ========================================================================
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

  // ========================================================================
  // Constructor
  // ========================================================================
  constructor
      --.name/string
      --tx-queue-size=100:
    tx-bus = Channel tx-queue-size

  // ========================================================================
  // Public API
  // ========================================================================
  start -> none:
    if main-task:
      log.warn "[Wi-Fi] start called while already running, ignoring"
      return

    log.info "Initializing and starting Wi-Fi Server..."
    set-state_ STATE-STARTING
    main-task = task::
      while true:
        error-latch := Latch
        error := catch:
          run-server_ error-latch

        if error == "CANCELED": break
        set-state_ STATE-ERROR --context=error
        release-resources_
        sleep RECOVERY-DELAY
        set-state_ STATE-STARTING
    log.info "SUCCESS: Wi-Fi Server startup initiated successfully"

  stop -> none:
    main-task = cancel-task_ main-task
    release-resources_
    set-state_ STATE-STOPPED

  /// Enqueue data to TX bus. Returns false if not connected or buffer full.
  send data/string -> bool:
    if state == STATE-CONNECTED:
      return tx-bus.try-send data.to-byte-array
    return false

  /// Enqueue raw byte array to TX bus without string allocations.
  send-bytes data/ByteArray -> bool:
    if state == STATE-CONNECTED:
      return tx-bus.try-send data
    return false

  // ========================================================================
  // State Management
  // ========================================================================
  static log-state-change_ state/int --context=null -> none:
    if state == STATE-ADVERTISING:
      log.info "SUCCESS: [Wi-Fi] UDP server advertising on port $PORT"
    else if state == STATE-CONNECTED:
      log.info "SUCCESS: [Wi-Fi] Client registered"
    else if state == STATE-ERROR:
      log.error "[Wi-Fi] Error" --tags={"context": context}
    else if state == STATE-STOPPED:
      log.warn "[Wi-Fi] Service stopped"

  set-state_ new-state/int --context=null -> none:
    if state == new-state: return
    state = new-state
    log-state-change_ state --context=context

  register-client_ address/net.SocketAddress -> none:
    if not target-address or target-address != address:
      target-address = address
      log.info "SUCCESS: [Wi-Fi] Client registered from $target-address"
    if state != STATE-CONNECTED:
      set-state_ STATE-CONNECTED
      if heartbeat-task: heartbeat-task.cancel
      heartbeat-task = task:: run-heartbeat-timeout-check_

  handle-client-timeout_ -> none:
    if target-address:
      log.warn "[Wi-Fi] Client $target-address disconnected (timeout)"
      target-address = null
      if state == STATE-CONNECTED:
        set-state_ STATE-ADVERTISING

  // ========================================================================
  // Core Loops
  // ========================================================================
  run-server_ error-latch/Latch -> none:
    log.info "Opening network..."
    network = net.open
    log.info "SUCCESS: Network opened! IP: $(network.address)"
    server-socket = network.udp-open --port=PORT
    log.info "SUCCESS: Wi-Fi Server '$name' listening on $(network.address):$PORT"
    set-state_ STATE-ADVERTISING

    tx-task = task:: run-tx-loop_
    rx-task = task:: run-rx-loop_ error-latch

    throw error-latch.get

  run-rx-loop_ error-latch/Latch -> none:
    error := catch:
      while true:
        datagram := server-socket.receive
        last-heartbeat-time = Time.now
        register-client_ datagram.address
    if error and error != "CANCELED":
      error-latch.set error

  run-tx-loop_ -> none:
    clear-tx-queue_
    while state == STATE-ADVERTISING or state == STATE-CONNECTED:
      data/ByteArray := tx-bus.receive
      if target-address:
        transmit_ data

  run-heartbeat-timeout-check_ -> none:
    while state == STATE-CONNECTED:
      elapsed := last-heartbeat-time.to Time.now
      if elapsed > HEARTBEAT-TIMEOUT:
        handle-client-timeout_
        return
      sleep HEARTBEAT-TIMEOUT - elapsed

  // ========================================================================
  // Network Utilities
  // ========================================================================
  transmit_ data/ByteArray -> none:
    error := catch: 
      datagram := udp.Datagram data target-address
      server-socket.send datagram
    if error:
      log.warn "[Wi-Fi] TX failed" --tags={"error": error}

  release-resources_ -> none:
    rx-task = cancel-task_ rx-task
    tx-task = cancel-task_ tx-task
    heartbeat-task = cancel-task_ heartbeat-task
    server-socket = close-socket_ server-socket
    network = close-network_ network
    target-address = null

  clear-tx-queue_ -> none:
    while tx-bus.receive --blocking=false:
      null

  cancel-task_ task/Task? -> Task?:
    if task: task.cancel
    return null

  close-socket_ socket/udp.Socket? -> udp.Socket?:
    if socket: catch: socket.close
    return null

  close-network_ netw/net.Interface? -> net.Interface?:
    if netw: catch: netw.close
    return null
