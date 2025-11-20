# gui/dialogs/calibration_wizard.py
import datetime
import tkinter as tk
import ttkbootstrap as ttk
from ttkbootstrap.constants import *
from tkinter import messagebox
import cv2
import numpy as np
from PIL import Image, ImageTk
import threading


class CalibrationWizardDialog(ttk.Toplevel):
    def __init__(self, parent, app, calibration_manager):
        super().__init__(parent)
        
        self.parent = parent
        self.app = app
        self.calibration_manager = calibration_manager
        
        self.title("Calibration Wizard")
        self.transient(parent)
        self.grab_set()
        
        # Window setup
        screen_width = self.parent.winfo_screenwidth()
        screen_height = self.parent.winfo_screenheight()
        
        dialog_width = 1000
        dialog_height = 700
        
        pos_x = (screen_width - dialog_width) // 2
        pos_y = (screen_height - dialog_height) // 2
        self.geometry(f"{dialog_width}x{dialog_height}+{pos_x}+{pos_y}")
        
        # Wizard state
        self.current_step = 0
        self.total_steps = 6
        self.wizard_data = {}
        self.scene_analysis = {}
        
        self.setup_ui()
        self.show_step(0)
        
        # Handle dialog close
        self.protocol("WM_DELETE_WINDOW", self.on_close)
        
    def setup_ui(self):
        """Setup the wizard UI"""
        # Main container
        self.main_frame = ttk.Frame(self, padding="20")
        self.main_frame.pack(fill=BOTH, expand=True)
        
        # Header
        self.header_frame = ttk.Frame(self.main_frame)
        self.header_frame.pack(fill=X, pady=(0, 20))
        
        self.title_label = ttk.Label(
            self.header_frame, 
            text="Vehicle Detection Calibration Wizard",
            font=("Arial", 16, "bold")
        )
        self.title_label.pack(side=LEFT)
        
        # Progress bar
        self.progress_frame = ttk.Frame(self.header_frame)
        self.progress_frame.pack(side=RIGHT)
        
        self.progress_label = ttk.Label(self.progress_frame, text="Step 1 of 6")
        self.progress_label.pack(side=TOP)
        
        self.progress_bar = ttk.Progressbar(
            self.progress_frame, 
            length=200, 
            mode='determinate'
        )
        self.progress_bar.pack(side=BOTTOM)
        self.progress_bar['value'] = 0
        
        # Content area
        self.content_frame = ttk.Frame(self.main_frame)
        self.content_frame.pack(fill=BOTH, expand=True, pady=(0, 20))
        
        # Buttons
        self.button_frame = ttk.Frame(self.main_frame)
        self.button_frame.pack(fill=X)
        
        self.back_button = ttk.Button(
            self.button_frame, 
            text="← Back", 
            command=self.previous_step,
            state="disabled"
        )
        self.back_button.pack(side=LEFT)
        
        self.cancel_button = ttk.Button(
            self.button_frame, 
            text="Cancel", 
            command=self.on_close,
            bootstyle="secondary"
        )
        self.cancel_button.pack(side=RIGHT, padx=(10, 0))
        
        self.next_button = ttk.Button(
            self.button_frame, 
            text="Next →", 
            command=self.next_step,
            bootstyle="success"
        )
        self.next_button.pack(side=RIGHT)
        
    def show_step(self, step):
        """Show specific wizard step"""
        # Clear content frame
        for widget in self.content_frame.winfo_children():
            widget.destroy()
            
        # Update progress
        self.current_step = step
        progress = (step / (self.total_steps - 1)) * 100
        self.progress_bar['value'] = progress
        self.progress_label.config(text=f"Step {step + 1} of {self.total_steps}")
        
        # Update buttons
        self.back_button.config(state="normal" if step > 0 else "disabled")
        
        if step == self.total_steps - 1:
            self.next_button.config(text="Finish", bootstyle="success")
        else:
            self.next_button.config(text="Next →", bootstyle="info")
            
        # Show step content
        if step == 0:
            self.show_welcome_step()
        elif step == 1:
            self.show_scene_analysis_step()
        elif step == 2:
            self.show_line_positioning_step()
        elif step == 3:
            self.show_distance_calculation_step()
        elif step == 4:
            self.show_roi_calibration_step()
        elif step == 5:
            self.show_final_validation_step()
            
    def show_welcome_step(self):
        """Step 0: Welcome and prerequisites"""
        welcome_frame = ttk.LabelFrame(self.content_frame, text="Welcome to Calibration Wizard", padding="20")
        welcome_frame.pack(fill=BOTH, expand=True)
        
        # Welcome text
        welcome_text = """
This wizard will guide you through the calibration process to optimize vehicle detection for your specific setup.

Before we begin, please ensure:
• Video source is loaded (video file or webcam)
• Camera/video has good lighting and clear view of the road
• You have a few minutes to complete the calibration process

The wizard will:
1. Analyze your video scene automatically
2. Help you position detection lines optimally
3. Calculate optimal line distance
4. Configure region of interest (ROI) filtering
5. Validate and apply the calibration

Click 'Next' to begin the automatic scene analysis.
        """
        
        text_label = ttk.Label(welcome_frame, text=welcome_text, justify=LEFT, wraplength=800)
        text_label.pack(pady=20)
        
        # Check prerequisites
        prereq_frame = ttk.Frame(welcome_frame)
        prereq_frame.pack(fill=X, pady=20)
        
        video_status = "✓ Video source loaded" if self.app.video_handler.video_source else "✗ No video source"
        video_color = "green" if self.app.video_handler.video_source else "red"
        
        status_label = ttk.Label(
            prereq_frame, 
            text=f"Status: {video_status}", 
            foreground=video_color
        )
        status_label.pack()
        
        if not self.app.video_handler.video_source:
            self.next_button.config(state="disabled")
            warning_label = ttk.Label(
                prereq_frame, 
                text="Please load a video source before starting calibration.",
                foreground="red"
            )
            warning_label.pack(pady=10)
        else:
            self.next_button.config(state="normal")
            
    def show_scene_analysis_step(self):
        """Step 1: Automatic scene analysis"""
        analysis_frame = ttk.LabelFrame(self.content_frame, text="Scene Analysis", padding="20")
        analysis_frame.pack(fill=BOTH, expand=True)
        
        # Analysis status
        self.analysis_label = ttk.Label(analysis_frame, text="Analyzing scene...", font=("Arial", 12))
        self.analysis_label.pack(pady=10)
        
        # Progress indicator
        self.analysis_progress = ttk.Progressbar(analysis_frame, mode='indeterminate')
        self.analysis_progress.pack(fill=X, pady=10)
        self.analysis_progress.start()
        
        # Results frame (initially empty)
        self.results_frame = ttk.Frame(analysis_frame)
        self.results_frame.pack(fill=BOTH, expand=True, pady=20)
        
        # Start analysis in background
        threading.Thread(target=self.run_scene_analysis, daemon=True).start()
        
    def run_scene_analysis(self):
        """Run scene analysis in background thread"""
        try:
            # Get current frame
            if not self.app.video_handler.cap or not self.app.video_handler.cap.isOpened():
                self.app.video_handler.display_first_frame()
                
            ret, frame = self.app.video_handler.cap.read()
            
            if ret:
                # Run analysis
                self.scene_analysis = self.calibration_manager.analyze_scene(frame)
                
                # Update UI in main thread
                self.after(0, self.show_analysis_results)
            else:
                self.after(0, lambda: self.show_analysis_error("Could not read video frame"))
                
        except Exception as e:
            self.after(0, lambda: self.show_analysis_error(str(e)))
            
    def show_analysis_results(self):
        """Show scene analysis results"""
        self.analysis_progress.stop()
        self.analysis_progress.pack_forget()
        self.analysis_label.config(text="Scene Analysis Complete!")
        
        # Clear results frame
        for widget in self.results_frame.winfo_children():
            widget.destroy()
            
        # Create results display
        results_text = ttk.Text(self.results_frame, height=12, wrap=tk.WORD)
        scrollbar = ttk.Scrollbar(self.results_frame, orient=VERTICAL, command=results_text.yview)
        results_text.configure(yscrollcommand=scrollbar.set)
        
        results_text.pack(side=LEFT, fill=BOTH, expand=True)
        scrollbar.pack(side=RIGHT, fill=Y)
        
        # Format analysis results
        analysis_output = f"""Scene Analysis Results:

Detected Scene Characteristics:
• Suggested line orientation: {self.scene_analysis.get('suggested_orientation', 'Unknown')}
• Scene brightness: {self.scene_analysis.get('scene_brightness', 0):.1f}
• Recommended confidence threshold: {self.scene_analysis.get('suggested_confidence', 0.3):.2f}
• Recommended ROI top margin: {self.scene_analysis.get('roi_top_margin', 0.3)*100:.1f}%

Analysis Confidence: {self.scene_analysis.get('analysis_confidence', 0)*100:.1f}%

Recommendations:
"""
        
        if self.scene_analysis.get('scene_brightness', 0) < 80:
            analysis_output += "• Low light detected - consider increasing confidence threshold\n"
        if self.scene_analysis.get('scene_brightness', 0) > 180:
            analysis_output += "• Bright conditions - standard settings should work well\n"
            
        analysis_output += "\nThese settings will be automatically applied in the next steps."
        
        results_text.insert(tk.END, analysis_output)
        results_text.config(state=tk.DISABLED)
        
        # Store suggestions in wizard data
        self.wizard_data['scene_analysis'] = self.scene_analysis
        
    def show_analysis_error(self, error_message):
        """Show scene analysis error"""
        self.analysis_progress.stop()
        self.analysis_progress.pack_forget()
        self.analysis_label.config(text=f"Analysis Error: {error_message}", foreground="red")
        
        # Use default values
        self.scene_analysis = {
            'suggested_orientation': 'Horizontal',
            'suggested_confidence': 0.3,
            'roi_top_margin': 0.3,
            'scene_brightness': 100,
            'analysis_confidence': 0.0
        }
        self.wizard_data['scene_analysis'] = self.scene_analysis
        
    def show_line_positioning_step(self):
        """Step 2: Interactive line positioning"""
        line_frame = ttk.LabelFrame(self.content_frame, text="Detection Line Positioning", padding="20")
        line_frame.pack(fill=BOTH, expand=True)
        
        # Instructions
        instructions = ttk.Label(
            line_frame,
            text="Position the detection lines by clicking on the video preview below.\nThe green line will appear where you click, and the red line will be automatically positioned based on the calculated distance.",
            wraplength=800,
            justify=CENTER
        )
        instructions.pack(pady=(0, 15))
        
        # Video preview frame
        preview_frame = ttk.Frame(line_frame)
        preview_frame.pack(fill=BOTH, expand=True)
        
        # Video canvas
        self.line_canvas = tk.Canvas(preview_frame, width=640, height=480, bg="black")
        self.line_canvas.pack()
        
        # Current line position info
        self.line_info_label = ttk.Label(
            line_frame,
            text="Click on the video preview to set detection line position"
        )
        self.line_info_label.pack(pady=10)
        
        # Orientation selection
        orientation_frame = ttk.LabelFrame(line_frame, text="Line Orientation", padding="10")
        orientation_frame.pack(pady=10)
        
        self.orientation_var = tk.StringVar(value=self.scene_analysis.get('suggested_orientation', 'Horizontal'))
        
        ttk.Radiobutton(
            orientation_frame, 
            text="Horizontal (for vertical traffic)", 
            variable=self.orientation_var, 
            value="Horizontal"
        ).pack(side=LEFT, padx=10)
        
        ttk.Radiobutton(
            orientation_frame, 
            text="Vertical (for horizontal traffic)", 
            variable=self.orientation_var, 
            value="Vertical"
        ).pack(side=LEFT, padx=10)
        
        # Bind canvas click
        self.line_canvas.bind("<Button-1>", self.on_line_canvas_click)
        
        # Load and display current frame
        self.update_line_preview()
        
    def on_line_canvas_click(self, event):
        """Handle click on line positioning canvas"""
        # Store click position
        self.wizard_data['line_click_x'] = event.x
        self.wizard_data['line_click_y'] = event.y
        
        # Update info label
        self.line_info_label.config(
            text=f"Detection line positioned at: ({event.x}, {event.y})"
        )
        
        # Redraw preview with lines
        self.update_line_preview()
        
    def update_line_preview(self):
        """Update line positioning preview"""
        if not self.app.video_handler.cap or not self.app.video_handler.cap.isOpened():
            return
            
        # Get current frame
        ret, frame = self.app.video_handler.cap.read()
        if not ret:
            return
            
        # Resize frame to canvas size
        canvas_width = 640
        canvas_height = 480
        frame_resized = cv2.resize(frame, (canvas_width, canvas_height))
        
        # Draw detection lines if position is set
        if 'line_click_x' in self.wizard_data and 'line_click_y' in self.wizard_data:
            click_x = self.wizard_data['line_click_x']
            click_y = self.wizard_data['line_click_y']
            
            # Get line distance (will be calculated in next step, use default for now)
            line_distance = 50
            
            if self.orientation_var.get() == "Horizontal":
                # Draw horizontal lines
                cv2.line(frame_resized, (0, click_y), (canvas_width, click_y), (0, 255, 0), 2)
                cv2.line(frame_resized, (0, click_y + line_distance), (canvas_width, click_y + line_distance), (0, 0, 255), 2)
            else:
                # Draw vertical lines
                cv2.line(frame_resized, (click_x, 0), (click_x, canvas_height), (0, 255, 0), 2)
                cv2.line(frame_resized, (click_x + line_distance, 0), (click_x + line_distance, canvas_height), (0, 0, 255), 2)
        
        # Convert to PhotoImage and display
        frame_rgb = cv2.cvtColor(frame_resized, cv2.COLOR_BGR2RGB)
        image = Image.fromarray(frame_rgb)
        photo = ImageTk.PhotoImage(image)
        
        self.line_canvas.delete("all")
        self.line_canvas.create_image(canvas_width//2, canvas_height//2, image=photo)
        self.line_canvas.image = photo  # Keep a reference
        
    def show_distance_calculation_step(self):
        """Step 3: Line distance calculation"""
        distance_frame = ttk.LabelFrame(self.content_frame, text="Line Distance Calculation", padding="20")
        distance_frame.pack(fill=BOTH, expand=True)
        
        # Instructions
        instructions = ttk.Label(
            distance_frame,
            text="Configure the distance between detection lines based on vehicle characteristics and traffic speed.",
            wraplength=800,
            justify=CENTER
        )
        instructions.pack(pady=(0, 20))
        
        # Input frame
        input_frame = ttk.Frame(distance_frame)
        input_frame.pack(fill=X, pady=20)
        
        # Left column - Manual settings
        manual_frame = ttk.LabelFrame(input_frame, text="Manual Configuration", padding="15")
        manual_frame.pack(side=LEFT, fill=BOTH, expand=True, padx=(0, 10))
        
        # Vehicle speed
        ttk.Label(manual_frame, text="Estimated Vehicle Speed (km/h):").pack(anchor=W, pady=5)
        self.speed_var = tk.DoubleVar(value=50.0)
        self.speed_scale = ttk.Scale(
            manual_frame, 
            from_=10, 
            to=120, 
            orient=HORIZONTAL,
            variable=self.speed_var,
            command=self.update_distance_calculation
        )
        self.speed_scale.pack(fill=X, pady=5)
        self.speed_label = ttk.Label(manual_frame, text="50.0 km/h")
        self.speed_label.pack(anchor=E)
        
        # Vehicle type
        ttk.Label(manual_frame, text="Primary Vehicle Type:").pack(anchor=W, pady=(15, 5))
        self.vehicle_type_var = tk.StringVar(value="car")
        vehicle_types = [("Motor/Motorcycle", "motor"), ("Car", "car"), ("Truck", "truck"), ("Bus", "bus")]
        for text, value in vehicle_types:
            ttk.Radiobutton(manual_frame, text=text, variable=self.vehicle_type_var, value=value,
                          command=self.update_distance_calculation).pack(anchor=W)
        
        # Right column - Calculated results
        result_frame = ttk.LabelFrame(input_frame, text="Calculated Distance", padding="15")
        result_frame.pack(side=RIGHT, fill=BOTH, expand=True)
        
        self.calculated_distance_label = ttk.Label(result_frame, text="Calculated Distance: 50 pixels", font=("Arial", 12, "bold"))
        self.calculated_distance_label.pack(pady=10)
        
        self.distance_explanation = ttk.Label(result_frame, text="", wraplength=300, justify=LEFT)
        self.distance_explanation.pack(pady=10)
        
        # Manual override
        override_frame = ttk.Frame(result_frame)
        override_frame.pack(fill=X, pady=15)
        
        ttk.Label(override_frame, text="Manual Override (pixels):").pack(anchor=W)
        self.manual_distance_var = tk.IntVar(value=50)
        self.manual_distance_scale = ttk.Scale(
            override_frame,
            from_=20,
            to=200,
            orient=HORIZONTAL,
            variable=self.manual_distance_var
        )
        self.manual_distance_scale.pack(fill=X, pady=5)
        self.manual_distance_label = ttk.Label(override_frame, text="50 pixels")
        self.manual_distance_label.pack(anchor=E)
        
        # Bind manual override
        self.manual_distance_scale.config(command=self.update_manual_distance)
        
        # Initial calculation
        self.update_distance_calculation()
        
    def update_distance_calculation(self, event=None):
        """Update distance calculation based on inputs"""
        speed = self.speed_var.get()
        vehicle_type = self.vehicle_type_var.get()
        video_fps = self.app.video_handler.video_fps
        
        # Calculate optimal distance
        optimal_distance = self.calibration_manager.calculate_optimal_line_distance(
            video_fps, speed, vehicle_type
        )
        
        # Update labels
        self.speed_label.config(text=f"{speed:.1f} km/h")
        self.calculated_distance_label.config(text=f"Calculated Distance: {optimal_distance} pixels")
        
        explanation = f"""Based on:
• Vehicle speed: {speed:.1f} km/h
• Vehicle type: {vehicle_type}
• Video FPS: {video_fps:.1f}
• Safety factor applied

This distance ensures proper vehicle separation for accurate counting."""
        
        self.distance_explanation.config(text=explanation)
        
        # Update manual override to match calculation
        self.manual_distance_var.set(optimal_distance)
        self.manual_distance_label.config(text=f"{optimal_distance} pixels")
        
        # Store in wizard data
        self.wizard_data['calculated_distance'] = optimal_distance
        self.wizard_data['manual_distance'] = optimal_distance
        
    def update_manual_distance(self, event=None):
        """Update manual distance override"""
        distance = self.manual_distance_var.get()
        self.manual_distance_label.config(text=f"{distance} pixels")
        self.wizard_data['manual_distance'] = distance
        
    def show_roi_calibration_step(self):
        """Step 4: ROI calibration"""
        roi_frame = ttk.LabelFrame(self.content_frame, text="Region of Interest (ROI) Configuration", padding="20")
        roi_frame.pack(fill=BOTH, expand=True)
        
        # Instructions
        instructions = ttk.Label(
            roi_frame,
            text="Configure the Region of Interest to focus detection on the road area and exclude buildings, sky, etc.",
            wraplength=800,
            justify=CENTER
        )
        instructions.pack(pady=(0, 15))
        
        # ROI settings frame
        settings_frame = ttk.Frame(roi_frame)
        settings_frame.pack(fill=X, pady=15)
        
        # Left column - ROI controls
        controls_frame = ttk.LabelFrame(settings_frame, text="ROI Settings", padding="15")
        controls_frame.pack(side=LEFT, fill=Y, padx=(0, 10))
        
        # Top margin
        ttk.Label(controls_frame, text="Top Margin (%):").pack(anchor=W, pady=5)
        self.roi_top_var = tk.DoubleVar(value=self.scene_analysis.get('roi_top_margin', 0.3) * 100)
        self.roi_top_scale = ttk.Scale(
            controls_frame,
            from_=0,
            to=60,
            orient=HORIZONTAL,
            variable=self.roi_top_var,
            command=self.update_roi_preview
        )
        self.roi_top_scale.pack(fill=X, pady=5)
        self.roi_top_label = ttk.Label(controls_frame, text="30%")
        self.roi_top_label.pack(anchor=E)
        
        # Side margin
        ttk.Label(controls_frame, text="Side Margin (%):").pack(anchor=W, pady=(15, 5))
        self.roi_side_var = tk.DoubleVar(value=10.0)
        self.roi_side_scale = ttk.Scale(
            controls_frame,
            from_=0,
            to=40,
            orient=HORIZONTAL,
            variable=self.roi_side_var,
            command=self.update_roi_preview
        )
        self.roi_side_scale.pack(fill=X, pady=5)
        self.roi_side_label = ttk.Label(controls_frame, text="10%")
        self.roi_side_label.pack(anchor=E)
        
        # Max object size
        ttk.Label(controls_frame, text="Max Object Size (%):").pack(anchor=W, pady=(15, 5))
        self.roi_max_size_var = tk.DoubleVar(value=30.0)
        self.roi_max_size_scale = ttk.Scale(
            controls_frame,
            from_=10,
            to=50,
            orient=HORIZONTAL,
            variable=self.roi_max_size_var,
            command=self.update_roi_preview
        )
        self.roi_max_size_scale.pack(fill=X, pady=5)
        self.roi_max_size_label = ttk.Label(controls_frame, text="30%")
        self.roi_max_size_label.pack(anchor=E)
        
        # Right column - ROI preview
        preview_frame = ttk.LabelFrame(settings_frame, text="ROI Preview", padding="15")
        preview_frame.pack(side=RIGHT, fill=BOTH, expand=True)
        
        self.roi_canvas = tk.Canvas(preview_frame, width=400, height=300, bg="black")
        self.roi_canvas.pack()
        
        # ROI info
        self.roi_info_label = ttk.Label(
            roi_frame,
            text="Green area: Detection zone | Red area: Excluded zone"
        )
        self.roi_info_label.pack(pady=10)
        
        # Initial ROI preview
        self.update_roi_preview()
        
    def update_roi_preview(self, event=None):
        """Update ROI preview"""
        # Update labels
        top_margin = self.roi_top_var.get()
        side_margin = self.roi_side_var.get()
        max_size = self.roi_max_size_var.get()
        
        self.roi_top_label.config(text=f"{top_margin:.0f}%")
        self.roi_side_label.config(text=f"{side_margin:.0f}%")
        self.roi_max_size_label.config(text=f"{max_size:.0f}%")
        
        # Store in wizard data
        self.wizard_data['roi_top_margin'] = top_margin / 100.0
        self.wizard_data['roi_side_margin'] = side_margin / 100.0
        self.wizard_data['roi_max_size'] = max_size / 100.0
        
        # Update preview canvas
        if not self.app.video_handler.cap or not self.app.video_handler.cap.isOpened():
            return
            
        ret, frame = self.app.video_handler.cap.read()
        if not ret:
            return
            
        # Resize frame
        canvas_width = 400
        canvas_height = 300
        frame_resized = cv2.resize(frame, (canvas_width, canvas_height))
        
        # Calculate ROI boundaries
        top_boundary = int(canvas_height * top_margin / 100)
        side_boundary = int(canvas_width * side_margin / 100)
        
        # Create ROI overlay
        overlay = frame_resized.copy()
        
        # Draw excluded areas in red
        cv2.rectangle(overlay, (0, 0), (canvas_width, top_boundary), (0, 0, 255), -1)  # Top area
        cv2.rectangle(overlay, (0, 0), (side_boundary, canvas_height), (0, 0, 255), -1)  # Left area
        cv2.rectangle(overlay, (canvas_width - side_boundary, 0), (canvas_width, canvas_height), (0, 0, 255), -1)  # Right area
        
        # Draw detection area in green (transparent)
        roi_area = np.zeros_like(overlay)
        cv2.rectangle(roi_area, (side_boundary, top_boundary), 
                     (canvas_width - side_boundary, canvas_height), (0, 255, 0), -1)
        
        # Blend overlays
        frame_with_roi = cv2.addWeighted(frame_resized, 0.7, overlay, 0.2, 0)
        frame_with_roi = cv2.addWeighted(frame_with_roi, 0.9, roi_area, 0.1, 0)
        
        # Convert and display
        frame_rgb = cv2.cvtColor(frame_with_roi, cv2.COLOR_BGR2RGB)
        image = Image.fromarray(frame_rgb)
        photo = ImageTk.PhotoImage(image)
        
        self.roi_canvas.delete("all")
        self.roi_canvas.create_image(canvas_width//2, canvas_height//2, image=photo)
        self.roi_canvas.image = photo
        
    def show_final_validation_step(self):
        """Step 5: Final validation and summary"""
        validation_frame = ttk.LabelFrame(self.content_frame, text="Calibration Summary & Validation", padding="20")
        validation_frame.pack(fill=BOTH, expand=True)
        
        # Summary text
        summary_text = ttk.Text(validation_frame, height=15, wrap=tk.WORD)
        scrollbar = ttk.Scrollbar(validation_frame, orient=VERTICAL, command=summary_text.yview)
        summary_text.configure(yscrollcommand=scrollbar.set)
        
        summary_text.pack(side=LEFT, fill=BOTH, expand=True)
        scrollbar.pack(side=RIGHT, fill=Y)
        
        # Generate summary
        summary = self.generate_calibration_summary()
        summary_text.insert(tk.END, summary)
        summary_text.config(state=tk.DISABLED)
        
        # Test button
        test_frame = ttk.Frame(validation_frame)
        test_frame.pack(fill=X, pady=20)
        
        self.test_button = ttk.Button(
            test_frame,
            text="Run Validation Test (30s)",
            command=self.run_validation_test,
            bootstyle="info"
        )
        self.test_button.pack(side=LEFT)
        
        self.test_status_label = ttk.Label(test_frame, text="")
        self.test_status_label.pack(side=LEFT, padx=20)
        
    def generate_calibration_summary(self):
        """Generate calibration summary text"""
        summary = "CALIBRATION WIZARD SUMMARY\n"
        summary += "=" * 50 + "\n\n"
        
        # Scene analysis
        summary += "SCENE ANALYSIS:\n"
        summary += f"• Detected orientation: {self.wizard_data.get('scene_analysis', {}).get('suggested_orientation', 'N/A')}\n"
        summary += f"• Scene brightness: {self.wizard_data.get('scene_analysis', {}).get('scene_brightness', 0):.1f}\n"
        summary += f"• Analysis confidence: {self.wizard_data.get('scene_analysis', {}).get('analysis_confidence', 0)*100:.1f}%\n\n"
        
        # Line configuration
        summary += "DETECTION LINE CONFIGURATION:\n"
        if 'line_click_x' in self.wizard_data:
            summary += f"• Line position: ({self.wizard_data['line_click_x']}, {self.wizard_data['line_click_y']})\n"
        summary += f"• Line orientation: {getattr(self, 'orientation_var', tk.StringVar()).get()}\n"
        summary += f"• Line distance: {self.wizard_data.get('manual_distance', 50)} pixels\n\n"
        
        # ROI configuration
        summary += "ROI CONFIGURATION:\n"
        summary += f"• Top margin: {self.wizard_data.get('roi_top_margin', 0.3)*100:.1f}%\n"
        summary += f"• Side margin: {self.wizard_data.get('roi_side_margin', 0.1)*100:.1f}%\n"
        summary += f"• Max object size: {self.wizard_data.get('roi_max_size', 0.3)*100:.1f}%\n\n"
        
        # Recommended settings
        summary += "RECOMMENDED SETTINGS:\n"
        summary += f"• Confidence threshold: {self.wizard_data.get('scene_analysis', {}).get('suggested_confidence', 0.3):.2f}\n"
        summary += "• ROI filter: Enabled\n"
        summary += "• Size validation: Enabled\n"
        summary += "• Movement validation: Enabled\n\n"
        
        summary += "These settings will be applied when you click 'Finish'.\n"
        summary += "You can run a validation test to verify the configuration before applying."
        
        return summary
        
    def run_validation_test(self):
        """Run validation test"""
        self.test_button.config(state="disabled", text="Testing...")
        self.test_status_label.config(text="Running validation test...")
        
        def test_thread():
            # Apply temporary settings
            temp_settings = self.generate_final_settings()
            original_settings = self.app.settings.copy()
            
            try:
                # Apply test settings
                self.app.settings.update(temp_settings)
                self.app.new_settings_to_send = self.app.settings.copy()
                
                # Run short test
                test_results = self.calibration_manager.run_settings_test(test_duration=30)
                
                # Update UI
                self.after(0, lambda: self.show_test_results(test_results))
                
            except Exception as e:
                self.after(0, lambda: self.show_test_error(str(e)))
            finally:
                # Restore original settings
                self.app.settings = original_settings
                self.app.new_settings_to_send = self.app.settings.copy()
                
        threading.Thread(target=test_thread, daemon=True).start()
        
    def show_test_results(self, test_results):
        """Show validation test results"""
        self.test_button.config(state="normal", text="Run Validation Test (30s)")
        
        if test_results:
            metrics = test_results['metrics']
            accuracy = metrics.get('accuracy_estimate', 0)
            
            if accuracy > 85:
                status = f"✓ Validation passed! Estimated accuracy: {accuracy:.1f}%"
                color = "green"
            elif accuracy > 70:
                status = f"⚠ Acceptable results. Estimated accuracy: {accuracy:.1f}%"
                color = "orange"
            else:
                status = f"✗ Poor results. Estimated accuracy: {accuracy:.1f}%"
                color = "red"
                
            self.test_status_label.config(text=status, foreground=color)
        else:
            self.test_status_label.config(text="✗ Test failed", foreground="red")
            
    def show_test_error(self, error):
        """Show test error"""
        self.test_button.config(state="normal", text="Run Validation Test (30s)")
        self.test_status_label.config(text=f"Test error: {error}", foreground="red")
        
    def generate_final_settings(self):
        """Generate final settings from wizard data"""
        settings = {}
        
        # Basic detection settings
        scene_analysis = self.wizard_data.get('scene_analysis', {})
        settings['confidence_threshold'] = scene_analysis.get('suggested_confidence', 0.3)
        settings['line_orientation'] = getattr(self, 'orientation_var', tk.StringVar()).get()
        settings['line_offset'] = self.wizard_data.get('manual_distance', 50)
        
        # Line positions
        if 'line_click_x' in self.wizard_data and 'line_click_y' in self.wizard_data:
            # Convert canvas coordinates to settings coordinates
            settings['line1_x'] = self.wizard_data['line_click_x']
            settings['line1_y'] = self.wizard_data['line_click_y']
            
        # ROI settings
        settings['enable_roi_filter'] = True
        settings['roi_margin_y_top'] = self.wizard_data.get('roi_top_margin', 0.3)
        settings['roi_margin_x'] = self.wizard_data.get('roi_side_margin', 0.1)
        settings['max_object_size_ratio'] = self.wizard_data.get('roi_max_size', 0.3)
        
        # Enable recommended filters
        settings['enable_size_validation'] = True
        settings['enable_movement_validation'] = True
        settings['enable_building_class_filter'] = True
        
        return settings
        
    def next_step(self):
        """Go to next step or finish"""
        if self.current_step < self.total_steps - 1:
            self.show_step(self.current_step + 1)
        else:
            self.finish_calibration()
            
    def previous_step(self):
        """Go to previous step"""
        if self.current_step > 0:
            self.show_step(self.current_step - 1)
            
    def finish_calibration(self):
        """Apply calibration and close wizard"""
        try:
            # Generate final settings
            final_settings = self.generate_final_settings()
            
            # Apply to app
            self.app.settings.update(final_settings)
            self.app.new_settings_to_send = self.app.settings.copy()
            
            # Update display
            if self.app.video_handler.video_source:
                self.app.video_handler.display_first_frame()
                
            # Save configuration
            self.app.config_manager.save_config(self.app.settings)
            
            # Save as calibration profile
            profile_name = f"Wizard_{datetime.now().strftime('%Y%m%d_%H%M')}"
            self.calibration_manager.save_calibration_profile(
                profile_name, 
                final_settings,
                metadata={
                    'wizard_version': '1.0',
                    'scene_analysis': self.scene_analysis,
                    'validation_passed': hasattr(self, 'test_status_label') and 'passed' in self.test_status_label.cget('text')
                }
            )
            
            messagebox.showinfo(
                "Calibration Complete",
                f"Calibration applied successfully!\n\n"
                f"Settings have been saved and applied.\n"
                f"Profile saved as: {profile_name}\n\n"
                f"You can now start detection with the optimized settings."
            )
            
            self.destroy()
            
        except Exception as e:
            messagebox.showerror("Error", f"Failed to apply calibration: {e}")
            
    def on_close(self):
        """Handle dialog close"""
        if messagebox.askyesno("Cancel Calibration", "Are you sure you want to cancel the calibration wizard?"):
            self.destroy()