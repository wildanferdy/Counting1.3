# core/detection_process.py
import cv2
from ultralytics import YOLO
import os
import sys
import math
from multiprocessing import Queue, Event
from queue import Empty
from datetime import datetime, timedelta

MAX_DISPLAY_WIDTH = 960
MAX_DISPLAY_HEIGHT = 720

def resource_path(relative_path):
    try:
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.abspath(".")
    return os.path.join(base_path, relative_path)

def calculate_distance(pos1, pos2):
    """Hitung jarak euclidean antara dua posisi"""
    return math.sqrt((pos1[0] - pos2[0])**2 + (pos1[1] - pos2[1])**2)

def is_in_road_area(box, frame_shape, settings):
    """
    Filter untuk memastikan deteksi hanya di area jalan
    box: [x1, y1, x2, y2]
    frame_shape: (height, width)
    """
    h, w = frame_shape[:2]
    x1, y1, x2, y2 = box
    
    # Ambil setting ROI atau gunakan default
    road_y_start = h * settings.get('roi_margin_y_top', 0.3)  # 30% dari atas frame
    road_y_end = h * settings.get('roi_margin_y_bottom', 0.9)  # 90% dari atas frame
    road_x_start = w * settings.get('roi_margin_x', 0.1)  # 10% dari kiri frame  
    road_x_end = w * (1.0 - settings.get('roi_margin_x', 0.1))  # 90% dari kiri frame
    
    # Hitung center point objek
    center_x = (x1 + x2) / 2
    center_y = (y1 + y2) / 2
    
    # Cek apakah center point berada di area jalan
    return (road_x_start <= center_x <= road_x_end and 
            road_y_start <= center_y <= road_y_end)

def calculate_object_size_ratio(box, frame_shape):
    """
    Hitung rasio ukuran objek terhadap frame
    Rumah biasanya lebih besar dari kendaraan
    """
    h, w = frame_shape[:2]
    x1, y1, x2, y2 = box
    
    obj_width = x2 - x1
    obj_height = y2 - y1
    obj_area = obj_width * obj_height
    
    frame_area = h * w
    size_ratio = obj_area / frame_area
    
    return size_ratio

def is_likely_vehicle(box, frame_shape, confidence, settings):
    """
    Validasi apakah objek kemungkinan kendaraan
    """
    # Filter berdasarkan lokasi (jika ROI enabled)
    if settings.get('enable_roi_filter', True):
        if not is_in_road_area(box, frame_shape, settings):
            return False, "Outside ROI area"
    
    # Filter berdasarkan ukuran (rumah biasanya terlalu besar)
    size_ratio = calculate_object_size_ratio(box, frame_shape)
    max_size_ratio = settings.get('max_object_size_ratio', 0.3)
    if size_ratio > max_size_ratio:  # Jika objek lebih dari threshold frame, kemungkinan bukan kendaraan
        return False, f"Too large (size ratio: {size_ratio:.3f})"
    
    # Filter berdasarkan ukuran minimal (terlalu kecil juga tidak valid)
    if size_ratio < 0.005:  # Kurang dari 0.5% frame
        return False, f"Too small (size ratio: {size_ratio:.3f})"
    
    # Filter berdasarkan aspect ratio
    x1, y1, x2, y2 = box
    width = x2 - x1
    height = y2 - y1
    aspect_ratio = width / height if height > 0 else 0
    
    # Kendaraan biasanya memiliki aspect ratio tertentu
    if aspect_ratio < 0.5 or aspect_ratio > 5.0:
        return False, f"Invalid aspect ratio: {aspect_ratio:.2f}"
    
    return True, "Valid vehicle"

def get_class_specific_confidence(class_name, settings):
    """Get confidence threshold for specific class"""
    class_confidence = settings.get('class_confidence', {})
    return class_confidence.get(class_name, settings.get('confidence_threshold', 0.5))

