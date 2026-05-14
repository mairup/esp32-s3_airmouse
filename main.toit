import monitor show Channel
import .ble_server show BleServer
import .tasks.heartbeat show HeartbeatTask

BLE-DEVICE-NAME ::= "ESP32-S3"

main:
  print "$BLE-DEVICE-NAME starting..."

  data-bus := Channel 42
  command-bus := Channel 42
  state-cb := :: |new-state|
    if new-state == BleServer.STATE-ADVERTISING:
      print "[BLE] Ready and advertising"
    else if new-state == BleServer.STATE-CONNECTED:
      print "[BLE] Client connected/active"
    else if new-state == BleServer.STATE-ERROR:
      print "[BLE] Error occurred, attempting to recover..."
    else if new-state == BleServer.STATE-STOPPED:
      print "[BLE] Service stopped"

  ble := BleServer 
    --name=BLE-DEVICE-NAME 
    --commands=command-bus 
    --tx-buffer=42
    --on-state-change=state-cb

  // Start the BLE server via command
  command-bus.send "start"

  heartbeat := HeartbeatTask --output=data-bus --interval-ms=500
  heartbeat.start
  print "Heartbeat started, routing data-bus -> BLE"

  while true:
    data := data-bus.receive --blocking=false
    if data != null:
      // Only attempt to transmit if BLE is up
      if ble.state == BleServer.STATE-CONNECTED or ble.state == BleServer.STATE-ADVERTISING:
        ok := ble.send data
        if ok:
          print "[TX] $data"
        else:
          print "[DROP] BLE buffer full: $data"
      else:
        print "[DROP] BLE offline: $data"

    sleep --ms=10
