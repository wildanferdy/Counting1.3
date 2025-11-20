import tkinter as tk
from tkinter import messagebox

from gui.dialogs import EnhancedSettingsDialog, TimeDialog
import datetime
import os


class MenuManager:
    def __init__(self, app):
        self.app = app

    def create_menu(self):
        """Create application menu bar"""
        menubar = tk.Menu(self.app.root)
        self.app.root.config(menu=menubar)

        # File menu
        file_menu = tk.Menu(menubar, tearoff=0)
        file_menu.add_command(label="Export Data", command=self.app.save_to_excel)
        file_menu.add_separator()
        file_menu.add_command(label="Exit", command=self.app.on_closing)
        menubar.add_cascade(label="File", menu=file_menu)

        # Source menu
        source_menu = tk.Menu(menubar, tearoff=0)
        source_menu.add_command(label="Load Video File", command=self.app.video_handler.load_video)
        source_menu.add_command(label="Use Webcam", command=self.app.video_handler.open_webcam_selection)
        menubar.add_cascade(label="Source", menu=source_menu)

        # Settings menu
        settings_menu = tk.Menu(menubar, tearoff=0)
        settings_menu.add_command(label="Detection Configuration", command=self.open_settings_dialog)
        settings_menu.add_command(label="Time Settings", command=self.open_time_dialog)
        settings_menu.add_separator()
        settings_menu.add_command(label="Reset to Defaults", command=self.reset_all_settings)
        menubar.add_cascade(label="Settings", menu=settings_menu)

        # View menu
        view_menu = tk.Menu(menubar, tearoff=0)
        view_menu.add_command(label="Clear Data", command=self.clear_all_data)
        view_menu.add_command(label="Show Filter Statistics", command=self.show_filter_stats)
        menubar.add_cascade(label="View", menu=view_menu)

        # Help menu
        help_menu = tk.Menu(menubar, tearoff=0)
        help_menu.add_command(label="About Filtering", command=self.show_filter_help)
        help_menu.add_command(label="Troubleshooting", command=self.show_troubleshooting)
        menubar.add_cascade(label="Help", menu=help_menu)

    def open_settings_dialog(self):
        """Open enhanced settings configuration dialog"""
        def apply_settings_callback(new_settings):
            # Update app settings with all new settings
            self.app.settings.update(new_settings)
            
            # Mark settings for sending to detection process
            self.app.new_settings_to_send = self.app.settings.copy()

            # Apply speed settings for video files only
            if (self.app.video_handler.video_source and 
                self.app.video_handler.video_fps > 0 and 
                not self.app.video_handler.is_webcam):
                self.app.video_handler.frame_delay = ((1.0 / self.app.video_handler.video_fps) / 
                                                     self.app.settings['video_playback_speed'])

            # Show confirmation message with filter summary
            filter_summary = self.app.config_manager.get_filter_summary(self.app.settings)
            summary_text = "Settings applied successfully!\n\nActive Filters:\n" + "\n".join(f"• {s}" for s in filter_summary)
            
            if self.app.detection_manager.running:
                summary_text += "\n\nSettings will take effect on next frame."
            elif self.app.video_handler.video_source:
                self.app.video_handler.display_first_frame()
                summary_text += "\n\nPreview updated with new detection lines."

            messagebox.showinfo("Settings Applied", summary_text)

            # Save configuration
            self.app.config_manager.save_config(self.app.settings)

        EnhancedSettingsDialog(self.app.root, self.app.settings.copy(), apply_settings_callback)

    def open_time_dialog(self):
        """Open time configuration dialog"""
        def apply_time_callback(timestamp_str):
            self.app.settings["start_timestamp_user"] = timestamp_str
            self.app.new_settings_to_send = self.app.settings.copy()
            self.app.config_manager.save_config(self.app.settings)
            messagebox.showinfo("Time Set", f"Start time set to: {timestamp_str}")

        # Determine default timestamp
        if (self.app.video_handler.video_source and 
            isinstance(self.app.video_handler.video_source, str) and 
            os.path.exists(self.app.video_handler.video_source)):
            try:
                # Use video file timestamp
                timestamp = os.path.getmtime(self.app.video_handler.video_source)
                video_time = datetime.datetime.fromtimestamp(timestamp)
                default_timestamp = video_time.strftime("%Y-%m-%d %H:%M:%S")
            except Exception:
                default_timestamp = self.app.settings.get("start_timestamp_user")
        else:
            default_timestamp = self.app.settings.get("start_timestamp_user")

        TimeDialog(self.app.root, default_timestamp, apply_time_callback)

    def reset_all_settings(self):
        """Reset all settings to defaults"""
        if messagebox.askyesno("Reset Settings", 
                              "This will reset ALL settings to defaults.\n\n"
                              "This includes:\n"
                              "• Detection thresholds\n"
                              "• Filter settings\n"
                              "• Line configuration\n"
                              "• Class-specific settings\n\n"
                              "Continue?"):
            
            # Reset to defaults
            self.app.settings = self.app.config_manager.reset_to_defaults()
            self.app.new_settings_to_send = self.app.settings.copy()
            
            # Update video display if available
            if self.app.video_handler.video_source:
                self.app.video_handler.display_first_frame()
            
            messagebox.showinfo("Reset Complete", 
                              "All settings have been reset to defaults.\n"
                              "Changes will take effect on next detection.")

    def clear_all_data(self):
        """Clear all detection data"""
        if messagebox.askyesno("Clear Data", 
                              "This will clear all detection data.\n\n"
                              "Continue?"):
            self.app.data_manager.reset_data(clear_all=True)
            messagebox.showinfo("Data Cleared", "All detection data has been cleared.")

    def show_filter_stats(self):
        """Show current filter statistics"""
        settings = self.app.settings
        
        stats_text = "Current Filter Configuration:\n\n"
        
        # Basic settings
        stats_text += f"Detection Confidence: {settings.get('confidence_threshold', 0.5):.2f}\n"
        stats_text += f"Line Distance: {settings.get('line_offset', 50)} pixels\n"
        stats_text += f"Line Orientation: {settings.get('line_orientation', 'Horizontal')}\n\n"
        
        # Filter status
        stats_text += "Active Filters:\n"
        stats_text += f"• ROI Filter: {'✓' if settings.get('enable_roi_filter', True) else '✗'}\n"
        stats_text += f"• Size Validation: {'✓' if settings.get('enable_size_validation', True) else '✗'}\n"
        stats_text += f"• Movement Validation: {'✓' if settings.get('enable_movement_validation', True) else '✗'}\n"
        stats_text += f"• Aspect Ratio Check: {'✓' if settings.get('enable_aspect_ratio_validation', True) else '✗'}\n"
        stats_text += f"• Building Class Filter: {'✓' if settings.get('enable_building_class_filter', True) else '✗'}\n\n"
        
        # ROI settings
        if settings.get('enable_roi_filter', True):
            stats_text += "ROI Settings:\n"
            stats_text += f"• Top Margin: {settings.get('roi_margin_y_top', 0.3)*100:.1f}%\n"
            stats_text += f"• Side Margin: {settings.get('roi_margin_x', 0.1)*100:.1f}%\n"
            stats_text += f"• Max Object Size: {settings.get('max_object_size_ratio', 0.3)*100:.1f}%\n\n"
        
        # Movement settings
        if settings.get('enable_movement_validation', True):
            stats_text += "Movement Validation:\n"
            stats_text += f"• Min Movement: {settings.get('min_movement_threshold', 0.3):.1f} px/frame\n"
            stats_text += f"• Min Tracking: {settings.get('min_tracking_frames', 15)} frames\n\n"
        
        # Class confidence
        stats_text += "Class Confidence Thresholds:\n"
        class_conf = settings.get('class_confidence', {})
        for class_name, confidence in class_conf.items():
            stats_text += f"• {class_name}: {confidence:.2f}\n"
        
        messagebox.showinfo("Filter Statistics", stats_text)

    def show_filter_help(self):
        """Show help about filtering system"""
        help_text = """Enhanced Vehicle Detection Filters

The system uses multiple filters to reduce false detections:

ROI (Region of Interest) Filter:
• Restricts detection to road areas only
• Filters out objects in sky/building areas
• Configurable margins for different camera angles

Size Validation:
• Filters objects that are too large (likely buildings)
• Filters objects that are too small (noise/artifacts)
• Class-specific size limits

Movement Validation:
• Tracks object movement over time
• Filters stationary objects (buildings, poles)
• Requires minimum movement to confirm vehicles

Aspect Ratio Validation:
• Checks if object shape matches vehicle proportions
• Different limits for motorcycles vs trucks
• Filters unusually shaped objects

Building Class Filter:
• Automatically filters known building classes
• Prevents house/wall detections
• Maintains focus on vehicle classes only

Class-Specific Confidence:
• Different confidence thresholds per vehicle type
• Higher thresholds for easily confused classes
• Optimized for each vehicle category

Tips:
• Enable all filters for best results
• Adjust ROI margins based on camera angle
• Lower confidence = more detections (but more false positives)
• Higher confidence = fewer detections (but more accurate)"""
        
        messagebox.showinfo("Filter Help", help_text)

    def show_troubleshooting(self):
        """Show troubleshooting guide"""
        troubleshoot_text = """Troubleshooting Detection Issues

Problem: Houses detected as vehicles
Solution:
• Enable ROI Filter to limit detection area
• Increase confidence threshold (0.5 or higher)
• Enable Size Validation with max ratio 0.3
• Enable Building Class Filter

Problem: Too few vehicle detections
Solution:
• Lower confidence threshold (0.3-0.4)
• Adjust ROI margins to include more road area
• Disable movement validation temporarily
• Check class-specific confidence settings

Problem: Stationary objects counted as vehicles
Solution:
• Enable Movement Validation
• Increase min movement threshold
• Increase min tracking frames
• Check ROI filter coverage

Problem: Fast vehicles not detected
Solution:
• Lower confidence threshold
• Reduce min tracking frames (5-10)
• Lower movement threshold (0.1-0.2)
• Check detection line position
x
Problem: Wrong vehicle classification
Solution:
• Adjust class-specific confidence
• Retrain model with better dataset
• Enable debug logging to see classifications

General Tips:
• Test with different filter combinations
• Use debug mode to see what's being filtered
• Adjust settings gradually, one at a time
• Export/import configs to save good settings"""
        
        messagebox.showinfo("Troubleshooting", troubleshoot_text)