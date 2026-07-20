import log show Logger Target DefaultTarget level-name set-default DEBUG-LEVEL
import net
import net.udp
import monitor show Channel
import .env show LOGGER-ADDRESSES

class WirelessLogTarget implements Target:
  // ========================================================================
  // Instance Fields
  // ========================================================================
  socket/udp.Socket? := null
  log-queue/Channel ::= Channel 20
  
  addresses/List ::= LOGGER-ADDRESSES
  serial/Target ::= DefaultTarget
  logger-task_ /Task? := null

  // ========================================================================
  // Constructor
  // ========================================================================
  constructor:
    task::
      logger-task_ = Task.current
      send-loop_

  // ========================================================================
  // Public API
  // ========================================================================
  log level/int message/string names/List? keys/List? values/List? -> none:
    serial.log level message names keys values
    
    if Task.current == logger-task_: return

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

  // ========================================================================
  // Private Core Loops
  // ========================================================================
  send-loop_:
    while true:
      msg := log-queue.receive
      
      // Dynamic self-healing: Try to open the socket if not open yet
      if not socket:
        catch: socket = net.open.udp-open --port=0
          
      if socket:
        datagram-bytes := "$msg\n".to-byte-array
        addresses.do: |addr|
          catch: socket.send (udp.Datagram datagram-bytes addr)

// ========================================================================
// Top-Level Initialization
// ========================================================================
logger-init -> none:
  set-default (Logger DEBUG-LEVEL WirelessLogTarget)
