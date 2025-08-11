import os
import tkinter as tk
from tkinter import ttk
import ttkbootstrap as tb
from ttkbootstrap.constants import *
import json
# Assuming ui_authorization exists and provides an 'authorization' class
from UI.ui_authorization import authorization

from UI.ui_deployment import Algo_Deployment_Panel
from UI.ui_dashboard import Dashboard
from UI.ui_sims import *
import random
from datetime import datetime # Import datetime for time formatting

from constants import *
import threading
import time
from _tkinter import TclError # For Tooltip



# Constants for algo indexing (if not from constants.py)
try:
    from constants import *
except ImportError:
    # Define local constants if constants.py is not available
    ACTIVE = 0
    MULTIPLIER = 1
    PASSIVE = 2
    DESCRIPTION = 3



class UI:
    def __init__(self, root, manager=None):
        self.root = root
        self.style = self.root.style
        # Configure Treeview styles once for consistency across all Treeviews
        self.style.configure("Treeview",
            font=('Arial', 10), # Adjusted font size for data rows to match image
            rowheight=24,
        )

        self.SIMULATION_MODE = False

        self.style.configure("Treeview.Heading",borderwidth=2,relief="raised")
        # The background and foreground for Heading will be managed by ttkbootstrap's themes
        self.manager = manager

        self.running = True # Control for update threads
        
        self.auth_collapsed = False

        self.init_variables()
        self.init_design_map()
        self.init_panels()

        self.algo_authorization = authorization(self)

        self.sim_test = sim_test(self)

        self.algo_deployment = Algo_Deployment_Panel(self)

        self.dashboard = Dashboard(self)

        self.init_notification_panel()
        self.init_placeholders()

        self.init_system_panel()
        self.init_filter_panel()

        print('UI finished constructing')
        # Initialize the deployment panel Treeview
        # self.init_algo_deployment_panel() # This now uses the specified style

        #self.root.after(500, self.simulation_add) # This will add to the deployment panel
        


        # self.start_unreal_random_update_thread() # Start a general update thread

        # Ensure main dashboard placeholder is initially shown as it no longer has a Treeview
        #self.performance_panel.pack_propagate(False) # Prevent shrinking

        # self.dashboard_placeholder_label = tb.Label(
        #     self.performance_panel,
        #     text="Dashboard Overview Coming Soon...",
        #     font=("Segoe UI", 10, "italic"),
        #     bootstyle="secondary"
        # )
        # self.dashboard_placeholder_label.pack(anchor="center", expand=True)


    def init_variables(self):
        self.is_sort_running = False
        self.SYSTEM_STATUS = tk.StringVar(value="Error")

        if self.manager:
            self.USER = self.manager.USER
            self.ENV = self.manager.ENV
            self.SYSTEM_STATUS = self.manager.SYSTEM_STATUS

            self.DISASTER_MODE = self.manager.DISASTER_MODE
            self.POSITION_COUNT = self.manager.POSITION_COUNT
            self.OPEN_ORDER_COUNT = self.manager.OPEN_ORDER_COUNT
            self.TOTAL_ALGO_COUNT = self.manager.TOTAL_ALGO_COUNT
            self.ACTIVE_ALGO_COUNT = self.manager.ACTIVE_ALGO_COUNT
            self.PROACTIVE_ALGO_COUNT = self.manager.PROACTIVE_ALGO_COUNT
            self.HALT_NOTIFICATION = self.manager.HALT_NOTIFICATION
        else:
            self.USER = tk.StringVar(value="Disconnected")
            self.ENV = tk.StringVar(value="Disconnected")
            self.SYSTEM_STATUS = tk.StringVar(value='Error')

            self.DISASTER_MODE = tk.IntVar(value=0)
            self.POSITION_COUNT = tk.IntVar(value=0)
            self.OPEN_ORDER_COUNT = tk.IntVar(value=0)
            self.TOTAL_ALGO_COUNT = tk.IntVar(value=0)
            self.ACTIVE_ALGO_COUNT = tk.IntVar(value=0)
            self.PROACTIVE_ALGO_COUNT = tk.IntVar(value=0)
            self.HALT_NOTIFICATION = tk.IntVar(value=0)


        self.DARK_MODE = tk.IntVar(value=0)

        self.MAX_RISK = tk.IntVar(value=300)
        self.USER_EMAIL = tk.StringVar(value="")
        self.USER_PHONE = tk.StringVar(value="")




    def init_design_map(self):
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

    def init_panels(self):
        self.system_panel = tb.LabelFrame(self.root, text="System", bootstyle="primary")
        self.system_panel.place(x=10, y=10, height=350, width=340)

        self.user_panel = tb.LabelFrame(self.root, text="User", bootstyle="info")
        self.user_panel.place(x=10, y=365, height=880, width=340)


        self.user_panels = tb.Notebook(self.user_panel)
        self.user_panels.place(relx=0, rely=0.01, relheight=0.99, relwidth=1)

        # self.auth_panel = tb.LabelFrame(self.root, text="Authorization", bootstyle="info")
        # self.auth_panel.place(x=10, y=365, height=880, width=340)



        # Main Dashboard - Now just a placeholder panel
        self.dashboard_panel = tb.LabelFrame(self.root, text="Dashboard", bootstyle="success")
        self.dashboard_panel.place(x=360, y=10, height=270, width=1000)

        self.filter_panel = tb.LabelFrame(self.root, text="Algorithms Management", bootstyle="warning")
        self.filter_panel.place(x=360, y=280, height=80, width=1000)

        # Deployment Panel - This will contain the only Treeview
        self.deployment_panel = tb.LabelFrame(self.root, text="Algorithms Deployment", bootstyle="success")
        self.deployment_panel.place(x=360, y=365, height=880, width=1000)

        self.notification_panel = tb.LabelFrame(self.root, text="Notifications", bootstyle="info")
        self.notification_panel.place(x=1370, y=10, height=1240, width=270)

    def init_notification_panel(self):
        self.notification_text = tb.Text(self.notification_panel, wrap="word", font=("Segoe UI", 10), bg="white")
        scrollbar = tb.Scrollbar(self.notification_panel, command=self.notification_text.yview)
        self.notification_text.configure(yscrollcommand=scrollbar.set)
        scrollbar.pack(side="right", fill="y")
        self.notification_text.pack(fill="both", expand=True, padx=10, pady=10)
        self.notification_text.insert("end", "🟠 System starting...\n")

    def init_system_panel(self):
        self.system_status_label = None
        for row, (label_name, config) in enumerate(self.system_panel_design.items()):
            tk_var = config["var"]
            widget_type = config["type"]
            label = tb.Label(self.system_panel, text=f"{label_name}:", anchor="e", width=20, font=("Segoe UI", 10,'bold'),bootstyle='primary')
            label.grid(row=row, column=0, sticky="e", padx=(5, 5), pady=0)
            if widget_type == "label":
                value_widget = tb.Label(self.system_panel, textvariable=tk_var, anchor="w", width=22, bootstyle="success")
            elif widget_type == "entry":
                value_widget = tb.Entry(self.system_panel, textvariable=tk_var, width=15, font=("Segoe UI", 9))
            elif widget_type == "check":
                value_widget = tb.Checkbutton(self.system_panel, variable=tk_var, bootstyle="danger-round-toggle", onvalue=1, offvalue=0)
            else:
                value_widget = tb.Label(self.system_panel, text="[Unknown Widget Type]")
            if label_name == "System":
                self.system_status_label = value_widget
            value_widget.grid(row=row, column=1, sticky="w", padx=(5, 10), pady=0)
            self.system_panel.grid_propagate(False)

        self.SYSTEM_STATUS.trace_add("write", self.update_system_status_style)
        self.DARK_MODE.trace_add('write',self.dark_mode_switch)
        self.DISASTER_MODE.trace_add('write',self.disaster_mode_switch)

        self.update_system_status_style()

    def disaster_mode_switch(self,*args):
        if self.DISASTER_MODE.get()==1:
            self.style.theme_use('vapor')
            self.style.configure("Treeview", font=('Arial', 10), rowheight=24) # Ensure font/rowheight are consistent

            self.style.configure("Treeview.Heading", borderwidth=2, relief="raised")

        else:
            if self.DARK_MODE.get() == 1:
                self.style.theme_use('darkly')
                self.style.configure("Treeview", font=('Arial', 10), rowheight=24) # Ensure font/rowheight are consistent

                self.style.configure("Treeview.Heading", borderwidth=2, relief="raised")

            else:
                self.style.theme_use('flatly')
                self.style.configure("Treeview", font=('Arial', 10), rowheight=24) # Ensure font/rowheight are consistent

                self.style.configure("Treeview.Heading", borderwidth=2, relief="raised")
        # Call the new function to update Treeview row styles after theme change
        self.algo_deployment.update_treeview_row_styles()


    def dark_mode_switch(self,*args):
        if self.DISASTER_MODE.get()!=1:
            if self.DARK_MODE.get()==1:
                self.style.theme_use('darkly')

                self.style.configure("Treeview", font=('Arial', 10), rowheight=24) # Ensure font/rowheight are consistent

                self.style.configure("Treeview.Heading", borderwidth=2, relief="raised")

            else: # flatly theme
                self.style.theme_use('flatly')
                self.style.configure("Treeview", font=('Arial', 10), rowheight=24) # Ensure font/rowheight are consistent

                self.style.configure("Treeview.Heading", borderwidth=2, relief="raised")

        self.algo_deployment.update_treeview_row_styles()

    def change_theme(self, theme_name):
        self.style.theme_use(theme_name)
        self.algo_deployment.update_treeview_row_styles() # Call this when theme changes programmatically as well


    def update_system_status_style(self, *args):
        value = self.SYSTEM_STATUS.get()
        if self.system_status_label:
            if value.upper() == "ERROR":
                self.system_status_label.configure(bootstyle="inverse-danger")

            else:
                self.system_status_label.configure(bootstyle="inverse-success") 
        if self.DISASTER_MODE.get()!=1:
            if self.DARK_MODE.get()==1:
                self.style.theme_use('darkly')

                self.style.configure("Treeview", font=('Arial', 10), rowheight=24) # Ensure font/rowheight are consistent

                self.style.configure("Treeview.Heading", borderwidth=2, relief="raised")

            else: # flatly theme
                self.style.theme_use('flatly')
                self.style.configure("Treeview", font=('Arial', 10), rowheight=24) # Ensure font/rowheight are consistent

                self.style.configure("Treeview.Heading", borderwidth=2, relief="raised")

    def init_placeholders(self):
        # The placeholder label is now created in __init__ and managed there
        pass

    def init_filter_panel(self):
        container = tb.Frame(self.filter_panel)
        container.grid(row=0, column=0, padx=5, pady=5, sticky="w") # Adjusted padx/pady

        r = 0
        c = 0

        self.only_running_btn = tb.Button(container, text="Clear Algos", bootstyle="primary")
        self.only_running_btn.grid(row=r, column=c, padx=(0, 5)) # Adjusted padx
        c += 1

        tk.Label(container, text="Symbol Filter:").grid(row=r, column=c, padx=(5, 2), sticky="w") # Adjusted padx
        c += 1

        self.symbol_filter_entry = tb.Entry(container, width=10)
        self.symbol_filter_entry.grid(row=r, column=c, padx=(0, 5)) # Adjusted padx
        c += 1

        self.filter_btn = tb.Button(container, text="Filter", bootstyle="primary")
        self.filter_btn.grid(row=r, column=c, padx=(0, 5)) # Adjusted padx
        c += 1

        tk.Label(container, text="Algo Filter:").grid(row=r, column=c, padx=(5, 2), sticky="w") # Adjusted padx
        c += 1

        self.algo_filter_entry = tb.Entry(container, width=10)
        self.algo_filter_entry.grid(row=r, column=c, padx=(0, 5)) # Adjusted padx
        c += 1

        self.filter_btn2 = tb.Button(container, text="Filter", bootstyle="primary")
        self.filter_btn2.grid(row=r, column=c, padx=(0, 10)) # Adjusted padx
        c += 1

        self.plus_25_btn = tb.Button(container, text="+ 25% to W", bootstyle="success-outline")
        self.plus_25_btn.grid(row=r, column=c, padx=(0, 2)) # Adjusted padx
        c += 1

        self.minus_25_btn = tb.Button(container, text="- 25% to W", bootstyle="success-outline")
        self.minus_25_btn.grid(row=r, column=c, padx=(0, 5)) # Adjusted padx
        c += 1

        self.plus_25_btnl = tb.Button(container, text="+ 25% to L", bootstyle="danger-outline")
        self.plus_25_btnl.grid(row=r, column=c, padx=(0, 2)) # Adjusted padx
        c += 1

        self.minus_25_btnl = tb.Button(container, text="- 25% to L", bootstyle="danger-outline")
        self.minus_25_btnl.grid(row=r, column=c, padx=0) # Adjusted padx (no padding on last item)



    def _on_closing(self):
        print("Closing application...")
        self.running = False
        self.root.destroy()


if __name__ == '__main__':
    root = tb.Window(themename="flatly") # Start with a light theme
    root.title("GoodTrade AMS")

    screen_width = root.winfo_screenwidth()
    screen_height = root.winfo_screenheight()

    root.geometry("1770x1280")

    app = UI(root)
    root.protocol("WM_DELETE_WINDOW", app._on_closing)
    root.mainloop()