import os
import json
import tkinter as tk
import ttkbootstrap as tb
from ttkbootstrap.constants import *

ACTIVE = 0
MULTIPLIER = 1
PASSIVE = 2
DESCRIPTION = 3

# Venue definitions per market and grouping
GROUP_MAP = {
    'US DEFAULT': ['.NQ', '.NY', '.AM'],
    'CA DEFAULT': ['.TO', '.VN', '.CC'],
}
MARKET = {
    'US DEFAULT': [
        "ARCA ACTION ARCX Limit DAY",
        "BATS ACTION Parallel-2D Limit DAY",
        "EDGA ACTION ROUC Limit DAY",
        "MEMX ACTION MEMX Limit Visible DAY",
    ],
    '.NQ': [
        "ARCA ACTION ARCX Limit DAY",
        "BATS ACTION Parallel-2D Limit DAY",
        "EDGA ACTION ROUC Limit DAY",
        "MEMX ACTION MEMX Limit Visible DAY",
    ],
    '.NY': [
        "ARCA ACTION ARCX Limit DAY",
        "BATS ACTION Parallel-2D Limit DAY",
        "EDGA ACTION ROUC Limit DAY",
        "MEMX ACTION MEMX Limit Visible DAY",
    ],
    '.AM': [
        "ARCA ACTION ARCX Limit DAY",
        "BATS ACTION Parallel-2D Limit DAY",
        "EDGA ACTION ROUC Limit DAY",
        "MEMX ACTION MEMX Limit Visible DAY",
    ],
    'CA DEFAULT': [
        "AEQN ACTION AequitasLIT Limit Broker DAY",
        "AEQN ACTION AequitasNEO Limit Broker DAY",
        "ALPH ACTION ALPHA Limit Broker DAY",
        "CHIX ACTION SMART Limit Broker DAY",
        "LYNX ACTION LYNXSOR Limit Broker DAY",
        "OMGA ACTION OMEGASOR Limit Broker DAY",
        "TSX ACTION SweepSOR Limit Broker DAY",
        "XCSE ACTION CSESMRT Limit Broker DAY",
        "CX2 ACTION SMART Limit DAY",
        "CXD ACTION NasdaqCXD Limit DAY",
    ],
    '.TO': [
        "AEQN ACTION AequitasLIT Limit Broker DAY",
        "AEQN ACTION AequitasNEO Limit Broker DAY",
        "ALPH ACTION ALPHA Limit Broker DAY",
        "CHIX ACTION SMART Limit Broker DAY",
        "LYNX ACTION LYNXSOR Limit Broker DAY",
        "OMGA ACTION OMEGASOR Limit Broker DAY",
        "TSX ACTION SweepSOR Limit Broker DAY",
        "XCSE ACTION CSESMRT Limit Broker DAY",
        "CX2 ACTION SMART Limit DAY",
        "CXD ACTION NasdaqCXD Limit DAY",
    ],
    '.VN': [
        "AEQN ACTION AequitasLIT Limit Broker DAY",
        "AEQN ACTION AequitasNEO Limit Broker DAY",
        "ALPH ACTION ALPHA Limit Broker DAY",
        "CHIX ACTION SMART Limit Broker DAY",
        "LYNX ACTION LYNXSOR Limit Broker DAY",
        "OMGA ACTION OMEGASOR Limit Broker DAY",
        "TSX ACTION SweepSOR Limit Broker DAY",
        "XCSE ACTION CSESMRT Limit Broker DAY",
        "CX2 ACTION SMART Limit DAY",
        "CXD ACTION NasdaqCXD Limit DAY",
    ],
    '.CC': [
        "AEQN ACTION AequitasLIT Limit Broker DAY",
        "AEQN ACTION AequitasNEO Limit Broker DAY",
        "ALPH ACTION ALPHA Limit Broker DAY",
        "CHIX ACTION SMART Limit Broker DAY",
        "LYNX ACTION LYNXSOR Limit Broker DAY",
        "OMGA ACTION OMEGASOR Limit Broker DAY",
        "TSX ACTION SweepSOR Limit Broker DAY",
        "XCSE ACTION CSESMRT Limit Broker DAY",
        "CX2 ACTION SMART Limit DAY",
        "CXD ACTION NasdaqCXD Limit DAY",
    ],
}

