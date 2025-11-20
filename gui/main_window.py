import tkinter as tk
from tkinter import messagebox
import ttkbootstrap as ttk
from ttkbootstrap.constants import *
import pandas as pd
from multiprocessing import Process, Queue, Event
import json
import sys
import os

from .ui_components import UIComponents
from .video_handler import VideoHandler
from .detection_manager import DetectionManager
from .menu_manager import MenuManager
from .data_manager import DataManager
from utils.config import ConfigManager
from utils.constants import MAX_DISPLAY_WIDTH, MAX_DISPLAY_HEIGHT
from core.exporter import save_to_excel


class VehicleDetectorApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Vehicle Detection System [Multiprocess & Stabilized]")
        
        # Screen setup
        self.screen_width = self.root.winfo_screenwidth()
        self.screen_height = self.root.winfo_screenheight()
        self.root.geometry(f"{self.screen_width}x{self.screen_height}+0+0")

        # Initialize managers
        self.config_manager = ConfigManager()
        self.settings = self.config_manager.load_config()
        
        # Initialize components
        self.ui_components = UIComponents(self.root)
        self.video_handler = VideoHandler(self)
        self.detection_manager = DetectionManager(self)
        self.menu_manager = MenuManager(self)
        self.data_manager = DataManager(self)
        
        # Setup UI
        self.create_widgets()
        self.create_menu()
        self.update_gui_display()
        
        # Window close protocol
        self.root.protocol("WM_DELETE_WINDOW", self.on_closing)

    def create_widgets(self):
        """Create main UI widgets"""
        self.ui_components.create_main_layout()
        self.ui_components.setup_callbacks(self)

    def create_menu(self):
        """Create application menu"""
        self.menu_manager.create_menu()

    def update_gui_display(self):
        """Update GUI display with current data"""
        self.data_manager.update_gui_display()

    def on_closing(self):
        """Handle application closing"""
        if messagebox.askokcancel("Quit", "Do you want to quit?"):
            if self.detection_manager.running or self.detection_manager.is_loading:
                self.detection_manager.stop_detection()
            self.root.after(500, self._force_exit)

    def _force_exit(self):
        """Force exit the application"""
        try:
            self.detection_manager.cleanup()
            self.video_handler.cleanup()
            self.root.quit()
            self.root.destroy()
            sys.exit(0)
        except Exception as e:
            print(f"Error during force exit: {e}")
            sys.exit(1)

    def save_to_excel(self):
        """Save data to Excel file"""
        save_to_excel(
            self.data_manager.df, 
            self.settings, 
            self.data_manager.vehicle_counts
        )