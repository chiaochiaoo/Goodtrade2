import tkinter as tk
from tkinter import ttk
import ttkbootstrap as tb
import random
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg


class DashboardApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Trading Dashboard")
        self.style = root.style

        # ============ Data =============
        self.pnl_x = []
        self.pnl_y = []
        self.entry_counter = 0
        self.groups = {}
        self.entries = []

        # ============ Layout =============
        self.top_frame = tb.Frame(root)
        self.bottom_frame = tb.Frame(root)
        self.top_frame.pack(fill="both", expand=True)
        self.bottom_frame.pack(fill="x")

        self.left_frame = tb.Frame(self.top_frame)
        self.right_frame = tb.Frame(self.top_frame)
        self.left_frame.pack(side="left", fill="both", expand=True)
        self.right_frame.pack(side="right", fill="both", expand=True)

        # ============ Treeview (Positions Log) ============
        self.tree = ttk.Treeview(self.left_frame, columns=("Unrealized", "Realized"), show="tree headings")
        self.tree.heading("#0", text="Name", anchor="w")
        self.tree.heading("Unrealized", text="Unrealized")
        self.tree.heading("Realized", text="Realized")
        self.tree.pack(fill="both", expand=True, padx=10, pady=10)

        # ============ Matplotlib PnL Graph ============
        self.fig, self.ax = plt.subplots(figsize=(5, 3))
        self.line, = self.ax.plot([], [], label="PnL")
        self.ax.set_title("PnL Over Time")
        self.ax.set_xlabel("Trade Count")
        self.ax.set_ylabel("PnL")
        self.ax.legend()

        self.canvas = FigureCanvasTkAgg(self.fig, master=self.right_frame)
        self.canvas.get_tk_widget().pack(fill="both", expand=True, padx=10, pady=10)
        self.canvas.draw()

        # ============ Controls =============
        self.entry_input = tb.Entry(self.bottom_frame, width=40)
        self.entry_input.insert(0, "AAPL, Open, 100.0, 20.0")
        self.entry_input.pack(side="left", padx=10, pady=10)

        self.sim_button = tb.Button(self.bottom_frame, text="Simulate Trade", bootstyle="success", command=self.simulate_trade)
        self.sim_button.pack(side="left", padx=5)

        self.clear_button = tb.Button(self.bottom_frame, text="Clear", bootstyle="danger", command=self.clear_all)
        self.clear_button.pack(side="left", padx=5)

        # ============ Loop ============
        self.update_graph()

    def simulate_trade(self):
        text = self.entry_input.get()
        try:
            name, status, unrealized, realized = map(str.strip, text.split(","))
        except:
            return

        unrealized_val = float(unrealized)
        realized_val = float(realized)
        self.entry_counter += 1

        if status not in self.groups:
            self.groups[status] = self.tree.insert("", "end", text=f"[{status}]", open=True)

        iid = self.tree.insert(
            self.groups[status],
            "end",
            text=name,
            values=(f"{unrealized_val:.2f}", f"{realized_val:.2f}")
        )
        self.entries.append((iid, name, unrealized_val, realized_val))

        # PnL calculation: sum of realized
        cumulative_pnl = sum(real for _, _, _, real in self.entries)
        self.pnl_x.append(self.entry_counter)
        self.pnl_y.append(cumulative_pnl)

    def clear_all(self):
        self.tree.delete(*self.tree.get_children())
        self.groups.clear()
        self.entries.clear()
        self.pnl_x.clear()
        self.pnl_y.clear()
        self.entry_counter = 0

    def update_graph(self):
        self.line.set_data(self.pnl_x, self.pnl_y)
        self.ax.relim()
        self.ax.autoscale_view()
        self.canvas.draw()
        self.root.after(500, self.update_graph)


# ============ Run =============
if __name__ == "__main__":
    root = tb.Window(themename="flatly")
    app = DashboardApp(root)
    root.mainloop()
