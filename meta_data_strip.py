#!/usr/bin/env python3
import os
import tkinter as tk
from tkinter import filedialog, ttk, messagebox
import threading
import subprocess
from PIL import Image
import piexif

class MetadataStripperApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Metadata Stripper")
        self.root.geometry("700x500")
        self.root.resizable(True, True)
        
        self.files = []
        self.output_dir = None
        self.ffmpeg_available = self.check_ffmpeg()
        self.setup_ui()
        
    def setup_ui(self):
        # Main frame
        main_frame = ttk.Frame(self.root, padding="10")
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        # Button frame
        button_frame = ttk.Frame(main_frame)
        button_frame.pack(fill=tk.X, pady=(0, 10))
        
        # Select button (for both files and folders)
        select_btn = ttk.Button(button_frame, text="Select Files/Folder", command=self.select_items)
        select_btn.pack(side=tk.LEFT, padx=(0, 5))
        
        # Clear button
        clear_btn = ttk.Button(button_frame, text="Clear Selection", command=self.clear_selection)
        clear_btn.pack(side=tk.LEFT, padx=(0, 5))
        
        # Process button
        process_btn = ttk.Button(button_frame, text="Strip Metadata", command=self.start_processing)
        process_btn.pack(side=tk.LEFT)
        
        # Files list frame
        list_frame = ttk.LabelFrame(main_frame, text="Selected Files")
        list_frame.pack(fill=tk.BOTH, expand=True)
        
        # Scrollbar
        scrollbar = ttk.Scrollbar(list_frame)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        # Files listbox
        self.files_listbox = tk.Listbox(list_frame, yscrollcommand=scrollbar.set)
        self.files_listbox.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        scrollbar.config(command=self.files_listbox.yview)
        
        # Progress bar
        self.progress_frame = ttk.Frame(main_frame)
        self.progress_frame.pack(fill=tk.X, pady=(10, 0))
        
        self.progress_var = tk.DoubleVar()
        self.progress_bar = ttk.Progressbar(
            self.progress_frame, 
            variable=self.progress_var, 
            maximum=100
        )
        self.progress_bar.pack(fill=tk.X)
        
        # Status label
        self.status_var = tk.StringVar()
        self.status_var.set("Ready")
        status_label = ttk.Label(self.progress_frame, textvariable=self.status_var)
        status_label.pack(anchor=tk.W, pady=(5, 0))
        
        # Output directory selection
        output_frame = ttk.Frame(main_frame)
        output_frame.pack(fill=tk.X, pady=(10, 0))
        
        ttk.Label(output_frame, text="Output Directory:").pack(side=tk.LEFT, padx=(0, 5))
        
        self.output_var = tk.StringVar()
        output_entry = ttk.Entry(output_frame, textvariable=self.output_var, width=50)
        output_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 5))
        
        output_btn = ttk.Button(output_frame, text="Browse", command=self.select_output_dir)
        output_btn.pack(side=tk.LEFT)
    
    def select_items(self):
        # Create a custom dialog for selection type
        selection_window = tk.Toplevel(self.root)
        selection_window.title("Select Items")
        selection_window.geometry("300x100")
        selection_window.resizable(False, False)
        selection_window.transient(self.root)
        selection_window.grab_set()
        
        # Center the window
        selection_window.update_idletasks()
        width = selection_window.winfo_width()
        height = selection_window.winfo_height()
        x = (selection_window.winfo_screenwidth() // 2) - (width // 2)
        y = (selection_window.winfo_screenheight() // 2) - (height // 2)
        selection_window.geometry('{}x{}+{}+{}'.format(width, height, x, y))
        
        # Frame for buttons
        btn_frame = ttk.Frame(selection_window, padding="10")
        btn_frame.pack(fill=tk.BOTH, expand=True)
        
        # Label
        ttk.Label(btn_frame, text="What would you like to select?").pack(pady=(0, 10))
        
        # Buttons
        ttk.Button(
            btn_frame, 
            text="Files", 
            command=lambda: [selection_window.destroy(), self.select_files()]
        ).pack(side=tk.LEFT, padx=(0, 5), expand=True)
        
        ttk.Button(
            btn_frame, 
            text="Folder", 
            command=lambda: [selection_window.destroy(), self.select_folder()]
        ).pack(side=tk.LEFT, expand=True)
    
    def select_output_dir(self):
        output_dir = filedialog.askdirectory(title="Select Output Directory")
        if output_dir:
            self.output_dir = output_dir
            self.output_var.set(output_dir)
    
    def select_files(self):
        filetypes = (
            ("Image/Video files", "*.jpg *.jpeg *.png *.gif *.bmp *.tiff *.mp4 *.mov *.avi *.mkv"),
            ("All files", "*.*")
        )
        files = filedialog.askopenfilenames(filetypes=filetypes)
        if files:
            self.add_files(files)
    
    def select_folder(self):
        folder = filedialog.askdirectory()
        if folder:
            self.add_folder_files(folder)
    
    def add_folder_files(self, folder):
        image_extensions = ('.jpg', '.jpeg', '.png', '.gif', '.bmp', '.tiff')
        video_extensions = ('.mp4', '.mov', '.avi', '.mkv')
        
        for root, _, files in os.walk(folder):
            for file in files:
                ext = os.path.splitext(file.lower())[1]
                if ext in image_extensions or ext in video_extensions:
                    full_path = os.path.join(root, file)
                    if full_path not in self.files:
                        self.files.append(full_path)
                        self.files_listbox.insert(tk.END, full_path)
        
        self.status_var.set(f"{len(self.files)} files selected")
    
    def add_files(self, files):
        for file in files:
            if file not in self.files:
                self.files.append(file)
                self.files_listbox.insert(tk.END, file)
        
        self.status_var.set(f"{len(self.files)} files selected")
    
    def clear_selection(self):
        self.files = []
        self.files_listbox.delete(0, tk.END)
        self.status_var.set("Ready")
        self.progress_var.set(0)
    
    def start_processing(self):
        if not self.files:
            messagebox.showinfo("No Files", "Please select files to process")
            return
        
        if not self.output_dir:
            messagebox.showinfo("No Output Directory", "Please select an output directory")
            return
            
        # Create a thread to process files
        threading.Thread(
            target=self.process_files,
            args=(self.output_dir,),
            daemon=True
        ).start()
    
    def process_files(self, output_dir):
        total = len(self.files)
        processed = 0
        skipped = 0
        
        for file in self.files:
            try:
                # Update status
                file_name = os.path.basename(file)
                self.status_var.set(f"Processing: {file_name}")
                
                # Process based on file type
                ext = os.path.splitext(file.lower())[1]
                
                if ext in ('.jpg', '.jpeg', '.png', '.tiff', '.bmp', '.gif'):
                    self.strip_image_metadata(file, output_dir)
                elif ext in ('.mp4', '.mov', '.avi', '.mkv'):
                    # Skip video processing if FFmpeg is not available
                    if not self.ffmpeg_available:
                        self.status_var.set(f"Skipping video file (FFmpeg not available): {file_name}")
                        skipped += 1
                        continue
                    self.strip_video_metadata(file, output_dir)
                else:
                    # Just copy the file for unsupported types
                    output_path = os.path.join(output_dir, os.path.basename(file))
                    with open(file, 'rb') as src, open(output_path, 'wb') as dst:
                        dst.write(src.read())
                
                # Update progress
                processed += 1
                progress = (processed / total) * 100
                self.progress_var.set(progress)
                self.root.update_idletasks()
                
            except Exception as e:
                self.status_var.set(f"Error processing {file_name}: {str(e)}")
                skipped += 1
                # Continue with next file
        
        # Update final status message with processed and skipped counts
        status_msg = f"Completed! Processed {processed} of {total} files."
        if skipped > 0:
            status_msg += f" Skipped {skipped} files."
        
        self.status_var.set(status_msg)
        messagebox.showinfo("Complete", status_msg)
    
    def strip_image_metadata(self, file_path, output_dir):
        try:
            # Get the output file path
            file_name = os.path.basename(file_path)
            output_path = os.path.join(output_dir, file_name)
            
            # Process based on file type
            ext = os.path.splitext(file_path.lower())[1]
            
            if ext in ('.jpg', '.jpeg'):
                # Remove EXIF data using piexif
                try:
                    piexif.remove(file_path)
                    # Save as new file
                    img = Image.open(file_path)
                    img.save(output_path)
                except:
                    # Fallback to PIL if piexif fails
                    img = Image.open(file_path)
                    data = list(img.getdata())
                    image_without_exif = Image.new(img.mode, img.size)
                    image_without_exif.putdata(data)
                    image_without_exif.save(output_path)
            else:
                # For PNG, GIF, etc.
                img = Image.open(file_path)
                data = list(img.getdata())
                image_without_meta = Image.new(img.mode, img.size)
                image_without_meta.putdata(data)
                image_without_meta.save(output_path)
                
        except Exception as e:
            raise Exception(f"Failed to process image: {str(e)}")
    
    def strip_video_metadata(self, file_path, output_dir):
        try:
            # Get the output file path
            file_name = os.path.basename(file_path)
            output_path = os.path.join(output_dir, file_name)
            
            # Check if FFmpeg is available
            try:
                # Try to run a simple FFmpeg command to check if it's available
                subprocess.run(
                    ['ffmpeg', '-version'],
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    check=True
                )
            except (subprocess.SubprocessError, FileNotFoundError):
                messagebox.showerror(
                    "FFmpeg Not Found", 
                    "FFmpeg is required for video processing but was not found. "
                    "Please install FFmpeg and make sure it's in your system PATH."
                )
                raise Exception("FFmpeg not found")
            
            # Use FFmpeg to strip metadata with more robust options
            command = [
                'ffmpeg',
                '-i', file_path,
                '-map_metadata', '-1',       # Remove all metadata
                '-map', '0',                 # Map all streams from input to output
                '-c', 'copy',                # Copy all streams without re-encoding
                '-movflags', 'faststart',    # Optimize for web playback
                '-y',                        # Overwrite output files without asking
                output_path
            ]
            
            # Run FFmpeg process with timeout
            try:
                result = subprocess.run(
                    command,
                    stderr=subprocess.PIPE,
                    stdout=subprocess.PIPE,
                    text=True,
                    timeout=300  # 5 minute timeout for very large files
                )
                
                if result.returncode != 0:
                    error_msg = result.stderr
                    # Make the error message more user-friendly
                    if "No such file or directory" in error_msg:
                        error_msg = "FFmpeg could not find the input file."
                    elif "Invalid data found when processing input" in error_msg:
                        error_msg = "The video file appears to be corrupt or in an unsupported format."
                    raise Exception(f"FFmpeg error: {error_msg}")
                    
            except subprocess.TimeoutExpired:
                raise Exception("Video processing timed out. The file may be too large.")
                
        except Exception as e:
            # If something goes wrong, try a simpler approach for some common formats
            if os.path.splitext(file_path.lower())[1] in ('.mp4', '.mov'):
                try:
                    self.status_var.set(f"Trying alternative method for {os.path.basename(file_path)}...")
                    # Alternative command for MP4/MOV files
                    alt_command = [
                        'ffmpeg',
                        '-i', file_path,
                        '-map_metadata', '-1',
                        '-c:v', 'copy',
                        '-c:a', 'copy',
                        '-f', 'mp4',
                        '-y',
                        output_path
                    ]
                    subprocess.run(
                        alt_command,
                        stderr=subprocess.PIPE,
                        stdout=subprocess.PIPE,
                        check=True,
                        timeout=300
                    )
                    return  # If alternative method succeeds, return
                except:
                    # If alternative also fails, continue with raising the original error
                    pass
                
            raise Exception(f"Failed to process video: {str(e)}")

    def check_ffmpeg(self):
        """Check if FFmpeg is available on the system"""
        try:
            # Try to run a simple FFmpeg command
            subprocess.run(
                ['ffmpeg', '-version'],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                check=False
            )
            return True
        except (subprocess.SubprocessError, FileNotFoundError):
            # Show a warning message
            messagebox.showwarning(
                "FFmpeg Not Found", 
                "FFmpeg is required for video processing but was not found. "
                "You can still process images, but video files will be skipped. "
                "To process videos, please install FFmpeg and make sure it's in your system PATH."
            )
            return False


if __name__ == "__main__":
    root = tk.Tk()
    app = MetadataStripperApp(root)
    root.mainloop() 