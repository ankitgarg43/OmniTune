"""OmniTune feature modules.

Each module exposes TITLE, DESCRIPTION, ROADMAP and a create_panel()
factory returning its tab page. Panels are placeholders in v0.1.0 and
grow into full implementations one module at a time.
"""
from PySide6.QtWidgets import QLabel, QListWidget, QVBoxLayout, QWidget


def make_panel(title: str, description: str, roadmap: list) -> QWidget:
    """Build a simple placeholder tab page for a module."""
    widget = QWidget()
    layout = QVBoxLayout(widget)

    heading = QLabel(f"<h2>{title}</h2>")
    desc = QLabel(description)
    desc.setWordWrap(True)
    roadmap_label = QLabel("<b>Planned features</b>")
    roadmap_list = QListWidget()
    roadmap_list.addItems(roadmap)

    layout.addWidget(heading)
    layout.addWidget(desc)
    layout.addWidget(roadmap_label)
    layout.addWidget(roadmap_list)
    layout.addStretch(1)
    return widget
