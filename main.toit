import .ble_server show BleServer 
import .tasks.heartbeat show Heartbeat

BLE-DEVICE-NAME ::= "ESP32-S3"


main:
  print "$BLE-DEVICE-NAME starting..."

  ble := start-ble
  start-heartbeat --send-to=:: |val/string| ble.send val


start-ble -> BleServer:
  ble := BleServer 
    --name=BLE-DEVICE-NAME 
    --tx-queue-size=42

  ble.start
  return ble


start-heartbeat --send-to/Lambda -> none:
  heartbeat-service := Heartbeat --send-to=send-to --interval-ms=250
  heartbeat-service.start
  print "Heartbeat started"
  


