import tkinter as tk
import ttkbootstrap as ttk
from ttkbootstrap.constants import *


class UIComponents:
    def __init__(self, root):
        self.root = root
        self.video_label = None
        self.trackbar = None
        self.time_label = None
        self.start_stop_button = None
        self.tree = None
        self.trackbar_var = tk.DoubleVar()

    def create_main_layout(self):
        """Create the main application layout"""
        self.main_frame = ttk.Frame(self.root, padding="10")
        self.main_frame.pack(fill=BOTH, expand=True)
        
        # Left and right frames
        left_frame = ttk.Frame(self.main_frame)
        left_frame.pack(side=LEFT, fill=BOTH, expand=True, padx=(0, 10))
        
        right_frame = ttk.Frame(self.main_frame, width=500)
        right_frame.pack(side=RIGHT, fill=Y, expand=False)
        right_frame.pack_propagate(False)

        # Create video area
        self._create_video_area(left_frame)
        
        # Create trackbar
        self._create_trackbar(left_frame)
        
        # Create control area
        self._create_control_area(left_frame)
        
        # Create data area
        self._create_data_area(right_frame)

    def _create_video_area(self, parent):
        """Create video display area"""
        video_container = ttk.Frame(parent, bootstyle="secondary")
        video_container.pack(fill=BOTH, expand=True)
        video_container.grid_rowconfigure(0, weight=1)
        video_container.grid_columnconfigure(0, weight=1)
        
        self.video_label = ttk.Label(
            video_container, 
            text="\n\nLoad Video or Use Webcam to Start\n", 
            anchor=CENTER,
            bootstyle="inverse-secondary"
        )
        self.video_label.grid(row=0, column=0, sticky="nsew")

    def _create_trackbar(self, parent):
        """Create video trackbar"""
        trackbar_frame = ttk.Frame(parent)
        trackbar_frame.pack(fill=X)

        self.trackbar = ttk.Scale(
            trackbar_frame,
            from_=0,
            to=0,
            orient=tk.HORIZONTAL,
            variable=self.trackbar_var
        )
        self.trackbar.pack(fill=X, side=LEFT, expand=True, padx=(10, 5))

        self.time_label = ttk.Label(trackbar_frame, text="00:00 / 00:00")
        # self.time_label.pack(side=RIGHT, padx=(5, 10), pady=(0, 0))

    def _create_control_area(self, parent):
        """Create control buttons area"""
        control_area = ttk.Frame(parent)
        control_area.pack(fill=X, pady=5)

        
        self.start_stop_button = ttk.Button(
            control_area, 
            text="Start Detection", 
            bootstyle="success", 
            state="disabled"
        )
        self.start_stop_button.pack(side=LEFT, fill=X, expand=True, pady=(10, 15))

    def _create_data_area(self, parent):
        """Create data display area"""
        data_frame = ttk.LabelFrame(parent, text="Counting Data", padding=10)
        data_frame.pack(fill=BOTH, expand=True, pady=(0, 10))

        # Frame untuk Treeview
        tree_frame = ttk.Frame(data_frame)
        tree_frame.pack(fill=BOTH, expand=True)

        # Treeview dan kolom
        columns = ("Timestamp", "ID", "Class", "Direction")
        self.tree = ttk.Treeview(
            tree_frame, 
            columns=columns, 
            show='headings', 
            bootstyle="primary"
        )

        # Configure columns
        self.tree.heading("Timestamp", text="Time")
        self.tree.column("Timestamp", width=160, anchor=W)
        self.tree.heading("ID", text="ID")
        self.tree.column("ID", width=40, anchor=CENTER)
        self.tree.heading("Class", text="Class")
        self.tree.column("Class", width=120, anchor=CENTER)
        self.tree.heading("Direction", text="Direction")
        self.tree.column("Direction", width=100, anchor=CENTER)

        # Scrollbar
        scrollbar = ttk.Scrollbar(tree_frame, orient=VERTICAL, command=self.tree.yview)
        self.tree.configure(yscrollcommand=scrollbar.set)

        # Pack tree and scrollbar
        self.tree.pack(side=LEFT, fill=BOTH, expand=True)
        scrollbar.pack(side=RIGHT, fill=Y)

        # Button frame
        self._create_data_buttons(data_frame)

    def _create_data_buttons(self, parent):
        """Create data management buttons"""
        button_frame = ttk.Frame(parent)
        button_frame.pack(fill=X, pady=(10, 0))

        button_frame.columnconfigure(0, weight=1)
        button_frame.columnconfigure(1, weight=1)

        btn_refresh = ttk.Button(
            button_frame,
            text="Refresh",
            bootstyle="success-outline"
        )
        btn_refresh.grid(row=0, column=0, sticky=NSEW, padx=(0, 3))

        self.btn_save_data = ttk.Button(
            button_frame,
            text="Save Data",
            bootstyle="warning-outline"
        )
        self.btn_save_data.grid(row=0, column=1, sticky=NSEW, padx=(3, 0))

    def setup_callbacks(self, app):
        """Setup UI callbacks"""
        self.video_label.bind("<Button-1>", app.video_handler.set_detection_line)
        self.start_stop_button.config(command=app.detection_manager.toggle_detection)
        self.btn_save_data.config(command=app.save_to_excel)
        
        # # Trackbar callbacks
        # self.trackbar.config(command=app.video_handler.on_trackbar_drag)
        # self.trackbar.bind("<ButtonPress-1>", app.video_handler.on_trackbar_press)
        # self.trackbar.bind("<ButtonRelease-1>", app.video_handler.on_trackbar_release)