import os
import json
import tkinter as tk
import ttkbootstrap as tb
from ttkbootstrap.constants import *

from UI.ui_dashboard_market import *
ACTIVE = 0
MULTIPLIER = 1
PASSIVE = 2
DESCRIPTION = 3



class Dashboard:
    def __init__(self, ui):
        self.ui = ui
        # Ensure dashboard_panel exists
        if not hasattr(self.ui, 'dashboard_panel'):
            self.ui.dashboard_panel = tb.Frame(self.ui)
            self.ui.dashboard_panel.place(relx=0, rely=0, relheight=1, relwidth=1)
        
        # Initialize main tabs (Market, Symbol, Strategy)
        self.tab = tb.Notebook(self.ui.dashboard_panel)
        self.tab.place(relx=0, rely=0.01, relheight=0.98, relwidth=1)
        self.frames = {}

        for name in ('Market', 'Symbol', 'Strategy'):
            frame = tb.Frame(self.tab)
            self.frames[name] = frame
            self.tab.add(frame, text=name)
        
        # Populate the Market tab with its own nested notebook
        #self.create_market_panel()


        MarketPanel(self.frames['Market'])



if __name__ == '__main__':
    root = tb.Window(themename='flatly')
    root.title('GoodTrade AMS')
    root.geometry('1000x700')
    dashboard = Dashboard(root)
    root.mainloop()