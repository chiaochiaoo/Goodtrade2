import tkinter as tk
import random
from ttkbootstrap import ttk, Window
from tksheet import Sheet

class AlgoDashboard(Window):
    def __init__(self):
        super().__init__(themename="flatly")  # Changed theme to "flatly"
        self.title("Algo Trading Dashboard")
        self.geometry("1000x600")

        self.headers = [
            "#", "Algo", "Status", "Position", "Unreal", "Real",
            "+25", "-25", "+50", "-50", "Flatten", "A-Flat"
        ]

        self.data = self.generate_data(20)  # Generate 20 rows of initial data

        self.sheet = Sheet(
            self,
            data=self.data,
            headers=self.headers,
            height=500,
            width=980
        )
        self.sheet.grid(row=0, column=0, sticky="nsew", padx=10, pady=10)
        self.grid_rowconfigure(0, weight=1)
        self.grid_columnconfigure(0, weight=1)

        # Enable header select binding to allow clicks on non-editable headers
        self.sheet.enable_bindings("single_selection", "row_select", "column_select", "auto_resize_columns", "copy", "cut", "paste", "delete", "undo", "redo", "edit_cell")
        self.sheet.extra_bindings([("header_select", self.handle_header_click)]) # Changed to header_select

    def generate_data(self, n):
        rows = []
        for i in range(n):
            name = random.choice(["AAPL", "GOOG", "TSLA", "MSFT", "NVDA", "AMZN", "META", "NFLX", "INTC"])
            status = random.choice(["RUNNING", "DEPLOYED", "REJECTED", "CANCELED", "ERROR"])
            position = f"{name}.NQ:{random.randint(1, 20)}"
            unreal = round(random.uniform(-50.0, 150.0), 2)
            real = round(random.uniform(-30.0, 30.0), 2)
            row = [
                str(i + 1), name, status, position,
                unreal, real,
                "[+25]", "[-25]", "[+50]", "[-50]", "[Flatten]", "[A-Flat]"
            ]
            rows.append(row)
        return rows

    def handle_header_click(self, event):
        clicked_column_index = event.column
        clicked_header_name = self.headers[clicked_column_index]

        if clicked_header_name == "Unreal":
            self.sort_by_column("Unreal")
        elif clicked_header_name == "Real":
            self.sort_by_column("Real")

    def sort_by_column(self, column_name):
        # Get the current data from the sheet
        current_data = self.sheet.get_sheet_data()

        # Find the index of the specified column
        try:
            col_index = self.headers.index(column_name)
        except ValueError:
            print(f"Error: Column '{column_name}' not found in headers.")
            return

        # Sort the data based on the specified column
        # We need to handle cases where the value might be an empty string or non-numeric
        sorted_data = sorted(current_data, key=lambda x: float(x[col_index]) if isinstance(x[col_index], (int, float)) else (float(x[col_index]) if x[col_index] else 0.0))

        # Update the sheet with the sorted data
        self.sheet.set_sheet_data(sorted_data)
        self.sheet.refresh_all()

if __name__ == "__main__":
    app = AlgoDashboard()
    app.mainloop()