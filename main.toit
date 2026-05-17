import log
import .ble_server show BleServer 
import .tasks.heartbeat show Heartbeat
import .utils.logger show logger-init
import .utils.rgb_led show RgbLed RgbIndicator

BLE-DEVICE-NAME ::= "ESP32-S3"
DEBUG           ::= true

// RGB LED GPIO Pins (top-left contiguous pins)
RED-RGB-PIN   ::= 6
GREEN-RGB-PIN ::= 5
BLUE-RGB-PIN  ::= 4


main:
  if DEBUG:
    logger-init
    log.info "Debug mode active (Wi-Fi UDP logger initialized)"

  log.info "$BLE-DEVICE-NAME starting..."

  rgb-led := RgbLed --red=RED-RGB-PIN --green=GREEN-RGB-PIN --blue=BLUE-RGB-PIN --brightness=10
  ble := start-ble
  rgb-indicator := RgbIndicator rgb-led ble
  rgb-indicator.start

  if DEBUG:
    start-heartbeat --send-to=:: |val/string| ble.send val


start-ble -> BleServer:
  ble := BleServer 
    --name=BLE-DEVICE-NAME 
    --tx-queue-size=42

  ble.start
  return ble


start-heartbeat --send-to/Lambda -> none:
  counter := 0
  heartbeat-service := Heartbeat
    --send-to=send-to
    --generator=:: "$(counter++)"
    --interval-ms=250
  heartbeat-service.start
  log.info "Heartbeat started"
