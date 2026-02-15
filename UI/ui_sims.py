import os
import json
import inspect
import tkinter as tk
import ttkbootstrap as tb
from ttkbootstrap.constants import *

ACTIVE = 0
MULTIPLIER = 1
PASSIVE = 2
DESCRIPTION = 3

class sim_test:
    def __init__(self, ui):
        self.ui = ui
        self.panel_name = 'TMS-SIMs'

        if not hasattr(self.ui, 'user_panels'):
            self.ui.user_panel = tb.LabelFrame(self.ui, text="User", bootstyle="info")
            self.ui.user_panel.place(relx=0, rely=0, relheight=1, relwidth=1)
            self.ui.user_panels = tb.Notebook(self.ui.user_panel)
            self.ui.user_panels.place(relx=0, rely=0, relheight=1, relwidth=1)

        self.tab = tb.Frame(self.ui.user_panels)
        self.ui.user_panels.add(self.tab, text=self.panel_name)

        # --- Two-pane grid: left = vertical buttons (scrollable), right = info ---
        self.tab.columnconfigure(0, weight=0, minsize=120)  # buttons column, fixed
        self.tab.columnconfigure(1, weight=1)  # info column, expands
        self.tab.rowconfigure(0, weight=1)

        # Left: scrollable vertical list
        self.btn_canvas = tk.Canvas(self.tab, highlightthickness=0, borderwidth=0,width=200)
        self.btn_scroll = tb.Scrollbar(self.tab, orient="vertical", command=self.btn_canvas.yview)
        self.btn_holder = tb.Frame(self.btn_canvas)

        self.btn_holder.bind(
            "<Configure>",
            lambda e: self.btn_canvas.configure(scrollregion=self.btn_canvas.bbox("all"))
        )
        self.btn_canvas.create_window((0, 0), window=self.btn_holder, anchor="nw")
        self.btn_canvas.configure(yscrollcommand=self.btn_scroll.set)

        self.btn_canvas.grid(row=0, column=0, sticky="nsw")
        self.btn_scroll.grid(row=0, column=0, sticky="nse")  # scrollbar sits at far right of left pane

        # Right: info/status
        self.info = tb.Label(self.tab, text="Select a SIM to run.", bootstyle="secondary", anchor="w", justify="left")
        self.info.grid(row=0, column=1, sticky="nsew", padx=8, pady=8)

        self.refresh_buttons()

    def refresh_buttons(self):
        # Clear previous
        for w in self.btn_holder.winfo_children():
            w.destroy()

        has_manager = hasattr(self.ui, 'manager')
        has_tests = has_manager and hasattr(self.ui.manager, 'test_files') and isinstance(self.ui.manager.test_files, dict)

        if not has_tests or not self.ui.manager.test_files:
            tb.Label(self.btn_holder, text="No tests found.", bootstyle="warning").pack(fill="x", pady=4)
            return

        # Strict vertical stack, full-width
        for name, func in self.ui.manager.test_files.items():
            tb.Button(
                self.btn_holder,
                text=name,
                bootstyle="primary-outline",
                command=lambda f=func, n=name: self._run_test(n, f)
            ).pack(fill="x", pady=4, padx=8)   # <- vertical, full width inside left pane

    def _run_test(self, name, func):
        """Call test function; pass manager if the function expects 1 positional arg."""
        try:
            sig = inspect.signature(func)
            # if it's a bound method, first param is already bound; check parameters count
            params = [p for p in sig.parameters.values()
                      if p.kind in (p.POSITIONAL_ONLY, p.POSITIONAL_OR_KEYWORD) and p.default is p.empty]

            if len(params) == 0:
                # func() – no args
                func()
            else:
                # Try func(manager) as the single dependency
                func(self.ui.manager)

            self.info.configure(text=f"✅ Ran: {name}", bootstyle="success")
        except Exception as e:
            self.info.configure(text=f"❌ {name} failed: {e}", bootstyle="danger")

# ---- Example wiring for quick testing ----
class ManagerExample:
    def __init__(self, root):
        # Define test functions; can be zero-arg or accept manager
        self.test_files = {
            'sim1': self.sim1,
            'sim2': self.sim2,
            'ping': self.ping_noarg
        }

    def sim1(self, manager):
        print("sim1 running with manager:", manager)

    def sim2(self, manager):
        print("sim2 running with manager:", manager)

    def ping_noarg(self):
        print("ping (no args)")

if __name__ == '__main__':
    root = tb.Window(themename='flatly')
    root.title('GoodTrade AMS')
    root.geometry('480x240')

    # Attach a manager that carries test_files
    root.manager = ManagerExample(root)

    dashboard = sim_test(root)
    root.mainloop()