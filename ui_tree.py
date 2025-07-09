import tkinter as tk
from tkinter import ttk
import ttkbootstrap as tb
from ttkbootstrap.constants import *

class TreeApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Grouped Trading Table")
        self.style = self.root.style

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

        # Treeview setup
        self.tree = ttk.Treeview(root, columns=("Unrealized", "Realized", "Position Count"), show="tree headings")
        self.tree.heading("#0", text="Name", anchor="w")
        self.tree.heading("Unrealized", text="Unrealized", anchor="center")
        self.tree.heading("Realized", text="Realized", anchor="center")
        self.tree.heading("Position Count", text="Position Count", anchor="center")

        self.tree.column("#0", width=140)
        self.tree.column("Unrealized", width=100, anchor="e")
        self.tree.column("Realized", width=100, anchor="e")
        self.tree.column("Position Count", width=150, anchor="center")

        self.tree.pack(fill="both", expand=True)

        # Bind double-click to duplicate
        self.tree.bind("<Double-1>", self.on_double_click)

        self.groups = {}  # key = status, value = tree item ID
        self.data = []    # list of data dicts

    def change_theme(self, theme_name):
        self.style.theme_use(theme_name)

    def insert_entry(self, data, parent_status=None, insert_after=None):
        status = data["Status"]
        if status not in self.groups:
            self.groups[status] = self.tree.insert("", "end", text=f"[{status}]", open=True)

        parent_id = self.groups[status]
        values = (
            data["Unrealized"],
            data["Realized"],
            ", ".join(data.get("Positions", []))
        )

        # Insert after another item (if duplicating)
        if insert_after:
            iid = self.tree.insert(parent_id, self.tree.index(insert_after)+1, text=data["Name"], values=values)
        else:
            iid = self.tree.insert(parent_id, "end", text=data["Name"], values=values)

        self.tree.item(iid, tags=("row",))
        self.data.append((iid, data))

        # Color logic
        try:
            unreal = float(data["Unrealized"])
            if unreal > 0:
                self.tree.tag_configure("row", background="#d1f7c4")
            elif unreal < 0:
                self.tree.tag_configure("row", background="#fbdcdc")
        except:
            pass

    def on_double_click(self, event):
        item_id = self.tree.focus()
        parent_id = self.tree.parent(item_id)
        if parent_id == "":
            return  # group header clicked

        # Find original data from self.data
        for (iid, entry) in self.data:
            if iid == item_id:
                # Duplicate the row
                new_data = entry.copy()
                new_data["Name"] += "_copy"
                self.insert_entry(new_data, parent_status=entry["Status"], insert_after=item_id)
                break

# Run the app
if __name__ == "__main__":
    root = tb.Window(themename="flatly")
    app = TreeApp(root)

    json_data = [
        {"Name": "AAPL", "Status": "Open", "Unrealized": "120.50", "Realized": "30.00", "Positions": ["Long", "Short"]},
        {"Name": "AAPL2", "Status": "Open", "Unrealized": "120.50", "Realized": "30.00", "Positions": ["Long", "Short"]},
        {"Name": "AAPL3", "Status": "Open", "Unrealized": "120.50", "Realized": "30.00", "Positions": ["Long", "Short"]},
        {"Name": "GOOG", "Status": "Closed", "Unrealized": "0.00", "Realized": "250.00", "Positions": ["Flat"]},
        {"Name": "TSLA", "Status": "Open", "Unrealized": "-42.13", "Realized": "-15.00", "Positions": ["Short", "Hedge"]}
    ]

    for entry in json_data:
        app.insert_entry(entry)

    root.mainloop()
