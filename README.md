# ESP32-S3 AirMouse - Report

---

## 1. Introduction

The project is based on the LSM6DSOX IMU sensor, whose primary task is providing real-time data from a 3-axis accelerometer and a 3-axis gyroscope to the ESP32-S3 via I2C. The ESP32-S3 packages the data into a packet and sends it over UDP to a computer, where all the "heavy" computations (filtering, pointer movement, etc.) take place in a Python client. All of this comes together in our "air-mouse" device, which wirelessly controls the cursor through hand rotation and movement.

---

## 2. Components

- ESP32-S3 development board
- 6-axis IMU LSM6DSOX
- 4x Push buttons ("clutch", left click, right click, gestures)
- 5x LED diodes
- RGB-LED diode
- Analog potentiometer, for adjusting motion sensitivity

---

## 3. Assembly

The circuit is connected according to the table schema:

| Component | Pin / function | GPIO ESP32-S3 |
| :--- | :--- | :--- |
| LSM6DSOX | SDA | GPIO 21 |
| LSM6DSOX | SCL | GPIO 20 |
| LSM6DSOX | INT (data-ready) | GPIO 7 |
| Clutch button | pull-up input | GPIO 1 |
| Left click | pull-up input | GPIO 35 |
| Right click | pull-up input | GPIO 16 |
| Gesture button | pull-up input | GPIO 3 |
| Potentiometer | ADC1 | GPIO 2 |
| Left/right click LED | output | GPIO 14 / 11 |
| LED pan / axis lock | output | GPIO 40 / 13 |
| Overload LED | output | GPIO 17 |
| RGB LED (R/G/B) | output | GPIO 6 / 5 / 4 |

All modules (buttons, LEDs, IMU, ...) are connected to the ESP32. The device itself is assembled on a breadboard, powered by a portable power bank.

![Device assembly on breadboard](img/breadboard.jpg)

---

## 4. System Operation

The device is divided into two parts: the ESP32-S3 handles data acquisition and transmission, while the Python program on the client handles data processing and cursor movement.

### 4.1 Data Acquisition and Transmission (ESP32-S3)

The LSM6DSOX samples the gyroscope and accelerometer at a frequency of 208 Hz. With every new sample, the sensor sends a short pulse to the INT1 pin, to which the ESP32-S3 responds with a single read of all 12 bytes of data over I²C (3 gyroscope axes and 3 accelerometer axes, 2 bytes per axis).

![Sensor data readout](img/code_read_sensors.png)

Mouse sensitivity is adjusted via an analog potentiometer, which the ESP32-S3 reads via the ADC input every 50 ms and transmits its value in every UDP packet. This allows the user to adjust sensitivity on the fly while working, without restarting or reconfiguring software.

![Potentiometer readout](img/code_potentiometer.png)

Because the data is read in a single transfer, both samples are synchronized in time. The program simultaneously subtracts gyroscope offsets, assigns button states (4-bit mask: clutch, left click, right click, gesture) and the potentiometer value, packages everything into a 17-byte UDP packet, and sends it via Wi-Fi to the computer.

![Packaging the UDP packet](img/code_encode_raw_packet.png)

All firmware is written in Toit, a high-level language for ESP32 microcontrollers. Its greatest advantage for this task is built-in concurrency, which ensures that each part of the system (IMU sampling, button polling, potentiometer, Wi-Fi server) runs in its own "task" without manual interrupt or thread management. The language features automatic memory management and exception handling, which simplifies reliable operation: for example, if an I2C read or Wi-Fi connection fails, the error is caught and the connection is re-established without restarting the device. The high-level nature of Toit thus enables rapid iterations of prototypes with new features.

### 4.3 Data Processing (Python on Computer)

The program receives UDP packets from the ESP32 server and, using various filters and effects, transforms them into responsive, user-tailored cursor movements.

To ensure cursor movement is smooth (rather than jittery) while remaining responsive to user input, the pipeline relies on the 1-Euro and Madgwick filters.

