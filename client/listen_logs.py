import socket
import sys

PORT = 8888

def listen_logs():
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.bind(("", PORT))
    print(f"Listening for wireless ESP32-S3 UDP logs on port {PORT}...", flush=True)
    
    try:
        while True:
            data, addr = sock.recvfrom(4096)
            sys.stdout.write(data.decode('utf-8', errors='ignore'))
            sys.stdout.flush()
    except KeyboardInterrupt:
        print("\nStopping wireless log listener...", flush=True)
    finally:
        sock.close()

if __name__ == "__main__":
    listen_logs()
