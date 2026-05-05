# config.py – ESP32 MicroPython configuration

# ── WiFi ──────────────────────────────────────────────────────────────────────
WIFI_SSID     = "YOUR_SSID"
WIFI_PASSWORD = "YOUR_PASSWORD"
WIFI_TIMEOUT_S = 15

# ── MQTT broker (Raspberry Pi local) ──────────────────────────────────────────
MQTT_BROKER    = "192.168.1.100"        # RPi IP on local network
MQTT_PORT      = 1883
MQTT_CLIENT_ID = "esp32_solar"
MQTT_KEEPALIVE = 60

MQTT_TOPIC_MEAS   = b"solar/measurements"
MQTT_TOPIC_CMD    = b"solar/commands"
MQTT_TOPIC_STATUS = b"solar/status"

# ── M90E32AS SPI pins (ESP32-DevKitC-VE) ──────────────────────────────────────
SPI_ID   = 1
SPI_SCK  = 14
SPI_MOSI = 13
SPI_MISO = 12
CS_PIN   = 15                           # one chip per phase → extend as needed
SPI_BAUD = 1_000_000

# ── Relay GPIO pins (one per phase, active-HIGH through BC337) ────────────────
RELAY_PINS = [25, 26, 27]              # L1, L2, L3

# ── Measurement loop ──────────────────────────────────────────────────────────
MEASUREMENT_INTERVAL_MS = 1_000        # publish every 1 s
STATUS_INTERVAL_MS      = 5_000        # heartbeat every 5 s

# ── Dead man's switch (ESP32 watchdog) ────────────────────────────────────────
DEAD_MANS_SWITCH_TIMEOUT_S = 60        # If RPi doesn't send command within 60s, open relays