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

  static RETRY-DELAY   ::= Duration --ms=10
  static RETRY-TIMEOUT ::= Duration --ms=1000
  static RECOVERY-DELAY        ::= Duration --ms=500
  static CLIENT-POLL-INTERVAL  ::= Duration --ms=10
  static HEALTH-CHECK-INTERVAL ::= Duration --ms=100

  /// Log state transitions
  static log-state state/int --context=null -> none:
    if state == STATE-STARTING:
      log.info "[BLE] Starting"
    else if state == STATE-ADVERTISING:
      log.info "[BLE] Advertising"
    else if state == STATE-CONNECTED:
      log.info "[BLE] Client connected"
    else if state == STATE-ERROR:
      log.error "[BLE] Error" --tags={"context": context}
    else if state == STATE-STOPPED:
      log.info "[BLE] Stopped"

  name /string
  tx-bus /Channel
  state /int := STATE-STOPPED

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


  set-state new-state/int --context=null -> none:
    state = new-state
    log-state state --context=context


  start -> none:
    set-state STATE-STARTING
    main-task = task::
      error := catch:
        configure-adapter
        while true:
          wait-for-client
          monitor-task := start-health-monitor_
          try:
            run-tx-loop
          finally:
            monitor-task.cancel

      if error and error != "CANCELED":
        set-state STATE-ERROR --context=error
        main-task = null
        sleep RECOVERY-DELAY
        start


  /// Initialize BLE peripheral and characteristic
  configure-adapter -> none:
    if adapter:
      catch: adapter.close
      adapter = null

    adapter = Adapter
    peripheral = adapter.peripheral --name=name

    retry-until-timeout_: service = peripheral.add-service SERVICE-UUID
    characteristic = service.add-notification-characteristic CHAR-UUID
    peripheral.deploy

    advertisement = Advertisement
      --name=name
      --services=[SERVICE-UUID]
      --flags=BLE-ADVERTISE-FLAGS-GENERAL-DISCOVERY | BLE-ADVERTISE-FLAGS-BREDR-UNSUPPORTED


  /// Retry a block until it succeeds or the hardware timeout expires
  retry-until-timeout_ [block] -> none:
    start-time := Time.monotonic_us
    while true:
      error := catch: block.call
      if not error: return

      elapsed := Time.monotonic_us - start-time
      if elapsed < RETRY-TIMEOUT.in-us:
        sleep RETRY-DELAY
      else:
        throw error


  /// Advertise and block until a client subscribes
  wait-for-client -> none:
    set-state STATE-ADVERTISING
    retry-until-timeout_:
      catch: peripheral.stop-advertise
      peripheral.start-advertise advertisement --allow-connections

    while true:
      if not subscribed-clients.is-empty:
        set-state STATE-CONNECTED
        return
      sleep CLIENT-POLL-INTERVAL


  /// Stream TX channel data to hardware while connected
  run-tx-loop -> none:
    clear-tx-queue_
    while state == STATE-CONNECTED:
      data/ByteArray := tx-bus.receive
      if data.is-empty: return
      if not transmit_ data: return


  /// Poll subscribed clients; unblock tx-loop on disconnect
  start-health-monitor_ -> Task:
    return task::
      while state == STATE-CONNECTED:
        if subscribed-clients.is-empty:
          log.warn "[BLE] Connection lost (monitor)"
          catch: tx-bus.send #[]
          break
        sleep HEALTH-CHECK-INTERVAL


  /// Transmit data to connected client.
  /// Returns false on hardware or connection error.
  transmit_ data/ByteArray -> bool:
    error := catch: characteristic.write data
    if error:
      log.warn "[BLE] TX failed" --tags={"error": error}
      return false
    return true


  /// Returns currently subscribed clients, or empty list on error
  subscribed-clients -> List:
    if not characteristic: return []
    resource := characteristic.resource_
    if not resource: return []

    clients := null
    error := catch: clients = ble-get-subscribed-clients_ resource
    return error ? [] : clients


  /// Cancel tasks and release hardware resources
  stop -> none:
    if main-task:
      main-task.cancel
      main-task = null

    if adapter:
      catch: adapter.close
      adapter = null
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

ble-get-subscribed-clients_ resource:
  #primitive.ble.get-subscribed-clients