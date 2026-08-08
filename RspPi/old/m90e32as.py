# m90e32as.py – M90E32AS energy metering IC driver (MicroPython / SPI)
#
# Register map subset used here:
#   0x01  SoftReset
#   0x07  MMode0       – metering mode
#   0x08  MMode1       – metering mode 1
#   0x09  PStartTh     – active startup power threshold
#   0x0A  QStartTh     – reactive startup power threshold
#   0x0F  CS1          – checksum 1
#   0x51  UrmsL1       – L1 RMS voltage
#   0x52  UrmsL2
#   0x53  UrmsL3
#   0x61  IrmsL1       – L1 RMS current
#   0x62  IrmsL2
#   0x63  IrmsL3
#   0x64  IrmsN
#   0xB1  PmeanL1      – L1 active power (signed)
#   0xB2  PmeanL2
#   0xB3  PmeanL3
#   0xB4  PmeanT       – total active power
#   0xD9  APenergyT    – total accumulated energy (AP)

import time
from machine import SPI, Pin


# ── Register addresses ────────────────────────────────────────────────────────
_REG_SOFTRESET  = 0x00
_REG_MMODE0     = 0x07
_REG_MMODE1     = 0x08
_REG_PSTARTTH   = 0x09
_REG_QSTARTTH   = 0x0A
_REG_CS1        = 0x0F

_REG_URMS_L1    = 0x51
_REG_URMS_L2    = 0x52
_REG_URMS_L3    = 0x53
_REG_IRMS_L1    = 0x61
_REG_IRMS_L2    = 0x62
_REG_IRMS_L3    = 0x63

_REG_PMEAN_L1   = 0xB1
_REG_PMEAN_L2   = 0xB2
_REG_PMEAN_L3   = 0xB3
_REG_PMEAN_T    = 0xB4

_REG_APENERGY_T = 0xD9

# ── Scale factors (LSB → physical unit) ───────────────────────────────────────
# These depend on the external shunt / voltage divider network on the PCB.
# Adjust UGAIN / IGAIN to calibrate against a reference meter.
_VOLTAGE_LSB = 0.0001         # V per LSB  (datasheet §6.3, application-specific)
_CURRENT_LSB = 0.000001       # A per LSB
_POWER_LSB   = 0.00001        # W per LSB
_ENERGY_LSB  = 0.001          # kWh per LSB


class M90E32AS:
    """Minimal driver for M90E32AS three-phase energy metering IC."""

    def __init__(self, spi: SPI, cs: Pin):
        self._spi = spi
        self._cs  = cs
        self._cs.init(Pin.OUT, value=1)

    # ── Initialisation ────────────────────────────────────────────────────────

    def init(self) -> None:
        """Reset and configure the IC for three-phase measurement."""
        self._write(_REG_SOFTRESET, 0x789A)   # software reset sequence
        time.sleep_ms(100)
        # MMode0: 3P4W mode, 50 Hz
        self._write(_REG_MMODE0,   0x0087)
        self._write(_REG_MMODE1,   0x0000)
        self._write(_REG_PSTARTTH, 0x0000)
        self._write(_REG_QSTARTTH, 0x0000)

    # ── Register I/O ─────────────────────────────────────────────────────────

    def _write(self, reg: int, value: int) -> None:
        buf = bytes([reg | 0x80, (value >> 8) & 0xFF, value & 0xFF])
        self._cs(0)
        self._spi.write(buf)
        self._cs(1)
        time.sleep_us(10)

    def _read(self, reg: int) -> int:
        buf = bytearray(2)
        self._cs(0)
        self._spi.write(bytes([reg & 0x7F, 0x00]))
        self._spi.readinto(buf)
        self._cs(1)
        time.sleep_us(10)
        return (buf[0] << 8) | buf[1]

    def _read_signed(self, reg: int) -> int:
        raw = self._read(reg)
        return raw if raw < 0x8000 else raw - 0x10000

    # ── Measurement reads ─────────────────────────────────────────────────────

    def voltage_l1(self) -> float:
        return self._read(_REG_URMS_L1) * _VOLTAGE_LSB

    def voltage_l2(self) -> float:
        return self._read(_REG_URMS_L2) * _VOLTAGE_LSB

    def voltage_l3(self) -> float:
        return self._read(_REG_URMS_L3) * _VOLTAGE_LSB

    def current_l1(self) -> float:
        return self._read(_REG_IRMS_L1) * _CURRENT_LSB

    def current_l2(self) -> float:
        return self._read(_REG_IRMS_L2) * _CURRENT_LSB

    def current_l3(self) -> float:
        return self._read(_REG_IRMS_L3) * _CURRENT_LSB

    def power_l1(self) -> float:
        return self._read_signed(_REG_PMEAN_L1) * _POWER_LSB

    def power_l2(self) -> float:
        return self._read_signed(_REG_PMEAN_L2) * _POWER_LSB

    def power_l3(self) -> float:
        return self._read_signed(_REG_PMEAN_L3) * _POWER_LSB

    def power_total(self) -> float:
        return self._read_signed(_REG_PMEAN_T) * _POWER_LSB

    def energy_total_kwh(self) -> float:
        return self._read(_REG_APENERGY_T) * _ENERGY_LSB

    def read_all(self) -> dict:
        """Return all measurements as a single dict (minimises CS toggles in time)."""
        ul1 = self.voltage_l1()
        ul2 = self.voltage_l2()
        ul3 = self.voltage_l3()
        il1 = self.current_l1()
        il2 = self.current_l2()
        il3 = self.current_l3()
        pl1 = self.power_l1()
        pl2 = self.power_l2()
        pl3 = self.power_l3()
        pt  = self.power_total()
        e   = self.energy_total_kwh()
        return {
            "voltage_l1": ul1,  "voltage_l2": ul2,  "voltage_l3": ul3,
            "current_l1": il1,  "current_l2": il2,  "current_l3": il3,
            "power_l1":   pl1,  "power_l2":   pl2,  "power_l3":   pl3,
            "power_total": pt,
            "energy_total": e,
        }