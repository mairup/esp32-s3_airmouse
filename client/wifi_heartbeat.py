"""
Interactive UDP Wi-Fi client for ESP32-S3 AirMouse.
Press Ctrl+C to quit.
Usage: python wifi_heartbeat.py <ESP32_IP>
"""
import sys
import time
import socket
import threading

PORT = 8889

def main():
    if len(sys.argv) < 2:
        print("Usage: python wifi_heartbeat.py <ESP32_IP>")
        sys.exit(1)
        
    ip = sys.argv[1]
    
    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
        # Send a hello packet so the ESP32 registers our IP and Port
        print(f"Sending UDP registration to {ip}:{PORT}...")
        sock.sendto(b"HELLO", (ip, PORT))
        
        print("Registered! Waiting for UDP events... (Press Ctrl+C to quit)")
        
        conn_start_time = time.monotonic()
        
        while True:
            try:
                data, addr = sock.recvfrom(1024)
                text = data.decode("utf-8", errors="replace").strip()
                if not text:
                    continue
                
                elapsed = time.monotonic() - conn_start_time
                
                if "BTN_DOWN" in text or "BTN_UP" in text:
                    print(f"[{time.strftime('%H:%M:%S.%f')[:-3]}] {text:<40} (Conn Alive: {elapsed:.2f}s)")
                else:
                    print(f"RX: {text} (Conn Alive: {elapsed:.2f}s)")
                    
            except KeyboardInterrupt:
                print("\n[Disconnected]")
                break
            except Exception as e:
                print(f"Error: {e}")
                break

if __name__ == "__main__":
    main()
