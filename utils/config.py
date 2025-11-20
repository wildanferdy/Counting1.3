import json
from tkinter import messagebox

from .constants import MAX_DISPLAY_WIDTH, MAX_DISPLAY_HEIGHT


class ConfigManager:
    def __init__(self):
        self.config_file = 'config.json'
        self.default_settings = {
            # Basic settings
            "confidence_threshold": 0.5,  # Dinaikkan dari 0.2 ke 0.5
            "line_offset": 50,
            "line_orientation": "Horizontal",
            "line1_y": (MAX_DISPLAY_HEIGHT // 2) - 25,
            "line1_x": (MAX_DISPLAY_WIDTH // 2) - 25,
            "video_playback_speed": 1.0,
            "start_timestamp_user": None,
            
            # Enhanced filtering settings
            "enable_roi_filter": True,
            "roi_margin_x": 0.1,  # 10% margin dari kiri-kanan
            "roi_margin_y_top": 0.3,  # 30% dari atas (area langit/bangunan)
            "roi_margin_y_bottom": 0.9,  # 90% dari atas (batas bawah)
            "max_object_size_ratio": 0.3,  # Maksimal 30% dari frame
            
            # Movement validation settings
            "enable_movement_validation": True,
            "min_tracking_frames": 15,  # Minimal 15 frame (0.5 detik) untuk validasi
            "min_movement_threshold": 0.3,  # Minimal 0.3 pixel movement per frame
            
            # Class-specific confidence thresholds
            "class_confidence": {
                "Motor": 0.4,
                "Gol I": 0.5,
                "Gol II": 0.5,
                "Gol III": 0.5,
                "Gol IV": 0.6,
                "Gol V": 0.6,
                "Gol 1": 0.5,  # Alternative naming
                "Gol 2": 0.5,
                "Gol 3": 0.5,
                "Gol 4": 0.6,
                "Gol 5": 0.6
            },
            
            # Advanced filtering options
            "enable_size_validation": True,
            "enable_aspect_ratio_validation": True,
            "enable_building_class_filter": True,
            
            # Debug settings
            "debug_filtering": False,  # Print filter decisions
            "show_filter_stats": False  # Show filtering statistics
        }

    def load_config(self):
        """Load configuration from file"""
        try:
            with open(self.config_file, 'r') as f:
                loaded_settings = json.load(f)
                # Merge with defaults to ensure all keys exist
                settings = self.default_settings.copy()
                settings.update(loaded_settings)
                
                # Validate loaded settings
                settings = self._validate_settings(settings)
                return settings
        except (FileNotFoundError, json.JSONDecodeError):
            return self.default_settings.copy()

    def save_config(self, settings):
        """Save configuration to file"""
        try:
            # Validate settings before saving
            validated_settings = self._validate_settings(settings)
            
            with open(self.config_file, 'w') as f:
                json.dump(validated_settings, f, indent=4)
            messagebox.showinfo("Info", "Configuration saved successfully.")
        except Exception as e:
            messagebox.showerror("Error", f"Error saving config: {e}")

    def _validate_settings(self, settings):
        """Validate and correct settings values"""
        validated = settings.copy()
        
        # Validate numeric ranges
        validated["confidence_threshold"] = max(0.1, min(1.0, validated.get("confidence_threshold", 0.5)))
        validated["line_offset"] = max(10, min(200, validated.get("line_offset", 50)))
        validated["video_playback_speed"] = max(0.1, min(5.0, validated.get("video_playback_speed", 1.0)))
        validated["max_object_size_ratio"] = max(0.1, min(0.8, validated.get("max_object_size_ratio", 0.3)))
        validated["min_movement_threshold"] = max(0.1, min(2.0, validated.get("min_movement_threshold", 0.3)))
        validated["min_tracking_frames"] = max(5, min(60, validated.get("min_tracking_frames", 15)))
        
        # Validate ROI margins
        validated["roi_margin_x"] = max(0.0, min(0.4, validated.get("roi_margin_x", 0.1)))
        validated["roi_margin_y_top"] = max(0.0, min(0.5, validated.get("roi_margin_y_top", 0.3)))
        validated["roi_margin_y_bottom"] = max(0.6, min(1.0, validated.get("roi_margin_y_bottom", 0.9)))
        
        # Ensure class_confidence is present and valid
        if "class_confidence" not in validated:
            validated["class_confidence"] = self.default_settings["class_confidence"].copy()
        else:
            # Validate each class confidence
            for class_name, conf in validated["class_confidence"].items():
                validated["class_confidence"][class_name] = max(0.1, min(1.0, conf))
        
        # Ensure boolean settings are boolean
        bool_settings = [
            "enable_roi_filter", "enable_movement_validation", "enable_size_validation",
            "enable_aspect_ratio_validation", "enable_building_class_filter",
            "debug_filtering", "show_filter_stats"
        ]
        
        for setting in bool_settings:
            if setting in validated:
                validated[setting] = bool(validated[setting])
        
        return validated

    def reset_to_defaults(self):
        """Reset configuration to default values"""
        try:
            with open(self.config_file, 'w') as f:
                json.dump(self.default_settings, f, indent=4)
            messagebox.showinfo("Info", "Configuration reset to defaults.")
            return self.default_settings.copy()
        except Exception as e:
            messagebox.showerror("Error", f"Error resetting config: {e}")
            return self.default_settings.copy()

    def get_filter_summary(self, settings):
        """Get summary of current filter settings"""
        summary = []
        summary.append(f"Confidence Threshold: {settings.get('confidence_threshold', 0.5):.2f}")
        summary.append(f"ROI Filter: {'Enabled' if settings.get('enable_roi_filter', True) else 'Disabled'}")
        summary.append(f"Movement Validation: {'Enabled' if settings.get('enable_movement_validation', True) else 'Disabled'}")
        summary.append(f"Max Object Size: {settings.get('max_object_size_ratio', 0.3)*100:.1f}%")
        summary.append(f"Min Movement: {settings.get('min_movement_threshold', 0.3):.1f} px/frame")
        return summary

    def export_config(self, file_path):
        """Export current configuration to specified file"""
        try:
            current_settings = self.load_config()
            with open(file_path, 'w') as f:
                json.dump(current_settings, f, indent=4)
            return True
        except Exception as e:
            messagebox.showerror("Export Error", f"Failed to export config: {e}")
            return False

    def import_config(self, file_path):
        """Import configuration from specified file"""
        try:
            with open(file_path, 'r') as f:
                imported_settings = json.load(f)
            
            # Validate imported settings
            validated_settings = self._validate_settings(imported_settings)
            
            # Save validated settings
            with open(self.config_file, 'w') as f:
                json.dump(validated_settings, f, indent=4)
            
            messagebox.showinfo("Import Success", "Configuration imported successfully.")
            return validated_settings
        except Exception as e:
            messagebox.showerror("Import Error", f"Failed to import config: {e}")
            return None