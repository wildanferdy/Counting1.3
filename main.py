import os
import sys
import multiprocessing

import ttkbootstrap as ttk

from gui.app import VehicleDetectorApp
from utils.env_checks import check_display_environment


if __name__ == "__main__":
    multiprocessing.freeze_support()

    if not check_display_environment():
        sys.exit(1)

    root = ttk.Window(themename="superhero")
    app = VehicleDetectorApp(root)
    root.mainloop()
