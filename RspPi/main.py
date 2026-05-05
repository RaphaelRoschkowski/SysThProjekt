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
from datetime import datetime, timezone

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


# ── Connection retry logic ────────────────────────────────────────────────────

def _connect_with_retries(name: str, connect_fn, retries: int, delay: int) -> bool:
    """Attempt to connect with exponential backoff retries.
    
    Parameters
    ----------
    name : str
        Service name for logging
    connect_fn : callable
        Function that performs the connection (raises on failure)
    retries : int
        Number of retry attempts
    delay : int
        Delay in seconds between retries
        
    Returns
    -------
    bool
        True if connection succeeded, False if all retries exhausted
    """
    for attempt in range(1, retries + 1):
        try:
            logger.info("%s: connection attempt %d/%d", name, attempt, retries)
            connect_fn()
            logger.info("%s: connected successfully", name)
            return True
        except Exception as exc:
            if attempt < retries:
                logger.warning("%s: attempt %d failed (%s) – retrying in %ds",
                              name, attempt, exc, delay)
                time.sleep(delay)
            else:
                logger.error("%s: all %d connection attempts failed (%s)",
                           name, retries, exc)
                return False
    return False


# ── Safety watchdog (monitors ESP heartbeat) ──────────────────────────────────

_emergency_stop_event = threading.Event()

def _watchdog_loop() -> None:
    """Monitor ESP heartbeat and trigger emergency shutdown if lost."""
    while not _emergency_stop_event.is_set():
        if esp.last_seen is not None:
            time_since_heartbeat = (datetime.now(timezone.utc) - esp.last_seen).total_seconds()
            
            if time_since_heartbeat > config.ESP_HEARTBEAT_TIMEOUT_S:
                logger.critical(
                    "SAFETY: ESP heartbeat lost (%.1fs timeout exceeded) – EMERGENCY SHUTDOWN",
                    time_since_heartbeat
                )
                _emergency_stop_event.set()
                break
        
        time.sleep(1)  # Check heartbeat every second


# ── Application entry ──────────────────────────────────────────────────────────

def main() -> None:
    # Start MQTT connection to ESP32 with retries (CRITICAL for safety)
    esp_ok = _connect_with_retries(
        "ESP32 MQTT",
        esp.connect,
        config.ESP_CONNECTION_RETRIES,
        config.ESP_CONNECTION_RETRY_DELAY_S
    )
    
    if not esp_ok:
        # CRITICAL: ESP connection failed – cannot safely operate
        logger.critical(
            "CRITICAL: ESP connection failed after %d retries. "
            "Sending emergency shutdown command to open relays.",
            config.ESP_CONNECTION_RETRIES
        )
        try:
            # Try to send shutdown command one more time to open relays
            esp.connect()
            esp.send_command("shutdown")
            time.sleep(config.EMERGENCY_SHUTDOWN_COOLDOWN_S)
        except Exception as exc:
            logger.critical("Failed to send emergency shutdown: %s", exc)
        logger.critical("Exiting due to critical ESP connection failure")
        return

    # Start safety watchdog thread (monitors ESP heartbeat)
    _emergency_stop_event.clear()
    t_watchdog = threading.Thread(target=_watchdog_loop, daemon=True)
    t_watchdog.start()
    logger.info("Safety watchdog started (timeout: %ds)",
               config.ESP_HEARTBEAT_TIMEOUT_S)

    # Start Azure IoT Hub connection with retries (non-critical)
    azure_ok = _connect_with_retries(
        "Azure IoT Hub",
        lambda: azure.__init__(on_cloud_command=_cloud_command_handler) or azure.connect(),
        config.AZURE_CONNECTION_RETRIES,
        config.AZURE_CONNECTION_RETRY_DELAY_S
    )
    
    if azure_ok:
        t_azure = threading.Thread(target=_azure_telemetry_loop, daemon=True)
        t_azure.start()
        logger.info("Azure telemetry thread started")
    else:
        logger.warning("Azure connection failed – running in offline mode")

    # Build and open GUI
    dashboard = Dashboard(on_shutdown=_shutdown, on_restore=_restore)
    dashboard.open()

    logger.info("GUI started – entering event loop")
    try:
        while True:
            # Check for emergency stop signal (from watchdog)
            if _emergency_stop_event.is_set():
                logger.critical("EMERGENCY STOP triggered – performing safe shutdown")
                try:
                    esp.send_command("shutdown")
                except Exception as exc:
                    logger.warning("Failed to send shutdown command: %s", exc)
                break
            
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