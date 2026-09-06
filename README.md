# ESP32-S3 Air Mouse

Low-latency wireless air mouse system with subpixel kinetic scrolling, dynamic click stabilization, and 6-DoF inertial motion tracking.

The system consists of two primary components:
- **Firmware (`Toit`)**: Runs on an ESP32-S3 microcontroller, streaming raw IMU, button, and potentiometer data over UDP at 208 Hz.
- **Client (`Python`)**: Runs on the host computer, processing telemetry through adaptive filters and injecting relative cursor and high-resolution scroll events via Linux `uinput`.

---

## Architecture Overview

```
                      +-----------------------------+
                      |   LSM6DSOX 6-DoF IMU        |
                      |   (I2C, 208 Hz Data-Ready)  |
                      +--------------+--------------+
                                     |
                                     v
+------------------------------------+------------------------------------+
|  ESP32-S3 Firmware (Toit)                                               |
|  - ImuPipeline: Burst reads 12 bytes IMU data on GPIO interrupt         |
|  - ButtonManager: Debounces clutch, left, right, and gesture inputs     |
|  - PotentiometerManager: Samples analog sensitivity potentiometer       |
|  - WifiServer: Streams 17-byte binary UDP datagrams to client           |
+------------------------------------+------------------------------------+
                                     |
                                     | UDP (Wi-Fi)
                                     v
+------------------------------------+------------------------------------+
|  Host Driver (Python / evdev)                                           |
|  - AirMousePipeline:                                                    |
|      * 1-Euro Filter: Jitter dampening & lag reduction                  |
|      * Madgwick Filter: Roll-compensated horizon alignment              |
|      * Dynamic Click Slowdown: Eliminates cursor jitter during clicks   |
|      * Pan / Scroll Engine: Subpixel smooth scrolling & axis locking    |
|  - Virtual Mouse: Emits EV_REL, REL_WHEEL_HI_RES, EV_KEY via /dev/uinput|
+-------------------------------------------------------------------------+
```

---

## Hardware Pinout

| Component | Pin / Function | ESP32-S3 GPIO | Note |
| :--- | :--- | :--- | :--- |
| **LSM6DSOX IMU** | SDA | GPIO 21 | I2C Data |
| | SCL | GPIO 20 | I2C Clock |
| | INT | GPIO 7 | Data-ready interrupt pin |
| **Buttons** | Clutch / Pan | GPIO 1 | Pull-up input |
| | Left Click | GPIO 35 | Pull-up input |
| | Right Click | GPIO 16 | Pull-up input |
| | Gesture Button | GPIO 3 | Pull-up input |
| **Analog** | Potentiometer | GPIO 2 | ADC1 analog input |
| **Status LEDs** | Left Click LED | GPIO 14 | Digital output |
| | Right Click LED | GPIO 11 | Digital output |
| | Pan Mode LED | GPIO 40 | Digital output |
| | Axis Lock LED | GPIO 13 | Digital output |
| | Overload LED | GPIO 17 | CPU monitor indicator |
| **RGB LED** | Red | GPIO 6 | System status indicator |
| | Green | GPIO 5 | System status indicator |
| | Blue | GPIO 4 | System status indicator |

---

## Pipeline Features & Configuration

All default tuning constants are defined in [client/config.py](file:///home/mai/Documents/FRI/L2/VIN/VIN%20PROJEKT/esp32-s3_airmouse/client/config.py):

- **Adaptive 1-Euro Filtering**: Dynamically adjusts cutoff frequency based on movement speed to filter resting hand tremors while maintaining low latency during fast flicks.
- **Dynamic Click Slowdown**: Briefly dampens cursor sensitivity upon button down to prevent unwanted cursor displacement during physical clicks.
- **2D Pan & Scroll Mode**: Holding the clutch button activates 2D scrolling. Motion is integrated using a leaky signed relative displacement model that locks to a single dominant axis (vertical or horizontal) to prevent diagonal jitter.
- **Kinetic Inertia**: Provides continuous velocity decay gliding after releasing scroll gestures.
- **Hardware Potentiometer Sensitivity**: Real-time analog knob scaling mapping a cubic curve across the ADC input range.
