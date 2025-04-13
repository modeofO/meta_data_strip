import os
import tkinter as tk
from tkinter import filedialog, ttk, messagebox
import threading
import subprocess
from PIL import Image
import piexif
import json
from datetime import datetime

class MetadataStripperApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Metadata Stripper")
        self.root.geometry("800x600")  # Increased size to accommodate tabbed interface
        self.root.resizable(True, True)
        
        self.files = []
        self.output_dir = None
        self.ffmpeg_available = self.check_ffmpeg()
        
        # User preferences with default values
        self.preferences = {
            "suppress_overwrite_warning": False,
            "suppress_overwrite_allowed_warning": False,
            "suppress_completion_message": False,
            "allow_overwrite": False,  # Default to not overwrite (safer)
            "last_output_directory": "",  # Remember last output directory
            "keep_log": True,  # Default to keeping processing history
            "max_history_entries": 100  # Maximum number of history entries to keep
        }
        
        # Processing history
        self.history = []
        
        # Try to load preferences and history
        self.load_preferences()
        self.load_history()
        
        # Initialize with saved preference
        self.allow_overwrite = tk.BooleanVar(value=self.preferences["allow_overwrite"])
        self.keep_log = tk.BooleanVar(value=self.preferences["keep_log"])
        
        self.setup_ui()
        
        # Set last used output directory if available
        if self.preferences["last_output_directory"] and os.path.exists(self.preferences["last_output_directory"]):
            self.output_dir = self.preferences["last_output_directory"]
            self.output_var.set(self.output_dir)
        
    def load_preferences(self):
        """Load user preferences from file"""
        try:
            preferences_file = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'preferences.json')
            if os.path.exists(preferences_file):
                with open(preferences_file, 'r') as f:
                    loaded_prefs = json.load(f)
                    # Update preferences with loaded values
                    self.preferences.update(loaded_prefs)
        except Exception:
            # If anything goes wrong, just use defaults
            pass
    
    def save_preferences(self):
        """Save user preferences to file"""
        try:
            # Update the current settings in preferences
            self.preferences["allow_overwrite"] = self.allow_overwrite.get()
            self.preferences["keep_log"] = self.keep_log.get()
            
            preferences_file = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'preferences.json')
            with open(preferences_file, 'w') as f:
                json.dump(self.preferences, f)
        except Exception:
            # If saving fails, just continue - not critical
            pass
    
    def load_history(self):
        """Load processing history from file"""
        try:
            history_file = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'processing_history.json')
            if os.path.exists(history_file):
                with open(history_file, 'r') as f:
                    self.history = json.load(f)
        except Exception:
            # If anything goes wrong, just use an empty history
            self.history = []
    
    def save_history(self):
        """Save processing history to file"""
        try:
            # Only save if history logging is enabled
            if not self.keep_log.get():
                return
                
            # Trim history if it exceeds the maximum number of entries
            if len(self.history) > self.preferences["max_history_entries"]:
                self.history = self.history[-self.preferences["max_history_entries"]:]
                
            history_file = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'processing_history.json')
            with open(history_file, 'w') as f:
                json.dump(self.history, f)
        except Exception:
            # If saving fails, just continue - not critical
            pass
    
    def add_to_history(self, source_file, output_file, status="Success"):
        """Add a processed file to the history"""
        if not self.keep_log.get():
            return
            
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        entry = {
            "timestamp": timestamp,
            "source_file": source_file,
            "output_file": output_file,
            "status": status
        }
        
        self.history.append(entry)
        
        # If the history tab is created, update it
        if hasattr(self, 'history_tree'):
            self.update_history_display()
    
    def clear_history(self):
        """Clear processing history"""
        self.history = []
        
        # Clear the history display if it exists
        if hasattr(self, 'history_tree'):
            for item in self.history_tree.get_children():
                self.history_tree.delete(item)
                
        # Delete the history file
        try:
            history_file = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'processing_history.json')
            if os.path.exists(history_file):
                os.remove(history_file)
        except Exception:
            pass
            
        messagebox.showinfo("History Cleared", "Processing history has been cleared.")
    
    def setup_ui(self):
        # Create notebook (tabbed interface)
        self.notebook = ttk.Notebook(self.root)
        self.notebook.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # Main tab for processing files
        self.main_tab = ttk.Frame(self.notebook)
        self.notebook.add(self.main_tab, text="Process Files")
        
        # History tab
        self.history_tab = ttk.Frame(self.notebook)
        self.notebook.add(self.history_tab, text="History")
        
        # Setup main processing UI
        self.setup_main_tab(self.main_tab)
        
        # Setup history tab
        self.setup_history_tab(self.history_tab)
    
    def setup_main_tab(self, parent):
        # Main frame
        main_frame = ttk.Frame(parent, padding="10")
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
        
        # Options frame
        options_frame = ttk.LabelFrame(main_frame, text="Options")
        options_frame.pack(fill=tk.X, pady=(10, 0))
        
        # Overwrite option
        overwrite_check = ttk.Checkbutton(
            options_frame, 
            text="Allow overwriting original files (use with caution!)",
            variable=self.allow_overwrite
        )
        overwrite_check.pack(anchor=tk.W, padx=5, pady=2)
        
        # Keep log option
        log_check = ttk.Checkbutton(
            options_frame, 
            text="Keep processing history log (Stored locally in processing_history.json)",
            variable=self.keep_log,
            command=self.update_log_preference
        )
        log_check.pack(anchor=tk.W, padx=5, pady=2)
    
    def setup_history_tab(self, parent):
        # Create a frame for the history tab
        history_frame = ttk.Frame(parent, padding="10")
        history_frame.pack(fill=tk.BOTH, expand=True)
        
        # Create a toolbar at the top
        toolbar = ttk.Frame(history_frame)
        toolbar.pack(fill=tk.X, pady=(0, 10))
        
        # Add a clear history button
        clear_btn = ttk.Button(toolbar, text="Clear History", command=self.clear_history)
        clear_btn.pack(side=tk.LEFT, padx=(0, 5))
        
        # Add a refresh button
        refresh_btn = ttk.Button(toolbar, text="Refresh", command=self.update_history_display)
        refresh_btn.pack(side=tk.LEFT)
        
        # Create a treeview for history display
        tree_frame = ttk.Frame(history_frame)
        tree_frame.pack(fill=tk.BOTH, expand=True)
        
        # Scrollbars
        vsb = ttk.Scrollbar(tree_frame, orient="vertical")
        hsb = ttk.Scrollbar(tree_frame, orient="horizontal")
        
        # Create the treeview
        self.history_tree = ttk.Treeview(
            tree_frame,
            columns=("timestamp", "source", "output", "status"),
            show="headings",
            yscrollcommand=vsb.set,
            xscrollcommand=hsb.set
        )
        
        # Set up the scrollbars
        vsb.config(command=self.history_tree.yview)
        hsb.config(command=self.history_tree.xview)
        
        # Configure column headings
        self.history_tree.heading("timestamp", text="Timestamp")
        self.history_tree.heading("source", text="Source File")
        self.history_tree.heading("output", text="Output File")
        self.history_tree.heading("status", text="Status")
        
        # Configure column widths
        self.history_tree.column("timestamp", width=150, minwidth=150)
        self.history_tree.column("source", width=250, minwidth=100)
        self.history_tree.column("output", width=250, minwidth=100)
        self.history_tree.column("status", width=80, minwidth=80)
        
        # Pack everything
        self.history_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        vsb.pack(side=tk.RIGHT, fill=tk.Y)
        hsb.pack(side=tk.BOTTOM, fill=tk.X)
        
        # Add right-click menu for copying paths
        self.create_context_menu()
        
        # Populate with existing history
        self.update_history_display()
    
    def create_context_menu(self):
        # Create a right-click menu
        self.context_menu = tk.Menu(self.root, tearoff=0)
        self.context_menu.add_command(label="Copy Source Path", command=self.copy_source_path)
        self.context_menu.add_command(label="Copy Output Path", command=self.copy_output_path)
        self.context_menu.add_separator()
        self.context_menu.add_command(label="Open Source Location", command=self.open_source_location)
        self.context_menu.add_command(label="Open Output Location", command=self.open_output_location)
        
        # Bind right-click to the treeview
        self.history_tree.bind("<Button-3>", self.show_context_menu)
    
    def show_context_menu(self, event):
        # Show the context menu at the mouse position
        try:
            # First identify the item
            item = self.history_tree.identify_row(event.y)
            if item:
                # Select the item
                self.history_tree.selection_set(item)
                # Show the menu
                self.context_menu.post(event.x_root, event.y_root)
        except Exception:
            pass
    
    def copy_source_path(self):
        # Get the selected item
        selection = self.history_tree.selection()
        if selection:
            item = selection[0]
            source_path = self.history_tree.item(item, "values")[1]
            self.root.clipboard_clear()
            self.root.clipboard_append(source_path)
    
    def copy_output_path(self):
        # Get the selected item
        selection = self.history_tree.selection()
        if selection:
            item = selection[0]
            output_path = self.history_tree.item(item, "values")[2]
            self.root.clipboard_clear()
            self.root.clipboard_append(output_path)
    
    def open_source_location(self):
        # Open file explorer at the source file location
        selection = self.history_tree.selection()
        if selection:
            item = selection[0]
            source_path = self.history_tree.item(item, "values")[1]
            if os.path.exists(source_path):
                self.open_file_location(source_path)
    
    def open_output_location(self):
        # Open file explorer at the output file location
        selection = self.history_tree.selection()
        if selection:
            item = selection[0]
            output_path = self.history_tree.item(item, "values")[2]
            if os.path.exists(output_path):
                self.open_file_location(output_path)
    
    def open_file_location(self, path):
        """Open the file explorer at the specified path"""
        try:
            # Get the directory of the file
            directory = os.path.dirname(path)
            
            # Open the directory in the file explorer based on OS
            if os.name == 'nt':  # Windows
                os.startfile(directory)
            elif os.name == 'posix':  # macOS, Linux
                if 'darwin' in os.sys.platform:  # macOS
                    subprocess.run(['open', directory])
                else:  # Linux
                    subprocess.run(['xdg-open', directory])
        except Exception:
            messagebox.showerror("Error", "Could not open file location.")
    
    def update_history_display(self):
        """Update the history treeview with current history data"""
        # Clear the current view
        for item in self.history_tree.get_children():
            self.history_tree.delete(item)
            
        # Add entries
        for entry in self.history:
            self.history_tree.insert(
                "", 
                "end", 
                values=(
                    entry.get("timestamp", "Unknown"),
                    entry.get("source_file", "Unknown"),
                    entry.get("output_file", "Unknown"),
                    entry.get("status", "Unknown")
                )
            )
    
    def update_log_preference(self):
        """Update the log keeping preference"""
        self.preferences["keep_log"] = self.keep_log.get()
        self.save_preferences()
        
        # If logging is disabled, ask if user wants to clear history
        if not self.keep_log.get() and self.history:
            if messagebox.askyesno(
                "Clear History", 
                "Do you want to clear the existing processing history?"
            ):
                self.clear_history()
    
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
            # Save the last used directory
            self.preferences["last_output_directory"] = output_dir
            self.save_preferences()
    
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
        
        # Save current overwrite preference
        if self.preferences["allow_overwrite"] != self.allow_overwrite.get():
            self.preferences["allow_overwrite"] = self.allow_overwrite.get()
            self.save_preferences()
        
        # Check if any files would be overwritten, only if overwrite is not allowed
        overwrite_risk = self.check_overwrite_risk()
        
        if not self.allow_overwrite.get() and overwrite_risk:
            # Skip warning if user chose to suppress it
            if not self.preferences["suppress_overwrite_warning"]:
                # Create custom warning dialog with "don't show again" option
                response = self.show_warning_with_dont_show_again(
                    "Overwrite Risk",
                    "Some original files may be overwritten because they are in the same directory "
                    "as your output directory. Do you want to continue?\n\n"
                    "It's recommended to select a different output directory to preserve your originals.",
                    "suppress_overwrite_warning"
                )
                if not response:
                    return
        elif self.allow_overwrite.get() and overwrite_risk:
            # If overwrite is allowed but there's a risk, show a stronger warning
            # Skip warning if user chose to suppress it
            if not self.preferences["suppress_overwrite_allowed_warning"]:
                # Create custom warning dialog with "don't show again" option
                response = self.show_warning_with_dont_show_again(
                    "Confirm Overwrite",
                    "WARNING: You have chosen to allow overwriting original files, and some of your "
                    "selected files are in the output directory. This will PERMANENTLY REPLACE your "
                    "original files with versions that have metadata removed.\n\n"
                    "Are you absolutely sure you want to continue?",
                    "suppress_overwrite_allowed_warning"
                )
                if not response:
                    return
            
        # Create a thread to process files
        threading.Thread(
            target=self.process_files,
            args=(self.output_dir,),
            daemon=True
        ).start()
    
    def show_warning_with_dont_show_again(self, title, message, preference_key):
        """Display a custom warning dialog with a 'Don't show again' checkbox"""
        dialog = tk.Toplevel(self.root)
        dialog.title(title)
        dialog.transient(self.root)
        dialog.grab_set()
        dialog.resizable(False, False)
        
        # Center the dialog
        dialog.geometry("450x250")
        dialog.update_idletasks()
        x = (dialog.winfo_screenwidth() // 2) - (dialog.winfo_width() // 2)
        y = (dialog.winfo_screenheight() // 2) - (dialog.winfo_height() // 2)
        dialog.geometry(f"+{x}+{y}")
        
        # Warning icon
        frame = ttk.Frame(dialog, padding="20")
        frame.pack(fill=tk.BOTH, expand=True)
        
        # Warning message
        msg_label = ttk.Label(frame, text=message, wraplength=400, justify="left")
        msg_label.pack(pady=(0, 20))
        
        # "Don't show again" checkbox
        dont_show_var = tk.BooleanVar(value=False)
        dont_show_check = ttk.Checkbutton(
            frame, 
            text="Don't show this warning again", 
            variable=dont_show_var
        )
        dont_show_check.pack(anchor=tk.W, pady=(0, 20))
        
        # Result variable to return
        result = tk.BooleanVar(value=False)
        
        # Button handlers
        def on_yes():
            result.set(True)
            # Update preference if checkbox is checked
            if dont_show_var.get():
                self.preferences[preference_key] = True
                self.save_preferences()
            dialog.destroy()
            
        def on_no():
            result.set(False)
            dialog.destroy()
            
        # Buttons
        btn_frame = ttk.Frame(frame)
        btn_frame.pack(fill=tk.X)
        
        yes_btn = ttk.Button(btn_frame, text="Yes", command=on_yes, width=10)
        yes_btn.pack(side=tk.RIGHT, padx=5)
        
        no_btn = ttk.Button(btn_frame, text="No", command=on_no, width=10)
        no_btn.pack(side=tk.RIGHT, padx=5)
        
        # Set focus to "No" button as it's the safer option
        no_btn.focus_set()
        
        # Make Escape key close with "No"
        dialog.bind("<Escape>", lambda e: on_no())
        
        # Wait for dialog to close
        dialog.wait_window()
        
        return result.get()
    
    def check_overwrite_risk(self):
        """Check if any original files would be overwritten"""
        for file_path in self.files:
            file_dir = os.path.dirname(file_path)
            if os.path.normpath(file_dir) == os.path.normpath(self.output_dir):
                return True
        return False
    
    def get_safe_output_path(self, file_path, output_dir):
        """Generate a safe output path that won't overwrite the original file"""
        file_name = os.path.basename(file_path)
        base_name, extension = os.path.splitext(file_name)
        output_path = os.path.join(output_dir, file_name)
        
        # If the input and output paths are identical, and overwrite is not allowed, modify the output filename
        if os.path.normpath(os.path.dirname(file_path)) == os.path.normpath(output_dir) and not self.allow_overwrite.get():
            output_path = os.path.join(output_dir, f"{base_name}_clean{extension}")
            # If that still exists, add a number
            counter = 1
            while os.path.exists(output_path):
                output_path = os.path.join(output_dir, f"{base_name}_clean_{counter}{extension}")
                counter += 1
                
        return output_path
    
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
                output_path = self.get_safe_output_path(file, output_dir)
                
                if ext in ('.jpg', '.jpeg', '.png', '.tiff', '.bmp', '.gif'):
                    self.strip_image_metadata(file, output_dir)
                    # Add to history
                    self.add_to_history(file, output_path)
                elif ext in ('.mp4', '.mov', '.avi', '.mkv'):
                    # Skip video processing if FFmpeg is not available
                    if not self.ffmpeg_available:
                        self.status_var.set(f"Skipping video file (FFmpeg not available): {file_name}")
                        # Add to history with skip status
                        self.add_to_history(file, output_path, "Skipped - No FFmpeg")
                        skipped += 1
                        continue
                    self.strip_video_metadata(file, output_dir)
                    # Add to history
                    self.add_to_history(file, output_path)
                else:
                    # Just copy the file for unsupported types
                    output_path = self.get_safe_output_path(file, output_dir)
                    with open(file, 'rb') as src, open(output_path, 'wb') as dst:
                        dst.write(src.read())
                    # Add to history
                    self.add_to_history(file, output_path, "Copied (No Metadata)")
                
                # Update progress
                processed += 1
                progress = (processed / total) * 100
                self.progress_var.set(progress)
                self.root.update_idletasks()
                
            except Exception as e:
                error_msg = str(e)
                self.status_var.set(f"Error processing {file_name}: {error_msg}")
                # Add to history with error status
                output_path = self.get_safe_output_path(file, output_dir)
                self.add_to_history(file, output_path, f"Error: {error_msg[:30]}...")
                skipped += 1
                # Continue with next file
        
        # Update final status message with processed and skipped counts
        status_msg = f"Completed! Processed {processed} of {total} files."
        if skipped > 0:
            status_msg += f" Skipped {skipped} files."
        
        self.status_var.set(status_msg)
        
        # Save the history to disk
        self.save_history()
        
        # Show completion message unless suppressed
        if not self.preferences["suppress_completion_message"]:
            self.show_completion_message(status_msg, processed, skipped, total)
    
    def strip_image_metadata(self, file_path, output_dir):
        try:
            # Get the output file path with safety check
            output_path = self.get_safe_output_path(file_path, output_dir)
            
            # Process based on file type
            ext = os.path.splitext(file_path.lower())[1]
            
            if ext in ('.jpg', '.jpeg'):
                # Remove EXIF data using piexif
                try:
                    # Create a copy first, don't modify the original
                    img = Image.open(file_path)
                    # Try to use piexif on the memory image 
                    piexif_data = piexif.load(img.info.get("exif", b""))
                    # Just create empty exif data
                    exif_bytes = piexif.dump({})
                    img.save(output_path, exif=exif_bytes)
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
            # Get the output file path with safety check
            output_path = self.get_safe_output_path(file_path, output_dir)
            
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

    def show_completion_message(self, status_msg, processed, skipped, total):
        """Show completion message with option to not show again"""
        dialog = tk.Toplevel(self.root)
        dialog.title("Processing Complete")
        dialog.transient(self.root)
        dialog.grab_set()
        dialog.resizable(False, False)
        
        # Center the dialog
        dialog.geometry("400x200")
        dialog.update_idletasks()
        x = (dialog.winfo_screenwidth() // 2) - (dialog.winfo_width() // 2)
        y = (dialog.winfo_screenheight() // 2) - (dialog.winfo_height() // 2)
        dialog.geometry(f"+{x}+{y}")
        
        frame = ttk.Frame(dialog, padding="20")
        frame.pack(fill=tk.BOTH, expand=True)
        
        # Success icon or image could be added here if desired
        
        # Message
        msg_label = ttk.Label(frame, text=status_msg, wraplength=350, justify="center")
        msg_label.pack(pady=(0, 10))
        
        # Add output directory info
        output_info = f"Files saved to: {self.output_dir}"
        output_label = ttk.Label(frame, text=output_info, wraplength=350, justify="center")
        output_label.pack(pady=(0, 20))
        
        # "Don't show again" checkbox
        dont_show_var = tk.BooleanVar(value=False)
        dont_show_check = ttk.Checkbutton(
            frame, 
            text="Don't show this message again", 
            variable=dont_show_var
        )
        dont_show_check.pack(anchor=tk.W, pady=(0, 10))
        
        # Button handler
        def on_ok():
            # Update preference if checkbox is checked
            if dont_show_var.get():
                self.preferences["suppress_completion_message"] = True
                self.save_preferences()
            dialog.destroy()
        
        # OK button
        ok_btn = ttk.Button(frame, text="OK", command=on_ok, width=10)
        ok_btn.pack()
        
        # Set focus to OK button
        ok_btn.focus_set()
        
        # Make Enter or Escape close the dialog
        dialog.bind("<Return>", lambda e: on_ok())
        dialog.bind("<Escape>", lambda e: on_ok())
        
        # Wait for dialog to close
        dialog.wait_window()


if __name__ == "__main__":
    root = tk.Tk()
    app = MetadataStripperApp(root)
    root.mainloop() 