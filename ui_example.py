import tkinter as tk
from tkinter import ttk
import ttkbootstrap as tb
from ttkbootstrap.constants import *

class App:
    def __init__(self, root):
        self.root = root
        self.root.title("Dynamic JSON Entry Table")
        self.style = self.root.style

        self.style.configure("Green.TLabel", background="#d1f7c4", foreground="black", padding=4, anchor="e")
        self.style.configure("Red.TLabel", background="#fbdcdc", foreground="black", padding=4, anchor="e")

        # Theme selector
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

        # Scrollable frame
        self.canvas = tk.Canvas(root)
        self.scroll_frame = ttk.Frame(self.canvas)
        self.scrollbar = ttk.Scrollbar(root, orient="vertical", command=self.canvas.yview)
        self.canvas.configure(yscrollcommand=self.scrollbar.set)
        self.scrollbar.pack(side="right", fill="y")
        self.canvas.pack(side="left", fill="both", expand=True)
        self.canvas.create_window((0, 0), window=self.scroll_frame, anchor="nw")
        self.scroll_frame.bind("<Configure>", lambda e: self.canvas.configure(scrollregion=self.canvas.bbox("all")))

        # Table headers (Row # + Data columns)
        headers = ["#", "Name", "Status", "Unrealized", "Realized", "Position Count", "Actions"]
        for col, text in enumerate(headers):
            tk.Label(self.scroll_frame, text=text, font=('Arial', 10, 'bold')).grid(row=0, column=col, padx=5, pady=5)
            self.scroll_frame.grid_columnconfigure(col, weight=1)

        self.rows = []  # Each row is a list of widget references

    def change_theme(self, theme_name):
        self.style.theme_use(theme_name)

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

        # Row number label (placeholder, will refresh later)
        row_number_label = tk.Label(self.scroll_frame, text="?", font=('Segoe UI', 10))
        row_number_label.grid(row=insert_at_index + 1, column=0, sticky="nsew", padx=2)
        row_widgets.append(row_number_label)

        # Name (clickable)
        name_label = tk.Label(self.scroll_frame, text=data.get("Name", ""), fg="blue", cursor="hand2")
        name_label.grid(row=insert_at_index + 1, column=1, sticky="nsew", padx=2)
        row_widgets.append(name_label)

        # Dynamically determine position at click time
        def bind_duplicate(label, row_widgets, data):
            label.bind("<Button-1>", lambda e: self.duplicate_row(data, self.rows.index(row_widgets)))

        bind_duplicate(name_label, row_widgets, data)

        make_label(data.get("Status", ""), 2)

        try:
            unreal = float(data.get("Unrealized", 0))
        except ValueError:
            unreal = 0
        unreal_style = "Green.TLabel" if unreal > 0 else "Red.TLabel"
        make_label(f"{unreal:.2f}", 3, unreal_style)

        try:
            realized = float(data.get("Realized", 0))
        except ValueError:
            realized = 0
        realized_style = "Green.TLabel" if realized > 0 else "Red.TLabel"
        make_label(f"{realized:.2f}", 4, realized_style)

        position_options = data.get("Positions", ["None"])
        position_var = tk.StringVar(value=position_options[0])
        dropdown = ttk.OptionMenu(self.scroll_frame, position_var, *position_options)
        dropdown.grid(row=insert_at_index + 1, column=5, sticky="nsew", padx=2)
        row_widgets.append(dropdown)

        edit_btn = tb.Button(self.scroll_frame, text="Edit", bootstyle="warning")
        edit_btn.grid(row=insert_at_index + 1, column=6, padx=2)
        row_widgets.append(edit_btn)

        close_btn = tb.Button(self.scroll_frame, text="Close", bootstyle="danger")
        close_btn.grid(row=insert_at_index + 1, column=7, padx=2)
        close_btn.config(command=lambda: self.remove_row(insert_at_index))
        row_widgets.append(close_btn)

        self.rows.insert(insert_at_index, row_widgets)
        self.refresh_row_numbers()

    def duplicate_row(self, data, index):
        print('adding')
        self.add_entry_from_json(data, insert_at_index=index + 1)

    def remove_row(self, index):
        print('removing',index)
        for widget in self.rows[index]:
            widget.destroy()
        del self.rows[index]

        for i in range(index, len(self.rows)):
            for widget in self.rows[i]:
                info = widget.grid_info()
                widget.grid(row=info['row'] - 1, column=info['column'])

        self.refresh_row_numbers()

    def refresh_row_numbers(self):
        for i, widgets in enumerate(self.rows):
            row_number_label = widgets[0]  # First widget is the row number
            row_number_label.config(text=str(i + 1))

# Run the app
if __name__ == "__main__":
    root = tb.Window(themename="flatly")
    app = App(root)

    json_data = [
        {"Name": "AAPL", "Status": "Open", "Unrealized": "120.50", "Realized": "30.00", "Positions": ["Long", "Short"]},
        {"Name": "AAPL2", "Status": "Open", "Unrealized": "120.50", "Realized": "30.00", "Positions": ["Long", "Short"]},
        {"Name": "AAPL3", "Status": "Open", "Unrealized": "120.50", "Realized": "30.00", "Positions": ["Long", "Short"]},
        {"Name": "GOOG", "Status": "Closed", "Unrealized": "0.00", "Realized": "250.00", "Positions": ["Flat"]},
        {"Name": "TSLA", "Status": "Open", "Unrealized": "-42.13", "Realized": "-15.00", "Positions": ["Short", "Hedge"]}
    ]

    for entry in json_data:
        app.add_entry_from_json(entry)

    root.mainloop()
