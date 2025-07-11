import os
import tkinter as tk
import ttkbootstrap as tb
from ttkbootstrap.constants import *
import json
from ui_authorization import authorization
import random
from constants import *

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


        self.auth_collapsed = False


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

        self.init_algo_deployment_panel()

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
            'Disaster Mode': {"var": self.DISASTER_MODE, "type": "check"},
            'Dark Mode': {"var": self.DARK_MODE, "type": "check"},
            'Max Risk': {"var": self.MAX_RISK, "type": "entry"},
            'User Email': {"var": self.USER_EMAIL, "type": "entry"},
            'User Phone': {"var": self.USER_PHONE, "type": "entry"},
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

        self.deployment_panel = tb.LabelFrame(self.root, text="Algorithms Deployment", bootstyle="success")
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
                value_widget = tb.Entry(self.system_panel, textvariable=tk_var, width=15,     font=("Segoe UI", 9))
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
        self.plus_25_btn = tb.Button(container, text="+ 25% to W", bootstyle="success-outline")
        self.plus_25_btn.grid(row=r, column=c, padx=1)
        c += 1

        # -25% to W
        self.minus_25_btn = tb.Button(container, text="- 25% to W", bootstyle="success-outline")
        self.minus_25_btn.grid(row=r, column=c, padx=2)
        c += 1

        # +25% to L
        self.plus_25_btnl = tb.Button(container, text="+ 25% to L", bootstyle="danger-outline")
        self.plus_25_btnl.grid(row=r, column=c, padx=6)
        c += 1

        # -25% to L
        self.minus_25_btnl = tb.Button(container, text="- 25% to L", bootstyle="danger-outline")
        self.minus_25_btnl.grid(row=r, column=c, padx=2)

    def generate_random_algo(self):
        names = ["AAPL", "GOOG", "TSLA", "MSFT", "NVDA", "AMZN", "META", "NFLX", "INTC"]

        statuses = ["RUNNING", "DEPLOYED","REJECTED","CANCELED","ERROR"]

        name = random.choice(names)
        status = random.choice(statuses)

        position = f"{name}.NQ:{random.randint(1, 20)}"

        unreal = round(random.uniform(-50.0, 150.0), 2)
        real = round(random.uniform(-30.0, 30.0), 2)

        return {
            "Name": tk.StringVar(value=name),
            "Status": tk.StringVar(value=status),
            "Position": tk.StringVar(value=position),
            "Unrealized": tk.DoubleVar(value=unreal),
            "Realized": tk.DoubleVar(value=real),
        }


    def init_algo_deployment_panel(self):


        self.deployment_clickable = tb.Label(
        self.root,
        text="Algorithms Deployment",
        font=("Segoe UI", 9),
        background="",
        foreground="#2780e3",  # Optional: match your theme
        cursor="hand2"
        )
        self.deployment_clickable.config(text="▶ Algorithms Deployment")

        # Position it exactly where the label frame title is
        self.deployment_clickable.place(x=370, y=360)  # Adjust Y slightly above the frame

        # Bind click event
        self.deployment_clickable.bind("<Button-1>", self.toggle_deployment_panel)


        self.deployment_only_mode=False 

        # Scrollable canvas inside deployment panel
        self.canvas = tb.Canvas(self.deployment_panel)
        self.scroll_frame = tb.Frame(self.canvas)
        self.scrollbar = tb.Scrollbar(self.deployment_panel, orient="vertical", command=self.canvas.yview)
        self.canvas.configure(yscrollcommand=self.scrollbar.set)

        self.scrollbar.pack(side="right", fill="y")
        self.canvas.pack(side="left", fill="both", expand=True)
        self.canvas.create_window((0, 0), window=self.scroll_frame, anchor="nw")
        self.scroll_frame.bind("<Configure>", lambda e: self.canvas.configure(scrollregion=self.canvas.bbox("all")))

        # Headers
        headers = ["#", "Algo", "Status", "Position","Unreal", "Real", "+25", "-25", "+50", "-50", "Flatten", "A-Flat"]
        for col, text in enumerate(headers):
            tb.Button(self.scroll_frame, text=text,bootstyle="outline").grid(row=0, column=col,sticky="nsew")  #, font=('Arial', 10, 'bold')
            self.scroll_frame.grid_columnconfigure(col, weight=1)

        # Insert a visual separator line below headers (row=1)
        # separator = tb.Separator(self.scroll_frame, orient="horizontal")
        # separator.grid(row=1, column=0, columnspan=len(headers), sticky="ew", padx=2, pady=0)


        self.rows = []

        # Demo: Add sample entries
        sample_data = [self.generate_random_algo() for _ in range(25)]

        for data in sample_data:
            self.add_algo_row(data)

    def toggle_deployment_panel(self, event=None):
        if not self.deployment_only_mode:
            # COLLAPSE dashboard + filter, EXPAND deployment
            self.performance_panel.place_forget()
            self.filter_panel.place_forget()

            self.deployment_panel.place(x=360, y=10, height=365+880-10, width=900)

            # Optional: move your clickable label too
            self.deployment_clickable.place(x=370, y=5)
            self.deployment_clickable.config(text="▼ Algorithms Deployment")

            self.deployment_only_mode = True
        
            #self.deployment_clickable.config(text="▼ Algorithms Deployment")  # expanded
        else:
            # RESTORE original layout
            self.performance_panel.place(x=360, y=10, height=270, width=900)
            self.filter_panel.place(x=360, y=280, height=80, width=900)
            self.deployment_panel.place(x=360, y=365, height=880, width=900)

            self.deployment_clickable.place(x=370, y=360)
            # self.deployment_clickable.config(text="▼ Algorithms Deployment")
            self.deployment_clickable.config(text="▶ Algorithms Deployment")  # collapsed

            self.deployment_only_mode = False

    def add_algo_row(self, data, insert_at_index=None):
        if not hasattr(self, 'rows'):
            self.rows = []

        if insert_at_index is None:
            insert_at_index = len(self.rows)

        for i in range(insert_at_index, len(self.rows)):
            for widget in self.rows[i]:
                info = widget.grid_info()
                widget.grid(row=info['row'] + 1, column=info['column'])

        row_widgets = []

        def make_var_label(var, col, style=None):
            label = tb.Label(self.scroll_frame, textvariable=var, anchor="w")
            label.grid(row=insert_at_index + 1, column=col, sticky="nsew", padx=5, pady=1)
            row_widgets.append(label)
            return label

        # Row number
        row_number_label = tb.Label(self.scroll_frame, text=str(insert_at_index + 1), anchor="w")
        row_number_label.grid(row=insert_at_index + 1, column=0, sticky="nsew", padx=5, pady=1)
        row_widgets.append(row_number_label)

        # Algo name (click to duplicate)
        name_label = tb.Label(self.scroll_frame, textvariable=data["Name"], anchor="w", cursor="hand2")
        name_label.grid(row=insert_at_index + 1, column=1, sticky="nsew", padx=5, pady=1)
        name_label.bind("<Button-1>", lambda e: self.add_algo_row(data, insert_at_index + 1))
        row_widgets.append(name_label)

        # Status
        make_var_label(data["Status"], 2)

        # Position (truncated + tooltip)
        full_position = data["Position"].get()
        short_position = full_position if len(full_position) <= 30 else full_position[:27] + "..."
        position_label = tb.Label(self.scroll_frame, text=short_position, anchor="w",width=10)
        position_label.grid(row=insert_at_index + 1, column=3, sticky="nsew", padx=5, pady=1)
        row_widgets.append(position_label)

        def show_tooltip(event):
            position_label.tooltip = tw = tk.Toplevel(position_label)
            tw.wm_overrideredirect(True)
            x = position_label.winfo_rootx() + 20
            y = position_label.winfo_rooty() + position_label.winfo_height() + 5
            tw.geometry(f"+{x}+{y}")
            tk.Label(tw, text=full_position, bg="#ffffe0", font=("Segoe UI", 9), relief="solid", borderwidth=1).pack()

        def hide_tooltip(event):
            if hasattr(position_label, 'tooltip') and position_label.tooltip:
                position_label.tooltip.destroy()
                position_label.tooltip = None

        position_label.bind("<Enter>", show_tooltip)
        position_label.bind("<Leave>", hide_tooltip)

        # Unrealized (colored)
        unreal_val = data["Unrealized"].get()
        unreal_style = "inverse-Success.TLabel" if unreal_val >= 0 else "inverse-Danger.TLabel"
        unreal_label = tb.Label(self.scroll_frame, text=f"{unreal_val:.2f}", style=unreal_style, anchor="e")
        unreal_label.grid(row=insert_at_index + 1, column=4, sticky="nsew", padx=1, pady=1)
        row_widgets.append(unreal_label)

        # Realized (colored)
        real_val = data["Realized"].get()
        real_style = "inverse-Success.TLabel" if real_val >= 0 else "inverse-Danger.TLabel"
        real_label = tb.Label(self.scroll_frame, text=f"{real_val:.2f}", style=real_style, anchor="e")
        real_label.grid(row=insert_at_index + 1, column=5, sticky="nsew", padx=1, pady=1)
        row_widgets.append(real_label)

        # Action buttons
        actions = ["+25", "-25", "+50", "-50", "Flatten", "A-Flat"]
        for i, label_text in enumerate(actions):
            btn = tb.Button(self.scroll_frame, text=label_text, bootstyle="success-outline", width=7)
            btn.grid(row=insert_at_index + 1, column=6 + i, padx=1)
            row_widgets.append(btn)

        self.rows.insert(insert_at_index, row_widgets)
        self.refresh_algo_row_numbers()

    def refresh_algo_row_numbers(self):
        if not hasattr(self, 'rows'):
            return
        for i, widgets in enumerate(self.rows):
            widgets[0].config(text=str(i + 1))


if __name__ == '__main__':
    root = tb.Window(themename="flatly")
    root.title("GoodTrade AMS")
    root.geometry("1570x1280")

    UI(root)
    root.mainloop()
