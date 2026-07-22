import io


// Pre-allocate circular buffers of ByteArrays to avoid garbage collection pauses
RAW-PACKET-BUFFERS_ ::= [
  ByteArray 15,
  ByteArray 15,
  ByteArray 15,
  ByteArray 15,
]
raw-buffer-idx_ := 0

// Encode Raw Stage Packet (15 bytes)
// [Seq:2][Buttons:1][Gx:2][Gy:2][Gz:2][Ax:2][Ay:2][Az:2]
encode-raw-packet --seq/int --buttons/int --gx/int --gy/int --gz/int --ax/int --ay/int --az/int -> ByteArray:
  b := RAW-PACKET-BUFFERS_[raw-buffer-idx_]
  raw-buffer-idx_ = (raw-buffer-idx_ + 1) % RAW-PACKET-BUFFERS_.size

  io.LITTLE-ENDIAN.put-int16 b 0 seq
  b[2] = buttons
  
  io.LITTLE-ENDIAN.put-int16 b 3 gx
  io.LITTLE-ENDIAN.put-int16 b 5 gy
  io.LITTLE-ENDIAN.put-int16 b 7 gz
  io.LITTLE-ENDIAN.put-int16 b 9 ax
  io.LITTLE-ENDIAN.put-int16 b 11 ay
  io.LITTLE-ENDIAN.put-int16 b 13 az
  return b


