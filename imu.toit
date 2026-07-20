import gpio
import i2c
import log
WHO-AM-I-REG ::= 0x0F
WHO-AM-I-VALUE ::= 0x6C

CTRL1-XL ::= 0x10
CTRL2-G ::= 0x11
CTRL3-C ::= 0x12
CTRL4-C ::= 0x13
CTRL6-C ::= 0x15
CTRL7-G ::= 0x16

STATUS-REG ::= 0x1E
OUTX-L-G ::= 0x22
OUTX-L-A ::= 0x28

ADDRESS-LOW ::= 0x6A
ADDRESS-HIGH ::= 0x6B

class Imu:
  device_ /i2c.Device

  constructor sda-pin/int scl-pin/int:
    sda := gpio.Pin sda-pin
    scl := gpio.Pin scl-pin

    bus := i2c.Bus --sda=sda --scl=scl

    device_ = detect-imu bus
    if device_ == null:
      throw "IMU not found on I2C bus"
    reset-imu_ device_
    verify-imu-identification_ device_
    configure-gyro_ device_
    configure-accelerometer_ device_
    enable-control-features_ device_
    disable-unneeded-gyro-features_ device_
    disable-unneeded-control-features_ device_
    finish-imu-startup_ device_
    log.info "IMU initialized successfully"

reset-imu_ device/i2c.Device -> none:
  device.write-reg CTRL3-C #[0x01]
  sleep --ms=50

verify-imu-identification_ device/i2c.Device -> none:
  id := device.read-reg WHO-AM-I-REG 1
  if id[0] != WHO-AM-I-VALUE:
    throw "IMU not found: WHO_AM_I=0x$(%02x id[0]), expected 0x$(%02x WHO-AM-I-VALUE)"

configure-gyro_ device/i2c.Device -> none:
  device.write-reg CTRL2-G #[0x44]

configure-accelerometer_ device/i2c.Device -> none:
  device.write-reg CTRL1-XL #[0x22]

enable-control-features_ device/i2c.Device -> none:
  device.write-reg CTRL3-C #[0x44]

disable-unneeded-gyro-features_ device/i2c.Device -> none:
  device.write-reg CTRL7-G #[0x00]

disable-unneeded-control-features_ device/i2c.Device -> none:
  device.write-reg CTRL4-C #[0x00]
  device.write-reg CTRL6-C #[0x00]

finish-imu-startup_ device/i2c.Device -> none:
  sleep --ms=10

detect-imu bus/i2c.Bus -> i2c.Device?:
  log.info "Scanning I2C bus for LSM6DSOX..."
  found := bus.scan
  log.info "Found devices at: $found"
  if found.contains ADDRESS-LOW:
    log.info  "Found IMU at 0x$(%02x ADDRESS-LOW) (SA0=GND)"
    return bus.device ADDRESS-LOW
  if found.contains ADDRESS-HIGH:
    log.info "Found IMU at 0x$(%02x ADDRESS-HIGH) (SA0=VDDIO)"
    return bus.device ADDRESS-HIGH
  return null