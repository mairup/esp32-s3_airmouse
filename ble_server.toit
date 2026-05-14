import ble show BleUuid Adapter Advertisement Peripheral LocalCharacteristic \
  BLE-ADVERTISE-FLAGS-GENERAL-DISCOVERY BLE-ADVERTISE-FLAGS-BREDR-UNSUPPORTED
import monitor show Channel

SERVICE-UUID ::= BleUuid "0000FFE0-0000-1000-8000-00805F9B34FB"
CHAR-UUID   ::= BleUuid "0000FFE1-0000-1000-8000-00805F9B34FB"

class BleServer:
  static STATE-STOPPED     ::= 0
  static STATE-STARTING    ::= 1
  static STATE-ADVERTISING ::= 2
  static STATE-CONNECTED   ::= 3
  static STATE-ERROR       ::= 4

  name /string
  tx /Channel
  commands /Channel
  
  state /int := STATE-STOPPED
  on-state-change /Lambda?

  task_ /Task? := null
  cmd-task_ /Task? := null

  constructor
      --.name/string
      --.commands/Channel
      --.on-state-change/Lambda?=null
      --tx-buffer=10:
    tx = Channel tx-buffer
    // Start listening for commands immediately in the background
    cmd-task_ = task:: command-loop_

  set-state_ new-state/int -> none:
    if state != new-state:
      state = new-state
      if on-state-change:
        on-state-change.call state

  command-loop_ -> none:
    while true:
      command := commands.receive
      if command == "start":
        start-ble_
      else if command == "stop":
        stop-ble_
      else if command == "reload":
        stop-ble_
        sleep --ms=200
        start-ble_

  start-ble_ -> none:
    if task_: return
    set-state_ STATE-STARTING
    task_ = task::
      error := catch:
        adapter := Adapter
        peripheral := adapter.peripheral --name=name
        service := peripheral.add-service SERVICE-UUID
        characteristic := service.add-notification-characteristic CHAR-UUID
        peripheral.deploy

        advertisement := Advertisement
          --name=name
          --services=[SERVICE-UUID]
          --flags=BLE-ADVERTISE-FLAGS-GENERAL-DISCOVERY | BLE-ADVERTISE-FLAGS-BREDR-UNSUPPORTED
        peripheral.start-advertise advertisement --allow-connections
        set-state_ STATE-ADVERTISING

        while true:
          data := tx.receive

          err := catch:
            characteristic.write data.to-utf8
            null
          
          if err:
            set-state_ STATE-ERROR
            peripheral.stop-advertise
            sleep --ms=200
            peripheral.start-advertise advertisement --allow-connections
            set-state_ STATE-ADVERTISING
          else:
            // State transitions to connected only IF the write succeeds
            if state == STATE-ADVERTISING:
              set-state_ STATE-CONNECTED

      if error:
        set-state_ STATE-ERROR
        print "BLE Task Error: $error"
        task_ = null

  stop-ble_ -> none:
    if task_:
      task_.cancel
      task_ = null
    set-state_ STATE-STOPPED

  send data/string -> bool:
    if not able-to-tx:
      return false
    else:
      return tx.try-send data

  able-to-tx -> bool:
    return state == STATE-CONNECTED or state == STATE-ADVERTISING