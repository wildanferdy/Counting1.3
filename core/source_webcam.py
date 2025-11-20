import cv2
import tkinter as tk
import ttkbootstrap as ttk
import sys
import threading
import time

from ttkbootstrap.constants import *
from tkinter import messagebox

class WebcamSelectionDialog:
    def __init__(self, parent, callback):
        self.callback = callback
        self.selected_camera = None
        self.detection_thread = None
        self.detection_complete = False
        self.available_cameras = []
        self.parent = parent

        # Get screen dimensions from parent
        screen_width = parent.winfo_screenwidth()
        screen_height = parent.winfo_screenheight()
        
        # Create dialog window
        self.dialog = tk.Toplevel(parent)
        self.dialog.title("Select Webcam")

        DEFAULT_DIALOG_WIDTH = 600
        DEFAULT_DIALOG_HEIGHT = 350  # Increased height for better layout

        # Center the dialog on screen
        pos_x = (screen_width - DEFAULT_DIALOG_WIDTH) // 2
        pos_y = (screen_height - DEFAULT_DIALOG_HEIGHT) // 2

        # Set geometry properly on dialog, not self
        self.dialog.geometry(f"{DEFAULT_DIALOG_WIDTH}x{DEFAULT_DIALOG_HEIGHT}+{pos_x}+{pos_y}")
        
        self.dialog.transient(parent)
        self.dialog.grab_set()
        self.dialog.resizable(True, True)  # Allow resize for better UX
        
        # Create main frame
        self.main_frame = ttk.Frame(self.dialog, padding="20")
        self.main_frame.pack(fill=BOTH, expand=True)
        
        # Title
        self.title_label = ttk.Label(self.main_frame, text="Scanning for Webcams...", 
                                    font=("Arial", 12, "bold"))
        self.title_label.pack(anchor=W, pady=(0, 10))
        
        # Progress bar
        self.progress = ttk.Progressbar(self.main_frame, mode='indeterminate', bootstyle="info")
        self.progress.pack(fill=X, pady=(0, 10))    
        self.progress.start()
        
        # Status label
        self.status_label = ttk.Label(self.main_frame, text="Please wait while we detect available cameras...")
        self.status_label.pack(anchor=W, pady=(0, 10))
        
        # Camera selection frame (initially hidden)
        self.camera_frame = ttk.Frame(self.main_frame)
        
        ttk.Label(self.camera_frame, text="Available Webcams:", 
                 font=("Arial", 10, "bold")).pack(anchor=W, pady=(0, 5))
        
        # Listbox with scrollbar
        listbox_frame = ttk.Frame(self.camera_frame)
        listbox_frame.pack(fill=BOTH, expand=True, pady=(0, 10))
        
        self.camera_listbox = tk.Listbox(listbox_frame, height=6, font=("Arial", 9),
                                        selectmode=tk.SINGLE)
        scrollbar = ttk.Scrollbar(listbox_frame, orient=VERTICAL, command=self.camera_listbox.yview)
        self.camera_listbox.configure(yscrollcommand=scrollbar.set)
        
        self.camera_listbox.pack(side=LEFT, fill=BOTH, expand=True)
        scrollbar.pack(side=RIGHT, fill=Y)
        
        # Buttons frame
        self.button_frame = ttk.Frame(self.camera_frame)
        self.button_frame.pack(fill=X, pady=(10, 0))
        
        # Left side buttons
        left_buttons = ttk.Frame(self.button_frame)
        left_buttons.pack(side=LEFT)
        
        self.test_button = ttk.Button(left_buttons, text="Test Camera", command=self.test_camera, 
                                     bootstyle="info-outline", state="disabled")
        self.test_button.pack(side=LEFT, padx=(0, 5))
        
        self.refresh_button = ttk.Button(left_buttons, text="Refresh", command=self.refresh_cameras, 
                                        bootstyle="secondary-outline")
        self.refresh_button.pack(side=LEFT, padx=(0, 5))
        
        # Right side buttons
        right_buttons = ttk.Frame(self.button_frame)
        right_buttons.pack(side=RIGHT)
        
        self.cancel_button = ttk.Button(right_buttons, text="Cancel", command=self.cancel, 
                                       bootstyle="secondary-outline")
        self.cancel_button.pack(side=RIGHT)
        
        self.ok_button = ttk.Button(right_buttons, text="OK", command=self.ok, 
                                   bootstyle="success", state="disabled")
        self.ok_button.pack(side=RIGHT, padx=(0, 5))
        
        # Bind selection event
        self.camera_listbox.bind('<<ListboxSelect>>', self.on_camera_select)
        self.camera_listbox.bind('<Double-Button-1>', self.on_double_click)
        
        # Start detection in background
        self.start_camera_detection()
        
        # Handle dialog close
        self.dialog.protocol("WM_DELETE_WINDOW", self.cancel)
        
        # Focus on dialog
        self.dialog.focus_set()
    
    def start_camera_detection(self):
        """Start camera detection in background thread"""
        if self.detection_thread and self.detection_thread.is_alive():
            return
            
        self.detection_thread = threading.Thread(target=self.detect_cameras_threaded, daemon=True)
        self.detection_thread.start()
    
    def detect_cameras_threaded(self):
        """Detect cameras in background thread with optimized approach"""
        try:
            cameras = []
            max_cameras = 10  # Check up to 10 camera indices
            
            for i in range(max_cameras):
                try:
                    # Use different backends based on platform
                    backends = []
                    if sys.platform.startswith('win'):
                        backends = [cv2.CAP_DSHOW, cv2.CAP_MSMF]
                    elif sys.platform.startswith('linux'):
                        backends = [cv2.CAP_V4L2, cv2.CAP_ANY]
                    else:  # macOS
                        backends = [cv2.CAP_AVFOUNDATION, cv2.CAP_ANY]
                    
                    camera_found = False
                    for backend in backends:
                        try:
                            cap = cv2.VideoCapture(i, backend)
                            
                            # Set timeout properties
                            cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)
                            
                            if cap.isOpened():
                                # Try to read a frame with timeout
                                start_time = time.time()
                                ret, frame = cap.read()
                                read_time = time.time() - start_time
                                
                                if ret and frame is not None and frame.size > 0 and read_time < 2.0:
                                    # Get camera properties
                                    width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
                                    height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
                                    fps = cap.get(cv2.CAP_PROP_FPS)
                                    
                                    # Try to get a more descriptive name
                                    backend_name = self.get_backend_name(backend)
                                    
                                    camera_info = {
                                        'index': i,
                                        'name': f"Camera {i} ({backend_name})",
                                        'resolution': f"{width}x{height}",
                                        'fps': f"{fps:.0f}" if fps > 0 else "30",
                                        'backend': backend
                                    }
                                    cameras.append(camera_info)
                                    camera_found = True
                                    break  # Found working camera with this backend
                            
                            cap.release()
                            
                        except Exception as e:
                            print(f"Error testing camera {i} with backend {backend}: {e}")
                            continue
                    
                    if camera_found:
                        continue
                        
                except Exception as e:
                    print(f"Error testing camera {i}: {e}")
                    continue
            
            self.available_cameras = cameras
            
            # Schedule GUI update on main thread
            if hasattr(self.dialog, 'after'):
                self.dialog.after(0, self.update_camera_list)
            
        except Exception as e:
            print(f"Error in camera detection: {e}")
            if hasattr(self.dialog, 'after'):
                self.dialog.after(0, self.show_detection_error)
    
    def get_backend_name(self, backend):
        """Get human-readable backend name"""
        backend_names = {
            cv2.CAP_DSHOW: "DirectShow",
            cv2.CAP_MSMF: "Media Foundation",
            cv2.CAP_V4L2: "Video4Linux2",
            cv2.CAP_AVFOUNDATION: "AVFoundation",
            cv2.CAP_ANY: "Default"
        }
        return backend_names.get(backend, "Unknown")
    
    def update_camera_list(self):
        """Update GUI with detected cameras"""
        try:
            self.progress.stop()
            self.progress.pack_forget()
            
            if self.available_cameras:
                self.title_label.config(text="Select Webcam")
                self.status_label.config(text=f"Found {len(self.available_cameras)} camera(s)")
                
                # Show camera list
                self.camera_frame.pack(fill=BOTH, expand=True, pady=(10, 0))
                
                # Populate listbox
                self.camera_listbox.delete(0, tk.END)
                for camera in self.available_cameras:
                    display_text = f"{camera['name']} - {camera['resolution']} @ {camera['fps']}fps"
                    self.camera_listbox.insert(tk.END, display_text)
                
                # Auto-select first camera
                if self.available_cameras:
                    self.camera_listbox.selection_set(0)
                    self.camera_listbox.activate(0)
                    self.on_camera_select(None)
                
            else:
                self.title_label.config(text="No Webcams Found")
                self.status_label.config(text="No webcams detected on this system.")
                
                # Show error suggestions
                error_frame = ttk.LabelFrame(self.main_frame, text="Troubleshooting", padding="10")
                error_frame.pack(fill=X, pady=(10, 0))
                
                suggestions = [
                    "• Make sure your webcam is connected properly",
                    "• Try a different USB port",
                    "• Check if another application is using the camera",
                    "• Restart the application and try again",
                    "• Check camera permissions in system settings"
                ]
                
                for suggestion in suggestions:
                    ttk.Label(error_frame, text=suggestion, foreground="red").pack(anchor=W, pady=1)
                
                # Only show refresh and cancel buttons
                button_frame = ttk.Frame(self.main_frame)
                button_frame.pack(fill=X, pady=(20, 0))
                
                ttk.Button(button_frame, text="Refresh", command=self.refresh_cameras, 
                          bootstyle="info").pack(side=LEFT)
                ttk.Button(button_frame, text="Cancel", command=self.cancel, 
                          bootstyle="secondary").pack(side=RIGHT)
            
            self.detection_complete = True
            
        except Exception as e:
            print(f"Error updating camera list: {e}")
            self.show_detection_error()
    
    def show_detection_error(self):
        """Show error message if detection fails"""
        self.progress.stop()
        self.progress.pack_forget()
        self.title_label.config(text="Detection Error")
        self.status_label.config(text="Error detecting cameras. Please try refreshing.")
    
    def on_camera_select(self, event):
        """Handle camera selection"""
        selection = self.camera_listbox.curselection()
        if selection:
            self.test_button.config(state="normal")
            self.ok_button.config(state="normal")
        else:
            self.test_button.config(state="disabled")
            self.ok_button.config(state="disabled")
    
    def on_double_click(self, event):
        """Handle double-click on camera (same as OK)"""
        if self.camera_listbox.curselection():
            self.ok()
    
    def refresh_cameras(self):
        """Refresh camera list"""
        # Reset UI
        self.camera_listbox.delete(0, tk.END)
        self.camera_frame.pack_forget()
        
        # Reset progress bar
        self.progress.pack(fill=X, pady=(0, 10))
        self.progress.start()
        
        self.title_label.config(text="Scanning for Webcams...")
        self.status_label.config(text="Refreshing camera list...")
        self.test_button.config(state="disabled")
        self.ok_button.config(state="disabled")
        
        # Clear previous results
        self.available_cameras = []
        self.detection_complete = False
        
        # Start detection again
        self.start_camera_detection()
    
    def test_camera(self):
        """Test selected camera with optimized preview"""
        selection = self.camera_listbox.curselection()
        if not selection:
            messagebox.showwarning("Warning", "Please select a camera first.")
            return
        
        camera_info = self.available_cameras[selection[0]]
        camera_index = camera_info['index']
        backend = camera_info.get('backend', cv2.CAP_ANY)
        
        # Show loading state
        original_text = self.test_button.cget("text")
        self.test_button.config(text="Testing...", state="disabled")
        self.dialog.config(cursor="wait")
        
        def test_in_background():
            try:
                # Use the same backend that worked during detection
                cap = cv2.VideoCapture(camera_index, backend)
                
                # Optimize for quick test
                cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)
                cap.set(cv2.CAP_PROP_FPS, 30)
                
                success = False
                error_msg = ""
                
                if cap.isOpened():
                    # Try to read multiple frames to ensure stability
                    for _ in range(3):
                        ret, frame = cap.read()
                        if ret and frame is not None and frame.size > 0:
                            success = True
                        else:
                            success = False
                            break
                        time.sleep(0.1)  # Small delay between frames
                else:
                    error_msg = "Failed to open camera"
                
                cap.release()
                
                # Update UI in main thread
                def update_ui():
                    self.test_button.config(text=original_text, state="normal")
                    self.dialog.config(cursor="")
                    if success:
                        messagebox.showinfo("Camera Test", 
                                          f"✓ Camera {camera_index} is working properly!\n\n"
                                          f"Resolution: {camera_info['resolution']}\n"
                                          f"Backend: {camera_info['name']}")
                    else:
                        messagebox.showerror("Camera Test", 
                                           f"✗ Camera {camera_index} test failed!\n\n"
                                           f"Error: {error_msg if error_msg else 'Could not capture frames'}\n"
                                           f"Try selecting a different camera or refresh the list.")
                
                if hasattr(self.dialog, 'after'):
                    self.dialog.after(0, update_ui)
                
            except Exception as e:
                def show_error():
                    self.test_button.config(text=original_text, state="normal")
                    self.dialog.config(cursor="")
                    messagebox.showerror("Camera Test", f"Error testing camera: {str(e)}")
                
                if hasattr(self.dialog, 'after'):
                    self.dialog.after(0, show_error)
        
        # Run test in background thread
        threading.Thread(target=test_in_background, daemon=True).start()
    
    def ok(self):
        """Select camera and close dialog"""
        selection = self.camera_listbox.curselection()
        if selection:
            self.selected_camera = self.available_cameras[selection[0]]['index']
            if self.callback:
                self.callback(self.selected_camera)
        self.dialog.destroy()
    
    def cancel(self):
        """Cancel selection and close dialog"""
        if self.callback:
            self.callback(None)  # Pass None to indicate cancellation
        self.dialog.destroy()
    
    def get_selected_camera(self):
        """Get the selected camera index"""
        return self.selected_camera