import tkinter as tk
from tkinter import filedialog, messagebox
import ttkbootstrap as ttk
from ttkbootstrap.constants import *
import pandas as pd
from PIL import Image, ImageTk, ImageDraw
import threading
import datetime
import os
import sys
from multiprocessing import Process, Queue, Event
from queue import Empty, Full
import json
import time
import cv2

from core.detection_process import detection_process
from core.source_webcam import WebcamSelectionDialog
from core.exporter import save_to_excel

from gui.dialogs import SettingsDialog, TimeDialog

MAX_DISPLAY_WIDTH = 960
MAX_DISPLAY_HEIGHT = 720

def resource_path(relative_path):
    try:
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.abspath(".")
    return os.path.join(base_path, relative_path)


class VehicleDetectorApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Vehicle Detection System [Multiprocess & Stabilized]")
        self.screen_width = self.root.winfo_screenwidth()
        self.screen_height = self.root.winfo_screenheight()
        self.root.geometry(f"{self.screen_width}x{self.screen_height}+0+0")

        self.frame_q = Queue(maxsize=5)
        self.result_q = Queue()
        self.detection_proc: Process | None = None
        self.stop_event = Event()
        self.animation_job = None
        self.trackbar = None
        self.time_label = None
        self.total_frames = 0
        self.is_video_file = False
        self.is_webcam = False
        self.is_seeking = False
        self.trackbar_var = tk.DoubleVar()

        self.settings = {
            "confidence_threshold": 0.2,
            "line_offset": 50,
            "line_orientation": "Horizontal",
            "line1_y": (MAX_DISPLAY_HEIGHT // 2) - 25,
            "line1_x": (MAX_DISPLAY_WIDTH // 2) - 25,
            "video_playback_speed": 1.0,
            "start_timestamp_user": None
        }
        self.load_config()
        self.new_settings_to_send = None

        self.video_source = None
        self.cap = None
        self.running = False
        self.is_loading = False
        self.video_fps = 30
        self.frame_delay = 1.0 / self.video_fps

        self.df = pd.DataFrame(columns=["Timestamp", "Vehicle ID", "Class", "Direction"])
        self.golongan_list = ["Gol I", "Gol II", "Gol III", "Gol IV", "Gol V", "Gol VI"]
        self.vehicle_counts = {golongan: {"In": 0, "Out": 0} for golongan in self.golongan_list}

        self.desired_width = 450
        self.desired_height = 280

        self.status_setting = None

        self.create_widgets()
        self.create_menu()
        self.update_gui_display()
        self.root.protocol("WM_DELETE_WINDOW", self.on_closing)

    def open_webcam_selection(self):
        """Open optimized webcam selection dialog"""
        def on_camera_selected(camera_index):
            self.settings["start_timestamp_user"] = None
            self._setup_video_source(camera_index)
        
        WebcamSelectionDialog(self.root, on_camera_selected)

    def load_config(self):
        try:
            with open('config.json', 'r') as f:
                loaded_settings = json.load(f)
                self.settings.update(loaded_settings)
        except (FileNotFoundError, json.JSONDecodeError):
            pass

    def save_config(self):
        try:
            with open('config.json', 'w') as f:
                json.dump(self.settings, f, indent=4)
            messagebox.showinfo("Info", "Config saved.")
        except Exception as e:
            messagebox.showerror("Info", f"Error saving config: {e}")

    def create_menu(self):
        menubar = tk.Menu(self.root)
        self.root.config(menu=menubar)

        file_menu = tk.Menu(menubar, tearoff=0)
        file_menu.add_command(label="Exit", command=self.on_closing)
        menubar.add_cascade(label="File", menu=file_menu)

        # Source menu - ADDED WEBCAM OPTION
        source_menu = tk.Menu(menubar, tearoff=0)
        source_menu.add_command(label="Load Video File", command=self.load_video)
        source_menu.add_command(label="Use Webcam", command=self.open_webcam_selection)
        menubar.add_cascade(label="Source", menu=source_menu)

        file_conf = tk.Menu(menubar)
        menubar.add_cascade(label="Settings", menu=file_conf)
        file_conf.add_command(label="Configuration", command=self.open_settings_dialog)
        file_conf.add_command(label="Time", command=self.open_time_dialog)

    def create_widgets(self):
        self.main_frame = ttk.Frame(self.root, padding="10")
        self.main_frame.pack(fill=BOTH, expand=True)
        left_frame = ttk.Frame(self.main_frame)
        left_frame.pack(side=LEFT, fill=BOTH, expand=True, padx=(0, 10))
        right_frame = ttk.Frame(self.main_frame, width=500)
        right_frame.pack(side=RIGHT, fill=Y, expand=False)
        right_frame.pack_propagate(False)

        video_container = ttk.Frame(left_frame, bootstyle="secondary")
        video_container.pack(fill=BOTH, expand=True)
        video_container.grid_rowconfigure(0, weight=1)
        video_container.grid_columnconfigure(0, weight=1)
        self.video_label = ttk.Label(video_container, text="\n\nLoad Video or Use Webcam to Start\n", anchor=CENTER,
                                     bootstyle="inverse-secondary")
        self.video_label.grid(row=0, column=0, sticky="nsew")
        self.video_label.bind("<Button-1>", self.set_detection_line)

        # Trackbar Frame
        trackbar_frame = ttk.Frame(left_frame)
        trackbar_frame.pack(fill=X)

        self.trackbar = ttk.Scale(
            trackbar_frame,
            from_=0,
            to=0,
            orient=tk.HORIZONTAL,
            variable=self.trackbar_var,
            command=self.on_trackbar_drag
        )
        self.trackbar.pack(fill=X, side=LEFT, expand=True, padx=(10, 5))

        # Label Durasi
        self.time_label = ttk.Label(trackbar_frame, text="00:00 / 00:00")
        self.time_label.pack(side=RIGHT, padx=(5, 10), pady=(20,0))

        # Event tambahan (klik dan lepas)
        self.trackbar.bind("<ButtonPress-1>", self.on_trackbar_press)
        self.trackbar.bind("<ButtonRelease-1>", self.on_trackbar_release)

        control_area = ttk.Frame(left_frame)
        control_area.pack(fill=X, pady=5)

        action_controls = ttk.LabelFrame(control_area, text="Actions", padding=10)
        action_controls.pack(fill=X, expand=True, side=LEFT)
        self.start_stop_button = ttk.Button(action_controls, text="Start Detection", command=self.toggle_detection,
                                            bootstyle="success", state="disabled")
        self.start_stop_button.pack(side=LEFT, fill=X, expand=True, padx=5)
        # ttk.Button(action_controls, text="Save Data", command=self.save_to_excel, bootstyle="warning-outline").pack(
        #     side=LEFT, fill=X, expand=True, padx=5)

        # Frame Data
        data_frame = ttk.LabelFrame(right_frame, text="Counting Data", padding=10)
        data_frame.pack(fill=BOTH, expand=True, pady=(0, 10))

        # Frame untuk Treeview
        tree_frame = ttk.Frame(data_frame)
        tree_frame.pack(fill=BOTH, expand=True)

        # Treeview dan kolom
        columns = ("Timestamp", "ID", "Class", "Direction")
        self.tree = ttk.Treeview(tree_frame, columns=columns, show='headings', bootstyle="primary")

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

        # Packing Tree dan Scrollbar
        self.tree.pack(side=LEFT, fill=BOTH, expand=True)
        scrollbar.pack(side=RIGHT, fill=Y)

        # Frame tombol di bawah Treeview
        button_frame = ttk.Frame(data_frame)
        button_frame.pack(fill=X, pady=(10, 0))

        # Gunakan grid agar tombol rapi dan sejajar
        button_frame.columnconfigure(0, weight=1)
        button_frame.columnconfigure(1, weight=1)

        btn_refresh = ttk.Button(
            button_frame,
            text="Refresh",
            bootstyle="success-outline",
            # command=self.refresh_data
        )
        btn_refresh.grid(row=0, column=0, sticky=NSEW, padx=(0, 3))

        btn_save_data = ttk.Button(
            button_frame,
            text="Save Data",
            bootstyle="warning-outline",
            command=self.save_to_excel
        )
        btn_save_data.grid(row=0, column=1, sticky=NSEW, padx=(3, 0))


    def on_trackbar_press(self, event):
        # Only allow seeking for video files, not webcam
        if self.is_video_file and not self.is_webcam: 
            self.is_seeking = True

    def on_trackbar_drag(self, event):
        if self.is_seeking:
            pos = int(self.trackbar_var.get())
            self.cap.set(cv2.CAP_PROP_POS_FRAMES, pos)
            self.display_current_frame()

    def on_trackbar_release(self, event):
        if not self.is_seeking: return
        self.is_seeking = False
        pos = int(self.trackbar_var.get())
        if self.cap: self.cap.set(cv2.CAP_PROP_POS_FRAMES, pos)

    def create_loading_frame(self, angle):
        size = 100
        image = Image.new('RGB', (size, size), '#2a3540')
        draw = ImageDraw.Draw(image)
        draw.arc([(10, 10), (size - 10, size - 10)], start=angle, end=angle + 270, width=8, fill='#17a2b8')
        return ImageTk.PhotoImage(image)

    def update_animation_frame(self, angle=0):
        if not self.is_loading: return
        imgtk = self.create_loading_frame(angle)
        self.video_label.imgtk = imgtk
        self.video_label.configure(image=imgtk)
        self.animation_job = self.root.after(50, self.update_animation_frame, (angle + 15) % 360)

    def open_settings_dialog(self):
        def apply_settings_callback(confidence, offset, orientation, speed):
            self.settings['confidence_threshold'] = confidence
            self.settings['line_offset'] = offset
            self.settings['line_orientation'] = orientation
            self.settings['video_playback_speed'] = speed
            self.new_settings_to_send = self.settings.copy()

            # Only apply speed settings for video files, not webcam
            if self.video_source and self.video_fps > 0 and not self.is_webcam:
                self.frame_delay = (1.0 / self.video_fps) / self.settings['video_playback_speed']

            if self.running:
                messagebox.showinfo("Info", "Pengaturan akan diterapkan pada frame berikutnya.")
            elif self.video_source:  # Hanya display jika ada video source
                self.display_first_frame()

            self.save_config()

        SettingsDialog(self.root, self.settings.copy(), apply_settings_callback)

    def open_time_dialog(self):
        def apply_time_callback(timestamp_str):
            self.settings["start_timestamp_user"] = timestamp_str
            self.new_settings_to_send = self.settings.copy()
            self.save_config()

        # Handle webcam case
        if self.video_source and isinstance(self.video_source, str) and os.path.exists(self.video_source):
            try:
                timestamp = os.path.getmtime(self.video_source)
                video_time = datetime.datetime.fromtimestamp(timestamp)
                default_timestamp = video_time.strftime("%Y-%m-%d %H:%M:%S")
            except Exception as e:
                default_timestamp = self.settings["start_timestamp_user"]
        else:
            default_timestamp = self.settings["start_timestamp_user"]

        TimeDialog(self.root, default_timestamp, apply_time_callback)

    def apply_time_settings(self, time_win):
        try:
            input_hour = int(self.start_hour_var.get())
            input_minute = int(self.start_minute_var.get())

            if not (0 <= input_hour <= 23 and 0 <= input_minute <= 59):
                raise ValueError("Hour must be 0-23, Minute must be 0-59")

            today_date = datetime.date.today()
            user_start_dt = datetime.datetime(today_date.year, today_date.month, today_date.day,
                                              input_hour, input_minute, 0)
            self.settings["start_timestamp_user"] = user_start_dt.strftime("%Y-%m-%d %H:%M:%S")
            messagebox.showinfo("Info", f"Start time set to: {self.settings['start_timestamp_user']}")

        except ValueError as e:
            messagebox.showerror("Invalid Input", f"Invalid time format: {e}. Defaulting to current time.")
            self.settings["start_timestamp_user"] = None

        self.new_settings_to_send = self.settings.copy()
        self.save_config()
        time_win.destroy()

    def _setup_video_source(self, source):
        if self.running or self.is_loading:
            self.stop_detection()

        self.video_source = source
        
        # Determine source type
        self.is_webcam = isinstance(source, int)
        self.is_video_file = not self.is_webcam

        # Tambahkan dialog konfirmasi
        if not self.df.empty:
            response = messagebox.askyesno("Existing Data",
                                        "Do you want to keep the previous detection data?")
            self.reset_data(clear_all=not response)
        else:
            self.reset_data(clear_all=False)

        # Optimized video capture initialization
        self._init_video_capture_optimized()

        if self.cap and self.cap.isOpened():
            self.start_stop_button.config(state="normal")
            self.display_first_frame()
            
            # Handle UI differences for webcam vs video
            if self.is_webcam:
                self.trackbar.config(state="disabled")
                self.time_label.config(text="Webcam Live")
                self.root.title(f"Vehicle Detection System - Webcam {source}")
            else:
                self.trackbar.config(state="normal")
                self.root.title("Vehicle Detection System - Video File")
        else:
            error_msg = f"Could not open webcam {source}" if self.is_webcam else f"Could not open video file: {source}"
            messagebox.showerror("Error", error_msg)

    def _init_video_capture_optimized(self):
        """Optimized video capture initialization"""
        if self.cap:
            self.cap.release()

        if self.video_source is not None:
            # Use optimized capture settings based on platform and source type
            if self.is_webcam:
                if sys.platform.startswith('win'):
                    # Use DirectShow on Windows for faster webcam access
                    self.cap = cv2.VideoCapture(self.video_source, cv2.CAP_DSHOW)
                else:
                    self.cap = cv2.VideoCapture(self.video_source)
                
                if self.cap and self.cap.isOpened():
                    # Optimize webcam settings for performance
                    self.cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)  # Reduce buffer to minimize delay
                    self.cap.set(cv2.CAP_PROP_FPS, 30)        # Set target FPS
                    
                    # Try to get actual FPS
                    actual_fps = self.cap.get(cv2.CAP_PROP_FPS)
                    self.video_fps = actual_fps if actual_fps > 0 else 30
                    self.frame_delay = 1.0 / 30  # Fixed delay for webcam
            else:
                # Regular video file
                self.cap = cv2.VideoCapture(self.video_source)
                if self.cap and self.cap.isOpened():
                    self.video_fps = self.cap.get(cv2.CAP_PROP_FPS)
                    if self.video_fps == 0 or self.video_fps > 60:
                        self.video_fps = 30
                    self.frame_delay = (1.0 / self.video_fps) / self.settings['video_playback_speed']
        else:
            self.cap = None

    def _init_video_capture(self):
        """Legacy method - now calls optimized version"""
        self._init_video_capture_optimized()

    def load_video(self):
        path = filedialog.askopenfilename(filetypes=[("Video files", "*.mp4 *.avi *.mov *.flv*")])
        if not path:
            return  # User cancel

        self.settings["start_timestamp_user"] = None
        self._setup_video_source(path)

        # Only setup trackbar for video files
        if self.cap and self.cap.isOpened() and not self.is_webcam:
            self.total_frames = int(self.cap.get(cv2.CAP_PROP_FRAME_COUNT))
            self.trackbar.config(to=self.total_frames - 1)
        else:
            if not self.cap or not self.cap.isOpened():
                messagebox.showerror("Error", "Failed load video.")

    def reset_data(self, clear_all=False):
        if clear_all:
            # Jika clear_all=True, hapus semua data
            self.df = self.df.iloc[0:0]
            self.vehicle_counts = {golongan: {"In": 0, "Out": 0} for golongan in self.golongan_list}
        else:
            # Jika clear_all=False (default), hanya reset count untuk video baru
            self.vehicle_counts = {golongan: {"In": 0, "Out": 0} for golongan in self.golongan_list}

        self.update_gui_display()

    def toggle_detection(self):
        if self.running or self.is_loading:
            self.stop_detection()
        else:
            self.start_detection()

    def start_detection(self):
        # Better error message
        if self.video_source is None:
            messagebox.showwarning("Warning", "Please load a video or select a webcam first.")
            return

        if self.running or self.is_loading:
            return

        # Pastikan video capture siap
        if not self.cap or not self.cap.isOpened():
            self._init_video_capture_optimized()
            if not self.cap or not self.cap.isOpened():
                error_msg = "Could not initialize webcam." if self.is_webcam else "Could not initialize video capture."
                messagebox.showerror("Error", error_msg)
                return

        self.reset_data()
        self.is_loading = True
        self.start_stop_button.config(text="Loading...", state="disabled", bootstyle="info")
        self.update_animation_frame()

        self.stop_event.clear()
        self.frame_q = Queue(maxsize=5)
        self.result_q = Queue()

        # Only set frame delay for video files
        if not self.is_webcam:
            self.frame_delay = (1.0 / self.video_fps) / self.settings['video_playback_speed']

        self.detection_proc = Process(target=detection_process,
                                      args=(self.frame_q, self.result_q, self.stop_event, self.settings.copy()))
        self.detection_proc.start()

        self.process_results()

    def stop_detection(self):
        # 1. Hentikan semua aktivitas yang sedang berjalan
        self.running = False
        self.is_loading = False

        # 3. Hentikan animasi loading
        if self.animation_job:
            self.root.after_cancel(self.animation_job)
            self.animation_job = None

        # 4. Beri sinyal pada proses deteksi untuk berhenti
        if self.detection_proc and self.detection_proc.is_alive():
            self.stop_event.set()
            self._shutdown_attempts = 0
            self.root.after(100, self._check_process_shutdown)
        else:
            self.detection_proc = None

        # 5. Reset tampilan tombol
        self.start_stop_button.config(text="Start Detection", state="normal", bootstyle="success")

        # 6. Kosongkan antrian (opsional, tapi praktik yang baik)
        for q in [self.result_q, self.frame_q]:
            while not q.empty():
                try:
                    q.get_nowait()
                except Exception:
                    break

        # 7. Only display first frame for video files
        if self.video_source is not None and not self.is_webcam:
            self.display_first_frame()

    def _check_process_shutdown(self):
        if not self.detection_proc:
            return

        if self.detection_proc.is_alive():
            self._shutdown_attempts += 1
            if self._shutdown_attempts > 20:
                print("[WARNING] Detection process did not stop gracefully. Terminating.")
                self.detection_proc.terminate()
                self.detection_proc.join()
                self.detection_proc = None
            else:
                self.root.after(100, self._check_process_shutdown)
        else:
            print("Detection process stopped gracefully.")
            self.detection_proc.join()
            self.detection_proc = None

    def video_feed_loop(self):
        """Optimized video feed loop with better performance for webcam"""
        frame_skip_counter = 0
        while self.running:
            start_time = time.time()
            
            if not self.cap or not self.cap.isOpened():
                self.root.after(0, self.stop_detection)
                break

            ret, frame = self.cap.read()
            if not ret:
                # Only stop for video files on read failure
                if not self.is_webcam:  
                    self.root.after(0, self.stop_detection)
                    break
                else:
                    # For webcam, try to continue
                    time.sleep(0.01)
                    continue

            # For webcam, implement frame skipping if processing is too slow
            if self.is_webcam and self.frame_q.qsize() > 2:
                frame_skip_counter += 1
                if frame_skip_counter % 2 == 0:  # Skip every other frame if queue is backed up
                    continue

            try:
                # Clear old frames from queue if it's full
                if self.frame_q.full():
                    try:
                        self.frame_q.get_nowait()
                    except Empty:
                        pass

                settings_payload = self.new_settings_to_send
                self.frame_q.put_nowait((frame, settings_payload))
                if self.new_settings_to_send: 
                    self.new_settings_to_send = None
                    
            except Full:
                # Skip this frame if queue is full
                pass

            # Only apply frame delay for video files
            if not self.is_webcam:
                elapsed_time = time.time() - start_time
                sleep_time = self.frame_delay - elapsed_time
                if sleep_time > 0:
                    time.sleep(sleep_time)
            else:
                # For webcam, minimal delay to prevent CPU overload
                time.sleep(0.001)

    def process_results(self):
        try:
            result = self.result_q.get_nowait()

            if result['type'] == 'model_ready':
                self.is_loading = False
                self.running = True
                self.start_stop_button.config(text="Stop Detection", state="normal", bootstyle="danger")
                self.video_feed_thread = threading.Thread(target=self.video_feed_loop, daemon=True)
                self.video_feed_thread.start()

            elif result['type'] == 'model_error':
                messagebox.showerror("Model Error", f"Failed to load YOLO model: {result['error']}")
                self.stop_detection()

            elif result['type'] == 'frame' and self.running:
                # Optimized frame display
                img = cv2.cvtColor(result['image'], cv2.COLOR_BGR2RGB)
                img = cv2.resize(img, (MAX_DISPLAY_WIDTH, MAX_DISPLAY_HEIGHT))
                imgtk = ImageTk.PhotoImage(Image.fromarray(img))
                self.video_label.imgtk = imgtk
                self.video_label.configure(image=imgtk)

                # Only update trackbar for video files
                if self.cap and self.is_video_file and not self.is_webcam:
                    current_frame = int(self.cap.get(cv2.CAP_PROP_POS_FRAMES))
                    if not self.is_seeking:
                        self.trackbar_var.set(current_frame)

                    total_sec = self.total_frames / self.video_fps
                    current_sec = current_frame / self.video_fps
                    self.time_label.config(text=f"{format_time(current_sec)} / {format_time(total_sec)}")

            elif result['type'] == 'data_update' and self.running:
                self.vehicle_counts = result['counts']
                new_df = pd.DataFrame(result['new_rows'])
                self.df = pd.concat([self.df, new_df], ignore_index=True)
                self.update_gui_display()
        except Empty:
            pass

        if self.is_loading or self.running:
            self.root.after(20, self.process_results)

    def update_gui_display(self):
        for i in self.tree.get_children(): 
            self.tree.delete(i)
        for _, row in self.df.iterrows():
            self.tree.insert("", "end", values=list(row))
        if not self.df.empty: 
            self.tree.yview_moveto(1)

    def set_detection_line(self, event):
        if self.running or self.is_loading: 
            return
        if not hasattr(self, 'video_label') or not self.video_label.winfo_exists() or not hasattr(self.video_label, 'imgtk'):
            return

        self.settings['line1_y'] = event.y
        self.settings['line1_x'] = event.x
        self.display_first_frame()

    def display_first_frame(self):
        """Optimized first frame display"""
        # Handle both video and webcam cases
        if self.video_source is None:
            self.video_label.configure(image='', text="\n\nLoad Video or Use Webcam to Start\n")
            return

        # Pastikan video capture siap
        if not self.cap or not self.cap.isOpened():
            self._init_video_capture_optimized()
            if not self.cap or not self.cap.isOpened():
                error_msg = "\n\nCould not access webcam.\n" if self.is_webcam else "\n\nCould not read video frame.\n"
                self.video_label.configure(image='', text=error_msg)
                return

        # For video files, go to first frame. For webcams, just read current frame
        if not self.is_webcam:
            self.cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
        
        ret, frame = self.cap.read()
        if not ret:
            error_msg = "\n\nCould not read from webcam.\n" if self.is_webcam else "\n\nCould not read video frame.\n"
            self.video_label.configure(image='', text=error_msg)
            return

        # Draw detection lines
        (h_orig, w_orig) = frame.shape[:2]
        line_offset_scaled = int(self.settings['line_offset'] * (h_orig / MAX_DISPLAY_HEIGHT))

        if self.settings['line_orientation'] == "Horizontal":
            line1_pos_scaled = int(self.settings['line1_y'] * (h_orig / MAX_DISPLAY_HEIGHT))
            line2_pos_scaled = line1_pos_scaled + line_offset_scaled
            cv2.line(frame, (0, line1_pos_scaled), (w_orig, line1_pos_scaled), (0, 255, 0), 2)
            cv2.line(frame, (0, line2_pos_scaled), (w_orig, line2_pos_scaled), (0, 0, 255), 2)
        else:
            line1_pos_scaled = int(self.settings['line1_x'] * (w_orig / MAX_DISPLAY_WIDTH))
            line2_pos_scaled = line1_pos_scaled + line_offset_scaled
            cv2.line(frame, (line1_pos_scaled, 0), (line1_pos_scaled, h_orig), (0, 255, 0), 2)
            cv2.line(frame, (line2_pos_scaled, 0), (line2_pos_scaled, h_orig), (0, 0, 255), 2)

        # Convert and display
        img = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        img = cv2.resize(img, (MAX_DISPLAY_WIDTH, MAX_DISPLAY_HEIGHT))
        imgtk = ImageTk.PhotoImage(Image.fromarray(img))
        self.video_label.imgtk = imgtk
        self.video_label.configure(image=imgtk)

    def _force_exit(self):
        try:
            # Hentikan event loop jika ada
            if self.animation_job:
                self.root.after_cancel(self.animation_job)

            # Tutup video capture
            if self.cap:
                self.cap.release()

            # Terminate proses deteksi jika masih berjalan
            if self.detection_proc and self.detection_proc.is_alive():
                print("[FORCE EXIT] Terminating remaining process.")
                self.detection_proc.terminate()
                self.detection_proc.join()

            # Tutup event
            self.stop_event.set()

            # Kosongkan antrian
            for q in [self.result_q, self.frame_q]:
                while not q.empty():
                    try:
                        q.get_nowait()
                    except Exception:
                        break

            # Tutup jendela
            self.root.quit()
            self.root.destroy()

            # Keluar dari aplikasi
            sys.exit(0)

        except Exception as e:
            print(f"Error during force exit: {e}")
            sys.exit(1)

    def on_closing(self):
        if messagebox.askokcancel("Quit", "Do you want to quit?"):
            if self.running or self.is_loading:
                self.stop_detection()
            self.root.after(500, self._force_exit)

    def save_to_excel(self):
        save_to_excel(self.df, self.settings, self.vehicle_counts)

    def display_current_frame(self):
        if not self.cap or not self.cap.isOpened():
            return
        ret, frame = self.cap.read()
        if not ret:
            return
        img = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        img = cv2.resize(img, (MAX_DISPLAY_WIDTH, MAX_DISPLAY_HEIGHT))
        imgtk = ImageTk.PhotoImage(Image.fromarray(img))
        self.video_label.imgtk = imgtk
        self.video_label.configure(image=imgtk)


def format_time(seconds):
    m, s = divmod(int(seconds), 60)
    return f"{m:02}:{s:02}"