# azure_client.py – Azure IoT Hub interface (telemetry + cloud commands)

import json
import logging
import threading
from datetime import datetime, timezone
from typing import Callable, Optional

from azure.iot.device import IoTHubDeviceClient, Message, MethodResponse

import config

logger = logging.getLogger(__name__)


class AzureClient:
    """Wraps azure-iot-device SDK.

    Responsibilities
    ----------------
    - Send measurement telemetry to IoT Hub (D2C).
    - Receive direct-method calls from the cloud (C2D) and dispatch them
      to a registered handler.
    """

    def __init__(self, on_cloud_command: Optional[Callable[[str, dict], dict]] = None):
        """
        Parameters
        ----------
        on_cloud_command:
            Callback invoked on every incoming direct-method call.
            Signature: (method_name: str, payload: dict) -> response_payload: dict
        """
        self._client: Optional[IoTHubDeviceClient] = None
        self._on_cloud_command = on_cloud_command
        self._connected = False
        self._lock = threading.Lock()

    # ── Connection lifecycle ──────────────────────────────────────────────────

    def connect(self) -> None:
        """Create client and open connection to Azure IoT Hub."""
        self._client = IoTHubDeviceClient.create_from_connection_string(
            config.AZURE_CONNECTION_STRING
        )
        if self._on_cloud_command:
            self._client.on_method_request_received = self._method_handler
        self._client.connect()
        self._connected = True
        logger.info("Azure IoT Hub: connected")

    def disconnect(self) -> None:
        if self._client and self._connected:
            self._client.disconnect()
            self._connected = False
            logger.info("Azure IoT Hub: disconnected")

    @property
    def connected(self) -> bool:
        return self._connected

    # ── Telemetry ─────────────────────────────────────────────────────────────

    def send_telemetry(self, measurement: dict) -> None:
        """Serialize measurement dict and send as IoT Hub message."""
        if not self._connected:
            logger.warning("send_telemetry skipped – not connected")
            return

        payload = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            **measurement,
        }
        msg = Message(json.dumps(payload))
        msg.content_encoding = "utf-8"
        msg.content_type = "application/json"

        with self._lock:
            self._client.send_message(msg)
        logger.debug("Telemetry sent: %s W total", measurement.get("power_total", "?"))

    # ── Direct-method handler (cloud → device) ────────────────────────────────

    def _method_handler(self, method_request) -> None:
        """Called by SDK thread on every incoming direct method."""
        name = method_request.name
        try:
            payload = json.loads(method_request.payload) if method_request.payload else {}
        except json.JSONDecodeError:
            payload = {}

        logger.info("Cloud method received: %s  payload=%s", name, payload)

        if self._on_cloud_command:
            result = self._on_cloud_command(name, payload)
        else:
            result = {"status": "no_handler"}

        response = MethodResponse.create_from_method_request(
            method_request, status=200, payload=result
        )
        self._client.send_method_response(response)