def validate_class_detection(class_name, confidence, box, frame_shape, settings):
    """Validate detection based on class-specific rules"""
    
    # Get class-specific confidence threshold
    required_confidence = get_class_specific_confidence(class_name, settings)
    if confidence < required_confidence:
        return False, f"Confidence {confidence:.2f} below threshold {required_confidence:.2f}"
    
    # Class-specific size validation
    size_ratio = calculate_object_size_ratio(box, frame_shape)
    
    size_limits = {
        "Motor": (0.005, 0.15),    # Motorcycles: 0.5% - 15% of frame
        "Gol I": (0.01, 0.25),    # Small cars: 1% - 25% of frame  
        "Gol II": (0.015, 0.30),  # Medium cars: 1.5% - 30% of frame
        "Gol III": (0.02, 0.35),  # Large cars: 2% - 35% of frame
        "Gol IV": (0.03, 0.50),   # Trucks: 3% - 50% of frame
        "Gol V": (0.04, 0.60),    # Large trucks: 4% - 60% of frame
        "Gol 1": (0.01, 0.25),    # Alternative naming
        "Gol 2": (0.015, 0.30),
        "Gol 3": (0.02, 0.35),
        "Gol 4": (0.03, 0.50),
        "Gol 5": (0.04, 0.60),
    }
    
    if class_name in size_limits:
        min_size, max_size = size_limits[class_name]
        if not (min_size <= size_ratio <= max_size):
            return False, f"Size ratio {size_ratio:.3f} outside valid range {min_size}-{max_size}"
    
    # Class-specific aspect ratio validation
    x1, y1, x2, y2 = box
    width = x2 - x1
    height = y2 - y1
    aspect_ratio = width / height if height > 0 else 0
    
    aspect_limits = {
        "Motor": (0.8, 2.5),      # Motorcycles: narrower
        "Gol I": (1.2, 2.8),     # Cars: typical car proportions
        "Gol II": (1.2, 2.8),    
        "Gol III": (1.2, 2.8),
        "Gol IV": (1.5, 4.0),    # Trucks: can be longer
        "Gol V": (1.5, 5.0),     # Large trucks: very long
        "Gol 1": (1.2, 2.8),     # Alternative naming
        "Gol 2": (1.2, 2.8),
        "Gol 3": (1.2, 2.8),
        "Gol 4": (1.5, 4.0),
        "Gol 5": (1.5, 5.0),
    }
    
    if class_name in aspect_limits:
        min_aspect, max_aspect = aspect_limits[class_name]
        if not (min_aspect <= aspect_ratio <= max_aspect):
            return False, f"Aspect ratio {aspect_ratio:.2f} outside valid range {min_aspect}-{max_aspect}"
    
    return True, "Valid detection"

# Blacklist untuk class yang sering salah deteksi
BUILDING_CLASSES = ["house", "building", "wall", "fence", "structure", "person", "people"]

def is_building_class(class_name):
    """Check if detected class is likely a building"""
    class_lower = class_name.lower()
    return any(building in class_lower for building in BUILDING_CLASSES)

def initialize_vehicle_state(track_id, box, golongan, line, frame_num):
    """Inisialisasi state kendaraan dengan tracking posisi"""
    center_x = (box[0] + box[2]) / 2
    center_y = (box[1] + box[3]) / 2
    
    return {
        'line': line,
        'golongan': golongan,
        'counted': False,
        'last_seen': frame_num,
        'positions': [(center_x, center_y)],  # Track posisi
        'first_seen': frame_num,
        'is_moving': False,
        'total_distance': 0.0,
        'valid_detections': 0  # Counter untuk deteksi yang valid
    }

