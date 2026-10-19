"""App-wide theme handling."""
import os
import sys


def _resource_path(*parts):
    base = getattr(sys, "_MEIPASS", None)
    if base:
        return os.path.join(base, "omniture", "resources", *parts)
    here = os.path.dirname(os.path.abspath(__file__))
    return os.path.normpath(os.path.join(here, "resources", *parts))


def apply_theme(app):
    """Apply the bundled dark stylesheet. Silently keeps default on failure."""
    try:
        with open(_resource_path("theme", "dark.qss"), encoding="utf-8") as fh:
            app.setStyleSheet(fh.read())
    except OSError:
        pass
