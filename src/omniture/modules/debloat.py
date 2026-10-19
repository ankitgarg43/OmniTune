"""Debloat & tweaks module.

Concept inspired by Win11Debloat (MIT):
https://github.com/Raphire/Win11Debloat
Clean-room reimplementation — no Win11Debloat code is used.
"""
from PySide6.QtWidgets import QWidget

from . import make_panel

TITLE = "Debloat"
DESCRIPTION = (
    "Remove pre-installed apps, disable telemetry and ads, and apply "
    "curated Windows tweaks — always with a restore point and a full "
    "undo path before anything changes."
)
ROADMAP = [
    "Pre-installed app removal (per-app picker + curated defaults)",
    "Telemetry, diagnostic data & ad/tracking toggles",
    "Windows tweaks: Explorer, taskbar, Start menu, search",
    "Copilot / Recall / AI feature controls",
    "System restore point before applying changes",
    "One-click revert of every applied change",
]


def create_panel() -> QWidget:
    return make_panel(TITLE, DESCRIPTION, ROADMAP)