def update_vehicle_movement(vehicle_state, new_box, frame_num):
    """Update tracking movement kendaraan"""
    center_x = (new_box[0] + new_box[2]) / 2
    center_y = (new_box[1] + new_box[3]) / 2
    new_position = (center_x, center_y)
    
    # Tambahkan posisi baru
    vehicle_state['positions'].append(new_position)
    vehicle_state['last_seen'] = frame_num
    vehicle_state['valid_detections'] += 1
    
    # Hitung total pergerakan jika ada posisi sebelumnya
    if len(vehicle_state['positions']) > 1:
        last_pos = vehicle_state['positions'][-2]
        distance = calculate_distance(last_pos, new_position)
        vehicle_state['total_distance'] += distance
    
    # Tentukan apakah objek bergerak (minimal movement dalam period tertentu)
    frames_tracked = frame_num - vehicle_state['first_seen']
    if frames_tracked > 15:  # Setelah 0.5 detik (30 fps)
        avg_movement = vehicle_state['total_distance'] / frames_tracked
        vehicle_state['is_moving'] = avg_movement > 0.3  # Minimal 0.3 pixel per frame
    
    # Batasi history posisi (hanya simpan 30 frame terakhir)
    if len(vehicle_state['positions']) > 30:
        vehicle_state['positions'] = vehicle_state['positions'][-30:]

def is_valid_vehicle_movement(vehicle_state, settings, min_tracking_frames=15):
    """Validasi apakah objek bergerak seperti kendaraan"""
    if not settings.get('enable_movement_validation', True):
        return True  # Skip validation jika disabled
        
    frames_tracked = vehicle_state['last_seen'] - vehicle_state['first_seen']
    
    # Jika belum cukup lama di-track, anggap valid dulu
    if frames_tracked < min_tracking_frames:
        return True
    
    # Jika sudah cukup lama tapi tidak bergerak, kemungkinan bukan kendaraan
    min_movement = settings.get('min_movement_threshold', 0.3)
    if frames_tracked > min_tracking_frames:
        avg_movement = vehicle_state['total_distance'] / frames_tracked
        if avg_movement < min_movement:
            return False
    
    return True

def enhanced_detection_validation(results, settings, frame, model):
    """Enhanced detection validation with multiple filters"""
    valid_detections = []
    
    if results[0].boxes.id is not None:
        track_ids = results[0].boxes.id.int().cpu().tolist()
        class_ids = results[0].boxes.cls.int().cpu().tolist()
        boxes = results[0].boxes.xyxy.cpu()
        confidences = results[0].boxes.conf.cpu().tolist()
        
        for i in range(len(track_ids)):
            track_id = track_ids[i]
            class_id = class_ids[i]
            box = boxes[i].tolist()
            confidence = confidences[i]
            
            yolo_class_name = model.names[class_id]
            
            # Filter 1: Skip building classes immediately
            if is_building_class(yolo_class_name):
                print(f"[FILTER] Skipped ID {track_id}: {yolo_class_name} (building class)")
                continue
            
            # Filter 2: General vehicle-like validation
            is_valid_vehicle_check, reason = is_likely_vehicle(box, frame.shape, confidence, settings)
            if not is_valid_vehicle_check:
                print(f"[FILTER] Skipped ID {track_id}: {yolo_class_name} ({reason})")
                continue
            
            # Filter 3: Class-specific validation
            is_valid_class, class_reason = validate_class_detection(yolo_class_name, confidence, box, frame.shape, settings)
            if not is_valid_class:
                print(f"[FILTER] Skipped ID {track_id}: {yolo_class_name} ({class_reason})")
                continue
            
            # If all filters pass, add to valid detections
            valid_detections.append({
                'track_id': track_id,
                'class_name': yolo_class_name,
                'box': box,
                'confidence': confidence,
                'class_id': class_id
            })
            
    return valid_detections

