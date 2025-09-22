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
from UI.ui_tfm import *
from UI.ui_quickhedge import *
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

        self.flashing_red_ = False

        self.init_variables()
        self.init_design_map()
        self.init_panels()

        self.algo_authorization = authorization(self)

        self.sim_test = sim_test(self)
        self.tmf = TFMPanel(self)


        self.user_panels.add(self.tmf, text="TradeForMe")

        self.qh = QuickHedgePanel(self)
        self.user_panels.add(self.qh, text="QuickHedge")

        self.algo_deployment = Algo_Deployment_Panel(self)

        self.dashboard = Dashboard(self)

        self.init_notification_panel()
        self.init_placeholders()

        self.init_system_panel()
        self.init_filter_panel()

        #print('UI finished constructing')
        # Initialize the deployment panel Treeview


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
            self.NO_MORE_ALGOS = self.manager.NO_MORE_ALGOS

            self.DEBUG_mode = self.manager.DEBUG_mode


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
            self.NO_MORE_ALGOS = tk.IntVar(value=0)

            self.DEBUG_mode = tk.IntVar(value=0)


        

        self.DARK_MODE = tk.IntVar(value=1)
        self.DISCONNECTED = tk.IntVar(value=0)
        # self.MAX_RISK = tk.IntVar(value=300)
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
            'Anticipatory Algos': {"var": self.PROACTIVE_ALGO_COUNT, "type": "label"},
            'Stop Receiving Algos':{'var':self.NO_MORE_ALGOS,'type':"check"},
            #'Halt Notification':{'var':self.HALT_NOTIFICATION,'type':"check"},
            'Disaster Mode': {"var": self.DISASTER_MODE, "type": "check"},
            'Dark Mode': {"var": self.DARK_MODE, "type": "check"},
            'Debug Mode': {'var':self.DEBUG_mode,"type":'check'},
            # 'Max Risk': {"var": self.MAX_RISK, "type": "entry"},
            'User Email': {"var": self.USER_EMAIL, "type": "entry"},
            'User Phone': {"var": self.USER_PHONE, "type": "entry"},
        }

    def init_panels(self):
        self.system_panel = tb.LabelFrame(self.root, text="System", bootstyle="primary")
        self.system_panel.place(x=10, y=10, height=350, width=340)

        self.user_panel = tb.LabelFrame(self.root, text="User", bootstyle="info")
        self.user_panel.place(x=10, y=365, height=880, width=340)

        self.user_clickable = tb.Label(
            self.root,
            text="▶ User",
            font=("Segoe UI", 9),
            background="",
            foreground="#2780e3",
            cursor="hand2"
        )

        self.user_only_mode = False
        self.user_clickable.place(x=20, y=360)
        self.user_clickable.bind("<Button-1>", self.toggle_user_pannel)


        self.user_panels = tb.Notebook(self.user_panel)
        self.user_panels.place(relx=0, rely=0.01, relheight=0.99, relwidth=1)

        # self.auth_panel = tb.LabelFrame(self.root, text="Authorization", bootstyle="info")
        # self.auth_panel.place(x=10, y=365, height=880, width=340)



        # Main Dashboard - Now just a placeholder panel
        self.dashboard_panel = tb.LabelFrame(self.root, text="Dashboard", bootstyle="success")
        self.dashboard_panel.place(x=360, y=10, height=270, width=1200)

        self.filter_panel = tb.LabelFrame(self.root, text="Algorithms Management", bootstyle="warning")
        self.filter_panel.place(x=360, y=280, height=80, width=1200)

        # Deployment Panel - This will contain the only Treeview
        self.deployment_panel = tb.LabelFrame(self.root, text="Algorithms Deployment", bootstyle="success")
        self.deployment_panel.place(x=360, y=365, height=880, width=1200)

        self.notification_panel = tb.LabelFrame(self.root, text="Notifications", bootstyle="info")
        self.notification_panel.place(x=1570, y=10, height=630, width=270)


        self.rejection_info_pannel = tb.LabelFrame(self.root, text="Rejections window", bootstyle="info")
        self.rejection_info_pannel.place(x=1570, y=640, height=610, width=270)

    def init_notification_panel(self):
        self.notification_text = tb.Text(self.notification_panel, wrap="word",
                                         font=("Segoe UI", 10), bg="white")
        scrollbar = tb.Scrollbar(self.notification_panel, command=self.notification_text.yview)
        self.notification_text.configure(yscrollcommand=scrollbar.set)
        scrollbar.pack(side="right", fill="y")
        self.notification_text.pack(fill="both", expand=True, padx=10, pady=10)

        #self._apply_notification_theme()   # <-- set colors for current mode
        self.notification_text.insert("end", "🟠 System starting...\n", "normal")

        

        ######################################################################################

        self.rejection_text= tb.Text(self.rejection_info_pannel, wrap="word",
                                         font=("Segoe UI", 10), bg="white")
        scrollbar = tb.Scrollbar(self.rejection_info_pannel, command=self.rejection_text.yview)
        self.rejection_text.configure(yscrollcommand=scrollbar.set)
        scrollbar.pack(side="right", fill="y")
        self.rejection_text.pack(fill="both", expand=True, padx=10, pady=10)

        
        self.rejection_text.insert("end", "🟠 Rejects Info:\n", "normal")


        ###############################
        self._apply_notification_theme() 
        self.demo_notifications()
    def check(self):
        print('UI CHECk')

    def demo_notifications(self):
        """Populate the notification panel with demo messages and clickable links."""
        # Apply palette once more in case theme just switched
        if hasattr(self, "_apply_notification_theme"):
            self._apply_notification_theme()

        # Header
        self.notification_text.config(state='normal')
        self.notification_text.insert(tk.END, "\n—— System start ——\n", ("muted",))
        self.notification_text.config(state='disabled')

        ts = datetime.now().strftime("%H:%M:%S")

        self.notification_text.see(tk.END)

    def show_notification(self, message: str, max_lines=500, color="black"):

        if 'mode switch' in message:
            color='red'
        if not self.notification_text.tag_names().__contains__(color):
            self.notification_text.tag_config(color, foreground=color)

        # Insert the message with the color tag
        self.notification_text.insert(tk.END, message + '\n', color)
        self.notification_text.see(tk.END)

        # Trim to keep only the last 500 lines
        lines = self.notification_text.get("1.0", tk.END).splitlines()
        if len(lines) > max_lines:
            self.notification_text.delete("1.0", f"{len(lines) - max_lines + 1}.0")

        self.notification_text.config(state='disabled')

        print(message)

    def show_notification(self, message: str, max_lines=500, color="normal"):
        if 'mode switch' in message:
            color = 'error'

        # ensure tag exists (palette will recolor it)
        if color not in self.notification_text.tag_names():
            self.notification_text.tag_config(color)

        self.notification_text.config(state='normal')
        self.notification_text.insert(tk.END, message + '\n', color)
        self.notification_text.see(tk.END)

        lines = self.notification_text.get("1.0", tk.END).splitlines()
        if len(lines) > max_lines:
            self.notification_text.delete("1.0", f"{len(lines) - max_lines + 1}.0")

        self.notification_text.config(state='disabled')


    # def clickable_notification(self, message: str, cmd):
    #     tag = f"clickable_{random.randint(1000,9999)}"  # Unique tag in case of multiple

    #     # Make the Text widget editable temporarily
    #     self.notification_text.config(state='normal')

    #     # Insert clickable message with tag
    #     start_index = self.notification_text.index(tk.END)
    #     # self.notification_text.insert(tk.END, "🔵 Click here to retry:\n", tag)
    #     self.notification_text.insert(tk.END, message + '\n',tag)
    #     end_index = self.notification_text.index(tk.END)

    #     # Configure style and behavior
    #     self.notification_text.tag_config(tag, foreground="blue", underline=1)
    #     self.notification_text.tag_bind(tag, "<Enter>", lambda e: self.notification_text.config(cursor="hand2"))
    #     self.notification_text.tag_bind(tag, "<Leave>", lambda e: self.notification_text.config(cursor=""))
    #     self.notification_text.tag_bind(tag, "<Button-1>", lambda e: cmd())

    #     # Scroll to bottom and lock
    #     self.notification_text.see(tk.END)
    #     self.notification_text.config(state='disabled')


    def clickable_notification(self, message: str, cmd):
        self.rejection_text.config(state='normal')
        unique = f"act_{random.randint(1000,9999)}"

        # style via "link" tag; unique tag has NO color
        self.rejection_text.insert(tk.END, message + "\n", ("link", unique))

        self.rejection_text.tag_bind(unique, "<Enter>", lambda e: self.rejection_text.config(cursor="hand2"))
        self.rejection_text.tag_bind(unique, "<Leave>", lambda e: self.rejection_text.config(cursor=""))
        self.rejection_text.tag_bind(unique, "<Button-1>", lambda e: cmd())

        self.rejection_text.see(tk.END)
        self.rejection_text.config(state='disabled')

    def on_refresh_clicked(self, event=None):
        print("Refresh triggered!")  # Replace this with your actual function
        self.notification_text.insert("end", "🔄 Refresh initiated...\n")

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


        #self.DISCONNECTED.trace_add('write',self.DISCONNECTED_switch)

        self.update_system_status_style()


    def _apply_notification_theme(self):
        # choose palette
        dark = self.DISASTER_MODE.get() == 1 or self.DARK_MODE.get() == 1
        pal = {
            "bg":  "#0F1115" if dark else "white",
            "fg":  "#E6E6E6" if dark else "#000000",
            "muted": "#9AA1A9" if dark else "#6B7280",
            # ↓ Use light green in dark mode; keep blue in light mode
            "link": "#CBD1CC" if dark else "#1A73E8", ##cbd1cc 7EE787
            "blue": "#7EE787" if dark else "#1A73E8",   # remap “blue” to same green in dark
            "error": "#FF6B6B" if dark else "#B00020",
            "warn":  "#FFB86C" if dark else "#B56200",
            "ok":    "#34D399" if dark else "#1B7F3B",
            "black": "#E6E6E6" if dark else "#000000",
            "red":   "#FF6B6B" if dark else "#B00020",
            "green": "#34D399" if dark else "#1B7F3B",
        }

        for w  in [self.notification_text,self.rejection_text]:
            # safe even if disabled
            w.configure(bg=pal["bg"])

            # standard tags you might use
            w.tag_config("normal",  foreground=pal["fg"])
            w.tag_config("muted",   foreground=pal["muted"])
            w.tag_config("link",    foreground=pal["link"], underline=1)
            w.tag_config("error",   foreground=pal["error"])
            w.tag_config("warning", foreground=pal["warn"])
            w.tag_config("success", foreground=pal["ok"])

            # if you’ve already created simple color tags (e.g., "black", "blue", "red")
            for t in ("black","blue","red","green"):
                if t in w.tag_names():
                    w.tag_config(t, foreground=pal[t])

    def flashing_red(self, *args):
        print('UI, flashing red')
        if self.DISCONNECTED.get() == 1:
            if self.flashing_red_==True:
                self.root.configure(bg="red")
                self.flashing_red_=False
            else:
                self.root.configure(bg="")
                self.flashing_red_=True
        else:
            # Restore normal theme
            
            self.dark_mode_switch()

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
        self.dashboard.symbol_panel.update_treeview_row_styles()
        self._apply_notification_theme() 



    def dark_mode_switch(self,*args):

        if self.DISCONNECTED.get()!=1:
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
                self.dashboard.symbol_panel.update_treeview_row_styles()
                self._apply_notification_theme() 

    def change_theme(self, theme_name):
        self.style.theme_use(theme_name)
        self.algo_deployment.update_treeview_row_styles() # Call this when theme changes programmatically as well
        self.dashboard.symbol_panel.update_treeview_row_styles()

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


        self.show_all = tb.Button(container, text="Show All Algos", bootstyle="primary",command=self.algo_deployment.show_all)
        self.show_all.grid(row=r, column=c, padx=(0, 5)) # Adjusted padx
        c += 1


        self.only_running_btn = tb.Button(container, text="Only Running", bootstyle="primary",command=self.algo_deployment.clear_algos)
        self.only_running_btn.grid(row=r, column=c, padx=(0, 5)) # Adjusted padx
        c += 1



        self.only_running_btn = tb.Button(container, text="Only User Algo", bootstyle="primary",command=self.algo_deployment.usr_only_algo)
        self.only_running_btn.grid(row=r, column=c, padx=(0, 5)) # Adjusted padx
        c += 1

        tk.Label(container, text="Symbol Filter:").grid(row=r, column=c, padx=(5, 2), sticky="w") # Adjusted padx
        c += 1

        self.symbol_filter_entry = tb.Entry(container, width=10)
        self.symbol_filter_entry.grid(row=r, column=c, padx=(0, 5)) # Adjusted padx
        c += 1

        self.filter_btn = tb.Button(container, text="Filter", bootstyle="primary",command=self.algo_deployment.filter_by_symbol)
        self.filter_btn.grid(row=r, column=c, padx=(0, 5)) # Adjusted padx
        c += 1

        tk.Label(container, text="Algo Filter:").grid(row=r, column=c, padx=(5, 2), sticky="w") # Adjusted padx
        c += 1

        self.algo_filter_entry = tb.Entry(container, width=10)
        self.algo_filter_entry.grid(row=r, column=c, padx=(0, 5)) # Adjusted padx
        c += 1

        self.filter_btn2 = tb.Button(container, text="Filter", bootstyle="primary",command=self.algo_deployment.filter_by_algo)
        self.filter_btn2.grid(row=r, column=c, padx=(0, 10)) # Adjusted padx
        c += 1

        try:
            self.flatten_all = tb.Button(container, text="Flatten All", bootstyle="success-outline",command=self.manager.flatten_all)
            self.flatten_all.grid(row=r, column=c, padx=(0, 2)) # Adjusted padx
            c += 1
        except:
            self.flatten_all = tb.Button(container, text="Flatten All", bootstyle="success-outline")
            self.flatten_all.grid(row=r, column=c, padx=(0, 2)) # Adjusted padx
            c += 1

        try:
            self.flatten_all = tb.Button(container, text="A-Flatten All", bootstyle="success-outline",command=self.manager.aflatten_all)
            self.flatten_all.grid(row=r, column=c, padx=(0, 2)) # Adjusted padx
            c += 1
        except:
            self.flatten_all = tb.Button(container, text="A-Flatten All", bootstyle="success-outline")
            self.flatten_all.grid(row=r, column=c, padx=(0, 2)) # Adjusted padx
            c += 1

        # self.plus_25_btn = tb.Button(container, text="+ 25% to W", bootstyle="success-outline")
        # self.plus_25_btn.grid(row=r, column=c, padx=(0, 2)) # Adjusted padx
        # c += 1

        # self.minus_25_btn = tb.Button(container, text="- 25% to W", bootstyle="success-outline")
        # self.minus_25_btn.grid(row=r, column=c, padx=(0, 5)) # Adjusted padx
        # c += 1

        # self.plus_25_btnl = tb.Button(container, text="+ 25% to L", bootstyle="danger-outline")
        # self.plus_25_btnl.grid(row=r, column=c, padx=(0, 2)) # Adjusted padx
        # c += 1

        # self.minus_25_btnl = tb.Button(container, text="- 25% to L", bootstyle="danger-outline")
        # self.minus_25_btnl.grid(row=r, column=c, padx=0) # Adjusted padx (no padding on last item)



    def _on_closing(self):
        print("Closing application...")
        self.running = False
        self.root.destroy()


    def toggle_user_pannel(self, event=None):


        # self.system_panel = tb.LabelFrame(self.root, text="System", bootstyle="primary")
        # self.system_panel.place(x=10, y=10, height=350, width=340)

        # self.user_panel = tb.LabelFrame(self.root, text="User", bootstyle="info")
        # self.user_panel.place(x=10, y=365, height=880, width=340)

        if not self.user_only_mode:
            # Hide the dashboard and filter panels
            self.system_panel.place_forget()

            # Make deployment panel take more space
            #self.system_panel.place(x=10, y=10, height=self.ui.root.winfo_height() - 20)
            self.user_panel.place(x=10, y=10, height=880, width=340)
            self.user_clickable.place(x=20, y=5)
            self.user_clickable.config(text="▼ User")
            self.user_only_mode = True
        else:
            # Restore original layout
            self.system_panel.place(x=10, y=10, height=350, width=340)
            self.user_panel.place(x=10, y=365, height=880, width=340)

            self.user_clickable.place(x=20, y=360)
            self.user_clickable.config(text="▶ User")
            self.user_only_mode = False

