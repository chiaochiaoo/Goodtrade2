import tkinter as tk
from tkinter import ttk
import ttkbootstrap as tb
from ttkbootstrap.constants import *

class App:
    def __init__(self, root):
        self.root = root
        self.root.title("Algo Dashboard")
        self.style = self.root.style

        self.style.configure("Green.TLabel", background="#d1f7c4", foreground="black", padding=4, anchor="e")
        self.style.configure("Red.TLabel", background="#fbdcdc", foreground="black", padding=4, anchor="e")


        # Scrollable frame
        self.canvas = tk.Canvas(root)
        self.scroll_frame = ttk.Frame(self.canvas)
        self.scrollbar = ttk.Scrollbar(root, orient="vertical", command=self.canvas.yview)
        self.canvas.configure(yscrollcommand=self.scrollbar.set)
        self.scrollbar.pack(side="right", fill="y")
        self.canvas.pack(side="left", fill="both", expand=True)
        self.canvas.create_window((0, 0), window=self.scroll_frame, anchor="nw")
        self.scroll_frame.bind("<Configure>", lambda e: self.canvas.configure(scrollregion=self.canvas.bbox("all")))

        # Table headers
        headers = ["#", "Algo", "Status", "Unreal", "Real", "+25", "-25", "+50", "-50", "Flatten", "A-Flat"]
        for col, text in enumerate(headers):
            tk.Label(self.scroll_frame, text=text, font=('Arial', 10, 'bold')).grid(row=0, column=col, padx=5, pady=5)
            self.scroll_frame.grid_columnconfigure(col, weight=1)

        self.rows = []  # List of rows (each row is a list of widgets)

    def change_theme(self, theme_name):
        self.style.theme_use(theme_name)

    def bind_duplicate(self, label, row_widgets, data):
        label.bind("<Button-1>", lambda e: self.duplicate_row(data, self.rows.index(row_widgets)))

    def add_entry_from_json(self, data, insert_at_index=None):
        if insert_at_index is None:
            insert_at_index = len(self.rows)

        for i in range(insert_at_index, len(self.rows)):
            for widget in self.rows[i]:
                info = widget.grid_info()
                widget.grid(row=info['row'] + 1, column=info['column'])

        row_widgets = []

        def make_label(text, col, style=None):
            if style:
                label = ttk.Label(self.scroll_frame, text=text, style=style, width=10)
            else:
                label = tk.Label(self.scroll_frame, text=text)
            label.grid(row=insert_at_index + 1, column=col, sticky="nsew", padx=2, pady=1)
            row_widgets.append(label)
            return label

        # Row number
        row_number_label = tk.Label(self.scroll_frame, text="?", font=('Segoe UI', 10))
        row_number_label.grid(row=insert_at_index + 1, column=0, sticky="nsew", padx=2)
        row_widgets.append(row_number_label)

        # Algo name (clickable to duplicate)
        algo_label = tk.Label(self.scroll_frame, text=data.get("Name", ""), fg="blue", cursor="hand2")
        algo_label.grid(row=insert_at_index + 1, column=1, sticky="nsew", padx=2)
        row_widgets.append(algo_label)
        self.bind_duplicate(algo_label, row_widgets, data)

        # Status
        make_label(data.get("Status", ""), 2)

        # Unrealized
        try:
            unreal = float(data.get("Unrealized", 0))
        except ValueError:
            unreal = 0
        unreal_style = "Green.TLabel" if unreal > 0 else "Red.TLabel"
        make_label(f"{unreal:.2f}", 3, unreal_style)

        # Realized
        try:
            realized = float(data.get("Realized", 0))
        except ValueError:
            realized = 0
        realized_style = "Green.TLabel" if realized > 0 else "Red.TLabel"
        make_label(f"{realized:.2f}", 4, realized_style)

        # Buttons
        actions = ["+25", "-25", "+50", "-50", "Flatten", "A-Flat"]
        for i, label in enumerate(actions):
            btn = tb.Button(self.scroll_frame, text=label, bootstyle="primary", width=7)
            btn.grid(row=insert_at_index + 1, column=5 + i, padx=1)
            row_widgets.append(btn)

        self.rows.insert(insert_at_index, row_widgets)
        self.refresh_row_numbers()

    def duplicate_row(self, data, index):
        print(f'Duplicating row at index {index}')
        self.add_entry_from_json(data, insert_at_index=index + 1)

    def refresh_row_numbers(self):
        for i, widgets in enumerate(self.rows):
            widgets[0].config(text=str(i + 1))

# Run the app
if __name__ == "__main__":
    root = tb.Window(themename="flatly")
    app = App(root)

    json_data = [
        {"Name": "AAPL", "Status": "Open", "Unrealized": "120.50", "Realized": "30.00"},
        {"Name": "AAPL2", "Status": "Open", "Unrealized": "75.00", "Realized": "10.00"},
        {"Name": "GOOG", "Status": "Closed", "Unrealized": "0.00", "Realized": "250.00"},
        {"Name": "TSLA", "Status": "Open", "Unrealized": "-42.13", "Realized": "-15.00"}
    ]

    for entry in json_data:
        app.add_entry_from_json(entry)

    root.mainloop()