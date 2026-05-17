import ble show BleUuid Adapter Advertisement Peripheral LocalCharacteristic \
  BLE-ADVERTISE-FLAGS-GENERAL-DISCOVERY BLE-ADVERTISE-FLAGS-BREDR-UNSUPPORTED
import monitor show Channel
import log

SERVICE-UUID ::= BleUuid "0000FFE0-0000-1000-8000-00805F9B34FB"
CHAR-UUID   ::= BleUuid "0000FFE2-0000-1000-8000-00805F9B34FB"

class BleServer:
  static STATE-STOPPED     ::= 0
  static STATE-STARTING    ::= 1
  static STATE-ADVERTISING ::= 2
  static STATE-CONNECTED   ::= 3
  static STATE-ERROR       ::= 4

  static HEALTH-CHECK-INTERVAL   ::= Duration --ms=100
  static HARDWARE-RETRY-DELAY    ::= Duration --ms=10     //  time between try start advertising (waiting for BLE stack restart)
  static HARDWARE-RETRY-TIMEOUT  ::= Duration --s=1       //  hardware stack not starting -> hard crash

  /// Default state-change logger
  static print-state state/int context/any -> none:
    if state == STATE-ADVERTISING:
      log.info "[BLE] Ready and advertising"
    else if state == STATE-CONNECTED:
      log.info "[BLE] Client connected/active"
    else if state == STATE-ERROR:
      log.error "[BLE] Error" --tags={"context": context}
    else if state == STATE-STOPPED:
      log.info "[BLE] Service stopped"

  name /string
  tx-bus /Channel
  
  state /int := STATE-STOPPED
  last-health-check_ /int := 0



  main-task /Task? := null
  adapter /Adapter? := null
  peripheral /Peripheral? := null
  service /any := null
  characteristic /LocalCharacteristic? := null
  advertisement /Advertisement? := null

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




  /// Start BLE adapter and TX loop in background
  start -> none:
    if main-task:
      set-state STATE-ERROR --context="START_REQUESTED_WHILE_RUNNING"
      return

    set-state STATE-STARTING
    main-task = task::
      error := catch:
        configure-adapter
        while true:
          if connect-to-client:
            run-tx-loop
          else:
            sleep --ms=1000
            
      if error != "CANCELED":
        set-state STATE-ERROR --context=error


  /// Initialize BLE peripheral and characteristic
  configure-adapter -> none:
    if adapter:
      catch: adapter.close
      adapter = null
    
    adapter = Adapter
    peripheral = adapter.peripheral --name=name
    
    try-add-service SERVICE-UUID
    characteristic = service.add-notification-characteristic CHAR-UUID
    peripheral.deploy

    advertisement = Advertisement
      --name=name
      --services=[SERVICE-UUID]
      --flags=BLE-ADVERTISE-FLAGS-GENERAL-DISCOVERY | BLE-ADVERTISE-FLAGS-BREDR-UNSUPPORTED

  /// Adds a service to the peripheral, retrying if the hardware is still busy
  /// from a previous session.
  try-add-service uuid/BleUuid -> none:
    start-time := Time.monotonic_us
    while true:
      error := catch: service = peripheral.add-service uuid
      if not error: return
      
      elapsed := Time.monotonic_us - start-time
      if error == "ALREADY_EXISTS" and elapsed < HARDWARE-RETRY-TIMEOUT.in-us:
        sleep HARDWARE-RETRY-DELAY
      else:
        throw error

  /// Starts advertising, retrying if the hardware is still busy
  /// from a previous session.
  try-start-advertising -> none:
    start-time := Time.monotonic_us
    while true:
      catch: peripheral.stop-advertise
      error := catch: peripheral.start-advertise advertisement --allow-connections
      if not error: return
      
      elapsed := Time.monotonic_us - start-time
      if error == "ALREADY_EXISTS" and elapsed < HARDWARE-RETRY-TIMEOUT.in-us:
        sleep HARDWARE-RETRY-DELAY
      else:
        throw error

  /// Stream TX channel data to hardware while connected
  run-tx-loop -> none:
    last-health-check_ = Time.monotonic_us
    while state == STATE-CONNECTED:
      data/ByteArray := tx-bus.receive
      if not transmit_ data: return

  /// Transmit data to connected client with periodic health checks.
  /// Returns false on hardware or connection error.
  transmit_ data/ByteArray -> bool:
    if (Time.monotonic_us - last-health-check_) > HEALTH-CHECK-INTERVAL.in-us:
      if not health-check:
        log.warn "[BLE] Health check failed, disconnecting"
        return false

    error := catch: characteristic.write data
    if error:
      if error == "LOOKUP_FAILED":
        log.warn "[BLE] Connection lost"
      else:
        log.error "[BLE] Transmission error" --tags={"error": error}
      return false
    return true

  /// Performs a connection health check.
  /// Returns true if the connection is healthy, false otherwise.
  health-check -> bool:
    if subscribed-clients.is-empty:
      log.warn "[BLE] Connection lost (monitored)"
      return false
    last-health-check_ = Time.monotonic_us
    return true

  /// Check if the client is still active and subscribed
  /// Returns a list of currently subscribed clients.
  /// Returns an empty list if the characteristic is not ready or if an error occurs.
  subscribed-clients -> List:
    if not characteristic: return []
    resource := characteristic.resource_
    if not resource: return []
    
    clients := null
    error := catch: clients = ble-get-subscribed-clients_ resource
    return error ? [] : clients

          
  /// Advertise until device is connected to client. 
  /// Returns true when connected or false on error/timeout
  connect-to-client -> bool:
    set-state STATE-ADVERTISING
    try-start-advertising
    log.info "BLE advertising as $name and is ready to connect"

    while state == STATE-ADVERTISING:
      clients := subscribed-clients
      if not clients.is-empty:
        log.info "[BLE] Connection established" --tags={"clients": clients}
        set-state STATE-CONNECTED
        return true
      sleep --ms=10
    return false
    


  /// Cancel tasks and release hardware resources
  stop -> none:
    if main-task:
      main-task.cancel
      main-task = null

    if adapter:
      adapter.close
      adapter = null
    set-state STATE-STOPPED

  /// Enqueue data chunk to TX channel. 
  /// Returns false if not ready or buffer full
  send data/string -> bool:
    if state == STATE-CONNECTED or state == STATE-ADVERTISING:
      return tx-bus.try-send data.to-byte-array
    return false
    
ble-get-subscribed-clients_ resource:
  #primitive.ble.get-subscribed-clients