if __name__ == '__main__':
    root = tb.Window(themename="flatly") # Start with a light theme
    root.title("GoodTrade AMS")

    screen_width = root.winfo_screenwidth()
    screen_height = root.winfo_screenheight()

    root.geometry("1870x1280")

    app = UI(root)

        # ---- demo algos (mock) ----
    class MockTP:
        def __init__(self, name, *, nbbo_only=False, algo_type="MarketMaker",
                     shares=0, unreal=0.0, realized=0.0, status="IDLE", multiplier=1.0):
            self.algo_name = name
            self.nbbo_only = nbbo_only      # used by NBBO_Mode column (toggle)
            self.algo_type = algo_type      # used by Type column (read-only)
            self.break_even=False
            self.data = {
                "current_shares": shares,   # REQUIRED by add_algo(...)
                "unreal": unreal,           # REQUIRED by add_algo(...)
                "realized": realized,       # REQUIRED by add_algo(...)
                "status": status,           # REQUIRED by add_algo(...)
                "multiplier": multiplier,   # REQUIRED by add_algo(...)
            }

        # Optional handlers your panel calls when clicking cells:
        def change_percentage(self, pct):
            self.data["unreal"] = round(self.data.get("unreal", 0.0) + pct * 100, 2)
            self.data["status"] = f"Δ {int(pct*100)}%"

        def create_clone(self):
            print(f"[MockTP] create_clone() for {self.algo_name}")

        def print_info(self):
            print(f"[MockTP] {self.algo_name} | nbbo_only={self.nbbo_only} | "
                  f"type={self.algo_type} | data={self.data}")

        def flatten_cmd(self):
            self.data["current_shares"] = 0
            self.data["status"] = "FLATTEN"

        def break_even_function(self):
            pass
    # Seed a couple of demo algos
    tp1 = MockTP(
        "GT_MM_NVDA",
        nbbo_only=True,
        algo_type="MarketMaker",
        shares=250,
        unreal=42.35,
        realized=130.10,
        status="RUNNING",
        multiplier=1.0,
    )
    tp2 = MockTP(
        "GT_RSI_SPY",
        nbbo_only=False,
        algo_type="SignalFollower",
        shares=-100,
        unreal=-15.90,
        realized=72.00,
        status="IDLE",
        multiplier=0.5,
    )

    # Insert into the deployment panel
    app.algo_deployment.add_algo(tp1)
    app.algo_deployment.add_algo(tp2)
    
    #app.SIMULATION_MODE=True
    root.protocol("WM_DELETE_WINDOW", app._on_closing)
    root.mainloop()