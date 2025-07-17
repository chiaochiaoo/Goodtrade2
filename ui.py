import os
import tkinter as tk
from tkinter import ttk
import ttkbootstrap as tb
from ttkbootstrap.constants import *
import json
# Assuming ui_authorization exists and provides an 'authorization' class
from ui_authorization import authorization
from ui_tooltips import Tooltip
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

        self.style.configure("Treeview.Heading",borderwidth=2,relief="raised")
        # The background and foreground for Heading will be managed by ttkbootstrap's themes
        self.manager = manager

        self.auth_collapsed = False

        self.init_variables()
        self.init_design_map()
        self.init_panels()

        self.algo_ui = authorization(self)

        self.init_notification_panel()
        self.init_placeholders()

        self.init_system_panel()
        self.init_filter_panel()

        # Initialize the deployment panel Treeview
        self.init_algo_deployment_panel() # This now uses the specified style

        self.root.after(500, self.simulation_add) # This will add to the deployment panel
        self.running = True # Control for update threads
        self.start_unreal_random_update_thread() # Start a general update thread

        # Ensure main dashboard placeholder is initially shown as it no longer has a Treeview
        self.performance_panel.pack_propagate(False) # Prevent shrinking

        self.dashboard_placeholder_label = tb.Label(
            self.performance_panel,
            text="Dashboard Overview Coming Soon...",
            font=("Segoe UI", 10, "italic"),
            bootstyle="secondary"
        )
        self.dashboard_placeholder_label.pack(anchor="center", expand=True)


    def init_variables(self):
        self.is_sort_running = False
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
        self.HALT_NOTIFICATION = tk.IntVar(value=0)

        # Headers: Added "Time Added" beside "Algo"
        self.headers = ["#", "Algo", "Time Added", "Status", "Unreal", "Real", "+25", "-25", "+50", "-50", "Flatten", "A-Flat"]
        self.clickable_cols = ["+25", "-25", "+50", "-50", "Flatten", "A-Flat"]
        self.deployment_algo_data_by_item_id = {} # Only for the deployment Treeview
        self.current_algo_id = 0 # Used to generate unique IDs for the '#' column
        self.current_cursor_is_hand = False
        self.tooltip = None # A single tooltip instance, reused for the deployment treeview


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

        self.auth_panel = tb.LabelFrame(self.root, text="Authorization", bootstyle="info")
        self.auth_panel.place(x=10, y=365, height=880, width=340)

        # Main Dashboard - Now just a placeholder panel
        self.performance_panel = tb.LabelFrame(self.root, text="Dashboard", bootstyle="success")
        self.performance_panel.place(x=360, y=10, height=270, width=900)

        self.filter_panel = tb.LabelFrame(self.root, text="Algorithms Management", bootstyle="warning")
        self.filter_panel.place(x=360, y=280, height=80, width=900)

        # Deployment Panel - This will contain the only Treeview
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
        else:
            if self.DARK_MODE.get() == 1:
                self.style.theme_use('darkly')
            else:
                self.style.theme_use('flatly')
        # Call the new function to update Treeview row styles after theme change
        self.update_treeview_row_styles()


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

        # Crucially, call this function to update all Treeview row styles
        # (including foreground and specific row tag colors) based on the new theme.
        self.update_treeview_row_styles()


    def update_system_status_style(self, *args):
        value = self.SYSTEM_STATUS.get()
        if self.system_status_label:
            if value.upper() == "ERROR":
                self.system_status_label.configure(bootstyle="inverse-danger")
            else:
                self.system_status_label.configure(bootstyle="inverse-success")

    def change_theme(self, theme_name):
        self.style.theme_use(theme_name)
        self.update_treeview_row_styles() # Call this when theme changes programmatically as well

    def init_notification_panel(self):
        self.notification_text = tb.Text(self.notification_panel, wrap="word", font=("Segoe UI", 10), bg="white")
        scrollbar = tb.Scrollbar(self.notification_panel, command=self.notification_text.yview)
        self.notification_text.configure(yscrollcommand=scrollbar.set)
        scrollbar.pack(side="right", fill="y")
        self.notification_text.pack(fill="both", expand=True, padx=10, pady=10)
        self.notification_text.insert("end", "🟠 System starting...\n")

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

    def generate_random_algo(self):
        """Generates random algorithm data including a position string and a time added."""
        names = ["AAPL", "GOOG", "TSLA", "MSFT", "NVDA", "AMZN", "META", "NFLX", "INTC"]
        statuses = ["RUNNING", "DEPLOYED", "REJECTED", "CANCELED", "ERROR"]

        name = random.choice(names)
        status = random.choice(statuses)
        position = f"{name}.NQ:{random.randint(1, 20)}" # Position data is still generated
        unreal = round(random.uniform(-50.0, 150.0), 2)
        real = round(random.uniform(-30.0, 30.0), 2)

        # Increment and assign a unique ID
        self.current_algo_id += 1
        algo_id = self.current_algo_id

        # Get current time in HH:MM:SS format and store original datetime object for sorting
        time_added_dt = datetime.now()
        time_added_str = time_added_dt.strftime("%H:%M:%S") # Changed to HH:MM:SS

        return {
            "ID": algo_id, # Fixed ID
            "Name": tk.StringVar(value=name),
            "Time Added": tk.StringVar(value=time_added_str), # Display string for time
            "Time Added_dt": time_added_dt, # Original datetime object for sorting
            "Position": tk.StringVar(value=position), # Store Position as a StringVar
            "Status": tk.StringVar(value=status),
            "Unrealized": tk.DoubleVar(value=unreal),
            "Realized": tk.DoubleVar(value=real),
        }

    def start_unreal_random_update_thread(self):
        def updater():
            while self.running: # Use self.running for graceful shutdown
                try:
                    # Update deployment Treeview (if it exists and has items)
                    if hasattr(self, 'deployment_tree') and self.deployment_tree.get_children():
                        for item_id in random.sample(self.deployment_tree.get_children(), k=min(len(self.deployment_tree.get_children()), 3)):
                            data_vars = self.deployment_algo_data_by_item_id[item_id]

                            # Generate a random change between -10 and 10, excluding 0
                            change = random.randint(1, 10)
                            if random.random() < 0.5: # 50% chance to be negative
                                change *= -1

                            # Update Unrealized value: add/subtract change
                            current_unreal = data_vars["Unrealized"].get()
                            data_vars["Unrealized"].set(round(current_unreal + change, 2))

                            # Realized value remains as before (random between -30 and 30)
                            data_vars["Realized"].set(round(random.uniform(-30.0, 30.0), 2))

                            self.root.after(0, self._update_treeview_row, self.deployment_tree, item_id, data_vars)

                except Exception as e:
                    print(f"[Thread Update Error] {e}")
                time.sleep(0.1) # Update more frequently

        threading.Thread(target=updater, daemon=True).start()

    def sort_column(self, col, reverse, tree_widget):
            """Sorts a Treeview column."""
            try:
                items = []
                for k in tree_widget.get_children():
                    data_vars = self.deployment_algo_data_by_item_id.get(k)
                    value_to_sort = None # Initialize

                    if data_vars:
                        if col == "#":
                            value_to_sort = data_vars.get("ID", 0) # Use the fixed ID
                        elif col == "Algo":
                            value_to_sort = data_vars["Name"].get()
                        elif col == "Time Added":
                            value_to_sort = data_vars.get("Time Added_dt") # Sort by the datetime object
                        elif col == "Unreal": # Specific handling for "Unreal"
                            value_to_sort = data_vars["Unrealized"].get() # Access "Unrealized" and get its float value
                        elif col == "Real": # Specific handling for "Real"
                            value_to_sort = data_vars["Realized"].get() # Access "Realized" and get its float value
                        elif col == "Status": # Specific handling for "Status"
                            value_to_sort = data_vars["Status"].get() # Get string value
                        else:
                            # For static action buttons (+25, -25, etc.), sort by their text
                            value_to_sort = tree_widget.set(k, col)
                    else:
                        # Fallback if data_vars is missing for some reason, sort by displayed text
                        value_str = tree_widget.set(k, col)
                        try:
                            if col in ["#", "Unreal", "Real"]: # These should still be convertible to float for display sorting
                                value_to_sort = float(value_str)
                            else:
                                value_to_sort = value_str
                        except ValueError:
                            value_to_sort = value_str # Keep as string if conversion fails (e.g., empty string)


                    items.append((value_to_sort, k))

                # Filter out items where value_to_sort is None if necessary (e.g., if data is truly missing)
                items = [item for item in items if item[0] is not None]

                items.sort(key=lambda x: x[0], reverse=reverse)

                for index, (_, k) in enumerate(items):
                    tree_widget.move(k, '', index)

                tree_widget.heading(col, command=lambda: self.sort_column(col, not reverse, tree_widget))

            except Exception as e:
                print(f"[Sort Error] {e}")

    def on_treeview_click(self, event):
        # Only the deployment_tree exists
        clicked_tree = self.deployment_tree
        data_source = self.deployment_algo_data_by_item_id

        item = clicked_tree.identify_row(event.y)
        col = clicked_tree.identify_column(event.x)

        if not item or not col:
            # If clicked outside a row or column, clear selection and do nothing else
            clicked_tree.selection_remove(clicked_tree.selection())
            return

        # Get currently selected items
        selected_items = clicked_tree.selection()

        # Determine if the clicked row is already selected
        is_clicked_row_selected = item in selected_items

        # Handle row selection/deselection first
        if event.state & 0x4: # Check for Ctrl key (multi-select)
            if is_clicked_row_selected:
                clicked_tree.selection_remove(item)
            else:
                clicked_tree.selection_add(item)
        else: # Single select behavior
            if not is_clicked_row_selected:
                clicked_tree.selection_remove(selected_items) # Clear previous selection
                clicked_tree.selection_add(item)
            # If clicked on an already selected row, we don't change selection unless it's a clickable action.
            # We'll rely on the 'if clicked_tree.selection():' check below for actions.


        # Now, check for clickable column logic ONLY if there is an active selection
        # and the clicked row is part of the selection.
        # This ensures actions only happen on explicitly selected rows.
        if clicked_tree.selection() and item in clicked_tree.selection(): # Ensure *this* clicked item is selected
            col_index = int(col[1:]) - 1
            col_name = self.headers[col_index]

            if col_name in self.clickable_cols:
                # Retrieve the original Tkinter variables for the clicked item
                algo_data = data_source.get(item)
                if algo_data:
                    name = algo_data["Name"].get()
                    print(f"[{col_name}] clicked for {name} on {clicked_tree.winfo_name()}")

                    if col_name == "+25":
                        algo_data["Unrealized"].set(algo_data["Unrealized"].get() + 25)
                    elif col_name == "-25":
                        algo_data["Unrealized"].set(algo_data["Unrealized"].get() - 25)
                    elif col_name == "+50":
                        algo_data["Unrealized"].set(algo_data["Unrealized"].get() + 50)
                    elif col_name == "-50":
                        algo_data["Unrealized"].set(algo_data["Unrealized"].get() - 50)
                    elif col_name == "Flatten":
                        print(f"Flattening position for {name}")
                        algo_data["Position"].set("")
                        algo_data["Unrealized"].set(0.0)
                        algo_data["Realized"].set(0.0)
                        algo_data["Status"].set("FLATTENED")
                    elif col_name == "A-Flat":
                        print(f"Applying A-Flat for {name}")
                        algo_data["Unrealized"].set(0.0)
                        algo_data["Status"].set("A-FLAT")

                    self._update_treeview_row(clicked_tree, item, algo_data)
        else:
            # If no row is selected, or clicked on an unselected row (and not multi-select),
            # ensure nothing happens for action columns.
            pass


    def on_treeview_motion(self, event):
        # Only the deployment_tree exists
        motion_tree = self.deployment_tree
        data_source = self.deployment_algo_data_by_item_id

        item = motion_tree.identify_row(event.y)
        col = motion_tree.identify_column(event.x)

        # Always hide existing tooltip before potentially showing a new one
        if self.tooltip and self.tooltip.tip_window:
            self.tooltip.hidetip()

        if item and col:
            idx = int(col[1:]) - 1
            col_name = self.headers[idx]

            # Logic for TOOLTIP (for "Algo" column) - Independent of selection
            if col_name == "Algo":
                algo_data = data_source.get(item)
                if algo_data and "Position" in algo_data:
                    full_position_text = algo_data["Position"].get()
                    if not self.tooltip:
                        self.tooltip = Tooltip(motion_tree)
                    self.tooltip.showtip(full_position_text, item, col)
            # Else (if not "Algo" column), the tooltip will remain hidden due to the initial hidetip()

            # Logic for CURSOR (for clickable columns) - Dependent on selection
            if col_name in self.clickable_cols and item in motion_tree.selection():
                motion_tree.config(cursor="hand2")
                self.current_cursor_is_hand = True
            else:
                motion_tree.config(cursor="")
                self.current_cursor_is_hand = False
        else:
            # If not hovering over any item/column, reset cursor and hide tooltip
            motion_tree.config(cursor="")
            self.current_cursor_is_hand = False
            # Tooltip is already handled by the initial hidetip() at the start of the function

    def on_treeview_leave(self, event):
        # Only the deployment_tree exists
        left_tree = self.deployment_tree
        left_tree.config(cursor="")
        self.current_cursor_is_hand = False
        if self.tooltip:
            self.tooltip.hidetip()

    def _on_closing(self):
        print("Closing application...")
        self.running = False
        self.root.destroy()

    # --- Deployment Treeview Initialization (only one Treeview now) ---
    def init_algo_deployment_panel(self): # Renamed from init_algo_deployment_panel2
        self.sort_reverse_unreal = False
        self.deployment_only_mode = False

        self.deployment_clickable = tb.Label(
            self.root,
            text="▶ Algorithms Deployment",
            font=("Segoe UI", 9),
            background="",
            foreground="#2780e3",
            cursor="hand2"
        )
        self.deployment_clickable.place(x=370, y=360)

        self.deployment_clickable.bind("<Button-1>", self.toggle_deployment_panel)

        deployment_tree_container = tb.Frame(self.deployment_panel)
        deployment_tree_container.pack(fill="both", expand=True, padx=5, pady=5) # Standardized padx/pady

        deployment_scroll_y = tb.Scrollbar(deployment_tree_container)
        deployment_scroll_y.pack(side="right", fill="y")
        deployment_scroll_x = tb.Scrollbar(deployment_tree_container, orient="horizontal")
        deployment_scroll_x.pack(side="bottom", fill="x")

        self.deployment_tree = tb.Treeview(deployment_tree_container,
            columns=self.headers, # Use the updated headers list
            show="headings",
            yscrollcommand=deployment_scroll_y.set,
            xscrollcommand=deployment_scroll_x.set,
            bootstyle="Treeview" # This applies the configured "Treeview" style
        )
        self.deployment_tree.pack(fill="both", expand=True)

        deployment_scroll_y.config(command=self.deployment_tree.yview)
        deployment_scroll_x.config(command=self.deployment_tree.xview)

        # Configure columns and headings for the deployment Treeview
        for col_name in self.headers:
            self.deployment_tree.heading(col_name, text=col_name, anchor="center",
                                         command=lambda c=col_name: self.sort_column(c, False, self.deployment_tree))
            # Default for all columns unless explicitly overridden below
            self.deployment_tree.column(col_name, anchor="center", width=80, stretch=False, minwidth=50)


        # Specific column widths
        self.deployment_tree.column("#", width=60, stretch=False, minwidth=40)
        self.deployment_tree.column("Algo", width=120, anchor="w", stretch=False, minwidth=80)
        self.deployment_tree.column("Time Added", width=90, anchor="center", stretch=False, minwidth=70) # Increased width for HH:MM:SS
        self.deployment_tree.column("Status", width=100, anchor="center", stretch=False, minwidth=80)
        # Position column is removed, so subsequent indices shift
        self.deployment_tree.column("Unreal", anchor="e", width=90, stretch=False, minwidth=60)
        self.deployment_tree.column("Real", anchor="e", width=90, stretch=False, minwidth=60)
        # Action buttons (these remain in their relative order)
        self.deployment_tree.column("+25", width=60, stretch=False, minwidth=50)
        self.deployment_tree.column("-25", width=60, stretch=False, minwidth=50)
        self.deployment_tree.column("+50", width=60, stretch=False, minwidth=50)
        self.deployment_tree.column("-50", width=60, stretch=False, minwidth=50)
        self.deployment_tree.column("Flatten", width=70, stretch=False, minwidth=60)
        self.deployment_tree.column("A-Flat", width=70, stretch=False, minwidth=60)


        # Configure row tags with original light backgrounds. Foreground will be set by update_treeview_row_styles.
        self.deployment_tree.tag_configure("row_green", background="#e6ffe6")
        self.deployment_tree.tag_configure("row_red", background="#ffe6e6")
        # Initialize a tag for default text color that will be dynamically set
        self.deployment_tree.tag_configure("default_text") # No background here, just for foreground


        self.deployment_tree.bind("<Button-1>", self.on_treeview_click)
        self.deployment_tree.bind("<Motion>", self.on_treeview_motion)
        self.deployment_tree.bind("<Leave>", self.on_treeview_leave)

        self.populate_deployment_treeview(10) # Populate with some initial data
        # Ensure initial styling is applied right after population
        self.update_treeview_row_styles()


    def populate_deployment_treeview(self, count=5):
        """Populates the deployment treeview with initial data."""
        for _ in range(count):
            self.add_algo_to_deployment_treeview()

    def add_algo_to_deployment_treeview(self):
        """
        Adds a new randomly generated algorithm to the deployment panel's treeview.
        """
        item_id = self.deployment_tree.insert("", "end")
        new_data = self.generate_random_algo()
        self.deployment_algo_data_by_item_id[item_id] = new_data
        self._update_treeview_row(self.deployment_tree, item_id, new_data)
        print(f"Added new algo {new_data['ID']} at {new_data['Time Added'].get()}")
        # self.deployment_tree.yview_moveto(1) # Auto-scroll is disabled

    def _update_treeview_row(self, tree_widget, item_id, data_vars):
        """
        Updates a specific row in the given Treeview widget.
        Assumes data_vars contains tk.StringVar/DoubleVar.
        Position is stored but not displayed in a column.
        """
        # Retrieve the fixed ID for the '#' column
        algo_fixed_id = data_vars.get("ID", "") # Get the fixed ID

        name = data_vars["Name"].get()
        time_added = data_vars["Time Added"].get() # Get the formatted time string
        status = data_vars["Status"].get()
        unreal = data_vars["Unrealized"].get()
        real = data_vars["Realized"].get()

        # The 'Position' value is no longer put directly into the values list for a column
        values = [
            algo_fixed_id,                   # Column 0: Fixed ID
            name,                            # Column 1: Algo
            time_added,                      # Column 2: Time Added
            status,                          # Column 3: Status
            f"{unreal:.2f}",                 # Column 4: Unreal (shifted left)
            f"{real:.2f}",                   # Column 5: Real (shifted left)
            "+25", "-25", "+50", "-50", "Flatten", "A-Flat" # Columns 6-11
        ]

        # Determine tags based on Unrealized value
        tags_to_apply = []
        if unreal >= 0:
            tags_to_apply.append("row_green")
        else:
            tags_to_apply.append("row_red")

        # Always ensure the default_text tag is applied for foreground control
        tags_to_apply.append("default_text")

        tree_widget.item(item_id, values=values, tags=tuple(tags_to_apply))


    def update_treeview_row_styles(self):
        """
        Configures and applies Treeview row styles based on the current theme.
        This function is now included as part of your UI class.
        """
        # Determine foreground colors based on current theme
        if self.DARK_MODE.get() == 1 or self.DISASTER_MODE.get() == 1:
            normal_text_color = "white" # For dark themes (darkly, vapor)
            # Background colors for row tags in dark mode
            green_bg = "#2a662a"  # Darker green for dark mode
            red_bg = "#802b2b"    # Darker red for dark mode
        else:
            normal_text_color = "black" # For light themes (flatly)
            # Background colors for row tags in light mode (your original colors)
            green_bg = "#e6ffe6"  # Original light green
            red_bg = "#ffe6e6"    # Original light red

        # Reconfigure the default_text tag's foreground (this affects all cells with this tag)
        self.deployment_tree.tag_configure("default_text", foreground=normal_text_color)

        # Apply the determined background colors to the row tags
        self.deployment_tree.tag_configure("row_green", background=green_bg)
        self.deployment_tree.tag_configure("row_red", background=red_bg)

        # Iterate through all items and force a re-render of their style
        for item_id in self.deployment_tree.get_children():
            data_vars = self.deployment_algo_data_by_item_id.get(item_id)
            if data_vars:
                self._update_treeview_row(self.deployment_tree, item_id, data_vars) # Re-applies tags


    def simulation_add(self):
        """
        Simulates adding new algorithms. It will add to the deployment panel's Treeview.
        """
        if self.running:
            self.add_algo_to_deployment_treeview()
            self.root.after(2000, self.simulation_add)

    def toggle_deployment_panel(self, event=None):
        """Toggles the visibility and layout of the deployment panel."""
        if not self.deployment_only_mode:
            # Hide the dashboard and filter panels
            self.performance_panel.place_forget()
            self.filter_panel.place_forget()

            # Make deployment panel take more space
            self.deployment_panel.place(x=360, y=10, height=self.root.winfo_height() - 20, width=900)
            self.deployment_clickable.place(x=370, y=5)
            self.deployment_clickable.config(text="▼ Algorithms Deployment")
            self.deployment_only_mode = True
        else:
            # Restore original layout
            self.performance_panel.place(x=360, y=10, height=270, width=900)
            self.filter_panel.place(x=360, y=280, height=80, width=900)
            self.deployment_panel.place(x=360, y=365, height=880, width=900)

            self.deployment_clickable.place(x=370, y=360)
            self.deployment_clickable.config(text="▶ Algorithms Deployment")
            self.deployment_only_mode = False


if __name__ == '__main__':
    root = tb.Window(themename="flatly") # Start with a light theme
    root.title("GoodTrade AMS")

    screen_width = root.winfo_screenwidth()
    screen_height = root.winfo_screenheight()

    root.geometry("1570x1280")

    app = UI(root)
    root.protocol("WM_DELETE_WINDOW", app._on_closing)
    root.mainloop()