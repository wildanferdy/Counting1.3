"""Environment validation helpers for launching the GUI app."""
from __future__ import annotations

import os
import sys


def check_display_environment() -> bool:
    """Ensure a display server is available before creating Tk windows.

    Returns:
        bool: True if GUI can be launched, False otherwise.
    """
    if sys.platform.startswith("linux") and not os.environ.get("DISPLAY"):
        print(
            "ERROR: Tidak ada DISPLAY yang tersedia. Jalankan di mesin dengan server grafis, "
            "set DISPLAY, atau gunakan virtual display (mis. xvfb)."
        )
        return False
    return True
