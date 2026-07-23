import io


RAW-PACKET-BUFFERS_ ::= [
  ByteArray 17,
  ByteArray 17,
  ByteArray 17,
  ByteArray 17,
]
raw-buffer-idx_ := 0

encode-raw-packet --seq/int --buttons/int --gx/int --gy/int --gz/int --ax/int --ay/int --az/int --pot/int -> ByteArray:
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
  io.LITTLE-ENDIAN.put-uint16 b 15 pot
  return b


