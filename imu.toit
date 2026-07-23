import gpio
import i2c
import log
import io
import .utils.imu_data as imu-data

WHO-AM-I-REGISTER ::= 0x0F
WHO-AM-I-VALUE    ::= 0x6C

CONTROL-REGISTER-1-ACCELEROMETER ::= 0x10
CONTROL-REGISTER-2-GYROSCOPE     ::= 0x11
CONTROL-REGISTER-3-COMMON        ::= 0x12
CONTROL-REGISTER-4-COMMON        ::= 0x13
CONTROL-REGISTER-6-COMMON        ::= 0x15
CONTROL-REGISTER-7-GYROSCOPE     ::= 0x16

COUNTER-BDR-REG1 ::= 0x0B
INT1-CTRL        ::= 0x0D

STATUS-REGISTER            ::= 0x1E
OUTPUT-X-LOW-GYROSCOPE     ::= 0x22
OUTPUT-X-LOW-ACCELEROMETER ::= 0x28

ADDRESS-LOW  ::= 0x6A
ADDRESS-HIGH ::= 0x6B

CONFIG-GYRO-104HZ-500DPS ::= #[0x44]
CONFIG-ACCEL-104HZ-4G    ::= #[0x48]
CONFIG-BDU-IF-INC        ::= #[0x44]
CONFIG-PULSED-DRDY       ::= #[0x80]
CONFIG-INT1-DRDY-BOTH    ::= #[0x03]
CONFIG-DISABLE-FEATURE   ::= #[0x00]
SW-RESET-CMD             ::= #[0x01]

class Imu:
  sda-pin_ /int
  scl-pin_ /int
  int-pin_ /int
  device_ /i2c.Device? := null

  constructor --sda/int --scl/int --int-pin/int:
    sda-pin_ = sda
    scl-pin_ = scl
    int-pin_ = int-pin

  int-pin-num -> int: return int-pin_

  start -> none:
    if device_: return

    log.info "Initializing IMU on SDA=$sda-pin_, SCL=$scl-pin_, INT=$int-pin_..."
    
    sda := gpio.Pin sda-pin_
    scl := gpio.Pin scl-pin_
    bus := i2c.Bus --sda=sda --scl=scl --frequency=400_000

    devices := [bus.device ADDRESS-LOW, bus.device ADDRESS-HIGH]

    while not device_:
      error := catch:
        device-detected := probe-for-imu_ devices
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
        configure-interrupts_
        configure-hardware-filters_
        finish-imu-startup_

      if error:
        device_ = null
        log.warn "Failed to initialize IMU: $error. Retrying in 1s..."
        sleep --ms=1000

    log.info "SUCCESS: IMU initialized successfully"

  probe-for-imu_ devices/List -> i2c.Device?:
    devices.do: | dev |
      probe-err := catch:
        id := dev.read-reg WHO-AM-I-REGISTER 1
        if id[0] == WHO-AM-I-VALUE:
          log.info "SUCCESS: Found LSM6DSOX at I2C address 0x$(%02x dev.address)"
          return dev
    return null

  /// Performs a software reset of the IMU by setting the SW_RESET bit (0x01).
  reset-imu_ -> none:
    device_.write-reg CONTROL-REGISTER-3-COMMON SW-RESET-CMD
    sleep --ms=50
    while true:
      reg := (device_.read-reg CONTROL-REGISTER-3-COMMON 1)[0]
      if (reg & 0x01) == 0: break
      sleep --ms=10

  verify-imu-identification_ -> none:
    device-identification := device_.read-reg WHO-AM-I-REGISTER 1
    if device-identification[0] != WHO-AM-I-VALUE:
      throw "IMU not found: WHO_AM_I=0x$(%02x device-identification[0]), expected 0x$(%02x WHO-AM-I-VALUE)"

  /// Configures Gyroscope: Output Data Rate = 104 Hz, Full Scale = ±500 dps.
  configure-gyro_ -> none:
    device_.write-reg CONTROL-REGISTER-2-GYROSCOPE CONFIG-GYRO-104HZ-500DPS

  /// Configures Accelerometer: Output Data Rate = 104 Hz, Full Scale = ±4g.
  configure-accelerometer_ -> none:
    device_.write-reg CONTROL-REGISTER-1-ACCELEROMETER CONFIG-ACCEL-104HZ-4G

  /// Enables Block Data Update (BDU) and Address Auto-Increment (IF_INC).
  enable-control-features_ -> none:
    device_.write-reg CONTROL-REGISTER-3-COMMON CONFIG-BDU-IF-INC

  disable-unneeded-gyro-features_ -> none:
    device_.write-reg CONTROL-REGISTER-7-GYROSCOPE CONFIG-DISABLE-FEATURE

  disable-unneeded-control-features_ -> none:
    device_.write-reg CONTROL-REGISTER-4-COMMON CONFIG-DISABLE-FEATURE

  configure-interrupts_ -> none:
    device_.write-reg COUNTER-BDR-REG1 CONFIG-PULSED-DRDY
    device_.write-reg INT1-CTRL CONFIG-INT1-DRDY-BOTH

  configure-hardware-filters_ -> none:
    device_.write-reg CONTROL-REGISTER-6-COMMON CONFIG-DISABLE-FEATURE

  finish-imu-startup_ -> none:
    sleep --ms=10
    read-sensors

  /// Reads both Gyroscope and Accelerometer data in a single burst I2C transaction (12 bytes).
  read-sensors -> none:
    if not device_: return
    error := catch:
      raw-data := device_.read-reg OUTPUT-X-LOW-GYROSCOPE 12
      
      imu-data.gyro_x = io.LITTLE-ENDIAN.int16 raw-data 0
      imu-data.gyro_y = io.LITTLE-ENDIAN.int16 raw-data 2
      imu-data.gyro_z = io.LITTLE-ENDIAN.int16 raw-data 4

      imu-data.accel_x = io.LITTLE-ENDIAN.int16 raw-data 6
      imu-data.accel_y = io.LITTLE-ENDIAN.int16 raw-data 8
      imu-data.accel_z = io.LITTLE-ENDIAN.int16 raw-data 10
    if error:
      log.warn "IMU read failed: $error"