class Dashboard:
    def __init__(self, ui):
        self.ui = ui
        if not hasattr(self.ui, 'dashboard_panel'):
            self.ui.dashboard_panel = tb.Frame(self.ui)
            self.ui.dashboard_panel.place(relx=0, rely=0, relheight=1, relwidth=1)

        self.tab = tb.Notebook(self.ui.dashboard_panel)
        self.tab.place(relx=0, rely=0.01, relheight=0.98, relwidth=1)

        # Create frames for tabs
        self.frames = {}
        for key in ('Market', 'Symbol', 'Strategy'):
            frame = tb.Frame(self.tab)
            self.frames[key] = frame
            self.tab.add(frame, text=key)

        # Build panels
        self.create_market_panel()

    def create_market_panel(self):
        """
        Populate Market tab with two labelframes side-by-side: Default sections.
        """
        market_frame = self.frames['Market']
        self.market_vars = {}

        # Create subframes
        us_frame = tb.Labelframe(market_frame,
                                 text='US Markets', bootstyle='primary', width=380, padding=15)
        ca_frame = tb.Labelframe(market_frame,
                                 text='Canada Markets', bootstyle='primary', width=380, padding=15)
        us_frame.grid(row=0, column=0, padx=20, pady=20, sticky='n')
        ca_frame.grid(row=0, column=1, padx=20, pady=20, sticky='n')

        # Populate groups
        self._populate_group(us_frame, 'US DEFAULT')
        self._populate_group(ca_frame, 'CA DEFAULT')

        # Bind propagation
        self._bind_group('US DEFAULT')
        self._bind_group('CA DEFAULT')

    def _populate_group(self, parent, group_key):
        """
        Helper to populate a group labelframe with its group and child markets.
        """
        # Group
        venues = MARKET[group_key]
        var = tk.StringVar(parent)
        var.set(venues[0])
        self.market_vars[group_key] = var
        tb.Label(parent, text=group_key, bootstyle='warning').grid(row=0, column=0, sticky='w', pady=2)
        tb.Combobox(parent, textvariable=var, values=venues, state='readonly',
                    bootstyle='warning', width=40).grid(row=0, column=1, pady=2)

        # Children
        for i, child in enumerate(GROUP_MAP[group_key], start=1):
            venues = MARKET[child]
            var = tk.StringVar(parent)
            var.set(venues[0])
            self.market_vars[child] = var
            tb.Label(parent, text=child).grid(row=i, column=0, sticky='w', pady=2)
            tb.Combobox(parent, textvariable=var, values=venues, state='readonly',
                        bootstyle='info', width=40).grid(row=i, column=1, pady=2)

    def _bind_group(self, group_key):
        """
        Bind a group's StringVar to propagate its value to child markets.
        """
        def callback(*args):
            val = self.market_vars[group_key].get()
            for child in GROUP_MAP[group_key]:
                if val in MARKET[child]:
                    self.market_vars[child].set(val)
        self.market_vars[group_key].trace_add('write', callback)

    def init_system_design_map(self):
        self.system_panel_design = {
            'System': {"var": self.SYSTEM_STATUS, "type": "label"},
        }

if __name__ == '__main__':
    root = tb.Window(themename='flatly')
    root.title('GoodTrade AMS')
    root.geometry('800x600')

    root.dashboard_panel = tb.Frame(root)
    root.dashboard_panel.place(relx=0, rely=0, relheight=1, relwidth=1)

    dashboard = Dashboard(root)
    root.mainloop()
