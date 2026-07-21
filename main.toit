import log
import .wifi_server show WifiServer 
import .tasks.heartbeat show Heartbeat
import .tasks.imu_reader show ImuReader
import .tasks.button show ButtonService
import .imu show Imu gyro_x gyro_y gyro_z
import .utils.logger show logger-init
import .utils.rgb_led show RgbLed
import .utils.rgb_indicator show RgbIndicator
import .utils.overload_led show OverloadLed
import .tasks.cpu_monitor show CpuMonitor
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
INT-PIN ::= 7
OVERLOAD-LED-PIN ::= 2

HEARTBEAT-INTERVAL ::= Duration --ms=10

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

  rgb-led := RgbLed --red=RED-RGB-PIN --green=GREEN-RGB-PIN --blue=BLUE-RGB-PIN --brightness=10

  overload-led := OverloadLed --pin-num=OVERLOAD-LED-PIN

  cpu-monitor := CpuMonitor --led=overload-led
  cpu-monitor.start

  wireless-connection := WifiServer --name=DEVICE-NAME --tx-queue-size=42
  wireless-connection.start

  rgb-indicator := RgbIndicator wireless-connection rgb-led
  rgb-indicator.start

  button-service := ButtonService --pin-num=BUTTON-PIN --send-to=:: |val/string|
    wireless-connection.send val
  button-service.start

  imu := Imu --sda=SDA-PIN --scl=SCL-PIN --int-pin=INT-PIN
  imu.start

  imu-reader := ImuReader --imu=imu --int-pin-num=INT-PIN --cpu-monitor=cpu-monitor
  imu-reader.start

  start-main-heartbeat
    --send-to=:: |val/string| wireless-connection.send "$val\n"
    --interval=HEARTBEAT-INTERVAL

// ========================================================================
// Helper Services
// ========================================================================
start-main-heartbeat --send-to/Lambda --interval/Duration -> none:
  counter := 0
  heartbeat-service := Heartbeat
    --send-to=send-to
    --generator=::
      uptime-ms := Time.monotonic-us / 1000
      "HB:$(counter++):$uptime-ms"
    --interval=interval
  heartbeat-service.start

// ========================================================================
// Diagnostics
// ========================================================================
display-imu-data:
    log.info "Starting IMU data display loop..."
    imu-instance := Imu --sda=SDA-PIN --scl=SCL-PIN --int-pin=INT-PIN
    imu-instance.start
    
    while true:
        imu-instance.read-sensors
        log.info "Gyroscope Data - X: $gyro_x, Y: $gyro_y, Z: $gyro_z"
        sleep --ms=2000
  
