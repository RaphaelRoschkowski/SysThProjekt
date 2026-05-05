# main.py – ESP32 MicroPython entry point
#
# Responsibilities
# ----------------
#  1. Connect to WiFi
#  2. Initialise M90E32AS and relay bank
#  3. Connect to MQTT broker (RPi)
#  4. Publish measurement frames every MEASUREMENT_INTERVAL_MS
#  5. Publish status heartbeat every STATUS_INTERVAL_MS
#  6. Subscribe solar/commands → execute shutdown / restore

import json
import time

import network
from machine import SPI, Pin
from umqtt.simple import MQTTClient

import config
from m90e32as import M90E32AS
from relay_control import RelayBank


# ── WiFi ──────────────────────────────────────────────────────────────────────

def wifi_connect() -> None:
    wlan = network.WLAN(network.STA_IF)
    wlan.active(True)
    if wlan.isconnected():
        return
    print(f"[wifi] connecting to {config.WIFI_SSID} ...")
    wlan.connect(config.WIFI_SSID, config.WIFI_PASSWORD)
    deadline = time.time() + config.WIFI_TIMEOUT_S
    while not wlan.isconnected():
        if time.time() > deadline:
            raise OSError("WiFi timeout")
        time.sleep(0.5)
    print("[wifi] connected –", wlan.ifconfig()[0])


# ── MQTT helpers ──────────────────────────────────────────────────────────────

_mqtt_client: MQTTClient | None = None
_relay: RelayBank | None        = None


def _mqtt_callback(topic: bytes, msg: bytes) -> None:
    """Called by umqtt on every incoming message."""
    if topic != config.MQTT_TOPIC_CMD:
        return
    try:
        payload: dict = json.loads(msg)
    except Exception:
        print("[mqtt] malformed command:", msg)
        return

    cmd = payload.get("command", "")
    print(f"[cmd] received: {cmd}")

    if cmd == "shutdown" and _relay is not None:
        _relay.shutdown()
        _publish_status()

    elif cmd == "restore" and _relay is not None:
        _relay.restore()
        _publish_status()

    elif cmd == "ping":
        _publish_status()


def _publish_status() -> None:
    if _mqtt_client is None or _relay is None:
        return
    payload = json.dumps({
        "online":      True,
        "relay_state": _relay.is_closed,
        "ts":          time.time(),
    })
    _mqtt_client.publish(config.MQTT_TOPIC_STATUS, payload)


def _mqtt_connect() -> MQTTClient:
    client = MQTTClient(
        config.MQTT_CLIENT_ID,
        config.MQTT_BROKER,
        port=config.MQTT_PORT,
        keepalive=config.MQTT_KEEPALIVE,
    )
    client.set_callback(_mqtt_callback)
    client.connect()
    client.subscribe(config.MQTT_TOPIC_CMD)
    print(f"[mqtt] connected to {config.MQTT_BROKER}:{config.MQTT_PORT}")
    return client


# ── Hardware init ─────────────────────────────────────────────────────────────

def _init_meter() -> M90E32AS:
    spi = SPI(
        config.SPI_ID,
        baudrate=config.SPI_BAUD,
        sck=Pin(config.SPI_SCK),
        mosi=Pin(config.SPI_MOSI),
        miso=Pin(config.SPI_MISO),
    )
    cs = Pin(config.CS_PIN, Pin.OUT, value=1)
    meter = M90E32AS(spi, cs)
    meter.init()
    print("[m90e32as] initialised")
    return meter


# ── Main loop ─────────────────────────────────────────────────────────────────

def main() -> None:
    global _mqtt_client, _relay

    wifi_connect()

    meter  = _init_meter()
    _relay = RelayBank()          # starts in safe/open state
    _mqtt_client = _mqtt_connect()

    t_last_meas   = time.ticks_ms()
    t_last_status = time.ticks_ms()

    print("[main] entering measurement loop")
    while True:
        # Non-blocking MQTT receive
        try:
            _mqtt_client.check_msg()
        except OSError:
            print("[mqtt] connection lost – reconnecting ...")
            time.sleep(2)
            try:
                _mqtt_client = _mqtt_connect()
            except OSError as exc:
                print("[mqtt] reconnect failed:", exc)

        now = time.ticks_ms()

        # Publish measurement
        if time.ticks_diff(now, t_last_meas) >= config.MEASUREMENT_INTERVAL_MS:
            t_last_meas = now
            try:
                data = meter.read_all()
                data["relay_state"] = _relay.is_closed
                data["ts"]          = time.time()
                _mqtt_client.publish(config.MQTT_TOPIC_MEAS, json.dumps(data))
            except Exception as exc:
                print("[meas] error:", exc)

        # Publish heartbeat
        if time.ticks_diff(now, t_last_status) >= config.STATUS_INTERVAL_MS:
            t_last_status = now
            _publish_status()

        time.sleep_ms(50)   # yield to prevent watchdog timeout


# ── Entry ─────────────────────────────────────────────────────────────────────
try:
    main()
except Exception as exc:
    import sys
    print("[FATAL]", exc)
    sys.print_exception(exc)
    # hard reset after fatal error so MicroPython auto-restarts
    time.sleep(3)
    import machine
    machine.reset()