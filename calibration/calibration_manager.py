# calibration/calibration_manager.py
import json
import os
import time
import threading
from datetime import datetime
from tkinter import messagebox, filedialog
import cv2
import numpy as np
from collections import defaultdict, deque


class CalibrationManager:
    def __init__(self, app):
        self.app = app
        self.profiles_dir = "calibration_profiles"
        self.test_results_dir = "calibration_tests"
        
        # Create directories
        os.makedirs(self.profiles_dir, exist_ok=True)
        os.makedirs(self.test_results_dir, exist_ok=True)
        
        # Calibration state
        self.is_calibrating = False
        self.calibration_data = {}
        self.test_metrics = {}
        self.realtime_stats = {
            'detections': 0,
            'false_positives_estimated': 0,
            'processing_fps': 0,
            'accuracy_estimate': 0.0
        }
        
        # Performance tracking
        self.detection_history = deque(maxlen=100)
        self.performance_history = deque(maxlen=50)
        
    def start_calibration_mode(self):
        """Start calibration mode with enhanced logging"""
        self.is_calibrating = True
        self.calibration_data = {
            'start_time': datetime.now(),
            'detections': [],
            'settings_tested': [],
            'performance_metrics': []
        }
        self.realtime_stats = {
            'detections': 0,
            'false_positives_estimated': 0,
            'processing_fps': 0,
            'accuracy_estimate': 0.0
        }
        
    def stop_calibration_mode(self):
        """Stop calibration mode"""
        self.is_calibrating = False
        
    def log_detection_event(self, detection_data):
        """Log detection event during calibration"""
        if not self.is_calibrating:
            return
            
        timestamp = time.time()
        self.calibration_data['detections'].append({
            'timestamp': timestamp,
            'vehicle_id': detection_data.get('vehicle_id'),
            'class': detection_data.get('class'),
            'confidence': detection_data.get('confidence'),
            'bbox': detection_data.get('bbox'),
            'direction': detection_data.get('direction')
        })
        
        # Update real-time stats
        self.update_realtime_stats()
        
    def update_realtime_stats(self):
        """Update real-time calibration statistics"""
        if not self.calibration_data['detections']:
            return
            
        recent_detections = [d for d in self.calibration_data['detections'] 
                           if time.time() - d['timestamp'] < 10.0]  # Last 10 seconds
        
        self.realtime_stats['detections'] = len(recent_detections)
        
        # Estimate false positives based on detection patterns
        if len(recent_detections) > 5:
            confidence_values = [d['confidence'] for d in recent_detections]
            low_confidence_ratio = len([c for c in confidence_values if c < 0.4]) / len(confidence_values)
            self.realtime_stats['false_positives_estimated'] = int(len(recent_detections) * low_confidence_ratio)
            
        # Calculate processing FPS
        if len(self.performance_history) > 0:
            self.realtime_stats['processing_fps'] = np.mean(list(self.performance_history))
            
        # Estimate accuracy based on confidence distribution
        if confidence_values:
            high_conf_ratio = len([c for c in confidence_values if c > 0.6]) / len(confidence_values)
            self.realtime_stats['accuracy_estimate'] = high_conf_ratio * 100
            
    def log_performance_metric(self, fps):
        """Log performance metrics"""
        self.performance_history.append(fps)
        
    def calculate_optimal_line_distance(self, video_fps, estimated_speed_kmh, vehicle_type="car"):
        """Calculate optimal line distance based on physics"""
        # Convert speed to m/s
        speed_ms = estimated_speed_kmh / 3.6
        
        # Assume pixel scale (this should be calibrated per camera setup)
        # For now, use reasonable defaults
        pixels_per_meter = 50  # This should be configurable
        
        # Basic calculation: distance = speed * time_between_frames * safety_factor
        time_between_frames = 1.0 / video_fps
        basic_distance = speed_ms * time_between_frames * pixels_per_meter
        
        # Vehicle type factors
        vehicle_factors = {
            "motor": 0.8,     # Smaller, faster
            "car": 1.0,       # Standard
            "truck": 1.3,     # Larger, needs more space
            "bus": 1.5        # Largest
        }
        
        safety_factor = vehicle_factors.get(vehicle_type, 1.0)
        optimal_distance = basic_distance * safety_factor
        
        # Ensure reasonable bounds
        optimal_distance = max(20, min(200, optimal_distance))
        
        return int(optimal_distance)
        
    def analyze_scene(self, frame):
        """Analyze scene and suggest optimal settings"""
        if frame is None:
            return {}
            
        h, w = frame.shape[:2]
        
        # Convert to grayscale for analysis
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        
        # Detect horizontal/vertical lines to determine road orientation
        edges = cv2.Canny(gray, 50, 150, apertureSize=3)
        lines = cv2.HoughLines(edges, 1, np.pi/180, threshold=100)
        
        horizontal_lines = 0
        vertical_lines = 0
        
        if lines is not None:
            for rho, theta in lines[:10]:  # Check first 10 lines
                angle = theta * 180 / np.pi
                if 45 <= angle <= 135:  # Horizontal-ish
                    horizontal_lines += 1
                else:  # Vertical-ish
                    vertical_lines += 1
                    
        # Suggest orientation
        suggested_orientation = "Horizontal" if vertical_lines > horizontal_lines else "Vertical"
        
        # Analyze brightness for confidence adjustment
        brightness = np.mean(gray)
        suggested_confidence = 0.3 if brightness > 100 else 0.4  # Lower confidence for darker scenes
        
        # Analyze top portion for buildings/sky
        top_portion = gray[:h//3, :]
        top_brightness = np.mean(top_portion)
        
        # Suggest ROI margins
        if top_brightness > brightness * 1.2:  # Bright sky detected
            roi_top_margin = 0.4
        else:  # Buildings or low angle
            roi_top_margin = 0.3
            
        return {
            'suggested_orientation': suggested_orientation,
            'suggested_confidence': suggested_confidence,
            'roi_top_margin': roi_top_margin,
            'scene_brightness': brightness,
            'analysis_confidence': 0.8  # How confident we are in suggestions
        }
        
    def run_settings_test(self, test_duration=60, test_type="standard"):
        """Run comprehensive settings test"""
        if not self.app.video_handler.video_source:
            messagebox.showwarning("Warning", "No video source loaded for testing.")
            return None
            
        # Start calibration mode
        self.start_calibration_mode()
        
        # Store original settings
        original_settings = self.app.settings.copy()
        
        test_results = {
            'start_time': datetime.now(),
            'test_duration': test_duration,
            'test_type': test_type,
            'settings': original_settings.copy(),
            'metrics': {},
            'recommendations': []
        }
        
        # Start detection if not running
        was_running = self.app.detection_manager.running
        if not was_running:
            self.app.detection_manager.start_detection()
            
        start_time = time.time()
        
        try:
            # Run test for specified duration
            while time.time() - start_time < test_duration:
                time.sleep(0.1)
                
                # Update metrics periodically
                if int((time.time() - start_time) * 10) % 10 == 0:
                    self.update_realtime_stats()
                    
        except KeyboardInterrupt:
            pass
            
        # Stop detection if we started it
        if not was_running:
            self.app.detection_manager.stop_detection()
            
        # Calculate final metrics
        total_detections = len(self.calibration_data['detections'])
        avg_confidence = np.mean([d['confidence'] for d in self.calibration_data['detections']]) if total_detections > 0 else 0
        
        test_results['metrics'] = {
            'total_detections': total_detections,
            'detections_per_minute': total_detections / (test_duration / 60),
            'average_confidence': avg_confidence,
            'estimated_false_positives': self.realtime_stats['false_positives_estimated'],
            'processing_fps': self.realtime_stats['processing_fps'],
            'accuracy_estimate': self.realtime_stats['accuracy_estimate']
        }
        
        # Generate recommendations
        test_results['recommendations'] = self.generate_recommendations(test_results['metrics'])
        
        # Save test results
        self.save_test_results(test_results)
        
        # Stop calibration mode
        self.stop_calibration_mode()
        
        return test_results
        
    def generate_recommendations(self, metrics):
        """Generate recommendations based on test results"""
        recommendations = []
        
        # Check detection rate
        if metrics['detections_per_minute'] < 5:
            recommendations.append({
                'type': 'warning',
                'message': 'Low detection rate. Consider lowering confidence threshold.',
                'action': 'Lower confidence to 0.3 or enable more sensitive filters.'
            })
        elif metrics['detections_per_minute'] > 60:
            recommendations.append({
                'type': 'warning', 
                'message': 'Very high detection rate. Possible false positives.',
                'action': 'Increase confidence threshold or enable stricter filtering.'
            })
            
        # Check confidence levels
        if metrics['average_confidence'] < 0.4:
            recommendations.append({
                'type': 'info',
                'message': 'Low average confidence detected.',
                'action': 'Consider improving lighting or camera angle.'
            })
            
        # Check performance
        if metrics['processing_fps'] < 15:
            recommendations.append({
                'type': 'warning',
                'message': 'Low processing FPS detected.',
                'action': 'Reduce video resolution or optimize filter settings.'
            })
            
        # Check accuracy estimate
        if metrics['accuracy_estimate'] < 80:
            recommendations.append({
                'type': 'critical',
                'message': 'Low accuracy estimate.',
                'action': 'Enable advanced filtering and recalibrate detection lines.'
            })
        elif metrics['accuracy_estimate'] > 95:
            recommendations.append({
                'type': 'success',
                'message': 'Excellent accuracy detected!',
                'action': 'Current settings are optimal.'
            })
            
        return recommendations
        
    def save_calibration_profile(self, name, settings, metadata=None):
        """Save calibration profile to file"""
        profile_data = {
            'name': name,
            'settings': settings,
            'created_date': datetime.now().isoformat(),
            'metadata': metadata or {},
            'version': '1.0'
        }
        
        filename = os.path.join(self.profiles_dir, f"{name}.json")
        try:
            with open(filename, 'w') as f:
                json.dump(profile_data, f, indent=4)
            return True
        except Exception as e:
            messagebox.showerror("Error", f"Failed to save profile: {e}")
            return False
            
    def load_calibration_profile(self, name):
        """Load calibration profile from file"""
        filename = os.path.join(self.profiles_dir, f"{name}.json")
        try:
            with open(filename, 'r') as f:
                profile_data = json.load(f)
            return profile_data['settings']
        except Exception as e:
            messagebox.showerror("Error", f"Failed to load profile: {e}")
            return None
            
    def list_calibration_profiles(self):
        """List all available calibration profiles"""
        profiles = []
        for filename in os.listdir(self.profiles_dir):
            if filename.endswith('.json'):
                name = filename[:-5]  # Remove .json extension
                profiles.append(name)
        return profiles
        
    def save_test_results(self, test_results):
        """Save test results to file"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = os.path.join(self.test_results_dir, f"test_{timestamp}.json")
        
        try:
            # Make results JSON serializable
            serializable_results = self.make_json_serializable(test_results)
            with open(filename, 'w') as f:
                json.dump(serializable_results, f, indent=4)
        except Exception as e:
            print(f"Failed to save test results: {e}")
            
    def make_json_serializable(self, obj):
        """Convert object to JSON serializable format"""
        if isinstance(obj, datetime):
            return obj.isoformat()
        elif isinstance(obj, np.floating):
            return float(obj)
        elif isinstance(obj, np.integer):
            return int(obj)
        elif isinstance(obj, dict):
            return {k: self.make_json_serializable(v) for k, v in obj.items()}
        elif isinstance(obj, list):
            return [self.make_json_serializable(item) for item in obj]
        else:
            return obj
            
    def export_calibration_config(self):
        """Export current calibration to file"""
        config_data = {
            'settings': self.app.settings.copy(),
            'export_date': datetime.now().isoformat(),
            'app_version': '1.0',
            'calibration_metadata': {
                'video_source': str(self.app.video_handler.video_source),
                'video_fps': self.app.video_handler.video_fps,
                'is_webcam': self.app.video_handler.is_webcam
            }
        }
        
        filename = filedialog.asksaveasfilename(
            defaultextension=".json",
            filetypes=[("JSON files", "*.json"), ("All files", "*.*")],
            title="Export Calibration Configuration"
        )
        
        if filename:
            try:
                serializable_config = self.make_json_serializable(config_data)
                with open(filename, 'w') as f:
                    json.dump(serializable_config, f, indent=4)
                messagebox.showinfo("Success", f"Configuration exported to {filename}")
                return True
            except Exception as e:
                messagebox.showerror("Error", f"Failed to export configuration: {e}")
                return False
        return False
        
    def import_calibration_config(self):
        """Import calibration configuration from file"""
        filename = filedialog.askopenfilename(
            filetypes=[("JSON files", "*.json"), ("All files", "*.*")],
            title="Import Calibration Configuration"
        )
        
        if filename:
            try:
                with open(filename, 'r') as f:
                    config_data = json.load(f)
                    
                # Validate config structure
                if 'settings' not in config_data:
                    messagebox.showerror("Error", "Invalid configuration file format.")
                    return False
                    
                # Apply settings
                self.app.settings.update(config_data['settings'])
                self.app.new_settings_to_send = self.app.settings.copy()
                
                # Update display
                if self.app.video_handler.video_source:
                    self.app.video_handler.display_first_frame()
                    
                # Save to current config
                self.app.config_manager.save_config(self.app.settings)
                
                messagebox.showinfo("Success", "Configuration imported successfully!")
                return True
                
            except Exception as e:
                messagebox.showerror("Error", f"Failed to import configuration: {e}")
                return False
        return False
        
    def get_calibration_statistics(self):
        """Get current calibration statistics"""
        return {
            'realtime_stats': self.realtime_stats.copy(),
            'is_calibrating': self.is_calibrating,
            'total_profiles': len(self.list_calibration_profiles()),
            'calibration_session_duration': 
                (datetime.now() - self.calibration_data['start_time']).total_seconds() 
                if self.is_calibrating else 0
        }