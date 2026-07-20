import gpio
import i2c
import log

WHO-AM-I-REGISTER ::= 0x0F
WHO-AM-I-VALUE ::= 0x6C

CONTROL-REGISTER-1-ACCELEROMETER ::= 0x10
CONTROL-REGISTER-2-GYROSCOPE ::= 0x11
CONTROL-REGISTER-3-COMMON ::= 0x12
CONTROL-REGISTER-4-COMMON ::= 0x13
CONTROL-REGISTER-6-COMMON ::= 0x15
CONTROL-REGISTER-7-GYROSCOPE ::= 0x16

STATUS-REGISTER ::= 0x1E
OUTPUT-X-LOW-GYROSCOPE ::= 0x22
OUTPUT-X-LOW-ACCELEROMETER ::= 0x28

ADDRESS-LOW ::= 0x6A
ADDRESS-HIGH ::= 0x6B

class Imu:
  sda-pin_ /int
  scl-pin_ /int
  device_ /i2c.Device? := null

  constructor --sda/int --scl/int:
    sda-pin_ = sda
    scl-pin_ = scl

  start -> none:
    if device_: return

    error := catch:
      sda := gpio.Pin sda-pin_
      scl := gpio.Pin scl-pin_

      bus := i2c.Bus --sda=sda --scl=scl

      device-detected := detect-imu_ bus
      if not device-detected:
        throw "IMU not found on I2C bus"
      
      device_ = device-detected
      
      reset-imu_
      verify-imu-identification_
      configure-gyro_
      configure-accelerometer_
      enable-control-features_
      disable-unneeded-gyro-features_
      disable-unneeded-control-features_
      finish-imu-startup_

    if error:
      log.warn "Failed to initialize IMU: $error. Continuing without IMU."
    else:
      log.info "IMU initialized successfully"

  /// Performs a software reset of the IMU by setting the SW_RESET bit (0x01).
  reset-imu_ -> none:
    device_.write-reg CONTROL-REGISTER-3-COMMON #[0x01]
    sleep --ms=50

  verify-imu-identification_ -> none:
    device-identification := device_.read-reg WHO-AM-I-REGISTER 1
    if device-identification[0] != WHO-AM-I-VALUE:
      throw "IMU not found: WHO_AM_I=0x$(%02x device-identification[0]), expected 0x$(%02x WHO-AM-I-VALUE)"

  /// Configures Gyroscope: Output Data Rate = 416 Hz, Full Scale = ±500 dps.
  /// Binary value 0x74 (0111 0100) sets the upper nibble for ODR and lower for FS.
  configure-gyro_ -> none:
    device_.write-reg CONTROL-REGISTER-2-GYROSCOPE #[0x74]

  /// Configures Accelerometer: Output Data Rate = 416 Hz, Full Scale = ±4g.
  /// Binary value 0x72 (0111 0010) sets the upper nibble for ODR and lower for FS.
  configure-accelerometer_ -> none:
    device_.write-reg CONTROL-REGISTER-1-ACCELEROMETER #[0x72]

  /// Enables Block Data Update (BDU) to prevent reading partial data, 
  /// and enables Address Auto-Increment (IF_INC) for burst reads.
  /// Binary value 0x44 (0100 0100) sets BDU (bit 6) and IF_INC (bit 2).
  enable-control-features_ -> none:
    device_.write-reg CONTROL-REGISTER-3-COMMON #[0x44]

  disable-unneeded-gyro-features_ -> none:
    device_.write-reg CONTROL-REGISTER-7-GYROSCOPE #[0x00]

  disable-unneeded-control-features_ -> none:
    device_.write-reg CONTROL-REGISTER-4-COMMON #[0x00]
    device_.write-reg CONTROL-REGISTER-6-COMMON #[0x00]

  finish-imu-startup_ -> none:
    sleep --ms=10

  detect-imu_ bus/i2c.Bus -> i2c.Device?:
    log.info "Scanning I2C bus for LSM6DSOX..."
    detected-addresses := bus.scan
    log.info "Found devices at: $detected-addresses"
    if detected-addresses.contains ADDRESS-LOW:
      log.info "Found IMU at 0x$(%02x ADDRESS-LOW) (SA0=GND)"
      return bus.device ADDRESS-LOW
    if detected-addresses.contains ADDRESS-HIGH:
      log.info "Found IMU at 0x$(%02x ADDRESS-HIGH) (SA0=VDDIO)"
      return bus.device ADDRESS-HIGH
    return null