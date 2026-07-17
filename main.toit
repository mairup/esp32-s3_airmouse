import log
import net
import .wifi_server show WifiServer 
import .tasks.heartbeat show Heartbeat
import .tasks.button show ButtonService
import .utils.logger show logger-init
import .utils.rgb_led show RgbLed
import .utils.rgb_indicator show RgbIndicator
import .utils.env show DEBUG


DEVICE-NAME ::= "ESP32-S3"

// GPIO Pins
BUTTON-PIN    ::= 1
RED-RGB-PIN   ::= 6
GREEN-RGB-PIN ::= 5
BLUE-RGB-PIN  ::= 4


main:
  if DEBUG:
    logger-init
    log.info "Debug mode active (Wi-Fi UDP logger initialized)"
    log.info "---------  MAIN ENTRY  ----------"

  exception := catch:
    run-airmouse-app

  if exception:
    log.error "FATAL EXCEPTION in main" --tags={"error": exception}
    if DEBUG:
      sleep --ms=500 // Allow UDP network buffer to flush to PC
    throw exception


run-airmouse-app:
  log.info "$DEVICE-NAME starting..."

  log.info "Opening network..."
  network := net.open
  log.info "Network opened! IP: $(network.address)"

  log.info "Initializing RgbLed on R:$RED-RGB-PIN, G:$GREEN-RGB-PIN, B:$BLUE-RGB-PIN..."
  rgb-led := RgbLed --red=RED-RGB-PIN --green=GREEN-RGB-PIN --blue=BLUE-RGB-PIN --brightness=10
  log.info "RgbLed initialized successfully"

  log.info "Initializing and starting Wi-Fi Server..."
  wireless-connection := start-wifi
  log.info "Wi-Fi Server startup initiated successfully"

  log.info "Starting RgbIndicator..."
  rgb-indicator := RgbIndicator wireless-connection rgb-led
  rgb-indicator.start
  log.info "RgbIndicator started"

  button-service := ButtonService --pin-num=BUTTON-PIN --send-to=:: |val/string| wireless-connection.send val
  button-service.start
  log.info "ButtonService started on Pin $BUTTON-PIN"

  start-heartbeat
    --send-to=:: |val/string| wireless-connection.send "$val\n"
    --interval=(Duration --us=5000)

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


start-wifi -> WifiServer:
  server := WifiServer 
    --name=DEVICE-NAME 
    --tx-queue-size=42

  server.start
  return server


start-heartbeat --send-to/Lambda --interval/Duration -> none:
  counter := 0
  heartbeat-service := Heartbeat
    --send-to=send-to
    --generator=::
      uptime-ms := Time.monotonic-us / 1000
      "HB:$(counter++):$uptime-ms"
    --interval=interval
  heartbeat-service.start
  log.info "Heartbeat started"