def detection_process(frame_q: Queue, result_q: Queue, stop_event: Event, initial_settings: dict):
    print(f"Detection process started with PID: {os.getpid()}")

    try:
        model = YOLO(resource_path('models/best1.pt'))
        result_q.put({"type": "model_ready"})
    except Exception as e:
        result_q.put({"type": "model_error", "error": str(e)})
        return

    settings = initial_settings
    vehicle_states = {}
    golongan_list = ["Gol 1", "Gol 2", "Gol 3", "Gol 4", "Gol 5", "Motor"]
    vehicle_counts = {golongan: {"In": 0, "Out": 0} for golongan in golongan_list}

    frame_num = 0
    pending_detections = []

    # --- Inisialisasi Time Offset ---
    if "start_timestamp_user" in settings and settings["start_timestamp_user"]:
        try:
            start_time = datetime.strptime(settings["start_timestamp_user"], "%Y-%m-%d %H:%M:%S")
            print(f"[INFO] Using custom start timestamp: {start_time}")
        except ValueError:
            print(f"[WARNING] Invalid start_timestamp_user: {settings['start_timestamp_user']}")
            start_time = datetime.now()
    else:
        start_time = datetime.now()

    print(f"[INFO] Enhanced filtering enabled:")
    print(f"  - ROI Filter: {settings.get('enable_roi_filter', True)}")
    print(f"  - Movement Validation: {settings.get('enable_movement_validation', True)}")
    print(f"  - Confidence Threshold: {settings.get('confidence_threshold', 0.5)}")
    print(f"  - Max Object Size Ratio: {settings.get('max_object_size_ratio', 0.3)}")

    while not stop_event.is_set():
        try:
            data = frame_q.get(timeout=0.05)
            frame, new_settings = data

            if new_settings:
                settings = new_settings
                print(f"[INFO] Settings updated in detection process")
                # Update time offset if needed
                if "start_timestamp_user" in settings and settings["start_timestamp_user"]:
                    try:
                        today_date = datetime.now().date()
                        user_dt_str = f"{today_date.year}-{today_date.month:02d}-{today_date.day:02d} {settings['start_timestamp_user'].split(' ')[1]}"
                        user_dt = datetime.strptime(user_dt_str, "%Y-%m-%d %H:%M:%S")
                        time_offset = user_dt - datetime.now()
                        print(f"Time offset updated to: {time_offset}")
                    except ValueError:
                        print(f"Invalid updated start_timestamp_user: {settings['start_timestamp_user']}")
                        time_offset = timedelta(seconds=0)
                else:
                    time_offset = timedelta(seconds=0)

            (h_orig, w_orig) = frame.shape[:2]

            # Hitung posisi garis deteksi
            line_offset_scaled = int(settings['line_offset'] * (h_orig / MAX_DISPLAY_HEIGHT))
            if settings['line_orientation'] == "Horizontal":
                line1_pos = int(settings['line1_y'] * (h_orig / MAX_DISPLAY_HEIGHT))
                line2_pos = line1_pos + line_offset_scaled
                # Gambar garis deteksi pada frame
                cv2.line(frame, (0, line1_pos), (w_orig, line1_pos), (0, 255, 0), 2)
                cv2.line(frame, (0, line2_pos), (w_orig, line2_pos), (0, 0, 255), 2)
            else: # Vertical
                line1_pos = int(settings['line1_x'] * (w_orig / MAX_DISPLAY_WIDTH))
                line2_pos = line1_pos + line_offset_scaled
                # Gambar garis deteksi pada frame
                cv2.line(frame, (line1_pos, 0), (line1_pos, h_orig), (0, 255, 0), 2)
                cv2.line(frame, (line2_pos, 0), (line2_pos, h_orig), (0, 0, 255), 2)

            # Jalankan deteksi YOLO
            results = model.track(frame, persist=True, tracker="bytetrack.yaml", 
                                conf=settings.get('confidence_threshold', 0.5), verbose=False)
            annotated_frame = results[0].plot()

            # Enhanced validation untuk deteksi
            valid_detections = enhanced_detection_validation(results, settings, frame, model)

            # Process valid detections
            for detection in valid_detections:
                track_id = detection['track_id']
                yolo_class_name = detection['class_name']
                box = detection['box']
                confidence = detection['confidence']

                # Update existing vehicle state
                if track_id in vehicle_states:
                    update_vehicle_movement(vehicle_states[track_id], box, frame_num)
                    
                    # Validasi movement jika enabled
                    if not is_valid_vehicle_movement(vehicle_states[track_id], settings):
                        print(f"[FILTER] Removed ID {track_id}: {yolo_class_name} (invalid movement)")
                        del vehicle_states[track_id]
                        continue

                # Check untuk counting
                if track_id in vehicle_states and not vehicle_states[track_id]['counted']:
                    initial_line = vehicle_states[track_id]['line']
                    direction_confirmed, direction = False, ""
                    vehicle_golongan = vehicle_states[track_id]['golongan']
                    
                    if settings['line_orientation'] == "Horizontal":
                        trigger_point = int(box[3])  # bottom of bounding box
                    else:
                        trigger_point = int((box[0] + box[2]) / 2)  # center x

                    # Check line crossing dengan toleransi
                    tolerance = 25
                    if initial_line == 1 and abs(trigger_point - line2_pos) < tolerance:
                        if vehicle_golongan != "Unknown": 
                            vehicle_counts[vehicle_golongan]["In"] += 1
                        direction, direction_confirmed = "In", True
                    elif initial_line == 2 and abs(trigger_point - line1_pos) < tolerance:
                        if vehicle_golongan != "Unknown": 
                            vehicle_counts[vehicle_golongan]["Out"] += 1
                        direction, direction_confirmed = "Out", True

                    if direction_confirmed:
                        vehicle_states[track_id]['counted'] = True
                        timestamp = (start_time + timedelta(seconds=frame_num / 30)).strftime("%Y-%m-%d %H:%M:%S")
                        new_row = {
                            "Timestamp": timestamp, 
                            "Vehicle ID": track_id, 
                            "Class": vehicle_golongan, 
                            "Direction": direction
                        }
                        pending_detections.append(new_row)
                        print(f"[COUNT] {vehicle_golongan} ID {track_id} -> {direction}")

                # Initialize new vehicle state
                elif track_id not in vehicle_states:
                    golongan = yolo_class_name if yolo_class_name in vehicle_counts else "Unknown"
                    
                    if settings['line_orientation'] == "Horizontal":
                        trigger_point = int(box[3])  # bottom of bounding box
                    else:
                        trigger_point = int((box[0] + box[2]) / 2)  # center x

                    tolerance = 25
                    if abs(trigger_point - line1_pos) < tolerance:
                        vehicle_states[track_id] = initialize_vehicle_state(track_id, box, golongan, 1, frame_num)
                        print(f"[INIT] New {golongan} ID {track_id} on Line 1")
                    elif abs(trigger_point - line2_pos) < tolerance:
                        vehicle_states[track_id] = initialize_vehicle_state(track_id, box, golongan, 2, frame_num)
                        print(f"[INIT] New {golongan} ID {track_id} on Line 2")

            # Cleanup inactive tracks (lebih agresif untuk objek statis)
            max_inactive_frames = 60  # 2 detik pada 30 fps
            inactive_tracks = []
            for tid, data in vehicle_states.items():
                frames_inactive = frame_num - data.get('last_seen', frame_num)
                if frames_inactive > max_inactive_frames:
                    inactive_tracks.append(tid)
                elif frames_inactive > 30 and not data.get('is_moving', False):
                    # Hapus objek yang tidak bergerak lebih cepat
                    inactive_tracks.append(tid)
                    
            for tid in inactive_tracks:
                print(f"[CLEANUP] Removed inactive vehicle ID {tid}")
                del vehicle_states[tid]

            # Send frame hasil
            result_q.put({"type": "frame", "image": annotated_frame})

            # Send data update jika ada
            if pending_detections:
                result_q.put({
                    "type": "data_update",
                    "counts": vehicle_counts.copy(),
                    "new_rows": list(pending_detections)
                })
                pending_detections.clear()

            frame_num += 1
            
        except Empty:
            continue
        except Exception as e:
            print(f"Error in detection process: {e}")
            import traceback
            traceback.print_exc()
            break
            
    print("Detection process received stop signal and is finishing.")