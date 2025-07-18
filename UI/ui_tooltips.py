# Tooltip class adapted for ttk.Treeview
import tkinter as tk
from tkinter import ttk

class Tooltip:
    def __init__(self, widget):
        self.widget = widget
        self.tip_window = None

    def showtip(self, text, item_id, column_id):
        if self.tip_window:
            self.hidetip()
        if not text:
            return

        try:
            # Get bounding box of the cell
            x_cell, y_cell, _, height_cell = self.widget.bbox(item_id, column_id)
        except TclError:
            # Handle cases where item_id or column_id might be invalid (e.g., item deleted)
            return

        # Calculate position for the tooltip window
        # winfo_rootx/y gets the absolute screen coordinates of the widget
        x = self.widget.winfo_rootx() + x_cell + 25
        y = self.widget.winfo_rooty() + y_cell + height_cell + 5

        # Create the toplevel window
        self.tip_window = tw = tk.Toplevel(self.widget)
        tw.wm_overrideredirect(True) # Remove window decorations
        tw.wm_geometry(f"+{x}+{y}")

        # Create the label for the tooltip text
        label = ttk.Label(
            tw,
            text=text,
            background="#FFFDD0",
            foreground="#333333",
            relief="solid",
            borderwidth=1,
            font=("Segoe UI", 10), # Slightly smaller font for tooltip
            wraplength=300 # Wrap text if too long
        )
        label.pack(ipadx=4, ipady=2)

    def hidetip(self):
        if self.tip_window:
            self.tip_window.destroy()
            self.tip_window = None
