# relay_control.py – Relay driver (normally-open, BC337 active-HIGH)
#
# Physical default: relay coil de-energised → contacts open → panels disconnected.
# "Restore" (close) energises the coils; "Shutdown" de-energises them.

from machine import Pin
import µ_config


class RelayBank:
    """Controls all three phase relays as a unit.

    Relay is wired as normally-open (NO):
        GPIO HIGH → BC337 ON  → relay coil energised  → contacts CLOSED (panels connected)
        GPIO LOW  → BC337 OFF → relay coil off         → contacts OPEN   (panels disconnected)
    """

    def __init__(self):
        self._pins = [Pin(p, Pin.OUT, value=0) for p in config.RELAY_PINS]
        self._closed = False          # safe default: open on power-up

    # ── Public API ────────────────────────────────────────────────────────────

    def shutdown(self) -> None:
        """Open all relay contacts – rapid shutdown."""
        for pin in self._pins:
            pin.value(0)
        self._closed = False

    def restore(self) -> None:
        """Close all relay contacts – resume normal operation."""
        for pin in self._pins:
            pin.value(1)
        self._closed = True

    @property
    def is_closed(self) -> bool:
        return self._closed