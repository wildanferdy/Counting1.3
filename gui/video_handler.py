import cv2
import sys
import os
from tkinter import filedialog, messagebox
from PIL import Image, ImageTk
import pandas as pd

from utils.constants import MAX_DISPLAY_WIDTH, MAX_DISPLAY_HEIGHT
from core.source_webcam import WebcamSelectionDialog


class VideoHandler:
    def __init__(self, app):
        self.app = app
        self.video_source = None
        self.cap = None
        self.is_video_file = False
        self.is_webcam = False
        self.is_seeking = False
        self.total_frames = 0
        self.video_fps = 30
        self.frame_delay = 1.0 / self.video_fps

    def open_webcam_selection(self):
        """Open optimized webcam selection dialog"""
        def on_camera_selected(camera_index):
            self.app.settings["start_timestamp_user"] = None
            self._setup_video_source(camera_index)
        
        WebcamSelectionDialog(self.app.root, on_camera_selected)

    def load_video(self):
        """Load video file"""
        path = filedialog.askopenfilename(
            filetypes=[("Video files", "*.mp4 *.avi *.mov *.flv*")]
        )
        if not path:
            return  # User cancel

        self.app.settings["start_timestamp_user"] = None
        self._setup_video_source(path)

        # Only setup trackbar for video files
        if self.cap and self.cap.isOpened() and not self.is_webcam:
            self.total_frames = int(self.cap.get(cv2.CAP_PROP_FRAME_COUNT))
            self.app.ui_components.trackbar.config(to=self.total_frames - 1)
        else:
            if not self.cap or not self.cap.isOpened():
                messagebox.showerror("Error", "Failed load video.")

    def _setup_video_source(self, source):
        """Setup video source (file or webcam)"""
        if self.app.detection_manager.running or self.app.detection_manager.is_loading:
            self.app.detection_manager.stop_detection()

        self.video_source = source
        
        # Determine source type
        self.is_webcam = isinstance(source, int)
        self.is_video_file = not self.is_webcam

        # Handle existing data
        if not self.app.data_manager.df.empty:
            response = messagebox.askyesno(
                "Existing Data",
                "Do you want to keep the previous detection data?"
            )
            self.app.data_manager.reset_data(clear_all=not response)
        else:
            self.app.data_manager.reset_data(clear_all=False)

        # Initialize video capture
        self._init_video_capture_optimized()

        if self.cap and self.cap.isOpened():
            self.app.ui_components.start_stop_button.config(state="normal")
            self.display_first_frame()
            
            # Handle UI differences for webcam vs video
            if self.is_webcam:
                self.app.ui_components.trackbar.config(state="disabled")
                self.app.ui_components.time_label.config(text="Webcam Live")
                self.app.root.title(f"Vehicle Detection System - Webcam {source}")
            else:
                self.app.ui_components.trackbar.config(state="normal")
                self.app.root.title("Vehicle Detection System - Video File")
        else:
            error_msg = (f"Could not open webcam {source}" if self.is_webcam 
                        else f"Could not open video file: {source}")
            messagebox.showerror("Error", error_msg)

    def _init_video_capture_optimized(self):
        """Optimized video capture initialization"""
        if self.cap:
            self.cap.release()

        if self.video_source is not None:
            if self.is_webcam:
                if sys.platform.startswith('win'):
                    # Use DirectShow on Windows for faster webcam access
                    self.cap = cv2.VideoCapture(self.video_source, cv2.CAP_DSHOW)
                else:
                    self.cap = cv2.VideoCapture(self.video_source)
                
                if self.cap and self.cap.isOpened():
                    # Optimize webcam settings for performance
                    self.cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)
                    self.cap.set(cv2.CAP_PROP_FPS, 30)
                    
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
                    self.frame_delay = ((1.0 / self.video_fps) / 
                                      self.app.settings['video_playback_speed'])
        else:
            self.cap = None

    def on_trackbar_press(self, event):
        """Handle trackbar press event"""
        if self.is_video_file and not self.is_webcam: 
            self.is_seeking = True

    def on_trackbar_drag(self, event):
        """Handle trackbar drag event"""
        if self.is_seeking:
            pos = int(self.app.ui_components.trackbar_var.get())
            self.cap.set(cv2.CAP_PROP_POS_FRAMES, pos)
            self.display_current_frame()

    def on_trackbar_release(self, event):
        """Handle trackbar release event"""
        if not self.is_seeking: 
            return
        self.is_seeking = False
        pos = int(self.app.ui_components.trackbar_var.get())
        if self.cap: 
            self.cap.set(cv2.CAP_PROP_POS_FRAMES, pos)

    def set_detection_line(self, event):
        """Set detection line position"""
        if (self.app.detection_manager.running or 
            self.app.detection_manager.is_loading): 
            return
        if (not hasattr(self.app.ui_components, 'video_label') or 
            not self.app.ui_components.video_label.winfo_exists() or 
            not hasattr(self.app.ui_components.video_label, 'imgtk')):
            return

        self.app.settings['line1_y'] = event.y
        self.app.settings['line1_x'] = event.x
        self.display_first_frame()

    def display_first_frame(self):
        """Display first frame with detection lines"""
        if self.video_source is None:
            self.app.ui_components.video_label.configure(
                image='', 
                text="\n\nLoad Video or Use Webcam to Start\n"
            )
            return

        # Ensure video capture is ready
        if not self.cap or not self.cap.isOpened():
            self._init_video_capture_optimized()
            if not self.cap or not self.cap.isOpened():
                error_msg = ("\n\nCould not access webcam.\n" if self.is_webcam 
                           else "\n\nCould not read video frame.\n")
                self.app.ui_components.video_label.configure(image='', text=error_msg)
                return

        # For video files, go to first frame. For webcams, just read current frame
        if not self.is_webcam:
            self.cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
        
        ret, frame = self.cap.read()
        if not ret:
            error_msg = ("\n\nCould not read from webcam.\n" if self.is_webcam 
                        else "\n\nCould not read video frame.\n")
            self.app.ui_components.video_label.configure(image='', text=error_msg)
            return

        # Draw detection lines
        self._draw_detection_lines(frame)

        # Convert and display
        img = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        img = cv2.resize(img, (MAX_DISPLAY_WIDTH, MAX_DISPLAY_HEIGHT))
        imgtk = ImageTk.PhotoImage(Image.fromarray(img))
        self.app.ui_components.video_label.imgtk = imgtk
        self.app.ui_components.video_label.configure(image=imgtk)

    def _draw_detection_lines(self, frame):
        """Draw detection lines on frame"""
        (h_orig, w_orig) = frame.shape[:2]
        line_offset_scaled = int(
            self.app.settings['line_offset'] * (h_orig / MAX_DISPLAY_HEIGHT)
        )

        if self.app.settings['line_orientation'] == "Horizontal":
            line1_pos_scaled = int(
                self.app.settings['line1_y'] * (h_orig / MAX_DISPLAY_HEIGHT)
            )
            line2_pos_scaled = line1_pos_scaled + line_offset_scaled
            cv2.line(frame, (0, line1_pos_scaled), (w_orig, line1_pos_scaled), (0, 255, 0), 2)
            cv2.line(frame, (0, line2_pos_scaled), (w_orig, line2_pos_scaled), (0, 0, 255), 2)
        else:
            line1_pos_scaled = int(
                self.app.settings['line1_x'] * (w_orig / MAX_DISPLAY_WIDTH)
            )
            line2_pos_scaled = line1_pos_scaled + line_offset_scaled
            cv2.line(frame, (line1_pos_scaled, 0), (line1_pos_scaled, h_orig), (0, 255, 0), 2)
            cv2.line(frame, (line2_pos_scaled, 0), (line2_pos_scaled, h_orig), (0, 0, 255), 2)

    def display_current_frame(self):
        """Display current frame"""
        if not self.cap or not self.cap.isOpened():
            return
        ret, frame = self.cap.read()
        if not ret:
            return
        img = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        img = cv2.resize(img, (MAX_DISPLAY_WIDTH, MAX_DISPLAY_HEIGHT))
        imgtk = ImageTk.PhotoImage(Image.fromarray(img))
        self.app.ui_components.video_label.imgtk = imgtk
        self.app.ui_components.video_label.configure(image=imgtk)

    def cleanup(self):
        """Cleanup video resources"""
        if self.cap:
            self.cap.release()