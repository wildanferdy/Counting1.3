# gui/dialogs.py
import tkinter as tk
import ttkbootstrap as ttk
from ttkbootstrap.constants import *
from tkinter import messagebox, filedialog
from ttkbootstrap import Toplevel, Frame, Label, Notebook
from datetime import datetime
import json

DEFAULT_DIALOG_WIDTH = 550
DEFAULT_DIALOG_HEIGHT = 450

class EnhancedSettingsDialog(ttk.Toplevel):
    def __init__(self, parent, current_settings, apply_callback):
        super().__init__(parent)

        self.title("Enhanced Configuration")
        self.transient(parent)
        self.grab_set()

        self.parent = parent
        self.current_settings = current_settings
        self.apply_callback = apply_callback

        screen_width = self.parent.winfo_screenwidth()
        screen_height = self.parent.winfo_screenheight()

        pos_x = (screen_width - DEFAULT_DIALOG_WIDTH) // 2
        pos_y = (screen_height - DEFAULT_DIALOG_HEIGHT) // 2
        self.geometry(f"{DEFAULT_DIALOG_WIDTH}x{DEFAULT_DIALOG_HEIGHT}+{pos_x}+{pos_y}")

        self.setup_ui()

    def setup_ui(self):
        """Setup the main UI with tabs"""
        main_frame = ttk.Frame(self, padding=15)
        main_frame.pack(fill=BOTH, expand=True)

        # Create notebook for tabs
        self.notebook = ttk.Notebook(main_frame)
        self.notebook.pack(fill=BOTH, expand=True, pady=(0, 10))

        # Tab 1: Basic Settings
        self.basic_tab = ttk.Frame(self.notebook)
        self.notebook.add(self.basic_tab, text="Basic Settings")
        self.create_basic_settings()

        # Tab 2: Advanced Filtering
        self.advanced_tab = ttk.Frame(self.notebook)
        self.notebook.add(self.advanced_tab, text="Advanced Filtering")
        self.create_advanced_settings()

        # Tab 3: Class Settings
        self.class_tab = ttk.Frame(self.notebook)
        self.notebook.add(self.class_tab, text="Class Settings")
        self.create_class_settings()

        # Buttons frame
        button_frame = ttk.Frame(main_frame)
        button_frame.pack(fill=X, pady=(10, 0))

        # Left side buttons
        left_buttons = ttk.Frame(button_frame)
        left_buttons.pack(side=LEFT)

        ttk.Button(left_buttons, text="Reset to Defaults", command=self.reset_to_defaults,
                  bootstyle="warning-outline").pack(side=LEFT, padx=(0, 5))

        ttk.Button(left_buttons, text="Import", command=self.import_config,
                  bootstyle="info-outline").pack(side=LEFT, padx=(0, 5))

        ttk.Button(left_buttons, text="Export", command=self.export_config,
                  bootstyle="secondary-outline").pack(side=LEFT)

        # Right side buttons
        right_buttons = ttk.Frame(button_frame)
        right_buttons.pack(side=RIGHT)

        ttk.Button(right_buttons, text="Cancel", command=self.destroy,
                  bootstyle="secondary").pack(side=RIGHT)

        ttk.Button(right_buttons, text="Apply", command=self.apply_settings,
                  bootstyle="success").pack(side=RIGHT, padx=(0, 5))

    def create_basic_settings(self):
        """Create basic settings tab"""
        # Create scrollable frame
        canvas = tk.Canvas(self.basic_tab)
        scrollbar = ttk.Scrollbar(self.basic_tab, orient="vertical", command=canvas.yview)
        scrollable_frame = ttk.Frame(canvas)

        scrollable_frame.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )

        canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)

        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

        frame = scrollable_frame
        row = 0

        # Confidence Threshold
        ttk.Label(frame, text="Detection Confidence Threshold", font=("Arial", 10, "bold")).grid(
            row=row, column=0, columnspan=2, sticky=W, pady=(0, 5))
        row += 1

        ttk.Label(frame, text="Confidence (0.1 - 1.0):").grid(row=row, column=0, sticky=W)
        self.confidence_var = tk.DoubleVar(value=self.current_settings.get('confidence_threshold', 0.5))
        self.confidence_scale = ttk.Scale(frame, from_=0.1, to=1.0, variable=self.confidence_var,
                                         orient=HORIZONTAL, command=self._update_confidence_label,
                                         bootstyle="info")
        self.confidence_scale.grid(row=row, column=1, sticky="ew", padx=(10, 0))
        row += 1

        self.confidence_label = ttk.Label(frame, text=f"{self.confidence_var.get():.2f}")
        self.confidence_label.grid(row=row, column=1, sticky=E, padx=(10, 0), pady=(0, 15))
        row += 1

        # Detection Lines
        ttk.Label(frame, text="Detection Line Configuration", font=("Arial", 10, "bold")).grid(
            row=row, column=0, columnspan=2, sticky=W, pady=(10, 5))
        row += 1

        ttk.Label(frame, text="Line Distance (pixels):").grid(row=row, column=0, sticky=W)
        self.offset_var = tk.IntVar(value=self.current_settings.get('line_offset', 50))
        self.offset_scale = ttk.Scale(frame, from_=10, to=200, variable=self.offset_var,
                                     orient=HORIZONTAL, command=self._update_offset_label,
                                     bootstyle="info")
        self.offset_scale.grid(row=row, column=1, sticky="ew", padx=(10, 0))
        row += 1

        self.offset_label = ttk.Label(frame, text=f"{self.offset_var.get()} px")
        self.offset_label.grid(row=row, column=1, sticky=E, padx=(10, 0), pady=(0, 5))
        row += 1

        # Line Orientation
        ttk.Label(frame, text="Line Orientation:").grid(row=row, column=0, sticky=W)
        orientation_frame = ttk.Frame(frame)
        orientation_frame.grid(row=row, column=1, sticky="w", padx=(10, 0), pady=(0, 15))
        self.orientation_var = tk.StringVar(value=self.current_settings.get('line_orientation', 'Horizontal'))
        ttk.Radiobutton(orientation_frame, text="Horizontal", variable=self.orientation_var,
                       value="Horizontal", bootstyle="info").pack(side=LEFT, padx=(0, 10))
        ttk.Radiobutton(orientation_frame, text="Vertical", variable=self.orientation_var,
                       value="Vertical", bootstyle="info").pack(side=LEFT)
        row += 1

        # Video Playback Speed
        ttk.Label(frame, text="Video Playback Speed", font=("Arial", 10, "bold")).grid(
            row=row, column=0, columnspan=2, sticky=W, pady=(10, 5))
        row += 1

        ttk.Label(frame, text="Speed (0.1x - 5.0x):").grid(row=row, column=0, sticky=W)
        self.speed_var = tk.DoubleVar(value=self.current_settings.get('video_playback_speed', 1.0))
        self.speed_scale = ttk.Scale(frame, from_=0.1, to=5.0, variable=self.speed_var,
                                    orient=HORIZONTAL, command=self._update_speed_label,
                                    bootstyle="info")
        self.speed_scale.grid(row=row, column=1, sticky="ew", padx=(10, 0))
        row += 1

        self.speed_label = ttk.Label(frame, text=f"{self.speed_var.get():.1f}x")
        self.speed_label.grid(row=row, column=1, sticky=E, padx=(10, 0))

        # Configure column weights
        frame.columnconfigure(1, weight=1)

    def create_advanced_settings(self):
        """Create advanced filtering settings tab"""
        # Create scrollable frame
        canvas = tk.Canvas(self.advanced_tab)
        scrollbar = ttk.Scrollbar(self.advanced_tab, orient="vertical", command=canvas.yview)
        scrollable_frame = ttk.Frame(canvas)

        scrollable_frame.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )

        canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)

        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

        frame = scrollable_frame

        # ROI Filter Section
        roi_frame = ttk.LabelFrame(frame, text="Region of Interest (ROI) Filter", padding=15)
        roi_frame.pack(fill=X, pady=(0, 15))

        self.roi_enabled_var = tk.BooleanVar(value=self.current_settings.get('enable_roi_filter', True))
        ttk.Checkbutton(roi_frame, text="Enable ROI Filtering (restrict detection to road area)",
                       variable=self.roi_enabled_var, bootstyle="info").pack(anchor=W, pady=(0, 10))

        # ROI margins
        roi_settings_frame = ttk.Frame(roi_frame)
        roi_settings_frame.pack(fill=X)
        roi_settings_frame.columnconfigure(1, weight=1)

        row = 0
        ttk.Label(roi_settings_frame, text="Top Margin (0.0-0.5):").grid(row=row, column=0, sticky=W, pady=2)
        self.roi_top_var = tk.DoubleVar(value=self.current_settings.get('roi_margin_y_top', 0.3))
        ttk.Scale(roi_settings_frame, from_=0.0, to=0.5, variable=self.roi_top_var,
                 orient=HORIZONTAL, bootstyle="info").grid(row=row, column=1, sticky="ew", padx=(10, 0))
        ttk.Label(roi_settings_frame, text=f"{self.roi_top_var.get():.2f}").grid(row=row, column=2, padx=(5, 0))
        row += 1

        ttk.Label(roi_settings_frame, text="Side Margin (0.0-0.4):").grid(row=row, column=0, sticky=W, pady=2)
        self.roi_side_var = tk.DoubleVar(value=self.current_settings.get('roi_margin_x', 0.1))
        ttk.Scale(roi_settings_frame, from_=0.0, to=0.4, variable=self.roi_side_var,
                 orient=HORIZONTAL, bootstyle="info").grid(row=row, column=1, sticky="ew", padx=(10, 0))
        ttk.Label(roi_settings_frame, text=f"{self.roi_side_var.get():.2f}").grid(row=row, column=2, padx=(5, 0))

        # Size Validation Section
        size_frame = ttk.LabelFrame(frame, text="Object Size Validation", padding=15)
        size_frame.pack(fill=X, pady=(0, 15))

        self.size_enabled_var = tk.BooleanVar(value=self.current_settings.get('enable_size_validation', True))
        ttk.Checkbutton(size_frame, text="Enable Size Validation (filter oversized objects)",
                       variable=self.size_enabled_var, bootstyle="info").pack(anchor=W, pady=(0, 10))

        size_settings_frame = ttk.Frame(size_frame)
        size_settings_frame.pack(fill=X)
        size_settings_frame.columnconfigure(1, weight=1)

        ttk.Label(size_settings_frame, text="Max Object Size Ratio (0.1-0.8):").grid(row=0, column=0, sticky=W)
        self.max_size_var = tk.DoubleVar(value=self.current_settings.get('max_object_size_ratio', 0.3))
        ttk.Scale(size_settings_frame, from_=0.1, to=0.8, variable=self.max_size_var,
                 orient=HORIZONTAL, bootstyle="info").grid(row=0, column=1, sticky="ew", padx=(10, 0))
        self.max_size_label = ttk.Label(size_settings_frame, text=f"{self.max_size_var.get()*100:.1f}%")
        self.max_size_label.grid(row=0, column=2, padx=(5, 0))

        # Movement Validation Section
        movement_frame = ttk.LabelFrame(frame, text="Movement Validation", padding=15)
        movement_frame.pack(fill=X, pady=(0, 15))

        self.movement_enabled_var = tk.BooleanVar(value=self.current_settings.get('enable_movement_validation', True))
        ttk.Checkbutton(movement_frame, text="Enable Movement Validation (filter stationary objects)",
                       variable=self.movement_enabled_var, bootstyle="info").pack(anchor=W, pady=(0, 10))

        movement_settings_frame = ttk.Frame(movement_frame)
        movement_settings_frame.pack(fill=X)
        movement_settings_frame.columnconfigure(1, weight=1)

        row = 0
        ttk.Label(movement_settings_frame, text="Min Movement Threshold:").grid(row=row, column=0, sticky=W, pady=2)
        self.movement_threshold_var = tk.DoubleVar(value=self.current_settings.get('min_movement_threshold', 0.3))
        ttk.Scale(movement_settings_frame, from_=0.1, to=2.0, variable=self.movement_threshold_var,
                 orient=HORIZONTAL, bootstyle="info").grid(row=row, column=1, sticky="ew", padx=(10, 0))
        ttk.Label(movement_settings_frame, text=f"{self.movement_threshold_var.get():.1f} px/frame").grid(row=row, column=2, padx=(5, 0))
        row += 1

        ttk.Label(movement_settings_frame, text="Min Tracking Frames:").grid(row=row, column=0, sticky=W, pady=2)
        self.tracking_frames_var = tk.IntVar(value=self.current_settings.get('min_tracking_frames', 15))
        ttk.Scale(movement_settings_frame, from_=5, to=60, variable=self.tracking_frames_var,
                 orient=HORIZONTAL, bootstyle="info").grid(row=row, column=1, sticky="ew", padx=(10, 0))
        ttk.Label(movement_settings_frame, text=f"{self.tracking_frames_var.get()} frames").grid(row=row, column=2, padx=(5, 0))

        # Additional Filters Section
        additional_frame = ttk.LabelFrame(frame, text="Additional Filters", padding=15)
        additional_frame.pack(fill=X, pady=(0, 15))

        self.aspect_ratio_var = tk.BooleanVar(value=self.current_settings.get('enable_aspect_ratio_validation', True))
        ttk.Checkbutton(additional_frame, text="Enable Aspect Ratio Validation",
                       variable=self.aspect_ratio_var, bootstyle="info").pack(anchor=W, pady=2)

        self.building_filter_var = tk.BooleanVar(value=self.current_settings.get('enable_building_class_filter', True))
        ttk.Checkbutton(additional_frame, text="Filter Building Classes (house, wall, etc.)",
                       variable=self.building_filter_var, bootstyle="info").pack(anchor=W, pady=2)

        # Debug Options
        debug_frame = ttk.LabelFrame(frame, text="Debug Options", padding=15)
        debug_frame.pack(fill=X)

        self.debug_filtering_var = tk.BooleanVar(value=self.current_settings.get('debug_filtering', False))
        ttk.Checkbutton(debug_frame, text="Enable Debug Logging (console output)",
                       variable=self.debug_filtering_var, bootstyle="info").pack(anchor=W, pady=2)

    def create_class_settings(self):
        """Create class-specific settings tab"""
        frame = ttk.Frame(self.class_tab, padding=15)
        frame.pack(fill=BOTH, expand=True)

        ttk.Label(frame, text="Class-Specific Confidence Thresholds", 
                 font=("Arial", 12, "bold")).pack(anchor=W, pady=(0, 15))

        # Create frame for class settings
        class_frame = ttk.Frame(frame)
        class_frame.pack(fill=X)
        class_frame.columnconfigure(1, weight=1)

        self.class_vars = {}
        class_confidence = self.current_settings.get('class_confidence', {})
        
        vehicle_classes = [
            ("Motor", "Motorcycles"),
            ("Gol 1", "Small Cars (Gol I)"),
            ("Gol 2", "Medium Cars (Gol II)"), 
            ("Gol 3", "Large Cars (Gol III)"),
            ("Gol 4", "Trucks (Gol IV)"),
            ("Gol 5", "Large Trucks (Gol V)")
        ]

        row = 0
        for class_key, class_desc in vehicle_classes:
            ttk.Label(class_frame, text=f"{class_desc}:").grid(row=row, column=0, sticky=W, pady=5)
            
            var = tk.DoubleVar(value=class_confidence.get(class_key, 0.5))
            self.class_vars[class_key] = var
            
            scale = ttk.Scale(class_frame, from_=0.1, to=1.0, variable=var,
                             orient=HORIZONTAL, bootstyle="info")
            scale.grid(row=row, column=1, sticky="ew", padx=(10, 10))
            
            label = ttk.Label(class_frame, text=f"{var.get():.2f}")
            label.grid(row=row, column=2, padx=(0, 0))
            
            # Update label when scale changes
            def make_updater(lbl, v):
                return lambda val: lbl.config(text=f"{float(val):.2f}")
            
            scale.config(command=make_updater(label, var))
            row += 1

        # Reset class defaults button
        ttk.Button(class_frame, text="Reset Class Defaults", 
                  command=self.reset_class_defaults,
                  bootstyle="secondary-outline").grid(row=row, column=0, columnspan=3, pady=(20, 0))

    def _update_confidence_label(self, val):
        self.confidence_label.config(text=f"{float(val):.2f}")

    def _update_offset_label(self, val):
        self.offset_label.config(text=f"{int(float(val))} px")

    def _update_speed_label(self, val):
        self.speed_label.config(text=f"{float(val):.1f}x")

    def reset_class_defaults(self):
        """Reset class confidence to defaults"""
        default_class_conf = {
            "Motor": 0.4,
            "Gol 1": 0.5,
            "Gol 2": 0.5, 
            "Gol 3": 0.5,
            "Gol 4": 0.6,
            "Gol 5": 0.6
        }
        
        for class_key, var in self.class_vars.items():
            var.set(default_class_conf.get(class_key, 0.5))

    def reset_to_defaults(self):
        """Reset all settings to defaults"""
        if messagebox.askyesno("Reset Settings", "Reset all settings to defaults?"):
            # Reset basic settings
            self.confidence_var.set(0.5)
            self.offset_var.set(50)
            self.orientation_var.set("Horizontal")
            self.speed_var.set(1.0)
            
            # Reset advanced settings
            self.roi_enabled_var.set(True)
            self.roi_top_var.set(0.3)
            self.roi_side_var.set(0.1)
            self.size_enabled_var.set(True)
            self.max_size_var.set(0.3)
            self.movement_enabled_var.set(True)
            self.movement_threshold_var.set(0.3)
            self.tracking_frames_var.set(15)
            self.aspect_ratio_var.set(True)
            self.building_filter_var.set(True)
            self.debug_filtering_var.set(False)
            
            # Reset class settings
            self.reset_class_defaults()

    def export_config(self):
        """Export current settings to file"""
        file_path = filedialog.asksaveasfilename(
            defaultextension=".json",
            filetypes=[("JSON files", "*.json"), ("All files", "*.*")],
            title="Export Configuration"
        )
        
        if file_path:
            try:
                current_config = self.get_current_settings()
                with open(file_path, 'w') as f:
                    json.dump(current_config, f, indent=4)
                messagebox.showinfo("Export Success", "Configuration exported successfully!")
            except Exception as e:
                messagebox.showerror("Export Error", f"Failed to export: {e}")

    def import_config(self):
        """Import settings from file"""
        file_path = filedialog.askopenfilename(
            filetypes=[("JSON files", "*.json"), ("All files", "*.*")],
            title="Import Configuration"
        )
        
        if file_path:
            try:
                with open(file_path, 'r') as f:
                    imported_settings = json.load(f)
                
                # Apply imported settings to UI
                self.apply_imported_settings(imported_settings)
                messagebox.showinfo("Import Success", "Configuration imported successfully!")
            except Exception as e:
                messagebox.showerror("Import Error", f"Failed to import: {e}")

    def apply_imported_settings(self, settings):
        """Apply imported settings to UI controls"""
        # Basic settings
        if 'confidence_threshold' in settings:
            self.confidence_var.set(settings['confidence_threshold'])
        if 'line_offset' in settings:
            self.offset_var.set(settings['line_offset'])
        if 'line_orientation' in settings:
            self.orientation_var.set(settings['line_orientation'])
        if 'video_playback_speed' in settings:
            self.speed_var.set(settings['video_playback_speed'])
            
        # Advanced settings
        if 'enable_roi_filter' in settings:
            self.roi_enabled_var.set(settings['enable_roi_filter'])
        if 'roi_margin_y_top' in settings:
            self.roi_top_var.set(settings['roi_margin_y_top'])
        if 'roi_margin_x' in settings:
            self.roi_side_var.set(settings['roi_margin_x'])
        if 'enable_size_validation' in settings:
            self.size_enabled_var.set(settings['enable_size_validation'])
        if 'max_object_size_ratio' in settings:
            self.max_size_var.set(settings['max_object_size_ratio'])
        if 'enable_movement_validation' in settings:
            self.movement_enabled_var.set(settings['enable_movement_validation'])
        if 'min_movement_threshold' in settings:
            self.movement_threshold_var.set(settings['min_movement_threshold'])
        if 'min_tracking_frames' in settings:
            self.tracking_frames_var.set(settings['min_tracking_frames'])
            
        # Class settings
        if 'class_confidence' in settings:
            for class_key, confidence in settings['class_confidence'].items():
                if class_key in self.class_vars:
                    self.class_vars[class_key].set(confidence)

    def get_current_settings(self):
        """Get current settings from UI"""
        settings = {}
        
        # Basic settings
        settings['confidence_threshold'] = round(self.confidence_var.get(), 2)
        settings['line_offset'] = int(self.offset_var.get())
        settings['line_orientation'] = self.orientation_var.get()
        settings['video_playback_speed'] = round(self.speed_var.get(), 1)
        
        # Advanced settings
        settings['enable_roi_filter'] = self.roi_enabled_var.get()
        settings['roi_margin_y_top'] = round(self.roi_top_var.get(), 2)
        settings['roi_margin_x'] = round(self.roi_side_var.get(), 2)
        settings['enable_size_validation'] = self.size_enabled_var.get()
        settings['max_object_size_ratio'] = round(self.max_size_var.get(), 2)
        settings['enable_movement_validation'] = self.movement_enabled_var.get()
        settings['min_movement_threshold'] = round(self.movement_threshold_var.get(), 1)
        settings['min_tracking_frames'] = int(self.tracking_frames_var.get())
        settings['enable_aspect_ratio_validation'] = self.aspect_ratio_var.get()
        settings['enable_building_class_filter'] = self.building_filter_var.get()
        settings['debug_filtering'] = self.debug_filtering_var.get()
        
        # Class settings
        settings['class_confidence'] = {}
        for class_key, var in self.class_vars.items():
            settings['class_confidence'][class_key] = round(var.get(), 2)
            
        return settings

    def apply_settings(self):
        """Apply current settings"""
        current_settings = self.get_current_settings()
        
        # Validate settings
        if current_settings['roi_margin_y_top'] >= 0.9:
            messagebox.showwarning("Invalid Setting", "ROI top margin must be less than 0.9")
            return
            
        if current_settings['max_object_size_ratio'] < 0.1:
            messagebox.showwarning("Invalid Setting", "Max object size ratio must be at least 0.1")
            return
        
        # Apply settings through callback
        self.apply_callback(current_settings)
        self.destroy()


