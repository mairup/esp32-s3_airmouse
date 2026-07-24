// Module-level global state for the IMU data and button states.

gyro_x := 0
gyro_y := 0
gyro_z := 0

accel_x := 0
accel_y := 0
accel_z := 0

// Bit 0: Clutch
// Bit 1: Left Click
// Bit 2: Right Click
button_states := 0
potentiometer_val := 0

gyro_offset_x := 0
gyro_offset_y := 0
gyro_offset_z := 0
