import os
import sys


def format_time(seconds):
    """Format seconds to MM:SS format"""
    m, s = divmod(int(seconds), 60)
    return f"{m:02}:{s:02}"


def resource_path(relative_path):
    """Get absolute path to resource, works for dev and for PyInstaller"""
    try:
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.abspath(".")
    return os.path.join(base_path, relative_path)


def validate_camera_index(index):
    """Validate if camera index is valid"""
    try:
        return isinstance(index, int) and index >= 0
    except:
        return False


def safe_int_conversion(value, default=0):
    """Safely convert value to int with default fallback"""
    try:
        return int(value)
    except (ValueError, TypeError):
        return default


def safe_float_conversion(value, default=0.0):
    """Safely convert value to float with default fallback"""
    try:
        return float(value)
    except (ValueError, TypeError):
        return default