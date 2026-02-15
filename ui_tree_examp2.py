    import tkinter as tk
    from tkinter import ttk
    import random
    import ttkbootstrap as tb
    import threading
    import time
    from _tkinter import TclError


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
                x_cell, y_cell, _, height_cell = self.widget.bbox(item_id, column_id)
            except TclError:
                return

            x = self.widget.winfo_rootx() + x_cell + 25
            y = self.widget.winfo_rooty() + y_cell + height_cell + 5

            self.tip_window = tw = tk.Toplevel(self.widget)
            tw.wm_overrideredirect(True)
            tw.wm_geometry(f"+{x}+{y}")

            label = ttk.Label(
                tw,
                text=text,
                background="#FFFDD0",
                foreground="#333333",
                relief="solid",
                borderwidth=1,
                font=("Segoe UI", 12),
                wraplength=300
            )
            label.pack(ipadx=4, ipady=2)

        def hidetip(self):
            if self.tip_window:
                self.tip_window.destroy()
                self.tip_window = None


    class AlgoDashboard(tb.Window):
        def __init__(self, theme_name="cosmo"):
            super().__init__(themename=theme_name)
            self.title("Algo Trading Dashboard")
            self.geometry("1400x700")
            self.resizable(True, True)

            self.headers = ["#", "Algo", "Status", "Position", "Unreal", "Real", "+25", "-25", "+50", "-50", "Flatten", "A-Flat"]
            self.clickable_cols = ["+25", "-25", "+50", "-50", "Flatten", "A-Flat"]
            self.algo_data_by_item_id = {}
            self.current_cursor_is_hand = False
            self.tooltip = None
            self.running = True

            self.create_widgets()
            self.populate_treeview(15)
            self.start_update_thread()
            self.protocol("WM_DELETE_WINDOW", self._on_closing)

        def create_widgets(self):
            # Clean Treeview style with Segoe UI
            self.style.configure("Treeview",
                font=('Arial', 12),
                rowheight=24,
            )

            # Header style
            self.style.configure("Treeview.Heading",
                font=('Segoe UI', 15, 'bold'),
                background="#007bff",
                foreground="white"
            )

            frame = ttk.Frame(self, bootstyle="light")
            frame.pack(padx=15, pady=15, fill="both", expand=True)

            scroll_y = ttk.Scrollbar(frame, bootstyle="info-round")
            scroll_y.pack(side="right", fill="y")

            scroll_x = ttk.Scrollbar(frame, orient="horizontal", bootstyle="info-round")
            scroll_x.pack(side="bottom", fill="x")

            self.tree = tb.Treeview(frame,
                columns=self.headers,
                show="headings",
                yscrollcommand=scroll_y.set,
                xscrollcommand=scroll_x.set,
                bootstyle="Treeview"
            )
            self.tree.pack(fill="both", expand=True)

            scroll_y.config(command=self.tree.yview)
            scroll_x.config(command=self.tree.xview)

            for col in self.headers:
                self.tree.heading(col, text=col, anchor="center", command=lambda c=col: self.sort_column(c, False))
                self.tree.column(col, anchor="center", width=130)

            self.tree.column("#", width=60)
            self.tree.column("Algo", width=160, anchor="w")
            self.tree.column("Position", width=400, anchor="w")
            self.tree.column("Unreal", anchor="e", width=130)
            self.tree.column("Real", anchor="e", width=130)

            # Conditional row coloring (background only)
            self.tree.tag_configure("row_green", background="#e6ffe6")
            self.tree.tag_configure("row_red", background="#ffe6e6")

            self.tree.bind("<Button-1>", self.on_treeview_click)
            self.tree.bind("<Motion>", self.on_treeview_motion)
            self.tree.bind("<Leave>", self.on_treeview_leave)

        def populate_treeview(self, count=15):
            for _ in range(count):
                item_id = self.tree.insert("", "end")
                data = self.generate_random_algo(item_id)
                self.algo_data_by_item_id[item_id] = data
                self._update_treeview_row(item_id, data)

        def generate_random_algo(self, item_id=None):
            names = ["AAPL", "GOOG", "TSLA", "MSFT", "NVDA"]
            statuses = ["RUNNING", "DEPLOYED", "REJECTED", "CANCELED", "ERROR"]
            name = random.choice(names)
            status = random.choice(statuses)
            pos = f"{name}.NQ:{random.randint(1, 20)}" if random.random() < 0.6 else f"{name}.NQ.FUT.{random.randint(1000,9999)}.DEC25:{random.randint(1, 20)}"
            return {
                "Name": name,
                "Position": pos,
                "Status": status,
                "Unrealized": round(random.uniform(-100, 200), 2),
                "Realized": round(random.uniform(-50, 50), 2),
                "item_id": item_id
            }

        def _update_treeview_row(self, item_id, data):
            unreal = data["Unrealized"]
            real = data["Realized"]

            values = [
                self.tree.index(item_id) + 1,
                data["Name"], data["Status"], data["Position"],
                f"{unreal:.2f}", f"{real:.2f}",
                "+25", "-25", "+50", "-50", "Flatten", "A-Flat"
            ]

            tags = ["row_green" if unreal >= 0 else "row_red"]
            self.tree.item(item_id, values=values, tags=tags)

        def start_update_thread(self):
            self.update_thread = threading.Thread(target=self._update_algo_values_threaded, daemon=True)
            self.update_thread.start()

        def _update_algo_values_threaded(self):
            while self.running:
                try:
                    for item_id in random.sample(self.tree.get_children(), k=random.randint(1, 3)):
                        existing = self.algo_data_by_item_id[item_id]
                        new_data = self.generate_random_algo(item_id)
                        existing["Unrealized"] = new_data["Unrealized"]
                        existing["Realized"] = new_data["Realized"]
                        self.after(0, self._update_treeview_row, item_id, existing)
                except Exception as e:
                    print(f"[Update Error] {e}")
                time.sleep(1)

        def sort_column(self, col, reverse):
            try:
                items = [(float(self.tree.set(k, col)), k) if col in ["#", "Unreal", "Real"]
                         else (self.tree.set(k, col), k) for k in self.tree.get_children()]
                items.sort(reverse=reverse)
                for i, (_, k) in enumerate(items):
                    self.tree.move(k, '', i)
                self.tree.heading(col, command=lambda: self.sort_column(col, not reverse))
            except Exception as e:
                print(f"[Sort Error] {e}")

        def on_treeview_click(self, event):
            item = self.tree.identify_row(event.y)
            col = self.tree.identify_column(event.x)
            if not item or not col:
                return
            col_index = int(col[1:]) - 1
            col_name = self.headers[col_index]
            if col_name in self.clickable_cols:
                name = self.tree.item(item, 'values')[1]
                print(f"[{col_name}] clicked for {name}")

        def on_treeview_motion(self, event):
            item = self.tree.identify_row(event.y)
            col = self.tree.identify_column(event.x)

            if self.tooltip and self.tooltip.tip_window:
                self.tooltip.hidetip()

            if item and col:
                idx = int(col[1:]) - 1
                col_name = self.headers[idx]
                if col_name == "Position":
                    text = self.tree.item(item, 'values')[idx]
                    if not self.tooltip:
                        self.tooltip = Tooltip(self.tree)
                    self.tooltip.showtip(text, item, col)

                self.tree.config(cursor="hand2" if col_name in self.clickable_cols else "")
                self.current_cursor_is_hand = col_name in self.clickable_cols
            else:
                self.tree.config(cursor="")
                self.current_cursor_is_hand = False

        def on_treeview_leave(self, _):
            self.tree.config(cursor="")
            self.current_cursor_is_hand = False
            if self.tooltip:
                self.tooltip.hidetip()

        def _on_closing(self):
            print("Closing...")
            self.running = False
            self.update_thread.join(timeout=2)
            self.destroy()


    if __name__ == "__main__":
        app = AlgoDashboard("cosmo")
        app.mainloop()
