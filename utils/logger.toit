import log show Logger Target DefaultTarget level-name set-default DEBUG-LEVEL
import net
import net.udp
import monitor show Channel

class WirelessLogTarget implements Target:
  socket/udp.Socket? := null
  log-queue/Channel ::= Channel 20
  
  // List of Tailnet and local destination addresses
  addresses/List ::= [
    net.SocketAddress (net.IpAddress.parse "100.69.0.100") 8888,
    net.SocketAddress (net.IpAddress.parse "100.69.0.69") 8888,
    net.SocketAddress (net.IpAddress.parse "100.69.0.14") 8888,
    net.SocketAddress (net.IpAddress.parse "100.69.0.8") 8888,
    net.SocketAddress (net.IpAddress.parse "100.69.0.67") 8888,
    net.SocketAddress (net.IpAddress.parse "192.168.5.100") 8888,
  ]

  serial/Target ::= DefaultTarget

  constructor:
    task::
      // 1. Wait for network stability and open socket
      sleep --ms=1000
      catch: socket = net.open.udp-open --port=0
      
      // 2. Flush queue and enter send loop
      send-loop_

  send-loop_:
    while true:
      msg := log-queue.receive
      if socket:
        datagram-bytes := "$msg\n".to-byte-array
        addresses.do: |addr|
          catch: socket.send (udp.Datagram datagram-bytes addr)

  log level/int message/string names/List? keys/List? values/List? -> none:
    serial.log level message names keys values
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
