# ESP32-S3 Air Mouse Hardware Wiring Guide

## Front Panel Module Header Layout (Standard 2x5 / 10-pin Header)

```text
       [ TOP ROW - EVEN PINS ]
   +---------+---------+---------+---------+---------+
   | Pin 2   | Pin 4   | Pin 6   | Pin 8   | Pin 10  |
   | PLED+   | PLED-   | PWR_SW  | PWR_GND | [KEY]   |
   +---------+---------+---------+---------+---------+
   | Pin 1   | Pin 3   | Pin 5   | Pin 7   | Pin 9   |
   | HDD_LED+| HDD_LED-| RST_GND | RST_SW  | NC      |
   +---------+---------+---------+---------+---------+
     [ BOTTOM ROW - ODD PINS ]
```

---

## Pin Mapping to ESP32-S3

| Front Panel / Component Pin | Function | Description | ESP32-S3 Connection |
| :--- | :--- | :--- | :--- |
| **Pin 6** (PWR_SW) | Power Button Switch | Left Click Input | **GPIO 16** (Pull-up Input) |
| **Pin 7** (RST_SW) | Reset Button Switch | Right Click Input | **GPIO 14** (Pull-up Input) |
| **Gesture Button** | Recalibration Gesture | Gesture Input | **GPIO 38** (Pull-up Input) |
| **Potentiometer Wiper** | Analog Sensitivity Knob | Analog Input | **GPIO 9** (ADC1 Input) |
| **Pin 2** (PLED+) | Power LED Positive | Left Click Indicator | **GPIO 8** (Output) |
| **Pin 1** (HDD_LED+) | HDD LED Positive | Right Click Indicator | **GPIO 11** (Output) |
| **Pin 3, 4, 5, 8** | Module Grounds | Grounds | **ESP32 GND** |
