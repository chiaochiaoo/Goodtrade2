"""
GoodTrade AuditLog Analyzer
A standalone UI application for filtering and viewing Goodtrade audit logs
"""

import tkinter as tk
from tkinter import scrolledtext, filedialog, messagebox
import os
import re
from datetime import datetime
import pytz

# Try to import tkinterdnd for drag and drop, fall back gracefully
try:
    from tkinterdnd2 import DND_FILES, DND_TEXT, TkinterDnD
    HAS_DND = True
except ImportError:
    HAS_DND = False

class AuditLogAnalyzer:
    def __init__(self, root):
        self.root = root
        self.root.title("GoodTrade AuditLog")
        self.root.geometry("1000x700")
        
        self.log_content = ""
        self.filtered_content = ""
        self.current_font_size = 11
        
        # Setup UI
        self.setup_ui()
        
    def setup_ui(self):
        """Create the UI layout"""
        # Title
        title_frame = tk.Frame(self.root, bg="#2c3e50")
        title_frame.pack(fill=tk.X, padx=10, pady=5)
        
        title_label = tk.Label(
            title_frame,
            text="GoodTrade AuditLog",
            font=("Arial", 18, "bold"),
            bg="#2c3e50",
            fg="white"
        )
        title_label.pack()
        
        # Control Panel
        control_frame = tk.LabelFrame(
            self.root,
            text="Filter Settings",
            font=("Arial", 10, "bold"),
            padx=10,
            pady=10
        )
        control_frame.pack(fill=tk.X, padx=10, pady=5)
        
        # File selection
        file_frame = tk.Frame(control_frame)
        file_frame.pack(fill=tk.X, pady=5)
        
        file_label = tk.Label(file_frame, text="Audit Log File:", width=15, anchor="w")
        file_label.pack(side=tk.LEFT, padx=5)
        
        self.file_display = tk.Label(
            file_frame,
            text="[Drag & drop file here or click Browse]",
            bg="#ecf0f1",
            fg="#7f8c8d",
            padx=10,
            pady=5,
            relief=tk.SUNKEN
        )
        self.file_display.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=5)
        
        browse_btn = tk.Button(
            file_frame,
            text="Browse",
            command=self.browse_file,
            width=10
        )
        browse_btn.pack(side=tk.LEFT, padx=5)
        
        # Ticker name
        ticker_frame = tk.Frame(control_frame)
        ticker_frame.pack(fill=tk.X, pady=5)
        
        ticker_label = tk.Label(ticker_frame, text="Ticker:", width=15, anchor="w")
        ticker_label.pack(side=tk.LEFT, padx=5)
        
        self.ticker_var = tk.StringVar(value="All")
        self.ticker_dropdown = tk.OptionMenu(
            ticker_frame,
            self.ticker_var,
            "All"
        )
        self.ticker_dropdown.pack(side=tk.LEFT, padx=5, fill=tk.X, expand=False)
        self.ticker_dropdown.config(width=20)
        
        # Time range frame
        time_frame = tk.Frame(control_frame)
        time_frame.pack(fill=tk.X, pady=5)
        
        start_label = tk.Label(time_frame, text="Start Time (HH:MM:SS):", width=22, anchor="w")
        start_label.pack(side=tk.LEFT, padx=5)
        
        self.start_time_entry = tk.Entry(time_frame, width=12)
        self.start_time_entry.pack(side=tk.LEFT, padx=5)
        self.start_time_entry.insert(0, "00:00:00")
        
        end_label = tk.Label(time_frame, text="End Time (HH:MM:SS):", anchor="w")
        end_label.pack(side=tk.LEFT, padx=5)
        
        self.end_time_entry = tk.Entry(time_frame, width=12)
        self.end_time_entry.pack(side=tk.LEFT, padx=5)
        self.end_time_entry.insert(0, "23:59:59")
        
        # Apply button
        apply_btn = tk.Button(
            time_frame,
            text="Apply Filter",
            command=self.apply_filter,
            bg="#27ae60",
            fg="white",
            width=15,
            font=("Arial", 10, "bold")
        )
        apply_btn.pack(side=tk.LEFT, padx=5)
        
        # Font size control frame
        font_frame = tk.Frame(control_frame)
        font_frame.pack(fill=tk.X, pady=5)
        
        font_label = tk.Label(font_frame, text="Font Size:", width=15, anchor="w")
        font_label.pack(side=tk.LEFT, padx=5)
        
        decrease_btn = tk.Button(
            font_frame,
            text="−",
            command=self.decrease_font_size,
            width=3,
            font=("Arial", 12, "bold")
        )
        decrease_btn.pack(side=tk.LEFT, padx=2)
        
        self.font_size_label = tk.Label(font_frame, text=str(self.current_font_size), width=3)
        self.font_size_label.pack(side=tk.LEFT, padx=5)
        
        increase_btn = tk.Button(
            font_frame,
            text="+",
            command=self.increase_font_size,
            width=3,
            font=("Arial", 12, "bold")
        )
        increase_btn.pack(side=tk.LEFT, padx=2)
        
        # Info label
        self.info_label = tk.Label(
            control_frame,
            text="Status: Ready",
            font=("Arial", 9),
            fg="#7f8c8d"
        )
        self.info_label.pack(fill=tk.X, pady=5)
        
        # Text display area
        display_frame = tk.LabelFrame(
            self.root,
            text="Filtered Audit Log",
            font=("Arial", 10, "bold"),
            padx=5,
            pady=5
        )
        display_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)
        
        self.text_display = scrolledtext.ScrolledText(
            display_frame,
            wrap=tk.WORD,
            font=("Courier", 11),
            bg="#f8f9fa",
            fg="#2c3e50",
            height=25
        )
        self.text_display.pack(fill=tk.BOTH, expand=True)
        
        # Setup drag and drop
        self.setup_drag_drop()
        
    def setup_drag_drop(self):
        """Setup drag and drop functionality"""
        if not HAS_DND:
            # Graceful fallback if dnd2 not available
            self.file_display.config(
                text="[Click Browse to select a file]",
                fg="#7f8c8d"
            )
            return
        
        try:
            # Register the drag and drop on file display label
            self.file_display.drop_target_register(DND_FILES)
            self.file_display.dnd_bind('<<Drop>>', self.drop_file)
        except Exception as e:
            print(f"Drag and drop setup error: {e}")
            self.file_display.config(
                text="[Click Browse to select a file]",
                fg="#7f8c8d"
            )
    
    def drop_file(self, event):
        """Handle dropped file"""
        files = self.root.tk.splitlist(event.data)
        if files:
            file_path = files[0]
            # Remove curly braces if present
            file_path = file_path.strip('{}')
            if os.path.isfile(file_path):
                self.load_file(file_path)
    
    def browse_file(self):
        """Browse for log file"""
        file_path = filedialog.askopenfilename(
            title="Select Audit Log File",
            filetypes=[("Text files", "*.txt"), ("All files", "*.*")]
        )
        if file_path:
            self.load_file(file_path)
    
    def load_file(self, file_path):
        """Load the log file"""
        try:
            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                self.log_content = f.read()
            
            self.file_display.config(
                text=os.path.basename(file_path),
                fg="#2c3e50"
            )
            self.info_label.config(
                text=f"Status: Loaded '{os.path.basename(file_path)}' ({len(self.log_content)} characters)"
            )
            
            # Clear filtered display
            self.text_display.config(state=tk.NORMAL)
            self.text_display.delete(1.0, tk.END)
            self.text_display.config(state=tk.DISABLED)
            
            # Extract and update ticker dropdown
            self.update_ticker_dropdown()
            
        except Exception as e:
            messagebox.showerror("Error", f"Failed to load file: {str(e)}")
            self.info_label.config(text="Status: Error loading file")
    
    def update_ticker_dropdown(self):
        """Extract unique tickers from log and update dropdown"""
        # Pattern to match ticker symbols (e.g., SPY.AM, MGRT.NQ, etc.)
        ticker_pattern = r'\b([A-Z]+\.[A-Z]+)\b'
        matches = re.findall(ticker_pattern, self.log_content)
        
        # Get unique tickers and sort them
        unique_tickers = sorted(set(matches))
        
        # Update dropdown menu
        menu = self.ticker_dropdown['menu']
        menu.delete(0, 'end')
        
        # Add "All" option
        menu.add_command(label="All", command=lambda: self.ticker_var.set("All"))
        
        # Add all found tickers
        for ticker in unique_tickers:
            menu.add_command(label=ticker, command=lambda t=ticker: self.ticker_var.set(t))
        
        self.ticker_var.set("All")
        self.info_label.config(
            text=f"Status: Loaded '{os.path.basename(self.log_content) if self.log_content else ''}' - Found {len(unique_tickers)} unique tickers"
        )
    
    def get_timezones(self):
        """Get list of common timezones"""
        timezones = [
            'UTC',
            'US/Eastern',
            'US/Central',
            'US/Mountain',
            'US/Pacific',
            'US/Alaska',
            'US/Hawaii',
            'Europe/London',
            'Europe/Paris',
            'Europe/Berlin',
            'Asia/Tokyo',
            'Asia/Hong_Kong',
            'Asia/Shanghai',
            'Australia/Sydney',
            'Australia/Melbourne',
        ]
        return timezones
    
    def parse_time(self, time_str):
        """Parse time string from log (HH:MM:SS format)"""
        try:
            return datetime.strptime(time_str, "%H:%M:%S").time()
        except:
            return None
    
    def increase_font_size(self):
        """Increase font size"""
        self.current_font_size += 1
        self.font_size_label.config(text=str(self.current_font_size))
        self.update_text_display_font()
    
    def decrease_font_size(self):
        """Decrease font size"""
        if self.current_font_size > 6:  # Minimum font size
            self.current_font_size -= 1
            self.font_size_label.config(text=str(self.current_font_size))
            self.update_text_display_font()
    
    def update_text_display_font(self):
        """Update the font of the text display"""
        self.text_display.config(font=("Courier", self.current_font_size))
    def apply_filter(self):
        """Apply filters and display results"""
        if not self.log_content:
            messagebox.showwarning("Warning", "Please load a log file first")
            return
        
        ticker = self.ticker_var.get()
        start_time_str = self.start_time_entry.get().strip()
        end_time_str = self.end_time_entry.get().strip()
        
        # Parse times
        try:
            start_time = self.parse_time(start_time_str) if start_time_str else None
            end_time = self.parse_time(end_time_str) if end_time_str else None
        except:
            messagebox.showerror("Error", "Invalid time format. Use HH:MM:SS")
            return
        
        lines = self.log_content.split('\n')
        filtered_lines = []
        
        for line in lines:
            # Skip empty lines
            if not line.strip():
                continue
            
            # Extract time from line (format: HH:MM:SS [...])
            time_match = re.match(r'^(\d{2}):(\d{2}):(\d{2})', line)
            if not time_match:
                continue
            
            line_time_str = time_match.group(0)
            line_time = self.parse_time(line_time_str)
            
            # Filter by time range
            if line_time:
                if start_time and line_time < start_time:
                    continue
                if end_time and line_time > end_time:
                    continue
            
            # Filter by ticker if not "All"
            if ticker != "All":
                if ticker not in line:
                    continue
            
            filtered_lines.append(line)
        
        # Display filtered results
        self.text_display.config(state=tk.NORMAL)
        self.text_display.delete(1.0, tk.END)
        
        if filtered_lines:
            result_text = '\n'.join(filtered_lines)
            self.text_display.insert(1.0, result_text)
            filter_desc = f"ticker: {ticker}" if ticker != "All" else "all tickers"
            self.info_label.config(
                text=f"Status: Showing {len(filtered_lines)} lines ({filter_desc}, {start_time_str} - {end_time_str})"
            )
        else:
            self.text_display.insert(1.0, "No matching entries found.")
            self.info_label.config(text="Status: No matching entries")
        
        self.text_display.config(state=tk.DISABLED)


def main():
    if HAS_DND:
        root = TkinterDnD.Tk()
    else:
        root = tk.Tk()
    app = AuditLogAnalyzer(root)
    root.mainloop()


if __name__ == "__main__":
    main()
