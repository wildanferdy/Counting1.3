# utils/enhanced_settings.py
"""
Enhanced settings untuk sistem deteksi kendaraan yang diperbaiki
Fokus pada penyelesaian masalah double counting dan kendaraan cepat
"""

# Default enhanced settings
ENHANCED_DEFAULT_SETTINGS = {
    # Basic detection settings
    "confidence_threshold": 0.23,  # Sedikit lebih rendah untuk kendaraan cepat
    "line_offset": 60,              # Jarak garis lebih besar
    "line_orientation": "Horizontal",
    "line1_y": 300,
    "line1_x": 300,
    "video_playback_speed": 1.0,
    "start_timestamp_user": None,
    
    # Enhanced tracking settings - KUNCI UNTUK SINGLE COUNTING
    "min_stable_frames": 3,         # Minimal frame stabil sebelum counting
    "detection_tolerance": 30,      # Tolerance garis deteksi (diperbesar untuk kendaraan cepat)
    "max_track_age": 90,           # Maksimal age vehicle sebelum dihapus (3 detik di 30fps)
    "speed_threshold": 15.0,       # Threshold kecepatan untuk kendaraan cepat (px/frame)
    
    # Performance settings
    "input_size": 640,             # Input size YOLO
    "use_half_precision": True,    # Gunakan FP16 untuk kecepatan
    "max_queue_size": 3,          # Ukuran queue processing
    "frame_skip_threshold": 0.1,   # Skip frame jika processing > 100ms
    
    # Enhanced filtering (dari sistem lama yang sudah bagus)
    "enable_roi_filter": True,
    "enable_movement_validation": True,
    "roi_margin_y_top": 0.25,      # Sedikit dikurangi untuk capture lebih banyak area
    "roi_margin_y_bottom": 0.95,
    "roi_margin_x": 0.05,          # Margin samping dikurangi
    "max_object_size_ratio": 0.35,  # Sedikit diperbesar
    "min_movement_threshold": 0.5,  # Movement threshold untuk validasi
    "min_tracking_frames": 12,      # Minimal frame untuk validasi movement
    
    # Class-specific confidence (tuned untuk akurasi)
    "class_confidence": {
        "Motor": 0.20,    # Motor sering miss, threshold rendah
        "Gol 1": 0.23,    # Mobil kecil
        "Gol 2": 0.25,    # Mobil sedang
        "Gol 3": 0.27,    # Mobil besar
        "Gol 4": 0.25,    # Truk kecil
        "Gol 5": 0.23,    # Truk besar (sering confident)
        "Gol I": 0.23,    # Alternative naming
        "Gol II": 0.25,
        "Gol III": 0.27,
        "Gol IV": 0.25,
        "Gol V": 0.23,
    }
}

# Profil untuk berbagai kondisi
SPEED_OPTIMIZED_PROFILE = {
    **ENHANCED_DEFAULT_SETTINGS,
    "confidence_threshold": 0.20,
    "detection_tolerance": 40,
    "min_stable_frames": 2,
    "input_size": 480,
    "max_queue_size": 2,
    "speed_threshold": 12.0,
    "class_confidence": {
        "Motor": 0.18,
        "Gol 1": 0.20,
        "Gol 2": 0.22,
        "Gol 3": 0.24,
        "Gol 4": 0.22,
        "Gol 5": 0.20,
        "Gol I": 0.20,
        "Gol II": 0.22,
        "Gol III": 0.24,
        "Gol IV": 0.22,
        "Gol V": 0.20,
    }
}

ACCURACY_OPTIMIZED_PROFILE = {
    **ENHANCED_DEFAULT_SETTINGS,
    "confidence_threshold": 0.35,
    "detection_tolerance": 25,
    "min_stable_frames": 5,
    "input_size": 800,
    "max_queue_size": 5,
    "use_half_precision": False,
    "speed_threshold": 20.0,
    "class_confidence": {
        "Motor": 0.30,
        "Gol 1": 0.35,
        "Gol 2": 0.37,
        "Gol 3": 0.40,
        "Gol 4": 0.35,
        "Gol 5": 0.33,
        "Gol I": 0.35,
        "Gol II": 0.37,
        "Gol III": 0.40,
        "Gol IV": 0.35,
        "Gol V": 0.33,
    }
}

BALANCED_PROFILE = ENHANCED_DEFAULT_SETTINGS  # Default is balanced

def get_profile_settings(profile_name="balanced"):
    """Get settings for specified profile"""
    profiles = {
        "speed": SPEED_OPTIMIZED_PROFILE,
        "accuracy": ACCURACY_OPTIMIZED_PROFILE,
        "balanced": BALANCED_PROFILE
    }
    return profiles.get(profile_name, BALANCED_PROFILE).copy()

def get_fast_vehicle_settings(base_settings):
    """Get optimized settings for fast vehicle detection"""
    fast_settings = base_settings.copy()
    
    # Reduce confidence for fast vehicles
    fast_settings["confidence_threshold"] *= 0.85
    
    # Increase detection tolerance
    fast_settings["detection_tolerance"] = max(fast_settings["detection_tolerance"], 35)
    
    # Reduce minimum stable frames for responsiveness
    fast_settings["min_stable_frames"] = max(1, fast_settings["min_stable_frames"] - 1)
    
    # Optimize for speed
    if fast_settings.get("input_size", 640) > 640:
        fast_settings["input_size"] = 640
    
    fast_settings["use_half_precision"] = True
    fast_settings["max_queue_size"] = min(fast_settings["max_queue_size"], 3)
    
    return fast_settings

