# gui.py – Solar IoT dashboard  (FreeSimpleGUI)

import logging
from datetime import datetime
from typing import Optional

import FreeSimpleGUI as sg

import config

logger = logging.getLogger(__name__)

# ── Colour palette ─────────────────────────────────────────────────────────────
BG          = "#1a1d23"
PANEL_BG    = "#22262f"
ACCENT      = "#f0a500"
ACCENT2     = "#3d9be9"
TEXT_MAIN   = "#e8eaf0"
TEXT_DIM    = "#7a7f8e"
GREEN       = "#4caf7d"
RED         = "#e05c5c"
FONT_MAIN   = ("Segoe UI", 11)
FONT_LABEL  = ("Segoe UI", 9)
FONT_BIG    = ("Segoe UI Semibold", 22)
FONT_MED    = ("Segoe UI Semibold", 14)
FONT_TITLE  = ("Segoe UI Semibold", 10)

sg.theme("DarkGrey13")
sg.set_options(font=FONT_MAIN, background_color=BG, text_color=TEXT_MAIN)


# ── Layout helpers ─────────────────────────────────────────────────────────────

def _phase_column(phase: str) -> sg.Column:
    """Single-phase metric block (U / I / P)."""
    lbl = sg.Text(f"Phase {phase}", font=FONT_TITLE, text_color=TEXT_DIM,
                  background_color=PANEL_BG)
    u   = _metric_pair(f"U_{phase}", "V",  f"voltage_{phase.lower()}")
    i   = _metric_pair(f"I_{phase}", "A",  f"current_{phase.lower()}")
    p   = _metric_pair(f"P_{phase}", "W",  f"power_{phase.lower()}")
    return sg.Column(
        [[lbl], [u], [i], [p]],
        background_color=PANEL_BG,
        pad=(8, 8),
        expand_x=True,
    )


def _metric_pair(key: str, unit: str, data_key: str) -> sg.Column:
    """Label + value in one row."""
    return sg.Column(
        [[
            sg.Text(key, font=FONT_LABEL, text_color=TEXT_DIM,
                    size=(6, 1), background_color=PANEL_BG),
            sg.Text("---", key=f"-{data_key}-", font=FONT_MED,
                    text_color=TEXT_MAIN, size=(8, 1),
                    background_color=PANEL_BG, justification="right"),
            sg.Text(unit, font=FONT_LABEL, text_color=TEXT_DIM,
                    background_color=PANEL_BG),
        ]],
        background_color=PANEL_BG, pad=(2, 1),
    )


def _status_led(key: str, label: str) -> list:
    """Coloured circle indicator + label."""
    return [
        sg.Text("●", key=key, text_color=TEXT_DIM, font=("Segoe UI", 14),
                background_color=BG),
        sg.Text(label, font=FONT_LABEL, text_color=TEXT_DIM, background_color=BG),
    ]


# ── Main layout ────────────────────────────────────────────────────────────────

