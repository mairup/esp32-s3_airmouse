import log
import net
import .wifi_server show WifiServer 
import .tasks.heartbeat show Heartbeat
import .tasks.imu_heartbeat show ImuHeartbeat
import .tasks.button show ButtonService
import .imu show Imu gyro_x gyro_y gyro_z
import .utils.logger show logger-init
import .utils.rgb_led show RgbLed
import .utils.rgb_indicator show RgbIndicator
import .utils.env show DEBUG

// ========================================================================
// Constants
// ========================================================================
DEVICE-NAME ::= "ESP32-S3"

// GPIO Pins
BUTTON-PIN    ::= 1
RED-RGB-PIN   ::= 6
GREEN-RGB-PIN ::= 5
BLUE-RGB-PIN  ::= 4
SDA-PIN ::= 21
SCL-PIN ::= 20

HEARTBEAT-INTERVAL ::= Duration --ms=10
IMU-HEARTBEAT-INTERVAL ::= Duration --ms=100
// ========================================================================
// Main Entry
// ========================================================================
main:
  if DEBUG:
    logger-init
    log.debug "Debug mode active (Wi-Fi UDP logger initialized)"
    log.info "---------  MAIN ENTRY  ----------"

  exception := catch:
    run-airmouse-app

  if exception:
    log.error "FATAL EXCEPTION in main" --tags={"error": exception}
    if DEBUG:
      sleep --ms=500 // Allow UDP network buffer to flush to PC
    throw exception

// ========================================================================
// App Setup & Loop
// ========================================================================
run-airmouse-app:
  log.info "$DEVICE-NAME starting..."

  log.info "Opening network..."
  network := net.open
  log.info "SUCCESS: Network opened! IP: $(network.address)"

  log.info "Initializing RgbLed on R:$RED-RGB-PIN, G:$GREEN-RGB-PIN, B:$BLUE-RGB-PIN..."
  rgb-led := RgbLed --red=RED-RGB-PIN --green=GREEN-RGB-PIN --blue=BLUE-RGB-PIN --brightness=10
  log.info "SUCCESS: RgbLed initialized successfully"

  log.info "Initializing and starting Wi-Fi Server..."
  wireless-connection := start-wifi
  log.info "SUCCESS: Wi-Fi Server startup initiated successfully"

  log.info "Starting RgbIndicator..."
  rgb-indicator := RgbIndicator wireless-connection rgb-led
  rgb-indicator.start
  log.info "SUCCESS: RgbIndicator started"

  log.info "Setting up button service..."
  button-service := ButtonService --pin-num=BUTTON-PIN --send-to=:: |val/string| wireless-connection.send val
  button-service.start
  log.info "SUCCESS: ButtonService started on Pin $BUTTON-PIN"

  log.info "Initializing IMU on SDA=$SDA-PIN, SCL=$SCL-PIN..."
  imu := Imu --sda=SDA-PIN --scl=SCL-PIN
  imu.start

  log.info "Starting IMU heartbeat..."
  imu-heartbeat := ImuHeartbeat --imu=imu --interval=IMU-HEARTBEAT-INTERVAL
  imu-heartbeat.start
  log.info "IMU heartbeat started"

  start-main-heartbeat
    --send-to=:: |val/string| wireless-connection.send "$val\n"
    --interval=HEARTBEAT-INTERVAL

// ========================================================================
// Helper Services
// ========================================================================
start-wifi -> WifiServer:
  server := WifiServer 
    --name=DEVICE-NAME 
    --tx-queue-size=42

  server.start
  return server

start-main-heartbeat --send-to/Lambda --interval/Duration -> none:
  counter := 0
  heartbeat-service := Heartbeat
    --send-to=send-to
    --generator=::
      uptime-ms := Time.monotonic-us / 1000
      "HB:$(counter++):$uptime-ms"
    --interval=interval
  heartbeat-service.start
  log.info "SUCCESS: Heartbeat started"

// ========================================================================
// Diagnostics
// ========================================================================
display-imu-data:
    log.info "Starting IMU data display loop..."
    imu-instance := Imu --sda=SDA-PIN --scl=SCL-PIN
    imu-instance.start
    
    while true:
        imu-instance.read-gyro
        log.info "Gyroscope Data - X: $gyro_x, Y: $gyro_y, Z: $gyro_z"
        sleep --ms=2000
  
