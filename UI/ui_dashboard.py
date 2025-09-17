import os
import json
import random
import tkinter as tk
import ttkbootstrap as tb
from ttkbootstrap.constants import *

try:
    from UI.ui_dashboard_market import *
except:
    from ui_dashboard_market import *

try:
    from UI.ui_dashboard_symbol import *
except:
    from ui_dashboard_symbol import *

try:
    from UI.ui_dashboard_risk import *
except:
    from ui_dashboard_risk import *

try:
    from UI.ui_dashboard_algos import*
except:
    from ui_dashboard_algos import *


ACTIVE = 0
MULTIPLIER = 1
PASSIVE = 2
DESCRIPTION = 3


class Dashboard:
    def __init__(self, ui):
        self.ui = ui

        # --- Ensure dashboard panel exists ---
        if not hasattr(self.ui, 'dashboard_panel'):
            self.ui.dashboard_panel = tb.Frame(self.ui)
            self.ui.dashboard_panel.place(relx=0, rely=0, relheight=1, relwidth=1)

        # --- Main tabs (Market / Symbol / Strategy) ---
        self.tab = tb.Notebook(self.ui.dashboard_panel)
        self.tab.place(relx=0, rely=0.01, relheight=0.98, relwidth=1)
        self.frames = {}

        for name in ( 'Risk','Gateways', 'Symbol', 'Algos'):
            frame = tb.Frame(self.tab)
            self.frames[name] = frame
            self.tab.add(frame, text=name)

        # --- MARKET tab content (your existing panel) ---
        # Keep a reference in case you want to call into it later
        try:
            self.market_panel = MarketPanel(self.frames['Gateways'])
        except Exception as e:
            # Fallback placeholder if MarketPanel import isn't available
            tb.Label(self.frames['Gateways'], text=f"MarketPanel unavailable: {e}").pack(padx=8, pady=8)

        # --- SYMBOL tab content (Symbol_Dashboard_Panel) ---
        self.symbol_panel = Symbol_Dashboard_Panel(self.frames['Symbol'], ui=self.ui)
        self.symbol_panel.pack(fill="both", expand=True)

        self.risk_panel = RiskPanel(self.frames['Risk'], master=self.ui)
        self.risk_panel.pack(fill="both", expand=True)
                # Optional: Strategy tab placeholder

        self.algo_pannel = Algo_Dashboard_Panel(self.frames['Algos'], ui=self.ui)
        self.algo_pannel.pack(fill="both", expand=True)

        #tb.Label(self.frames['Strategy'], text="(Strategy tab coming soon)").pack(padx=8, pady=8)

        # --- Seed demo data & start periodic updates ---
        #self._seed_symbol_demo()
        #self._start_symbol_demo_updates()

    # ---------------- Demo helpers ----------------

    def _seed_symbol_demo(self):
        demo_rows = [
            {"Symbol": "AAPL", "Net Pos": 120, "#Algos": 3, "Unreal": 235.42, "Real": 1020.00, "Risk": 1500.00},
            {"Symbol": "MSFT", "Net Pos": -60, "#Algos": 2, "Unreal": -88.10, "Real": 250.00, "Risk": 900.00},
            {"Symbol": "NVDA", "Net Pos": 0, "#Algos": 1, "Unreal": 0.00, "Real": 75.00, "Risk": 700.00},
            {"Symbol": "TSLA", "Net Pos": 25, "#Algos": 1, "Unreal": 12.55, "Real": -40.00, "Risk": 500.00},
            {"Symbol": "AMZN", "Net Pos": -10, "#Algos": 1, "Unreal": -5.25, "Real": 130.00, "Risk": 400.00},
        ]
        self.symbol_panel.set_data(demo_rows)

    def _start_symbol_demo_updates(self):
        """Simulate external updates every few seconds."""
        def tick():
            # Pick a few random symbols to update
            choices = ["AAPL", "MSFT", "NVDA", "TSLA", "AMZN"]
            for sym in random.sample(choices, k=3):
                # jitter PnL and risk a bit
                d_unreal = random.uniform(-25, 25)
                d_real = random.uniform(-5, 5)
                d_risk = random.uniform(-10, 10)
                d_pos = random.choice([-10, 0, 10])

                # call the public API expected to be called by other classes
                self.symbol_panel.update_row(
                    sym,
                    net_pos=None if d_pos == 0 else (self.symbol_panel._current_row(sym).get("Net Pos", 0) + d_pos),
                    unreal=self.symbol_panel._current_row(sym).get("Unreal", 0.0) + d_unreal,
                    real=self.symbol_panel._current_row(sym).get("Real", 0.0) + d_real,
                    risk=max(0.0, self.symbol_panel._current_row(sym).get("Risk", 0.0) + d_risk),
                )

            # schedule next tick (simulate "another class calls update every few seconds")
            self.ui.after(2000, tick)

        # kick off
        self.ui.after(1500, tick)


if __name__ == '__main__':
    root = tb.Window(themename='flatly')
    root.title('GoodTrade AMS')
    root.geometry('1000x700')
    dashboard = Dashboard(root)
    root.mainloop()