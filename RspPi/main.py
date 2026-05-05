# main.py – Raspberry Pi entry point
#
# Threads
# -------
#   main thread  : FreeSimpleGUI event loop
#   MQTT thread  : paho background loop (managed by EspInterface)
#   azure thread : periodic telemetry upload

import logging
import threading
import time

import config
from azure_client import AzureClient
from esp_interface import EspInterface, get_latest_measurement
from gui import Dashboard

logging.basicConfig(
    level=getattr(logging, config.LOG_LEVEL),
    format="%(asctime)s  %(levelname)-8s  %(name)s  %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger("main")


# ── Global service instances ───────────────────────────────────────────────────

esp   = EspInterface()
azure = AzureClient()


# ── Command dispatchers ────────────────────────────────────────────────────────

def _shutdown() -> None:
    """Triggered by GUI button or cloud direct method."""
    logger.info("SHUTDOWN command issued")
    esp.send_command("shutdown")


def _restore() -> None:
    """Triggered by GUI button or cloud direct method."""
    logger.info("RESTORE command issued")
    esp.send_command("restore")


def _cloud_command_handler(method: str, payload: dict) -> dict:
    """Dispatches Azure direct-method calls to local actions."""
    if method == "shutdown":
        _shutdown()
        return {"result": "shutdown_issued"}
    if method == "restore":
        _restore()
        return {"result": "restore_issued"}
    if method == "ping":
        return {"result": "pong", "esp_online": esp.esp_online}
    return {"result": "unknown_method", "method": method}


# ── Azure telemetry thread ─────────────────────────────────────────────────────

def _azure_telemetry_loop() -> None:
    while True:
        meas = get_latest_measurement()
        if meas and azure.connected:
            try:
                azure.send_telemetry(meas)
            except Exception as exc:
                logger.warning("Telemetry send failed: %s", exc)
        time.sleep(config.AZURE_TELEMETRY_INTERVAL_S)


# ── Application entry ──────────────────────────────────────────────────────────

def main() -> None:
    # Start MQTT connection to ESP32
    esp_ok = True
    try:
        esp.connect()
    except Exception as exc:
        logger.warning("ESP connection failed – running offline: %s", exc)
        esp_ok = False

    # Start Azure IoT Hub connection
    azure_ok = True
    try:
        azure.__init__(on_cloud_command=_cloud_command_handler)
        azure.connect()
        t_azure = threading.Thread(target=_azure_telemetry_loop, daemon=True)
        t_azure.start()
    except Exception as exc:
        logger.warning("Azure connection failed – running offline: %s", exc)
        azure_ok = False

    # Build and open GUI
    dashboard = Dashboard(on_shutdown=_shutdown, on_restore=_restore)
    dashboard.open()

    logger.info("GUI started – entering event loop")
    try:
        while True:
            if not dashboard.run_once():
                break

            meas = get_latest_measurement()
            dashboard.update(
                measurement  = meas,
                esp_online   = esp.esp_online,
                azure_online = azure.connected if azure_ok else False,
                last_seen    = esp.last_seen,
            )

    finally:
        dashboard.close()
        esp.disconnect()
        if azure_ok:
            azure.disconnect()
        logger.info("Clean shutdown complete")


if __name__ == "__main__":
    main()