def build_layout() -> list:
    menu_def = [
        ['Settings', ['MQTT Settings', 'Azure Settings', '---', 'Exit']],
    ]

    header = [
        sg.Text("☀  Solar IoT Monitor", font=("Segoe UI Semibold", 16),
                text_color=ACCENT, background_color=BG, expand_x=True),
        sg.Text("", key="-CLOCK-", font=FONT_LABEL, text_color=TEXT_DIM,
                background_color=BG, justification="right"),
    ]

    # ── Total power ──────────────────────────────────────────────────────────
    total_panel = sg.Frame(
        "", border_width=0,
        background_color=PANEL_BG,
        layout=[[
            sg.Column([
                [sg.Text("Gesamtleistung", font=FONT_LABEL, text_color=TEXT_DIM,
                         background_color=PANEL_BG)],
                [sg.Text("---", key="-power_total-", font=FONT_BIG,
                         text_color=ACCENT, background_color=PANEL_BG)],
                [sg.Text("W", font=FONT_LABEL, text_color=TEXT_DIM,
                         background_color=PANEL_BG)],
            ], background_color=PANEL_BG, expand_x=True),
            sg.Column([
                [sg.Text("Energie (gesamt)", font=FONT_LABEL, text_color=TEXT_DIM,
                         background_color=PANEL_BG)],
                [sg.Text("---", key="-energy_total-", font=FONT_MED,
                         text_color=ACCENT2, background_color=PANEL_BG)],
                [sg.Text("kWh", font=FONT_LABEL, text_color=TEXT_DIM,
                         background_color=PANEL_BG)],
            ], background_color=PANEL_BG, pad=(20, 0)),
        ]],
        pad=(0, 4),
        expand_x=True,
    )

    # ── Phase columns ────────────────────────────────────────────────────────
    phases_row = [_phase_column("L1"), _phase_column("L2"), _phase_column("L3")]

    # ── Control panel ────────────────────────────────────────────────────────
    relay_state_txt = sg.Text(
        "Relais: UNBEKANNT", key="-RELAY_STATUS-",
        font=FONT_MED, text_color=TEXT_DIM, background_color=PANEL_BG,
        expand_x=True,
    )
    btn_shutdown = sg.Button(
        "⚡  RAPID SHUTDOWN", key="-BTN_SHUTDOWN-",
        button_color=(BG, RED), font=("Segoe UI Semibold", 12),
        size=(22, 2), border_width=0,
        mouseover_colors=(BG, "#ff7777"),
    )
    btn_restore = sg.Button(
        "↺  Anlage zuschalten", key="-BTN_RESTORE-",
        button_color=(BG, GREEN), font=FONT_MAIN,
        size=(22, 1), border_width=0,
        mouseover_colors=(BG, "#6dd49a"),
    )
    control_panel = sg.Frame(
        "", border_width=0,
        background_color=PANEL_BG,
        layout=[
            [relay_state_txt],
            [sg.HSeparator(color=BG, pad=(0, 6))],
            [btn_shutdown],
            [sg.Text("", background_color=PANEL_BG, pad=(0, 2))],
            [btn_restore],
        ],
        pad=(0, 4),
        expand_x=False,
    )

    # ── Status bar ───────────────────────────────────────────────────────────
    status_bar = [
        *_status_led("-LED_ESP-",   "ESP32"),
        sg.Text("|", text_color=TEXT_DIM, background_color=BG, pad=(6, 0)),
        *_status_led("-LED_AZURE-", "Azure"),
        sg.Push(background_color=BG),
        sg.Text("Letzte Messung:", font=FONT_LABEL, text_color=TEXT_DIM,
                background_color=BG),
        sg.Text("---", key="-LAST_SEEN-", font=FONT_LABEL,
                text_color=TEXT_DIM, background_color=BG),
    ]

    return [
        [sg.Menu(menu_def, background_color=BG, text_color=TEXT_MAIN)],
        [sg.Column([header], background_color=BG, expand_x=True, pad=(0, 4))],
        [total_panel],
        [sg.Column([phases_row], background_color=BG, expand_x=True)],
        [sg.Column(
            [[control_panel]],
            background_color=BG, expand_x=True, element_justification="center",
        )],
        [sg.HSeparator(color=PANEL_BG, pad=(0, 6))],
        [sg.Column([status_bar], background_color=BG, expand_x=True)],
    ]


# ── Dashboard class ────────────────────────────────────────────────────────────

