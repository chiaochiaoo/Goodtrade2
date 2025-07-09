import tkinter as tk
from tkinter import ttk
import ttkbootstrap as tb
from ttkbootstrap.constants import *

class App:
    def __init__(self, root):
        self.root = root
        self.root.title("Dynamic JSON Entry Table")
        self.style = self.root.style  # ttkbootstrap style object

        # Custom styles for green/red labels
        self.style.configure("Green.TLabel", background="#d1f7c4", foreground="black", padding=4, anchor="e")
        self.style.configure("Red.TLabel", background="#fbdcdc", foreground="black", padding=4, anchor="e")

        # Top control panel with theme selector
        control_frame = tb.Frame(self.root)
        control_frame.pack(fill="x", pady=5)

        tb.Label(control_frame, text="Theme:", font=('Segoe UI', 10)).pack(side="left", padx=5)

        self.theme_var = tk.StringVar(value=self.style.theme.name)
        self.theme_dropdown = tb.OptionMenu(
            control_frame, self.theme_var,
            *self.style.theme_names(),
            command=self.change_theme
        )
        self.theme_dropdown.pack(side="left", padx=5)

        # Canvas + scrollable frame setup
        self.canvas = tk.Canvas(root)
        self.scroll_frame = ttk.Frame(self.canvas)
        self.scrollbar = ttk.Scrollbar(root, orient="vertical", command=self.canvas.yview)
        self.canvas.configure(yscrollcommand=self.scrollbar.set)

        self.scrollbar.pack(side="right", fill="y")
        self.canvas.pack(side="left", fill="both", expand=True)
        self.canvas.create_window((0, 0), window=self.scroll_frame, anchor="nw")
        self.scroll_frame.bind("<Configure>", lambda e: self.canvas.configure(scrollregion=self.canvas.bbox("all")))

        # Table header
        headers = ["Name", "Status", "Unrealized", "Realized", "Position Count", "Actions"]
        for col, text in enumerate(headers):
            tk.Label(self.scroll_frame, text=text, font=('Arial', 10, 'bold')).grid(row=0, column=col, padx=5, pady=5)

        for col in range(len(headers)):
            self.scroll_frame.grid_columnconfigure(col, weight=1)

        self.row_index = 1  # Start from row 1 for data entries

    def change_theme(self, theme_name):
        self.style.theme_use(theme_name)

    def add_entry_from_json(self, data):
        row = self.row_index
        self.row_index += 1

        # Name and Status
        tk.Label(self.scroll_frame, text=data.get("Name", "")).grid(row=row, column=0, sticky="nsew")
        tk.Label(self.scroll_frame, text=data.get("Status", "")).grid(row=row, column=1, sticky="nsew")

        # Conditional color for Unrealized
        try:
            unreal = float(data.get("Unrealized", 0))
        except ValueError:
            unreal = 0
        unreal_style = "Green.TLabel" if unreal > 0 else "Red.TLabel"
        ttk.Label(self.scroll_frame, text=f"{unreal:.2f}", style=unreal_style, width=10).grid(row=row, column=2, sticky="nsew")

        # Conditional color for Realized
        try:
            realized = float(data.get("Realized", 0))
        except ValueError:
            realized = 0
        realized_style = "Green.TLabel" if realized > 0 else "Red.TLabel"
        ttk.Label(self.scroll_frame, text=f"{realized:.2f}", style=realized_style, width=10).grid(row=row, column=3, sticky="nsew")

        # Dropdown for Position Count
        position_options = data.get("Positions", ["None"])
        position_var = tk.StringVar(value=position_options[0])
        ttk.OptionMenu(self.scroll_frame, position_var, *position_options).grid(row=row, column=4, sticky="nsew")

        # Action Buttons with bootstyle
        tb.Button(self.scroll_frame, text="Edit", bootstyle="warning").grid(row=row, column=5, padx=2)
        tb.Button(self.scroll_frame, text="Close", bootstyle="danger").grid(row=row, column=6, padx=2)

# Run the app
if __name__ == "__main__":
    root = tb.Window(themename="flatly")  # Initial theme
    app = App(root)

    # Simulated JSON data
    json_data = [
        {"Name": "AAPL", "Status": "Open", "Unrealized": "120.50", "Realized": "30.00", "Positions": ["Long", "Short"]},
        {"Name": "GOOG", "Status": "Closed", "Unrealized": "0.00", "Realized": "250.00", "Positions": ["Flat"]},
        {"Name": "TSLA", "Status": "Open", "Unrealized": "-42.13", "Realized": "-15.00", "Positions": ["Short", "Hedge"]}
    ]

    for entry in json_data:
        app.add_entry_from_json(entry)

    root.mainloop()
