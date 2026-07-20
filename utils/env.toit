import net

PORT ::= 8888
DEBUG ::= true

LOGGER-ADDRESSES/List ::= [
  net.SocketAddress (net.IpAddress.parse "192.168.5.69") PORT,
]

