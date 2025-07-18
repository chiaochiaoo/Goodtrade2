import os
import json
import tkinter as tk
import ttkbootstrap as tb
from ttkbootstrap.constants import *
import random
from datetime import datetime
from UI.ui_tooltips import Tooltip
import threading
import time

ACTIVE = 0
MULTIPLIER = 1
PASSIVE = 2
DESCRIPTION = 3

class Algo_Deployment_Panel:
    def __init__(self, ui):
        self.ui = ui

        # Headers: Added "Time Added" beside "Algo"
        self.headers = ["#", "Algo", "Time Added", "Status", "Unreal", "Real", "+25", "-25", "+50", "-50", "Flatten", "A-Flat"]
        self.clickable_cols = ["+25", "-25", "+50", "-50", "Flatten", "A-Flat"]

        self.deployment_algo_data_by_item_id = {} # Only for the deployment Treeview
        
        self.current_algo_id = 0 # Used to generate unique IDs for the '#' column
        self.current_cursor_is_hand = False
        self.tooltip = None # A single tooltip instance, reused for the deployment treeview

        self.init_algo_deployment_panel()
        self.populate_deployment_treeview(10)

        self.start_unreal_random_update_thread()

    def init_algo_deployment_panel(self): # Renamed from init_algo_deployment_panel2
        self.sort_reverse_unreal = False
        self.deployment_only_mode = False

        self.deployment_clickable = tb.Label(
            self.ui.root,
            text="▶ Algorithms Deployment",
            font=("Segoe UI", 9),
            background="",
            foreground="#2780e3",
            cursor="hand2"
        )
        self.deployment_clickable.place(x=370, y=360)

        self.deployment_clickable.bind("<Button-1>", self.toggle_deployment_panel)

        deployment_tree_container = tb.Frame(self.ui.deployment_panel)
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
        self.deployment_tree.column("Algo", width=160, anchor="w", stretch=False, minwidth=160)
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

        # Populate with some initial data
        # Ensure initial styling is applied right after population
        self.update_treeview_row_styles()

    def toggle_deployment_panel(self, event=None):
        """Toggles the visibility and layout of the deployment panel."""
        if not self.deployment_only_mode:
            # Hide the dashboard and filter panels
            self.ui.deployment_panel.place_forget()
            self.ui.filter_panel.place_forget()

            # Make deployment panel take more space
            self.ui.deployment_panel.place(x=360, y=10, height=self.ui.root.winfo_height() - 20, width=900)
            self.deployment_clickable.place(x=370, y=5)
            self.deployment_clickable.config(text="▼ Algorithms Deployment")
            self.deployment_only_mode = True
        else:
            # Restore original layout
            self.ui.deployment_panel.place(x=360, y=10, height=270, width=900)
            self.ui.filter_panel.place(x=360, y=280, height=80, width=900)
            self.ui.deployment_panel.place(x=360, y=365, height=880, width=900)

            self.deployment_clickable.place(x=370, y=360)
            self.deployment_clickable.config(text="▶ Algorithms Deployment")
            self.deployment_only_mode = False
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
            while self.ui.running: # Use self.running for graceful shutdown
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

                            self.ui.root.after(0, self._update_treeview_row, self.deployment_tree, item_id, data_vars)

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


    # --- Deployment Treeview Initialization (only one Treeview now) ---


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
        #print(f"Added new algo {new_data['ID']} at {new_data['Time Added'].get()}")
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
        if self.ui.DARK_MODE.get() == 1 or self.ui.DISASTER_MODE.get() == 1:
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
            self.ui.root.after(2000, self.simulation_add)