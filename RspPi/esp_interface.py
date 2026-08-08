# esp_interface.py – MQTT interface between RPi and ESP32

import json
import logging
import threading
from datetime import datetime, timezone
from typing import Callable, Optional

import paho.mqtt.client as mqtt

import config

logger = logging.getLogger(__name__)

# Latest measurement snapshot – written by MQTT thread, read by GUI/Azure threads
_latest_measurement: dict = {}
_measurement_lock = threading.Lock()


def get_latest_measurement() -> dict:
    with _measurement_lock:
        return dict(_latest_measurement)


class EspInterface:
    #Manages the local MQTT connection to the ESP32.


    def __init__(self, on_measurement: Optional[Callable[[dict], None]] = None):
        """
        Parameters
        ----------
        on_measurement:
            Optional callback, called in the MQTT network thread whenever
            a new measurement arrives.  Keep it short (no blocking I/O).
        """
        self._on_measurement = on_measurement
        self._esp_online = False
        self._last_seen: Optional[datetime] = None
        self._relay_status = False

        self._client = mqtt.Client(client_id="rpi_main", clean_session=True)
        self._client.on_connect    = self._on_connect
        self._client.on_disconnect = self._on_disconnect
        self._client.on_message    = self._on_message

    # ── Connection lifecycle ──────────────────────────────────────────────────

    def connect(self) -> None:
        self._client.connect(
            config.MQTT_BROKER_HOST,
            config.MQTT_BROKER_PORT,
            config.MQTT_KEEPALIVE_S,
        )
        self._client.loop_start()   # background thread
        logger.info("MQTT: connecting to broker %s:%d",
                    config.MQTT_BROKER_HOST, config.MQTT_BROKER_PORT)

    def disconnect(self) -> None:
        self._client.loop_stop()
        self._client.disconnect()
        logger.info("MQTT: disconnected")

    @property
    def esp_online(self) -> bool:
        return self._esp_online

    @property
    def last_seen(self) -> Optional[datetime]:
        return self._last_seen

    # ── Command publishing ────────────────────────────────────────────────────

    def send_command(self, command: str, params: dict | None = None) -> None:
        """Publish a command frame to the ESP32.

        Parameters
        ----------
        command : "shutdown" | "restore" | "ping"
        params  : optional extra fields merged into the JSON payload
        """
        payload = {
            "command": command,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            **(params or {}),
        }
        self._client.publish(config.MQTT_TOPIC_CMD, json.dumps(payload), qos=1)
        logger.info("Command published: %s", command)

    # ── MQTT callbacks (network thread) ───────────────────────────────────────

    def _on_connect(self, client, userdata, flags, rc) -> None:
        if rc == 0:
            client.subscribe(config.MQTT_TOPIC_MEAS,   qos=0)
            client.subscribe(config.MQTT_TOPIC_CONNECTION, qos=0)
            client.subscribe(config.MQTT_TOPIC_RELAY, qos=0)
            logger.info("MQTT: broker connected, subscriptions active")
        else:
            logger.error("MQTT: connection refused – rc=%d", rc)

    def _on_disconnect(self, client, userdata, rc) -> None:
        self._esp_online = False
        logger.warning("MQTT: disconnected rc=%d – auto-reconnect pending", rc)

    def _on_message(self, client, userdata, msg) -> None:
        try:
            data: dict = json.loads(msg.payload.decode())
        except (json.JSONDecodeError, UnicodeDecodeError):
            logger.warning("MQTT: malformed message on %s", msg.topic)
            return

        self._last_seen = datetime.now(timezone.utc)

        if msg.topic == config.MQTT_TOPIC_MEAS:
            self._esp_online = True
            with _measurement_lock:
                _latest_measurement.update(data)
            if self._on_measurement:
                self._on_measurement(data)
            logger.debug("Measurement: %.1f W total", data.get("power_total", 0))

        elif msg.topic == config.MQTT_TOPIC_CONNECTION:
            self._esp_online = data.get("online", True)
            logger.debug("ESP32 connection status: %s", data)
        else:
            self._relay_status = data.get("ON", True)
            logger.debug("Relais status: %s", data)
    