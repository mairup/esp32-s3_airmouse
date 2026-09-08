# ESP32-S3 AirMouse - Report

**Authors:** Laris Pintar, Mai Rupnik

**Written by:** Laris Pintar, *computer-assisted translation*

---

## 1. Introduction

The project is based on the LSM6DSOX IMU sensor, whose primary task is providing real-time data from a 3-axis accelerometer and a 3-axis gyroscope to the ESP32-S3 via I2C. The ESP32-S3 packages the data into a packet and sends it over UDP to a computer, where all the "heavy" computations (filtering, pointer movement, etc.) take place in a Python client. All of this comes together in our "air-mouse" device, which wirelessly controls the cursor through hand rotation and movement.

---

## 2. Components

- ESP32-S3 development board
- 6-axis IMU LSM6DSOX
- 4x Push buttons ("clutch", left click, right click, gestures)
- 5x LEDs
- RGB LED
- Analog potentiometer for adjusting motion sensitivity

---

## 3. Hardware Assembly

The circuit is connected according to the scheme in the table:

| Component | Pin / Function | ESP32-S3 GPIO |
| :--- | :--- | :--- |
| LSM6DSOX | SDA | GPIO 21 |
| LSM6DSOX | SCL | GPIO 20 |
| LSM6DSOX | INT (data-ready) | GPIO 7 |
| Clutch button | pull-up input | GPIO 1 |
| Left click | pull-up input | GPIO 35 |
| Right click | pull-up input | GPIO 16 |
| Gesture button | pull-up input | GPIO 3 |
| Potentiometer | ADC1 | GPIO 2 |
| Left/Right click LED | output | GPIO 14 / 11 |
| Pan / Axis lock LED | output | GPIO 40 / 13 |
| Overload LED | output | GPIO 17 |
| RGB LED (R/G/B) | output | GPIO 6 / 5 / 4 |

All modules (buttons, LEDs, IMU, etc.) are connected to the ESP32. The device itself is assembled on a breadboard, powered by a portable power bank.

![Device assembly on breadboard](img/breadboard.jpg)

---

## 4. System Operation

The system is divided into two parts: the ESP32-S3 handles data acquisition and transmission, while the Python program on the client side handles processing and cursor movement.

### 4.1 Data Acquisition and Transmission (ESP32-S3)

The LSM6DSOX samples the gyroscope and accelerometer at a frequency of 208 Hz. With every new sample, the sensor sends a short pulse to the INT1 pin, to which the ESP32-S3 responds with a single read of all 12 data bytes over I²C (3 gyroscope axes and 3 accelerometer axes, 2 bytes per axis).

![Sensor data readout](img/code_read_sensors.png)

Mouse sensitivity is adjusted via an analog potentiometer, which the ESP32-S3 reads via the ADC input every 50 ms and transmits its value in every UDP packet. This allows the user to adjust sensitivity on the fly without restarting or reconfiguring the software.

![Potentiometer readout](img/code_potentiometer.png)

Because the data is read in a single transfer, both sensor samples are synchronized in time. The firmware simultaneously subtracts gyroscope offsets, assigns button states (4-bit mask: clutch, left click, right click, gesture) and the potentiometer value, packages everything into a 17-byte UDP packet, and sends it via Wi-Fi to the computer.

![Packaging the UDP packet](img/code_encode_raw_packet.png)

All firmware is written in Toit, a high-level language for ESP32 microcontrollers. Its greatest advantage for this project is built-in concurrency, ensuring that each system subsystem (IMU sampling, button polling, potentiometer, Wi-Fi server) runs in its own "task" without manual interrupt or thread management. The language features automatic memory management and exception handling, which simplifies reliable operation: for example, if an I2C read or Wi-Fi connection fails, the error is caught and the connection is re-established without restarting the device. The high-level nature of Toit thus enables rapid iterations of prototypes with new features.

### 4.3 Data Processing (Python on Computer)

The program receives UDP packets and calculates cursor movement in three steps:

1. **Calibration and Deadzone:** When the hand is stationary, the program continuously adjusts the gyroscope's baseline offset to prevent error accumulation from gyroscope drift. Small tremors below a set threshold are ignored so that the cursor does not "dance" on screen while stationary.
2. **Filtering:** Each gyroscope axis is processed by a 1-Euro filter: it heavily smooths jitter during slow movements, while automatically adapting and opening up during fast movements to prevent latency. Simultaneously, a Madgwick filter fuses the gyroscope and accelerometer data to calculate hand tilt, ensuring that even if the device is held slightly tilted, it behaves as if oriented correctly.
3. **Pixel Mapping:** Angular velocity is multiplied by the sensitivity dynamically adjusted via the potentiometer and converted into relative cursor movement. All this data is then translated into mouse movements across the screen.

### 4.4 Operating Modes

| Mode | How to Activate | What Happens |
| :--- | :--- | :--- |
| cursor movement | default | 1-Euro filter + acceleration curve during fast motions |
| repositioning / recalibration | hold clutch | cursor slows down drastically and barely moves, allowing hand repositioning |
| click (left/right) | click left or right button | left or right click occurs |
| double click | hold gesture button + left click | double left click occurs |
| middle button | hold gesture button + right click | middle click occurs |
| content scrolling | hold clutch + device stationary for 100ms | content scrolling mode activates (vertical/horizontal) |
| back | hold gesture button + flick left | OS "back" event occurs |
| forward | hold gesture button + flick right | OS "forward" event occurs |

![Client-side terminal](img/terminal_monitor.png)

The image shows the terminal on the client side displaying all real-time information about the device.

### 4.5 State Indication with LEDs

The device has seven LEDs that communicate system status to the user in real time. Two light up when holding left or right click, while a yellow LED turns on whenever data processing on the microcontroller exceeds the time budget (more than 2.4 ms per sample), indicating an overload. The RGB LED indicates Wi-Fi connection state: orange during startup, blue while waiting for a client, green once connected to the computer, and red on error. Two LEDs (pan and axis lock) are controlled by the client program on the computer. During a calibration gesture, the RGB LED glows purple, and flashes green after successful recalibration.

---

## 5. Links and Demos:

- [Github repository](https://github.com/mairup/esp32-s3_airmouse)
- Video demonstration
