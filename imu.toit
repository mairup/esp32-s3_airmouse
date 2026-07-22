import gpio
import i2c
import log
import io
import .utils.imu_data as imu-data

WHO-AM-I-REGISTER ::= 0x0F
WHO-AM-I-VALUE ::= 0x6C

CONTROL-REGISTER-1-ACCELEROMETER ::= 0x10
CONTROL-REGISTER-2-GYROSCOPE ::= 0x11
CONTROL-REGISTER-3-COMMON ::= 0x12
CONTROL-REGISTER-4-COMMON ::= 0x13
CONTROL-REGISTER-6-COMMON ::= 0x15
CONTROL-REGISTER-7-GYROSCOPE ::= 0x16

COUNTER-BDR-REG1 ::= 0x0B
INT1-CTRL ::= 0x0D

STATUS-REGISTER ::= 0x1E
OUTPUT-X-LOW-GYROSCOPE ::= 0x22
OUTPUT-X-LOW-ACCELEROMETER ::= 0x28

ADDRESS-LOW ::= 0x6A
ADDRESS-HIGH ::= 0x6B

// Conversion factors for ±500 dps Gyro and ±4g Accel
GYRO-SCALE-RAD-PER-SEC ::= 0.000305432619 // 0.0175 dps/LSB * (PI / 180)
ACCEL-SCALE-G          ::= 0.000122       // 0.122 mg/LSB



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

    dev-low := bus.device ADDRESS-LOW
    dev-high := bus.device ADDRESS-HIGH
    devices := [dev-low, dev-high]

    while not device_:
      error := catch:
        device-detected /i2c.Device? := null
        devices.do: | dev |
          if not device-detected:
            probe-err := catch:
              id := dev.read-reg WHO-AM-I-REGISTER 1
              if id[0] == WHO-AM-I-VALUE:
                device-detected = dev
                log.info "SUCCESS: Found LSM6DSOX at I2C address 0x$(%02x dev.address)"

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

  /// Performs a software reset of the IMU by setting the SW_RESET bit (0x01).
  reset-imu_ -> none:
    device_.write-reg CONTROL-REGISTER-3-COMMON #[0x01]
    sleep --ms=50
    // Poll SW_RESET bit until cleared
    while true:
      reg := (device_.read-reg CONTROL-REGISTER-3-COMMON 1)[0]
      if (reg & 0x01) == 0: break
      sleep --ms=10

  verify-imu-identification_ -> none:
    device-identification := device_.read-reg WHO-AM-I-REGISTER 1
    if device-identification[0] != WHO-AM-I-VALUE:
      throw "IMU not found: WHO_AM_I=0x$(%02x device-identification[0]), expected 0x$(%02x WHO-AM-I-VALUE)"

  /// Configures Gyroscope: Output Data Rate = 104 Hz, Full Scale = ±500 dps.
  /// Binary value 0x44 (0100 0100) sets the upper nibble for ODR and lower for FS.
  configure-gyro_ -> none:
    device_.write-reg CONTROL-REGISTER-2-GYROSCOPE #[0x44]

  /// Configures Accelerometer: Output Data Rate = 104 Hz, Full Scale = ±4g.
  /// Binary value 0x48 (0100 1000) sets the upper nibble for ODR and lower for FS.
  configure-accelerometer_ -> none:
    device_.write-reg CONTROL-REGISTER-1-ACCELEROMETER #[0x48]

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
    // Set COUNTER_BDR_REG1 / DRDY_PULSE_CFG (0x0B) bit 7 = 1 for Pulsed DRDY mode (75us pulse)
    device_.write-reg COUNTER-BDR-REG1 #[0x80]
    // Bit 0 = Accel DRDY (DRDY_XL), Bit 1 = Gyro DRDY (DRDY_G) -> 0x03 enables both on INT1
    device_.write-reg INT1-CTRL #[0x03]

  configure-hardware-filters_ -> none:
    device_.write-reg CONTROL-REGISTER-6-COMMON #[0x00]

  finish-imu-startup_ -> none:
    sleep --ms=10
    // Flush initial interrupt status by reading sensors once
    read-sensors

  /// Reads both Gyroscope and Accelerometer data in a single burst I2C transaction (12 bytes).
  read-sensors -> none:
    if not device_: return
    error := catch:
      raw-data := device_.read-reg OUTPUT-X-LOW-GYROSCOPE 12
      
      // Process Gyroscope data
      imu-data.gyro_x = io.LITTLE-ENDIAN.int16 raw-data 0
      imu-data.gyro_y = io.LITTLE-ENDIAN.int16 raw-data 2
      imu-data.gyro_z = io.LITTLE-ENDIAN.int16 raw-data 4

      // Process Accelerometer data
      imu-data.accel_x = io.LITTLE-ENDIAN.int16 raw-data 6
      imu-data.accel_y = io.LITTLE-ENDIAN.int16 raw-data 8
      imu-data.accel_z = io.LITTLE-ENDIAN.int16 raw-data 10
    if error:
      log.warn "IMU read failed: $error"

  read-status -> int:
    if not device_: return 0
    error := catch:
      return (device_.read-reg STATUS-REGISTER 1)[0]
    return -1

  // Raw integer getters
  gyro-x -> int: return imu-data.gyro_x
  gyro-y -> int: return imu-data.gyro_y
  gyro-z -> int: return imu-data.gyro_z
  accel-x -> int: return imu-data.accel_x
  accel-y -> int: return imu-data.accel_y
  accel-z -> int: return imu-data.accel_z

  // Helper getters for physical units
  gyro-x-rad -> float: return imu-data.gyro_x * GYRO-SCALE-RAD-PER-SEC
  gyro-y-rad -> float: return imu-data.gyro_y * GYRO-SCALE-RAD-PER-SEC
  gyro-z-rad -> float: return imu-data.gyro_z * GYRO-SCALE-RAD-PER-SEC

  accel-x-g -> float: return imu-data.accel_x * ACCEL-SCALE-G
  accel-y-g -> float: return imu-data.accel_y * ACCEL-SCALE-G
  accel-z-g -> float: return imu-data.accel_z * ACCEL-SCALE-G

  to-signed-16_ value/int -> int:
    if value >= 32768:
      return value - 65536
    return value
