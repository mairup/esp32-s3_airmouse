import log
import .ble_server show BleServer 
import .tasks.heartbeat show Heartbeat
import .utils.logger show logger-init
import .utils.rgb_led show RgbLed
import .utils.rgb_indicator show RgbIndicator

BLE-DEVICE-NAME ::= "ESP32-S3"
DEBUG           ::= false

// RGB LED GPIO Pins (top-left contiguous pins)
RED-RGB-PIN   ::= 6
GREEN-RGB-PIN ::= 5
BLUE-RGB-PIN  ::= 4


main:
  run-airmouse-app
  // run-color-test


run-airmouse-app:
  if DEBUG:
    logger-init
    log.info "Debug mode active (Wi-Fi UDP logger initialized)"

  log.info "$BLE-DEVICE-NAME starting..."

  exception := catch:
    log.info "Initializing RgbLed on R:$RED-RGB-PIN, G:$GREEN-RGB-PIN, B:$BLUE-RGB-PIN..."

    rgb-led := RgbLed --red=RED-RGB-PIN --green=GREEN-RGB-PIN --blue=BLUE-RGB-PIN --brightness=10
    
    log.info "RgbLed initialized successfully"

    log.info "Initializing and starting BLE Server..."
    ble := start-ble
    log.info "BLE Server startup initiated successfully"

    log.info "Starting RgbIndicator..."
    rgb-indicator := RgbIndicator ble rgb-led
    rgb-indicator.start
    log.info "RgbIndicator started"

    if DEBUG:
      log.info "Starting heartbeat task..."
      start-heartbeat --send-to=:: |val/string| ble.send val
      log.info "Heartbeat task started"

  if exception:
    log.error "FATAL EXCEPTION in main" --tags={"error": exception}
    sleep --ms=2000 // Allow UDP network buffer to flush to PC
    throw exception


run-color-test:
  log.info "Starting color diagnostic test loop (switches every 2 seconds)..."
  rgb-led := RgbLed --red=RED-RGB-PIN --green=GREEN-RGB-PIN --blue=BLUE-RGB-PIN --brightness=100
  while true:
    log.info "Setting RED"
    rgb-led.set-color 255 0 0
    sleep --ms=2000

    log.info "Setting GREEN"
    rgb-led.set-color 0 255 0
    sleep --ms=2000

    log.info "Setting BLUE"
    rgb-led.set-color 0 0 255
    sleep --ms=2000

    log.info "Setting ORANGE"
    rgb-led.set-color 255 128 0
    sleep --ms=2000


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
