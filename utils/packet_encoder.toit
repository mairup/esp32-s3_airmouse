import io

// Encode Raw Stage Packet (17 bytes)
// [Magic:2][Seq:2][Buttons:1][Gx:2][Gy:2][Gz:2][Ax:2][Ay:2][Az:2]
encode-raw-packet --seq/int --buttons/int --gx/int --gy/int --gz/int --ax/int --ay/int --az/int -> ByteArray:
  b := ByteArray 17
  b[0] = 0x41 // 'A'
  b[1] = 0x4D // 'M'
  
  io.LITTLE-ENDIAN.put-int16 b 2 seq
  b[4] = buttons
  
  io.LITTLE-ENDIAN.put-int16 b 5 gx
  io.LITTLE-ENDIAN.put-int16 b 7 gy
  io.LITTLE-ENDIAN.put-int16 b 9 gz
  io.LITTLE-ENDIAN.put-int16 b 11 ax
  io.LITTLE-ENDIAN.put-int16 b 13 ay
  io.LITTLE-ENDIAN.put-int16 b 15 az
  return b

// Encode Fusion Stage Packet (17 bytes)
// [Magic:2][Seq:2][Buttons:1][Pitch:4f][Yaw:4f][Roll:4f]
encode-fusion-packet --seq/int --buttons/int --pitch/float --yaw/float --roll/float -> ByteArray:
  b := ByteArray 17
  b[0] = 0x53 // 'S'
  b[1] = 0x46 // 'F'
  
  io.LITTLE-ENDIAN.put-int16 b 2 seq
  b[4] = buttons
  
  io.LITTLE-ENDIAN.put-float32 b 5 pitch
  io.LITTLE-ENDIAN.put-float32 b 9 yaw
  io.LITTLE-ENDIAN.put-float32 b 13 roll
  return b

// Encode Kinematics Stage Packet (17 bytes)
// [Magic:2][Seq:2][Buttons:1][DeltaX:4f][DeltaY:4f][Pad:4]
encode-kinematics-packet --seq/int --buttons/int --delta-x/float --delta-y/float -> ByteArray:
  b := ByteArray 17
  b[0] = 0x4B // 'K'
  b[1] = 0x4E // 'N'
  
  io.LITTLE-ENDIAN.put-int16 b 2 seq
  b[4] = buttons
  
  io.LITTLE-ENDIAN.put-float32 b 5 delta-x
  io.LITTLE-ENDIAN.put-float32 b 9 delta-y
  
  // Remaining 4 bytes are implicitly 0 due to ByteArray initialization
  return b
