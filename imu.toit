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

INT1-CTRL ::= 0x0D

STATUS-REGISTER ::= 0x1E
OUTPUT-X-LOW-GYROSCOPE ::= 0x22
OUTPUT-X-LOW-ACCELEROMETER ::= 0x28

ADDRESS-LOW ::= 0x6A
ADDRESS-HIGH ::= 0x6B

// Conversion factors for ±500 dps Gyro and ±4g Accel
GYRO-SCALE-RAD-PER-SEC ::= 0.000305432619 // 0.0175 dps/LSB * (PI / 180)
ACCEL-SCALE-G          ::= 0.000122       // 0.122 mg/LSB

gyro_x := 0
gyro_y := 0
gyro_z := 0

accel_x := 0
accel_y := 0
accel_z := 0

class Imu:
  sda-pin_ /int
  scl-pin_ /int
  int-pin_ /int
  device_ /i2c.Device? := null

  constructor --sda/int --scl/int --int-pin/int:
    sda-pin_ = sda
    scl-pin_ = scl
    int-pin_ = int-pin

  start -> none:
    if device_: return

    log.info "Initializing IMU on SDA=$sda-pin_, SCL=$scl-pin_, INT=$int-pin_..."
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
      configure-interrupts_
      configure-hardware-filters_
      finish-imu-startup_

    if error:
      log.warn "Failed to initialize IMU: $error. Continuing without IMU."
    else:
      log.info "SUCCESS: IMU initialized successfully"

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

  configure-interrupts_ -> none:
    device_.write-reg INT1-CTRL #[0x02]

  configure-hardware-filters_ -> none:
    device_.write-reg CONTROL-REGISTER-6-COMMON #[0x00]

  finish-imu-startup_ -> none:
    sleep --ms=10

  /// Reads both Gyroscope and Accelerometer data in a single burst I2C transaction (12 bytes).
  read-sensors -> none:
    if not device_:
      log.warn "Attempted to read sensor data before IMU was initialized"
      sleep --ms=100
      return

    // Read 12 contiguous bytes: Gyro X,Y,Z (6 bytes) + Accel X,Y,Z (6 bytes)
    raw-data := device_.read-reg OUTPUT-X-LOW-GYROSCOPE 12

    gyro_x = to-signed-16_ (raw-data[0] | (raw-data[1] << 8))
    gyro_y = to-signed-16_ (raw-data[2] | (raw-data[3] << 8))
    gyro_z = to-signed-16_ (raw-data[4] | (raw-data[5] << 8))

    accel_x = to-signed-16_ (raw-data[6] | (raw-data[7] << 8))
    accel_y = to-signed-16_ (raw-data[8] | (raw-data[9] << 8))
    accel_z = to-signed-16_ (raw-data[10] | (raw-data[11] << 8))

  // Helper getters for physical units
  gyro-x-rad -> float: return gyro_x * GYRO-SCALE-RAD-PER-SEC
  gyro-y-rad -> float: return gyro_y * GYRO-SCALE-RAD-PER-SEC
  gyro-z-rad -> float: return gyro_z * GYRO-SCALE-RAD-PER-SEC

  accel-x-g -> float: return accel_x * ACCEL-SCALE-G
  accel-y-g -> float: return accel_y * ACCEL-SCALE-G
  accel-z-g -> float: return accel_z * ACCEL-SCALE-G

  to-signed-16_ value/int -> int:
    if value >= 32768:
      return value - 65536
    return value

  detect-imu_ bus/i2c.Bus -> i2c.Device?:
    log.debug "Scanning I2C bus for LSM6DSOX..."
    detected-addresses := bus.scan
    log.debug "Found devices at: $detected-addresses"
    if detected-addresses.contains ADDRESS-LOW:
      log.info "SUCCESS: Found IMU at 0x$(%02x ADDRESS-LOW) (SA0=GND)"
      return bus.device ADDRESS-LOW
    if detected-addresses.contains ADDRESS-HIGH:
      log.info "SUCCESS: Found IMU at 0x$(%02x ADDRESS-HIGH) (SA0=VDDIO)"
      return bus.device ADDRESS-HIGH
    return null
