import os
import tkinter as tk
import ttkbootstrap as tb
from ttkbootstrap.constants import *
import json
from ui_authorization import authorization

# Tooltip placeholder (simple version)
class Tooltip:
    def __init__(self, widget, title, text):
        widget.bind("<Enter>", lambda e: widget.configure(text=f"{title}: {text[:30]}..."))
        widget.bind("<Leave>", lambda e: widget.configure(text=widget.cget("text").split(':')[0]))

# Constants for algo indexing
ACTIVE = 0
MULTIPLIER = 1
PASSIVE = 2
DESCRIPTION = 3

class UI:
    def __init__(self, root, manager=None):
        self.root = root
        self.style = self.root.style
        self.manager = manager

        self.init_variables()
        self.init_design_map()
        self.init_panels()

        # External Algo UI logic (injected)
        self.algo_ui = authorization(self)


        self.init_notification_panel()
        self.init_placeholders()

        ###
        self.init_system_panel()
        self.init_filter_panel()


    def init_variables(self):
        self.SYSTEM_STATUS = tk.StringVar(value="ERROR")
        self.USER = tk.StringVar(value="Disconnected")
        self.ENV = tk.StringVar(value="Disconnected")
        self.DISASTER_MODE = tk.IntVar(value=0)
        self.POSITION_COUNT = tk.IntVar(value=0)
        self.OPEN_ORDER_COUNT = tk.IntVar(value=0)
        self.TOTAL_ALGO_COUNT = tk.IntVar(value=0)
        self.ACTIVE_ALGO_COUNT = tk.IntVar(value=0)
        self.PROACTIVE_ALGO_COUNT = tk.IntVar(value=0)
        self.DARK_MODE = tk.IntVar(value=0)

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
            'DISASTER MODE': {"var": self.DISASTER_MODE, "type": "check"},
            'DARK MODE': {"var": self.DARK_MODE, "type": "check"},
        }

    def init_panels(self):
        self.system_panel = tb.LabelFrame(self.root, text="System", bootstyle="primary")
        self.system_panel.place(x=10, y=10, height=350, width=340)

        self.auth_panel = tb.LabelFrame(self.root, text="Authorization", bootstyle="info")
        self.auth_panel.place(x=10, y=365, height=880, width=340)

        self.performance_panel = tb.LabelFrame(self.root, text="Dashboard", bootstyle="success")
        self.performance_panel.place(x=360, y=10, height=270, width=900)

        self.filter_panel = tb.LabelFrame(self.root, text="Algorithms Management", bootstyle="warning")
        self.filter_panel.place(x=360, y=280, height=80, width=900)

        self.deployment_panel = tb.LabelFrame(self.root, text="Algorithms Deployment", bootstyle="secondary")
        self.deployment_panel.place(x=360, y=365, height=880, width=900)

        self.notification_panel = tb.LabelFrame(self.root, text="Notifications", bootstyle="info")
        self.notification_panel.place(x=1270, y=10, height=1240, width=270)

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
                value_widget = tb.Entry(self.system_panel, textvariable=tk_var, width=24, bootstyle="secondary")
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
        # self.theme_var = tk.StringVar(value=self.style.theme.name)
        # self.theme_dropdown = tb.OptionMenu(
        #     self.system_panel, self.theme_var,
        #     *self.style.theme_names(),
        #     command=self.change_theme,
        #     bootstyle='secondary'
        # )
        # tb.Label(self.system_panel, text="UI Style", anchor="e", width=22, bootstyle="primary").grid(row=row+1,column=0, sticky="w")
        # self.theme_dropdown.grid(row=row+1,column=1, sticky="w")


        self.update_system_status_style()

    def disaster_mode_switch(self,*args):

        if self.DISASTER_MODE.get()==1:
            self.style.theme_use('vapor')
        else:
            if self.DARK_MODE.get() == 1:
                self.style.theme_use('darkly')
            else:
                self.style.theme_use('flatly')
    def dark_mode_switch(self,*args):

        if self.DISASTER_MODE.get()!=1:
            if self.DARK_MODE.get()==1:
                self.style.theme_use('darkly')

            else:
                self.style.theme_use('flatly')

    def update_system_status_style(self, *args):
        value = self.SYSTEM_STATUS.get()
        if self.system_status_label:
            if value.upper() == "ERROR":
                self.system_status_label.configure(bootstyle="inverse-danger")
            else:
                self.system_status_label.configure(bootstyle="inverse-success")

    def change_theme(self, theme_name):
        self.style.theme_use(theme_name)

    def init_notification_panel(self):
        self.notification_text = tb.Text(self.notification_panel, wrap="word", font=("Segoe UI", 10), bg="white")
        scrollbar = tb.Scrollbar(self.notification_panel, command=self.notification_text.yview)
        self.notification_text.configure(yscrollcommand=scrollbar.set)
        scrollbar.pack(side="right", fill="y")
        self.notification_text.pack(fill="both", expand=True, padx=10, pady=10)
        self.notification_text.insert("end", "🟠 System starting...\n")

    def init_placeholders(self):
        dashboard_label = tb.Label(self.performance_panel, text="Dashboard Overview Coming Soon...", font=("Segoe UI", 10, "italic"), bootstyle="secondary")
        dashboard_label.pack(anchor="center", pady=20)
        deployment_label = tb.Label(self.deployment_panel, text="No algorithms deployed yet.", font=("Segoe UI", 10, "italic"), bootstyle="warning")
        deployment_label.pack(anchor="center", pady=20)

    def init_filter_panel(self):
        container = tb.Frame(self.filter_panel)
        container.grid(row=0, column=0, padx=10, pady=10, sticky="w")

        # Row and column tracking
        r = 0
        c = 0

        # Clear Algos
        self.only_running_btn = tb.Button(container, text="Clear Algos", bootstyle="primary")
        self.only_running_btn.grid(row=r, column=c, padx=2)
        c += 1

        # Symbol Filter Label
        tk.Label(container, text="Symbol Filter:").grid(row=r, column=c, padx=(10, 2), sticky="w")
        c += 1

        # Symbol Filter Entry
        self.symbol_filter_entry = tb.Entry(container, width=10)
        self.symbol_filter_entry.grid(row=r, column=c, padx=1)
        c += 1

        # Filter Button 1
        self.filter_btn = tb.Button(container, text="Filter", bootstyle="primary")
        self.filter_btn.grid(row=r, column=c, padx=2)
        c += 1

        # Algo Filter Label
        tk.Label(container, text="Algo Filter:").grid(row=r, column=c, padx=(10, 2), sticky="w")
        c += 1

        # Algo Filter Entry
        self.algo_filter_entry = tb.Entry(container, width=10)
        self.algo_filter_entry.grid(row=r, column=c, padx=1)
        c += 1

        # Filter Button 2
        self.filter_btn2 = tb.Button(container, text="Filter", bootstyle="primary")
        self.filter_btn2.grid(row=r, column=c, padx=1)
        c += 1

        # +25% to W
        self.plus_25_btn = tb.Button(container, text="+ 25% to W", bootstyle="danger-outline")
        self.plus_25_btn.grid(row=r, column=c, padx=1)
        c += 1

        # -25% to W
        self.minus_25_btn = tb.Button(container, text="- 25% to W", bootstyle="danger-outline")
        self.minus_25_btn.grid(row=r, column=c, padx=2)
        c += 1

        # +25% to L
        self.plus_25_btnl = tb.Button(container, text="+ 25% to L", bootstyle="danger-outline")
        self.plus_25_btnl.grid(row=r, column=c, padx=6)
        c += 1

        # -25% to L
        self.minus_25_btnl = tb.Button(container, text="- 25% to L", bootstyle="danger-outline")
        self.minus_25_btnl.grid(row=r, column=c, padx=2)

if __name__ == '__main__':
    root = tb.Window(themename="flatly")
    root.title("GoodTrade AMS")
    root.geometry("1570x1280")

    UI(root)
    root.mainloop()
