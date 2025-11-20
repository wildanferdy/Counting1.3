import ttkbootstrap as ttk
import multiprocessing

from gui.app import VehicleDetectorApp

if __name__ == "__main__":
    multiprocessing.freeze_support()

    root = ttk.Window(themename="superhero")
    app = VehicleDetectorApp(root)
    root.mainloop()