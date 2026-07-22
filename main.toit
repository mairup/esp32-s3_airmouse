import log
import .wifi_server show WifiServer 
import .tasks.heartbeat show Heartbeat
import .tasks.imu_reader show ImuReader
import .tasks.button show ButtonService
import .imu show Imu gyro_x gyro_y gyro_z accel_x accel_y accel_z
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

  button-service := ButtonService --pin-num=BUTTON-PIN --send-to=:: |val/ByteArray|
    wireless-connection.send-bytes val
  button-service.start

  imu := Imu --sda=SDA-PIN --scl=SCL-PIN --int-pin=INT-PIN
  imu.start

  imu-reader := ImuReader --imu=imu --int-pin-num=INT-PIN --cpu-monitor=cpu-monitor
  imu-reader.start

  start-main-heartbeat
    --send-to=:: |val/ByteArray| wireless-connection.send-bytes val
    --interval=HEARTBEAT-INTERVAL
    --imu=imu

// ========================================================================
// Helper Services
// ========================================================================
start-main-heartbeat --send-to/Lambda --interval/Duration --imu/Imu -> none:
  counter := 0

  heartbeat-service := Heartbeat
    --send-to=send-to
    --generator=::
      packet-buffer := ByteArray 16
      packet-buffer[0] = 0x41 // 'A'
      packet-buffer[1] = 0x4D // 'M'

      seq := counter++
      packet-buffer[2] = seq & 0xFF
      packet-buffer[3] = (seq >> 8) & 0xFF

      gx := gyro_x
      gy := gyro_y
      gz := gyro_z
      ax := accel_x
      ay := accel_y
      az := accel_z

      packet-buffer[4] = gx & 0xFF
      packet-buffer[5] = (gx >> 8) & 0xFF
      packet-buffer[6] = gy & 0xFF
      packet-buffer[7] = (gy >> 8) & 0xFF
      packet-buffer[8] = gz & 0xFF
      packet-buffer[9] = (gz >> 8) & 0xFF

      packet-buffer[10] = ax & 0xFF
      packet-buffer[11] = (ax >> 8) & 0xFF
      packet-buffer[12] = ay & 0xFF
      packet-buffer[13] = (ay >> 8) & 0xFF
      packet-buffer[14] = az & 0xFF
      packet-buffer[15] = (az >> 8) & 0xFF

      packet-buffer
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
  