class Dashboard:
    """Wraps the FreeSimpleGUI window and update logic."""

    def __init__(self, on_shutdown: callable, on_restore: callable):
        self._on_shutdown = on_shutdown
        self._on_restore  = on_restore
        self._window: Optional[sg.Window] = None

    def open(self) -> None:
        self._window = sg.Window(
            "Solar IoT Monitor",
            build_layout(),
            background_color=BG,
            finalize=True,
            resizable=True,
            size=(860, 560),
            margins=(16, 12),
        )

    def run_once(self) -> bool:
        """Process one event cycle.  Returns False if window should close."""
        if self._window is None:
            return False

        event, _ = self._window.read(timeout=config.GUI_REFRESH_MS)

        if event in (sg.WIN_CLOSED, "Exit"):
            return False

        if event == "-BTN_SHUTDOWN-":
            confirmed = sg.popup_yes_no(
                "Rapid Shutdown auslösen?\n\nAlle Paneele werden sofort getrennt.",
                title="Bestätigung",
                background_color=PANEL_BG,
                text_color=TEXT_MAIN,
                button_color=(BG, RED),
                font=FONT_MAIN,
                keep_on_top=True,
            )
            if confirmed == "Yes":
                self._on_shutdown()

        if event == "-BTN_RESTORE-":
            self._on_restore()

        if event == "MQTT Settings":
            host = sg.popup_get_text("MQTT Broker Host:", default_text=config.MQTT_BROKER_HOST, title="MQTT Settings")
            if host:
                port_str = sg.popup_get_text("MQTT Broker Port:", default_text=str(config.MQTT_BROKER_PORT), title="MQTT Settings")
                if port_str:
                    try:
                        port = int(port_str)
                        # Here, you could update config or reconnect
                        sg.popup(f"MQTT settings updated: {host}:{port}", title="Settings")
                    except ValueError:
                        sg.popup("Invalid port number", title="Error")

        if event == "Azure Settings":
            conn_str = sg.popup_get_text("Azure Connection String:", default_text=config.AZURE_CONNECTION_STRING, title="Azure Settings")
            if conn_str:
                # Here, you could update config or reconnect
                sg.popup("Azure settings updated", title="Settings")

        return True

    def update(
        self,
        measurement: dict,
        esp_online: bool,
        relay_status: Optional[bool],
        azure_online: bool,
        last_seen: Optional[datetime],
    ) -> None:
        """Push fresh data into GUI elements (call from main thread)."""
        if self._window is None:
            return
        w = self._window

        # Clock
        w["-CLOCK-"].update(datetime.now().strftime("%d.%m.%Y  %H:%M:%S"))

        # Total power / energy
        _fmt(w, "-power_total-",  measurement.get("power_total"),  ".1f")
        _fmt(w, "-energy_total-", measurement.get("energy_total"), ".2f")

        # Per-phase values
        for ph, tag in (("l1", "L1"), ("l2", "L2"), ("l3", "L3")):
            _fmt(w, f"-voltage_{ph}-", measurement.get(f"voltage_{ph}"), ".1f")
            _fmt(w, f"-current_{ph}-", measurement.get(f"current_{ph}"), ".2f")
            _fmt(w, f"-power_{ph}-",   measurement.get(f"power_{ph}"),   ".1f")

        # Relay
        relay_on: Optional[bool] = relay_status
        if relay_on is True:
            w["-RELAY_STATUS-"].update("Relais: GESCHLOSSEN  ✔", text_color=GREEN)
        elif relay_on is False:
            w["-RELAY_STATUS-"].update("Relais: OFFEN  (Anlage getrennt)", text_color=RED)
        else:
            w["-RELAY_STATUS-"].update("Relais: UNBEKANNT", text_color=TEXT_DIM)

        # Status LEDs
        w["-LED_ESP-"].update(text_color=GREEN if esp_online else RED)
        w["-LED_AZURE-"].update(text_color=GREEN if azure_online else RED)

        # Last seen
        if last_seen:
            w["-LAST_SEEN-"].update(last_seen.strftime("%H:%M:%S"))

    def close(self) -> None:
        if self._window:
            self._window.close()
            self._window = None


# ── Utility ───────────────────────────────────────────────────────────────────

def _fmt(window: sg.Window, key: str, value, fmt: str) -> None:
    if value is None:
        window[key].update("---")
    else:
        window[key].update(f"{value:{fmt}}")