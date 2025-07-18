import os
import json
import tkinter as tk
import ttkbootstrap as tb
from ttkbootstrap.constants import *

ACTIVE = 0
MULTIPLIER = 1
PASSIVE = 2
DESCRIPTION = 3

class Dashboard:
    def __init__(self, ui):
        self.ui = ui
        self.tab = tb.Notebook(self.ui.dashboard_panel)
        self.tab.place(relx=0.0, rely=0.01, relheight=0.98, relwidth=1)


        self.frames = {}

        KEY = 'Symbol'
        self.frames[KEY] = tk.Frame(self.tab)
        self.tab.add(self.frames[KEY], text=KEY)

        KEY = 'Strategy'
        self.frames[KEY] = tk.Frame(self.tab)
        self.tab.add(self.frames[KEY], text=KEY)

    def init_system_design_map(self):
        self.system_panel_design = {
            'System': {"var": self.SYSTEM_STATUS, "type": "label"},
            'User': {"var": self.USER, "type": "label"},
            'Environment': {"var": self.ENV, "type": "label"},
            'Positions': {"var": self.POSITION_COUNT, "type": "label"},
            'Open Orders': {"var": self.OPEN_ORDER_COUNT, "type": "label"},
            'Total Algos': {"var": self.TOTAL_ALGO_COUNT, "type": "label"},
            'Active Algos': {"var": self.ACTIVE_ALGO_COUNT, "type": "label"},
            'Proactive Algos': {"var": self.PROACTIVE_ALGO_COUNT, "type": "label"},
            'Halt Notification':{'var':self.HALT_NOTIFICATION,'type':"check"},
            'Disaster Mode': {"var": self.DISASTER_MODE, "type": "check"},
            'Dark Mode': {"var": self.DARK_MODE, "type": "check"},
            'Max Risk': {"var": self.MAX_RISK, "type": "entry"},
            'User Email': {"var": self.USER_EMAIL, "type": "entry"},
            'User Phone': {"var": self.USER_PHONE, "type": "entry"},
        }


    def update_system_status_style(self, *args):
        value = self.ui.SYSTEM_STATUS.get()
        if self.system_status_label:
            if value.upper() == "ERROR":
                self.system_status_label.configure(bootstyle="inverse-danger")
            else:
                self.system_status_label.configure(bootstyle="inverse-success") 
        if self.ui.DISASTER_MODE.get()!=1:
            if self.ui.DARK_MODE.get()==1:
                self.ui.style.theme_use('darkly')

                self.ui.style.configure("Treeview", font=('Arial', 10), rowheight=24) # Ensure font/rowheight are consistent

                self.ui.style.configure("Treeview.Heading", borderwidth=2, relief="raised")

            else: # flatly theme
                self.ui.style.theme_use('flatly')
                self.ui.style.configure("Treeview", font=('Arial', 10), rowheight=24) # Ensure font/rowheight are consistent

                self.ui.style.configure("Treeview.Heading", borderwidth=2, relief="raised")

        # Crucially, call this function to update all Treeview row styles
        # (including foreground and specific row tag colors) based on the new theme.
        #self.update_treeview_row_styles()

    def dark_mode_switch(self,*args):
        if self.ui.DISASTER_MODE.get()!=1:
            if self.ui.DARK_MODE.get()==1:
                self.ui.style.theme_use('darkly')

                self.ui.style.configure("Treeview", font=('Arial', 10), rowheight=24) # Ensure font/rowheight are consistent

                self.ui.style.configure("Treeview.Heading", borderwidth=2, relief="raised")

            else: # flatly theme
                self.ui.style.theme_use('flatly')
                self.ui.style.configure("Treeview", font=('Arial', 10), rowheight=24) # Ensure font/rowheight are consistent

                self.ui.style.configure("Treeview.Heading", borderwidth=2, relief="raised")

        # Crucially, call this function to update all Treeview row styles
        # (including foreground and specific row tag colors) based on the new theme.
        #self.update_treeview_row_styles()


