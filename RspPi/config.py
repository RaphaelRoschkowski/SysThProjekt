# config.py – Central configuration for Raspberry Pi node

# ── Azure IoT Hub ─────────────────────────────────────────────────────────────
AZURE_CONNECTION_STRING = "HostName=<YOUR_HUB>.azure-devices.net;DeviceId=<DEVICE_ID>;SharedAccessKey=<KEY>"
AZURE_TELEMETRY_INTERVAL_S = 5          # seconds between cloud uploads

# ── Local MQTT broker (mosquitto on RPi) ──────────────────────────────────────
MQTT_BROKER_HOST   = "localhost"
MQTT_BROKER_PORT   = 1883
MQTT_KEEPALIVE_S   = 60

MQTT_TOPIC_MEAS    = "solar/measurements"   # ESP32 → RPi
MQTT_TOPIC_CMD     = "solar/commands"       # RPi  → ESP32
MQTT_TOPIC_STATUS  = "solar/status"         # ESP32 heartbeat

# ── GUI refresh ───────────────────────────────────────────────────────────────
GUI_REFRESH_MS = 500                    # poll interval for GUI event loop

# ── Misc ──────────────────────────────────────────────────────────────────────
LOG_LEVEL = "INFO"                      # DEBUG | INFO | WARNING | ERROR