# Panduan penggunaan settings
SETTINGS_GUIDE = {
    "confidence_threshold": {
        "description": "Threshold deteksi YOLO (0.1-1.0)",
        "recommendations": {
            "low_traffic": 0.3,
            "medium_traffic": 0.25, 
            "high_traffic": 0.2,
            "fast_vehicles": 0.18
        }
    },
    "detection_tolerance": {
        "description": "Toleransi crossing garis dalam pixel",
        "recommendations": {
            "slow_vehicles": 25,
            "normal_speed": 30,
            "fast_vehicles": 40,
            "very_fast": 50
        }
    },
    "min_stable_frames": {
        "description": "Minimal frame stabil sebelum counting",
        "recommendations": {
            "fast_response": 2,
            "balanced": 3,
            "stable_counting": 5
        }
    },
    "line_offset": {
        "description": "Jarak antara dua garis deteksi (pixel)",
        "recommendations": {
            "close_monitoring": 40,
            "normal": 60,
            "wide_coverage": 80
        }
    }
}

def validate_settings(settings):
    """Validate and fix settings values"""
    validated = settings.copy()
    
    # Ensure confidence is in valid range
    validated["confidence_threshold"] = max(0.1, min(1.0, 
        validated.get("confidence_threshold", 0.25)))
    
    # Ensure tolerance is reasonable
    validated["detection_tolerance"] = max(15, min(100, 
        validated.get("detection_tolerance", 30)))
    
    # Ensure stable frames is positive
    validated["min_stable_frames"] = max(1, min(10, 
        validated.get("min_stable_frames", 3)))
    
    # Ensure line offset is reasonable
    validated["line_offset"] = max(20, min(200, 
        validated.get("line_offset", 60)))
    
    # Validate input size
    valid_sizes = [320, 416, 480, 640, 800, 1024]
    if validated.get("input_size", 640) not in valid_sizes:
        validated["input_size"] = 640
    
    # Validate ROI margins
    validated["roi_margin_y_top"] = max(0.0, min(0.5, 
        validated.get("roi_margin_y_top", 0.25)))
    validated["roi_margin_y_bottom"] = max(0.5, min(1.0, 
        validated.get("roi_margin_y_bottom", 0.95)))
    validated["roi_margin_x"] = max(0.0, min(0.3, 
        validated.get("roi_margin_x", 0.05)))
    
    # Validate class confidence values
    if "class_confidence" in validated:
        for class_name, confidence in validated["class_confidence"].items():
            validated["class_confidence"][class_name] = max(0.1, min(1.0, confidence))
    
    return validated

def print_settings_summary(settings):
    """Print human-readable settings summary"""
    print("\n" + "="*50)
    print("ENHANCED DETECTION SETTINGS SUMMARY")
    print("="*50)
    
    print(f"Detection Confidence: {settings.get('confidence_threshold', 0.25):.2f}")
    print(f"Line Crossing Tolerance: {settings.get('detection_tolerance', 30)}px")
    print(f"Minimum Stable Frames: {settings.get('min_stable_frames', 3)}")
    print(f"Line Distance: {settings.get('line_offset', 60)}px")
    print(f"Line Orientation: {settings.get('line_orientation', 'Horizontal')}")
    
    print("\nPerformance Settings:")
    print(f"YOLO Input Size: {settings.get('input_size', 640)}")
    print(f"Half Precision: {settings.get('use_half_precision', True)}")
    print(f"Processing Queue Size: {settings.get('max_queue_size', 3)}")
    
    print("\nFiltering Settings:")
    print(f"ROI Filter: {settings.get('enable_roi_filter', True)}")
    print(f"Movement Validation: {settings.get('enable_movement_validation', True)}")
    print(f"Max Object Size Ratio: {settings.get('max_object_size_ratio', 0.35)}")
    
    if settings.get('class_confidence'):
        print("\nClass-Specific Confidence:")
        for class_name, conf in settings['class_confidence'].items():
            print(f"  {class_name}: {conf:.2f}")
    
    print("="*50)

# Troubleshooting recommendations
TROUBLESHOOTING_GUIDE = {
    "double_counting": {
        "problem": "Kendaraan dihitung berkali-kali",
        "solutions": [
            "Pastikan min_stable_frames >= 3",
            "Periksa line_offset tidak terlalu kecil (min 40px)",
            "Gunakan detection_tolerance yang sesuai (25-35px)",
            "Pastikan sistem enhanced tracker digunakan"
        ]
    },
    "missing_fast_vehicles": {
        "problem": "Kendaraan cepat tidak terdeteksi",
        "solutions": [
            "Turunkan confidence_threshold (0.18-0.22)",
            "Perbesar detection_tolerance (35-45px)", 
            "Kurangi min_stable_frames (2-3)",
            "Gunakan speed profile",
            "Periksa line_offset tidak terlalu besar"
        ]
    },
    "too_many_false_positives": {
        "problem": "Terlalu banyak deteksi palsu",
        "solutions": [
            "Naikkan confidence_threshold (0.3-0.4)",
            "Enable semua filter (ROI, movement, size)",
            "Sesuaikan ROI margins",
            "Gunakan accuracy profile",
            "Periksa class_confidence settings"
        ]
    },
    "slow_processing": {
        "problem": "Processing lambat/lag",
        "solutions": [
            "Kurangi input_size (480 atau 320)",
            "Enable use_half_precision",
            "Kurangi max_queue_size (2-3)",
            "Gunakan speed profile",
            "Periksa hardware GPU support"
        ]
    }
}