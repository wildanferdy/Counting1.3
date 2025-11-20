# gui/dialogs/line_distance_calculator.py
import tkinter as tk
import ttkbootstrap as ttk
from ttkbootstrap.constants import *
from tkinter import messagebox
import math
import numpy as np


class LineDistanceCalculatorDialog(ttk.Toplevel):
    def __init__(self, parent, app, calibration_manager):
        super().__init__(parent)
        
        self.parent = parent
        self.app = app
        self.calibration_manager = calibration_manager
        
        self.title("Line Distance Calculator")
        self.transient(parent)
        self.grab_set()
        
        # Window setup
        screen_width = self.parent.winfo_screenwidth()
        screen_height = self.parent.winfo_screenheight()
        
        dialog_width = 700
        dialog_height = 600
        
        pos_x = (screen_width - dialog_width) // 2
        pos_y = (screen_height - dialog_height) // 2
        self.geometry(f"{dialog_width}x{dialog_height}+{pos_x}+{pos_y}")
        
        self.setup_ui()
        
        # Handle dialog close
        self.protocol("WM_DELETE_WINDOW", self.on_close)
        
    def setup_ui(self):
        """Setup the calculator UI"""
        # Main container
        main_frame = ttk.Frame(self, padding="20")
        main_frame.pack(fill=BOTH, expand=True)
        
        # Title
        title_label = ttk.Label(
            main_frame,
            text="Optimal Line Distance Calculator",
            font=("Arial", 16, "bold")
        )
        title_label.pack(pady=(0, 20))
        
        # Description
        desc_label = ttk.Label(
            main_frame,
            text="This tool calculates the optimal distance between detection lines based on traffic characteristics and video properties.",
            wraplength=600,
            justify=CENTER
        )
        desc_label.pack(pady=(0, 20))
        
        # Input section
        input_frame = ttk.LabelFrame(main_frame, text="Input Parameters", padding="20")
        input_frame.pack(fill=X, pady=(0, 20))
        
        # Left column - Traffic parameters
        left_frame = ttk.Frame(input_frame)
        left_frame.pack(side=LEFT, fill=BOTH, expand=True, padx=(0, 20))
        
        # Vehicle speed
        ttk.Label(left_frame, text="Average Vehicle Speed:", font=("Arial", 10, "bold")).pack(anchor=W, pady=(0, 5))
        
        speed_frame = ttk.Frame(left_frame)
        speed_frame.pack(fill=X, pady=(0, 15))
        
        self.speed_var = tk.DoubleVar(value=50.0)
        self.speed_scale = ttk.Scale(
            speed_frame,
            from_=5,
            to=120,
            orient=HORIZONTAL,
            variable=self.speed_var,
            command=self.calculate_distance
        )
        self.speed_scale.pack(fill=X)
        
        speed_info_frame = ttk.Frame(speed_frame)
        speed_info_frame.pack(fill=X, pady=(5, 0))
        
        self.speed_value_label = ttk.Label(speed_info_frame, text="50.0 km/h", font=("Arial", 10, "bold"))
        self.speed_value_label.pack(side=LEFT)
        
        # Speed presets
        preset_frame = ttk.Frame(speed_info_frame)
        preset_frame.pack(side=RIGHT)
        
        ttk.Button(preset_frame, text="City (30)", command=lambda: self.set_speed(30), 
                  bootstyle="info-outline", width=8).pack(side=LEFT, padx=2)
        ttk.Button(preset_frame, text="Highway (80)", command=lambda: self.set_speed(80), 
                  bootstyle="info-outline", width=8).pack(side=LEFT, padx=2)
        
        # Vehicle type
        ttk.Label(left_frame, text="Primary Vehicle Type:", font=("Arial", 10, "bold")).pack(anchor=W, pady=(0, 5))
        
        self.vehicle_type_var = tk.StringVar(value="car")
        vehicle_types = [
            ("🏍️ Motorcycle/Scooter", "motor"),
            ("🚗 Car/SUV", "car"), 
            ("🚚 Truck/Van", "truck"),
            ("🚌 Bus/Large Vehicle", "bus")
        ]
        
        for text, value in vehicle_types:
            ttk.Radiobutton(
                left_frame, 
                text=text, 
                variable=self.vehicle_type_var, 
                value=value,
                command=self.calculate_distance
            ).pack(anchor=W, pady=2)
        
        # Traffic density
        ttk.Label(left_frame, text="Traffic Density:", font=("Arial", 10, "bold")).pack(anchor=W, pady=(15, 5))
        
        self.traffic_density_var = tk.StringVar(value="normal")
        traffic_densities = [
            ("🟢 Light Traffic", "light"),
            ("🟡 Normal Traffic", "normal"),
            ("🔴 Heavy Traffic", "heavy")
        ]
        
        for text, value in traffic_densities:
            ttk.Radiobutton(
                left_frame,
                text=text,
                variable=self.traffic_density_var,
                value=value,
                command=self.calculate_distance
            ).pack(anchor=W, pady=2)
        
        # Right column - Technical parameters
        right_frame = ttk.Frame(input_frame)
        right_frame.pack(side=RIGHT, fill=BOTH, expand=True)
        
        # Video FPS (auto-detected)
        ttk.Label(right_frame, text="Video Properties:", font=("Arial", 10, "bold")).pack(anchor=W, pady=(0, 5))
        
        fps_frame = ttk.Frame(right_frame)
        fps_frame.pack(fill=X, pady=(0, 10))
        
        video_fps = self.app.video_handler.video_fps if self.app.video_handler.video_fps > 0 else 30
        ttk.Label(fps_frame, text=f"Frame Rate: {video_fps:.1f} FPS").pack(side=LEFT)
        
        if self.app.video_handler.is_webcam:
            ttk.Label(fps_frame, text="📹 Webcam", foreground="green").pack(side=RIGHT)
        else:
            ttk.Label(fps_frame, text="🎬 Video File", foreground="blue").pack(side=RIGHT)
        
        # Pixel scale calibration
        ttk.Label(right_frame, text="Scale Calibration:", font=("Arial", 10, "bold")).pack(anchor=W, pady=(15, 5))
        
        scale_frame = ttk.Frame(right_frame)
        scale_frame.pack(fill=X, pady=(0, 10))
        
        ttk.Label(scale_frame, text="Pixels per meter:").pack(side=LEFT)
        self.pixel_scale_var = tk.DoubleVar(value=50.0)
        pixel_scale_spinbox = ttk.Spinbox(
            scale_frame,
            from_=10,
            to=200,
            width=8,
            textvariable=self.pixel_scale_var,
            command=self.calculate_distance
        )
        pixel_scale_spinbox.pack(side=RIGHT)
        
        # Scale help
        scale_help = ttk.Label(
            right_frame,
            text="💡 Tip: Measure a known object in the video to calibrate pixel scale",
            foreground="gray",
            wraplength=250
        )
        scale_help.pack(anchor=W, pady=(0, 15))
        
        # Safety margin
        ttk.Label(right_frame, text="Safety Margin:", font=("Arial", 10, "bold")).pack(anchor=W, pady=(0, 5))
        
        self.safety_margin_var = tk.DoubleVar(value=1.2)
        safety_margin_scale = ttk.Scale(
            right_frame,
            from_=1.0,
            to=2.0,
            orient=HORIZONTAL,
            variable=self.safety_margin_var,
            command=self.calculate_distance
        )
        safety_margin_scale.pack(fill=X, pady=5)
        
        self.safety_margin_label = ttk.Label(right_frame, text="1.2x")
        self.safety_margin_label.pack(anchor=E)
        
        # Results section
        results_frame = ttk.LabelFrame(main_frame, text="Calculation Results", padding="20")
        results_frame.pack(fill=BOTH, expand=True, pady=(0, 20))
        
        # Result display
        result_display_frame = ttk.Frame(results_frame)
        result_display_frame.pack(fill=X, pady=(0, 15))
        
        # Main result
        self.result_label = ttk.Label(
            result_display_frame,
            text="Optimal Distance: 50 pixels",
            font=("Arial", 16, "bold"),
            foreground="blue"
        )
        self.result_label.pack()
        
        # Detailed breakdown
        breakdown_frame = ttk.Frame(results_frame)
        breakdown_frame.pack(fill=BOTH, expand=True)
        
        # Left side - calculation details
        calc_frame = ttk.LabelFrame(breakdown_frame, text="Calculation Details", padding="10")
        calc_frame.pack(side=LEFT, fill=BOTH, expand=True, padx=(0, 10))
        
        self.calc_details_text = tk.Text(calc_frame, height=8, width=35, wrap=tk.WORD, font=("Courier", 9))
        calc_scrollbar = ttk.Scrollbar(calc_frame, orient=VERTICAL, command=self.calc_details_text.yview)
        self.calc_details_text.configure(yscrollcommand=calc_scrollbar.set)
        
        self.calc_details_text.pack(side=LEFT, fill=BOTH, expand=True)
        calc_scrollbar.pack(side=RIGHT, fill=Y)
        
        # Right side - recommendations
        rec_frame = ttk.LabelFrame(breakdown_frame, text="Recommendations", padding="10")
        rec_frame.pack(side=RIGHT, fill=BOTH, expand=True)
        
        self.recommendations_text = tk.Text(rec_frame, height=8, width=35, wrap=tk.WORD, font=("Arial", 9))
        rec_scrollbar = ttk.Scrollbar(rec_frame, orient=VERTICAL, command=self.recommendations_text.yview)
        self.recommendations_text.configure(yscrollcommand=rec_scrollbar.set)
        
        self.recommendations_text.pack(side=LEFT, fill=BOTH, expand=True)
        rec_scrollbar.pack(side=RIGHT, fill=Y)
        
        # Action buttons
        button_frame = ttk.Frame(main_frame)
        button_frame.pack(fill=X)
        
        ttk.Button(
            button_frame,
            text="Apply Distance",
            command=self.apply_distance,
            bootstyle="success"
        ).pack(side=LEFT)
        
        ttk.Button(
            button_frame,
            text="Reset to Defaults",
            command=self.reset_defaults,
            bootstyle="secondary-outline"
        ).pack(side=LEFT, padx=(10, 0))
        
        ttk.Button(
            button_frame,
            text="Close",
            command=self.on_close,
            bootstyle="secondary"
        ).pack(side=RIGHT)
        
        # Initial calculation
        self.calculate_distance()
        
    def set_speed(self, speed):
        """Set speed preset"""
        self.speed_var.set(speed)
        self.calculate_distance()
        
    def calculate_distance(self, event=None):
        """Calculate optimal line distance"""
        # Get parameters
        speed_kmh = self.speed_var.get()
        vehicle_type = self.vehicle_type_var.get()
        traffic_density = self.traffic_density_var.get()
        pixel_scale = self.pixel_scale_var.get()
        safety_margin = self.safety_margin_var.get()
        video_fps = self.app.video_handler.video_fps if self.app.video_handler.video_fps > 0 else 30
        
        # Update labels
        self.speed_value_label.config(text=f"{speed_kmh:.1f} km/h")
        self.safety_margin_label.config(text=f"{safety_margin:.1f}x")
        
        # Convert speed to m/s
        speed_ms = speed_kmh / 3.6
        
        # Calculate basic distance (distance traveled in one frame)
        time_per_frame = 1.0 / video_fps
        distance_per_frame_m = speed_ms * time_per_frame
        distance_per_frame_px = distance_per_frame_m * pixel_scale
        
        # Vehicle type factors
        vehicle_factors = {
            "motor": 0.8,    # Smaller, more agile
            "car": 1.0,      # Standard reference
            "truck": 1.3,    # Larger, needs more space
            "bus": 1.5       # Largest vehicles
        }
        
        # Traffic density factors
        density_factors = {
            "light": 0.9,    # Can use tighter spacing
            "normal": 1.0,   # Standard spacing
            "heavy": 1.2     # Need more space for accuracy
        }
        
        # Apply factors
        vehicle_factor = vehicle_factors.get(vehicle_type, 1.0)
        density_factor = density_factors.get(traffic_density, 1.0)
        
        # Calculate final distance
        optimal_distance = distance_per_frame_px * vehicle_factor * density_factor * safety_margin
        
        # Ensure reasonable bounds
        optimal_distance = max(20, min(300, optimal_distance))
        optimal_distance_int = int(round(optimal_distance))
        
        # Update result display
        self.result_label.config(text=f"Optimal Distance: {optimal_distance_int} pixels")
        
        # Update calculation details
        self.update_calculation_details(
            speed_kmh, speed_ms, time_per_frame, distance_per_frame_m, 
            distance_per_frame_px, vehicle_factor, density_factor, 
            safety_margin, optimal_distance_int
        )
        
        # Update recommendations
        self.update_recommendations(optimal_distance_int, speed_kmh, vehicle_type, traffic_density)
        
        # Store result
        self.calculated_distance = optimal_distance_int
        
    def update_calculation_details(self, speed_kmh, speed_ms, time_per_frame, 
                                 distance_per_frame_m, distance_per_frame_px, 
                                 vehicle_factor, density_factor, safety_margin, result):
        """Update calculation details display"""
        details = f"""CALCULATION BREAKDOWN:

Input Parameters:
• Speed: {speed_kmh:.1f} km/h = {speed_ms:.2f} m/s
• Video FPS: {1/time_per_frame:.1f}
• Time per frame: {time_per_frame*1000:.1f} ms
• Pixel scale: {self.pixel_scale_var.get():.1f} px/m

Basic Calculation:
• Distance per frame: {distance_per_frame_m:.3f} m
• Distance in pixels: {distance_per_frame_px:.1f} px

Applied Factors:
• Vehicle factor: {vehicle_factor:.1f}x
• Traffic factor: {density_factor:.1f}x  
• Safety margin: {safety_margin:.1f}x

Final Result:
• Optimal distance: {result} pixels

Formula Used:
distance = (speed × time_per_frame × 
           pixel_scale × vehicle_factor × 
           density_factor × safety_margin)
"""
        
        self.calc_details_text.delete(1.0, tk.END)
        self.calc_details_text.insert(tk.END, details)
        
    def update_recommendations(self, distance, speed, vehicle_type, density):
        """Update recommendations display"""
        recommendations = f"""RECOMMENDATIONS:

Calculated Distance: {distance} pixels

Usage Guidelines:
• This distance ensures proper vehicle 
  separation for accurate counting
• Adjust based on actual field testing
• Monitor false positives/negatives

For your setup:
"""
        
        # Speed-based recommendations
        if speed < 25:
            recommendations += "• SLOW TRAFFIC: Consider reducing distance by 10-20% for better sensitivity\n"
        elif speed > 80:
            recommendations += "• FAST TRAFFIC: Distance is critical - test carefully with real traffic\n"
        else:
            recommendations += "• NORMAL SPEED: Distance should work well for most scenarios\n"
            
        # Vehicle type recommendations
        vehicle_tips = {
            "motor": "• MOTORCYCLES: May need fine-tuning for smaller objects",
            "car": "• CARS: Standard settings should work optimally", 
            "truck": "• TRUCKS: Longer vehicles - monitor for double counting",
            "bus": "• BUSES: Very long vehicles - may need increased distance"
        }
        recommendations += vehicle_tips.get(vehicle_type, "") + "\n"
        
        # Traffic density recommendations
        if density == "heavy":
            recommendations += "• HEAVY TRAFFIC: Enable movement validation to filter stationary vehicles\n"
        elif density == "light":
            recommendations += "• LIGHT TRAFFIC: Can use more aggressive detection settings\n"
            
        recommendations += f"""
Testing Tips:
• Run detection for 1-2 minutes
• Count manually vs system count
• Adjust ±10-20 pixels if needed
• Test at different times of day

Current app settings:
• Will be applied to line_offset setting
• Orientation: {self.app.settings.get('line_orientation', 'Horizontal')}
• Current confidence: {self.app.settings.get('confidence_threshold', 0.3):.2f}
"""
        
        self.recommendations_text.delete(1.0, tk.END)
        self.recommendations_text.insert(tk.END, recommendations)
        
    def apply_distance(self):
        """Apply calculated distance to app settings"""
        if not hasattr(self, 'calculated_distance'):
            messagebox.showwarning("Warning", "Please wait for calculation to complete.")
            return
            
        # Apply to app settings
        self.app.settings['line_offset'] = self.calculated_distance
        self.app.new_settings_to_send = self.app.settings.copy()
        
        # Update display if video is loaded
        if self.app.video_handler.video_source:
            self.app.video_handler.display_first_frame()
            
        # Save configuration
        self.app.config_manager.save_config(self.app.settings)
        
        messagebox.showinfo(
            "Distance Applied",
            f"Line distance set to {self.calculated_distance} pixels.\n\n"
            f"Settings have been saved and applied.\n"
            f"You can now test the detection with the new distance."
        )
        
    def reset_defaults(self):
        """Reset all parameters to defaults"""
        self.speed_var.set(50.0)
        self.vehicle_type_var.set("car")
        self.traffic_density_var.set("normal")
        self.pixel_scale_var.set(50.0)
        self.safety_margin_var.set(1.2)
        
        self.calculate_distance()
        
    def on_close(self):
        """Handle dialog close"""
        self.destroy()