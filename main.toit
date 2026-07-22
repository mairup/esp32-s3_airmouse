import log
import .wifi_server show WifiServer 
import .tasks.imu_pipeline show ImuPipeline
import .tasks.button_manager show ButtonManager
import .imu show Imu
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

// IMU Pipeline Configuration
IMU-ACTIVE-STAGE ::= "fusion" // "raw" | "fusion" | "kinematics"

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

  button-manager := ButtonManager --clutch-pin=BUTTON-PIN

  imu := Imu --sda=SDA-PIN --scl=SCL-PIN --int-pin=INT-PIN
  imu.start

  imu-pipeline := ImuPipeline 
    --imu=imu 
    --cpu-monitor=cpu-monitor
    --send-to=:: |val/ByteArray| wireless-connection.send-bytes val
    --stage=IMU-ACTIVE-STAGE
  imu-pipeline.start
