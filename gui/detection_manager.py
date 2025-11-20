import threading
import time
import cv2
from tkinter import messagebox
from multiprocessing import Process, Queue, Event
from queue import Empty, Full
from PIL import Image, ImageTk, ImageDraw
import pandas as pd

from core.detection_process import detection_process
from utils.constants import MAX_DISPLAY_WIDTH, MAX_DISPLAY_HEIGHT
from utils.helpers import format_time


class DetectionManager:
    def __init__(self, app):
        self.app = app
        self.frame_q = Queue(maxsize=5)
        self.result_q = Queue()
        self.detection_proc = None
        self.stop_event = Event()
        self.running = False
        self.is_loading = False
        self.animation_job = None
        self.video_feed_thread = None
        self._shutdown_attempts = 0

    def toggle_detection(self):
        """Toggle detection on/off"""
        if self.running or self.is_loading:
            self.stop_detection()
        else:
            self.start_detection()

    def start_detection(self):
        """Start detection process"""
        if self.app.video_handler.video_source is None:
            messagebox.showwarning("Warning", "Please load a video or select a webcam first.")
            return

        if self.running or self.is_loading:
            return

        # Ensure video capture is ready
        if not self.app.video_handler.cap or not self.app.video_handler.cap.isOpened():
            self.app.video_handler._init_video_capture_optimized()
            if not self.app.video_handler.cap or not self.app.video_handler.cap.isOpened():
                error_msg = ("Could not initialize webcam." if self.app.video_handler.is_webcam 
                           else "Could not initialize video capture.")
                messagebox.showerror("Error", error_msg)
                return

        self.app.data_manager.reset_data()
        self.is_loading = True
        self.app.ui_components.start_stop_button.config(
            text="Loading...", 
            state="disabled", 
            bootstyle="info"
        )
        self.update_animation_frame()

        self.stop_event.clear()
        self.frame_q = Queue(maxsize=5)
        self.result_q = Queue()

        # Only set frame delay for video files
        if not self.app.video_handler.is_webcam:
            self.app.video_handler.frame_delay = ((1.0 / self.app.video_handler.video_fps) / 
                                                 self.app.settings['video_playback_speed'])

        self.detection_proc = Process(
            target=detection_process,
            args=(self.frame_q, self.result_q, self.stop_event, self.app.settings.copy())
        )
        self.detection_proc.start()
        self.process_results()

    def stop_detection(self):
        """Stop detection process"""
        self.running = False
        self.is_loading = False

        # Stop loading animation
        if self.animation_job:
            self.app.root.after_cancel(self.animation_job)
            self.animation_job = None

        # Signal detection process to stop
        if self.detection_proc and self.detection_proc.is_alive():
            self.stop_event.set()
            self._shutdown_attempts = 0
            self.app.root.after(100, self._check_process_shutdown)
        else:
            self.detection_proc = None

        # Reset button
        self.app.ui_components.start_stop_button.config(
            text="Start Detection", 
            state="normal", 
            bootstyle="success"
        )

        # Clear queues
        for q in [self.result_q, self.frame_q]:
            while not q.empty():
                try:
                    q.get_nowait()
                except Exception:
                    break

        # Only display first frame for video files
        if (self.app.video_handler.video_source is not None and 
            not self.app.video_handler.is_webcam):
            self.app.video_handler.display_first_frame()

    def _check_process_shutdown(self):
        """Check if detection process has shut down"""
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
                self.app.root.after(100, self._check_process_shutdown)
        else:
            print("Detection process stopped gracefully.")
            self.detection_proc.join()
            self.detection_proc = None

    def create_loading_frame(self, angle):
        """Create loading animation frame"""
        size = 100
        image = Image.new('RGB', (size, size), '#2a3540')
        draw = ImageDraw.Draw(image)
        draw.arc([(10, 10), (size - 10, size - 10)], 
                start=angle, end=angle + 270, width=8, fill='#17a2b8')
        return ImageTk.PhotoImage(image)

    def update_animation_frame(self, angle=0):
        """Update loading animation"""
        if not self.is_loading: 
            return
        imgtk = self.create_loading_frame(angle)
        self.app.ui_components.video_label.imgtk = imgtk
        self.app.ui_components.video_label.configure(image=imgtk)
        self.animation_job = self.app.root.after(
            50, self.update_animation_frame, (angle + 15) % 360
        )

    def video_feed_loop(self):
        """Optimized video feed loop"""
        frame_skip_counter = 0
        while self.running:
            start_time = time.time()
            
            if not self.app.video_handler.cap or not self.app.video_handler.cap.isOpened():
                self.app.root.after(0, self.stop_detection)
                break

            ret, frame = self.app.video_handler.cap.read()
            if not ret:
                # Only stop for video files on read failure
                if not self.app.video_handler.is_webcam:  
                    self.app.root.after(0, self.stop_detection)
                    break
                else:
                    # For webcam, try to continue
                    time.sleep(0.01)
                    continue

            # For webcam, implement frame skipping if processing is too slow
            if self.app.video_handler.is_webcam and self.frame_q.qsize() > 2:
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

                settings_payload = getattr(self.app, 'new_settings_to_send', None)
                self.frame_q.put_nowait((frame, settings_payload))
                if hasattr(self.app, 'new_settings_to_send') and self.app.new_settings_to_send: 
                    self.app.new_settings_to_send = None
                    
            except Full:
                # Skip this frame if queue is full
                pass

            # Only apply frame delay for video files
            if not self.app.video_handler.is_webcam:
                elapsed_time = time.time() - start_time
                sleep_time = self.app.video_handler.frame_delay - elapsed_time
                if sleep_time > 0:
                    time.sleep(sleep_time)
            else:
                # For webcam, minimal delay to prevent CPU overload
                time.sleep(0.001)

    def process_results(self):
        """Process detection results"""
        try:
            result = self.result_q.get_nowait()

            if result['type'] == 'model_ready':
                self.is_loading = False
                self.running = True
                self.app.ui_components.start_stop_button.config(
                    text="Stop Detection", 
                    state="normal", 
                    bootstyle="danger"
                )
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
                self.app.ui_components.video_label.imgtk = imgtk
                self.app.ui_components.video_label.configure(image=imgtk)

                # Only update trackbar for video files
                if (self.app.video_handler.cap and 
                    self.app.video_handler.is_video_file and 
                    not self.app.video_handler.is_webcam):
                    current_frame = int(self.app.video_handler.cap.get(cv2.CAP_PROP_POS_FRAMES))
                    if not self.app.video_handler.is_seeking:
                        self.app.ui_components.trackbar_var.set(current_frame)

                    total_sec = self.app.video_handler.total_frames / self.app.video_handler.video_fps
                    current_sec = current_frame / self.app.video_handler.video_fps
                    self.app.ui_components.time_label.config(
                        text=f"{format_time(current_sec)} / {format_time(total_sec)}"
                    )

            elif result['type'] == 'data_update' and self.running:
                self.app.data_manager.vehicle_counts = result['counts']
                new_df = pd.DataFrame(result['new_rows'])
                self.app.data_manager.df = pd.concat([self.app.data_manager.df, new_df], ignore_index=True)
                self.app.update_gui_display()
        except Empty:
            pass

        if self.is_loading or self.running:
            self.app.root.after(20, self.process_results)

    def cleanup(self):
        """Cleanup detection resources"""
        if self.animation_job:
            self.app.root.after_cancel(self.animation_job)

        # Terminate detection process if still running
        if self.detection_proc and self.detection_proc.is_alive():
            print("[CLEANUP] Terminating detection process.")
            self.detection_proc.terminate()
            self.detection_proc.join()

        # Set stop event
        self.stop_event.set()

        # Clear queues
        for q in [self.result_q, self.frame_q]:
            while not q.empty():
                try:
                    q.get_nowait()
                except Exception:
                    break