Filtered values are projected onto the 2D screen plane using a rotation matrix based on the current hand tilt (roll) computed by the Madgwick filter, and the resulting delta is converted into cursor displacement.

When the hand is stationary, the program continuously adjusts the gyroscope's baseline offset to prevent error accumulation from gyroscope drift. Subtle tremors below a defined threshold are ignored so the cursor does not jitter while at rest. This is referred to as the deadzone.

### 4.4 Operating Modes

| Mode | How to activate | What happens |
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

The device has 6 LEDs that communicate system status to the user in real time. The main one is the RGB LED, which indicates Wi-Fi connection state: orange during startup, blue while waiting for a client, green once the connection to the computer is established, and red on error. During a calibration gesture, the RGB LED glows purple, and flashes green 5 times after successful recalibration.

In addition, there are 5 single-color LEDs. These communicate various signals to the user. The red LED next to the microcontroller indicates high CPU load, while the green and yellow LEDs at the end of the remote display the status during content scrolling mode. The left and right click buttons each have their own LED indicating their state.

*Author: Laris Pintar, translated*

---

## 5. Links and Demos:

- [Online Interactive Report & Documentation (EN/SLO)](https://esp-demo.mairup.space/docs/)
- [Interactive Browser Demonstration (Live Demo)](https://esp-demo.mairup.space/)
- [Github repository](https://github.com/mairup/esp32-s3_airmouse)

### Demonstration Videos:

- **Device Startup & Wi-Fi Connection:** [`startup.mp4`](../vids/startup.mp4) — system initialization and status LED indication during connection handshakes.  
**(If you look closely, you can notice the Wi-Fi server advertising state for a few hundred ms, indicated in blue on the RGB LED. During this window, the ESP server and the client computer synchronize. Immediately after the RGB LED turns solid green, the device is fully operational.)**

- **Gyroscope Calibration:** [`calibration.mp4`](../vids/calibration.mp4) — recalibration gesture sequence (purple RGB LED followed by 5 green confirmation pulses).
- **Dynamic Sensitivity Adjustment (Potentiometer):** [`sensitivity-scaling.mp4`](../vids/sensitivity-scaling.mp4) — adjusting pointer sensitivity and speed on-the-fly using the analog potentiometer.
- **General Pointer Navigation:** [`use-example-1.mp4`](../vids/use-example-1.mp4) — baseline hand movement driving fluid cursor motion across the desktop.
- **Dynamic Click Stabilization:** [`pointer-slowdown-on-click.mp4`](../vids/pointer-slowdown-on-click.mp4) — damping cursor tremor on physical button actuation for pinpoint accuracy.
- **Click Stabilization in Open Area:** [`pointer-slowdown-on-click-free-area.mp4`](../vids/pointer-slowdown-on-click-free-area.mp4) — demonstration of zero cursor drift across rapid sequential clicking.
- **Double Click Gesture:** [`double-click.mp4`](../vids/double-click.mp4) — triggering native OS double clicks via gesture button + left click combo.
- **Drag & Drop Workspace:** [`drag-and-drop-tiles.mp4`](../vids/drag-and-drop-tiles.mp4) — grabbing and repositioning window tiles using sustained click hold and hand motion.
- **Vertical Scrolling:** [`vertical-scroll.mp4`](../vids/vertical-scroll.mp4) — smooth bidirectional vertical scrolling in pan mode.
- **Horizontal Scrolling:** [`horizontal-scroll.mp4`](../vids/horizontal-scroll.mp4) — lateral navigation through wide content streams.
- **2D Pan with Dominant Axis Lock:** [`area-scroll-with-axis-lock.mp4`](../vids/area-scroll-with-axis-lock.mp4) — 2D canvas navigation with automatic axis-locking to prevent accidental drift.
- **Back & Forward History Navigation:** [`back-and-forward-navigation.mp4`](../vids/back-and-forward-navigation.mp4) — browser history traversal using quick left/right flick gestures while holding the gesture button.