# Keep the original dialogs for backward compatibility
class SettingsDialog(ttk.Toplevel):
    """Simple settings dialog for basic configuration"""
    def __init__(self, parent, current_settings, apply_callback):
        super().__init__(parent)
        # Redirect to enhanced dialog
        self.destroy()
        EnhancedSettingsDialog(parent, current_settings, apply_callback)


class TimeDialog(Toplevel):
    def __init__(self, parent, current_timestamp_user, apply_callback):
        super().__init__(parent)
        self.title("Set Time and Date")
        self.transient(parent)
        self.grab_set()

        self.parent = parent
        self.current_timestamp_user = current_timestamp_user
        self.apply_callback = apply_callback

        screen_width = self.parent.winfo_screenwidth()
        screen_height = self.parent.winfo_screenheight()
        
        DEFAULT_DIALOG_HEIGHT = 200

        pos_x = (screen_width - DEFAULT_DIALOG_WIDTH) // 2
        pos_y = (screen_height - DEFAULT_DIALOG_HEIGHT) // 2
        self.geometry(f"{DEFAULT_DIALOG_WIDTH}x{DEFAULT_DIALOG_HEIGHT}+{pos_x}+{pos_y}")

        frame = Frame(self, padding=15)
        frame.pack(fill="both", expand=True)

        frame.columnconfigure(0, weight=1)
        frame.columnconfigure(1, weight=3)

        row_counter = 0

        # --- Tanggal ---
        Label(frame, text="Select Date (DD/MM/YYYY):").grid(row=row_counter, column=0, sticky="w")
        date_frame = Frame(frame)
        date_frame.grid(row=row_counter, column=1, sticky="ew", pady=(0, 10))
        row_counter += 1

        now = datetime.now()

        self.day_var = tk.StringVar()
        self.month_var = tk.StringVar()
        self.year_var = tk.StringVar()

        days = [f"{i:02d}" for i in range(1, 32)]
        months = [f"{i:02d}" for i in range(1, 13)]
        years = [str(y) for y in range(now.year - 10, now.year + 11)]

        # Default value
        if self.current_timestamp_user:
            try:
                dt_obj = datetime.strptime(self.current_timestamp_user, "%Y-%m-%d %H:%M:%S")
            except ValueError:
                dt_obj = now
        else:
            dt_obj = now

        self.day_var.set(f"{dt_obj.day:02d}")
        self.month_var.set(f"{dt_obj.month:02d}")
        self.year_var.set(str(dt_obj.year))

        ttk.Combobox(date_frame, textvariable=self.day_var, values=days, width=4, bootstyle="info").pack(side="left", padx=2)
        ttk.Combobox(date_frame, textvariable=self.month_var, values=months, width=4, bootstyle="info").pack(side="left", padx=2)
        ttk.Combobox(date_frame, textvariable=self.year_var, values=years, width=6, bootstyle="info").pack(side="left", padx=2)

        # --- Jam ---
        ttk.Label(frame, text="Set Time (HH:MM):").grid(row=row_counter, column=0, sticky="w")
        time_frame = Frame(frame)
        time_frame.grid(row=row_counter, column=1, sticky="w", pady=(0, 10))
        row_counter += 1

        self.hour_var = tk.StringVar(value=f"{dt_obj.hour:02d}")
        self.minute_var = tk.StringVar(value=f"{dt_obj.minute:02d}")

        ttk.Entry(time_frame, textvariable=self.hour_var, width=3).pack(side="left")
        ttk.Label(time_frame, text=":").pack(side="left")
        ttk.Entry(time_frame, textvariable=self.minute_var, width=3).pack(side="left")

        # --- Tombol Apply ---
        ttk.Button(frame, text="Apply", command=self._on_apply, bootstyle="success", width=25).grid(
            row=row_counter, column=0, columnspan=2, pady=(10, 0)
        )

    def _on_apply(self):
        try:
            day = int(self.day_var.get())
            month = int(self.month_var.get())
            year = int(self.year_var.get())
            hour = int(self.hour_var.get())
            minute = int(self.minute_var.get())

            if not (1 <= day <= 31 and 1 <= month <= 12 and 0 <= hour <= 23 and 0 <= minute <= 59):
                raise ValueError("Invalid date or time input")

            result_dt = datetime(year, month, day, hour, minute)
            self.apply_callback(result_dt.strftime("%Y-%m-%d %H:%M:%S"))
            self.destroy()
        except Exception as e:
            messagebox.showerror("Error", f"Invalid input: {e}")