-include .env

CHIP ?= esp32s3
PORT ?= /dev/ttyACM0
BAUD ?= 921600
DEVICE ?=
WIFI_SSID ?=
WIFI_PASSWORD ?=
IP ?= 192.168.5.126
CLIENT_PORT ?= 8889
ARGS ?=

.PHONY: esp flash client compile scan help

help:
	@echo "AirMouse Build and Automation Commands:"
	@echo "  make esp                     Run firmware on ESP32-S3 via Jaguar (optional: DEVICE=<name>)"
	@echo "  make flash                   Flash Jaguar VM with Wi-Fi credentials (.env or CLI overrides)"
	@echo "  make client                  Run host Python AirMouse client (optional: IP=<address> ARGS=\"<flags>\")"
	@echo "  make compile                 Compile standalone main.snapshot without running"
	@echo "  make scan                    Scan for online Jaguar devices on the local network"

esp:
	jag run $(if $(DEVICE),-d $(DEVICE),) main.toit

flash:
	@if [ -z "$(WIFI_SSID)" ] || [ -z "$(WIFI_PASSWORD)" ]; then \
		echo "Error: WIFI_SSID and WIFI_PASSWORD are required."; \
		echo "Set them in .env or pass as arguments:"; \
		echo "  make flash WIFI_SSID=\"SSID\" WIFI_PASSWORD=\"PASS\""; \
		exit 1; \
	fi
	jag flash --port $(PORT) --chip $(CHIP) --baud $(BAUD) $(if $(NAME),--name $(NAME),) --wifi-ssid "$(WIFI_SSID)" --wifi-password "$(WIFI_PASSWORD)"

client:
	python3 client/air_mouse_cli.py $(IP) --port $(CLIENT_PORT) $(ARGS)

compile:
	toit compile -s -o main.snapshot main.toit

scan:
	jag scan
