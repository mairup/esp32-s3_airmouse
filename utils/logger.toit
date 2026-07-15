import log show Logger Target DefaultTarget level-name set-default DEBUG-LEVEL
import net
import net.udp
import monitor show Channel
import .env show LOGGER-ADDRESSES

class WirelessLogTarget implements Target:
  socket/udp.Socket? := null
  log-queue/Channel ::= Channel 20
  is-sending_ /bool := false
  
  addresses/List ::= LOGGER-ADDRESSES

  serial/Target ::= DefaultTarget

  constructor:
    task::
      send-loop_

  send-loop_:
    while true:
      msg := log-queue.receive
      
      // Dynamic self-healing: Try to open the socket if not open yet
      if not socket:
        is-sending_ = true
        try:
          catch: socket = net.open.udp-open --port=0
        finally:
          is-sending_ = false
          
      if socket:
        datagram-bytes := "$msg\n".to-byte-array
        is-sending_ = true
        try:
          addresses.do: |addr|
            catch: socket.send (udp.Datagram datagram-bytes addr)
        finally:
          is-sending_ = false

  log level/int message/string names/List? keys/List? values/List? -> none:
    serial.log level message names keys values
    
    // Prevent recursive logging loops from within the network stack
    if is-sending_: return

    buffer := ""
    if names and names.size > 0:
      name-str := ""
      names.size.repeat:
        name-str += (it > 0 ? "." : "") + names[it]
      buffer += "[$name-str] "
    buffer += "$(level-name level): $message"
    if keys and keys.size > 0:
      tag-str := ""
      keys.size.repeat:
        tag-str += (it > 0 ? ", " : "") + "$(keys[it]): $(values[it])"
      buffer += " {$tag-str}"

    log-queue.try-send buffer

logger-init -> none:
  set-default (Logger DEBUG-LEVEL WirelessLogTarget)
