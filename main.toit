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
import .tasks.potentiometer_manager show PotentiometerManager
import .tasks.gesture_manager show GestureManager
import .utils.env show DEBUG

// ========================================================================
// Constants
// ========================================================================
DEVICE-NAME ::= "ESP32-S3"


// GPIO Pins
CLUTCH-PIN          ::= 1
LEFT-CLICK-PIN      ::= 16
RIGHT-CLICK-PIN     ::= 14
LEFT-CLICK-LED-PIN  ::= 8
RIGHT-CLICK-LED-PIN ::= 11
POTENTIOMETER-PIN   ::= 9
GESTURE-PIN         ::= 38

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

  run-airmouse-app

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

  button-manager := ButtonManager 
    --clutch-pin=CLUTCH-PIN
    --left-click-pin=LEFT-CLICK-PIN
    --right-click-pin=RIGHT-CLICK-PIN
    --left-click-led-pin=LEFT-CLICK-LED-PIN
    --right-click-led-pin=RIGHT-CLICK-LED-PIN

  potentiometer-manager := PotentiometerManager --pin-num=POTENTIOMETER-PIN
  potentiometer-manager.start

  imu := Imu --sda=SDA-PIN --scl=SCL-PIN --int-pin=INT-PIN
  imu.start

  gesture-manager := GestureManager
    --gesture-pin=GESTURE-PIN
    --imu=imu
    --rgb-led=rgb-led
    --rgb-indicator=rgb-indicator
  gesture-manager.start

  imu-pipeline := ImuPipeline 
    --imu=imu 
    --cpu-monitor=cpu-monitor
    --send-to=:: |val/ByteArray| wireless-connection.send-bytes val
  imu-pipeline.start
