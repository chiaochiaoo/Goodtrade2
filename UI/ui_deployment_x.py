import os
import json
import tkinter as tk
import ttkbootstrap as tb
from ttkbootstrap.constants import *
import random
from datetime import datetime
try:
	from UI.ui_tooltips import Tooltip
except:
	from ui_tooltips import Tooltip
import threading
import time

ACTIVE = 0
MULTIPLIER = 1
PASSIVE = 2
DESCRIPTION = 3

IDLE = 'IDLE'
ORDERING = 'ORDERING'
RUNNING = 'RUNNING'
FLATTENING = ' FLATTENING'
DONE = 'DONE'
REJECTED = 'REJECTED'



class Algo_Deployment_Panel:
	def __init__(self, ui):
		self.ui = ui
		style = tb.Style()
		style.map("Treeview",
		          background=[("selected", "#FFD966")],
		          foreground=[("selected", "black")])
		# Headers: Added "Time Added" beside "Algo"
		self.headers = ["#","Time Added", "Algo",  "Status","Positions", "Unreal", "Real", "+25", "-25", "+50", "-50", "Flatten", "A-Flat"]
		self.clickable_cols = [ "Algo", "Status", "+25", "-25", "+50", "-50", "Flatten", "A-Flat"]
		self.headers = [
			"#", "Time Added", "Algo", "Type", "Status", "Positions",
			"Unreal", "Real", "BREV","NBBO", "+25", "-25", "Flatten", "A-Flat"
		]

		# CHANGED (removed '+50','-50', added 'NBBO'; 'Type' is NOT clickable)
		self.clickable_cols = ["Algo", "Status", "BREV","NBBO", "+25", "-25", "Flatten", "A-Flat"]

		self.STATUS_SEQUENCE = [IDLE, ORDERING, RUNNING, FLATTENING, DONE, REJECTED]
		self.algo_ids = {}
		self.deployment_algo_data_by_item_id = {} # Only for the deployment Treeview
		#self.tradingplans = {}
		
		self.current_algo_id = 0 # Used to generate unique IDs for the '#' column
		self.current_cursor_is_hand = False
		self.tooltip = None # A single tooltip instance, reused for the deployment treeview


		self.last_sort_column = 'Unreal'
		self.last_sort_reverse = False

		self.hover_lock = False


		self.auto_clear_active = False

		self.init_algo_deployment_panel()

		self.status_cycle_idx = 0

		self.auto_sorting = False
		self.start_auto_sorting()

		if self.ui.SIMULATION_MODE:
			self.populate_deployment_treeview(1500)

			self.start_unreal_random_update_thread()

		# self.deployment_tree.tag_configure("row_red", background="#ffe6e6")
		# # Initialize a tag for custom highlighting
		#self.deployment_tree.tag_configure("highlight_style", background="#73A2D7", foreground="white") # <-- NEW HIGHLIGHT STYLE
		# # Initialize a tag for default text color that will be dynamically set
		self.deployment_tree.tag_configure(
			"highlight_style",
			background="#FFD966",   # soft yellow
			foreground="black"
		)

		self.current_highlighted_item = None

	def init_algo_deployment_panel(self): # Renamed from init_algo_deployment_panel2
		self.sort_reverse_unreal = False
		self.deployment_only_mode = False
		self.deployment_only_mode2 = False


		self.deployment_clickablex = tb.Label(
			self.ui.root,
			text="▶ Dashboard",
			font=("Segoe UI", 9),
			background="",
			foreground="#2780e3",
			cursor="hand2"
		)
		self.deployment_clickablex.place(x=370, y=10)

		self.deployment_clickablex.bind("<Button-1>", self.toggle_deployment_panel222)

		self.deployment_clickable = tb.Label(
			self.ui.root,
			text="▶ Algorithms Deployment",
			font=("Segoe UI", 9),
			background="",
			foreground="#2780e3",
			cursor="hand2"
		)
		self.deployment_clickable.place(x=370, y=360)

		self.deployment_clickable.bind("<Button-1>", self.toggle_deployment_panel222)

		deployment_tree_container = tb.Frame(self.ui.deployment_panel)
		deployment_tree_container.pack(fill="both", expand=True, padx=5, pady=5) # Standardized padx/pady

		deployment_scroll_y = tb.Scrollbar(deployment_tree_container)
		deployment_scroll_y.pack(side="right", fill="y")
		deployment_scroll_x = tb.Scrollbar(deployment_tree_container, orient="horizontal")
		deployment_scroll_x.pack(side="bottom", fill="x")

		self.deployment_tree = tb.Treeview(
			deployment_tree_container,
			columns=self.headers,
			show="headings",
			yscrollcommand=deployment_scroll_y.set,
			xscrollcommand=deployment_scroll_x.set,
			bootstyle="Treeview",
			selectmode="extended"  # <-- Add this line
		)
		self.deployment_tree.pack(fill="both", expand=True)

		self.deployment_tree.tag_configure(
			"highlight_style",
			background="#FFD966",
			foreground="black"
		)

		deployment_scroll_y.config(command=self.deployment_tree.yview)
		deployment_scroll_x.config(command=self.deployment_tree.xview)

		# Configure columns and headings for the deployment Treeview
		for col_name in self.headers:
			self.deployment_tree.heading(col_name, text=col_name, anchor="center",
										 command=lambda c=col_name: self.sort_column(c, False, self.deployment_tree))
			# Default for all columns unless explicitly overridden below
			self.deployment_tree.column(col_name, anchor="center", width=80, stretch=False, minwidth=50)


		# Specific column widths
		self.deployment_tree.column("#", width=30, stretch=False, minwidth=30)
		self.deployment_tree.column("Time Added", width=90, anchor="center", stretch=False, minwidth=70)
		self.deployment_tree.column("Algo", width=180, anchor="w", stretch=False, minwidth=180)

		# NEW
		self.deployment_tree.column("Type", width=60, anchor="center", stretch=False, minwidth=60)

		self.deployment_tree.column("Status", width=100, anchor="center", stretch=False, minwidth=80)
		self.deployment_tree.column("Positions", width=200, anchor="center", stretch=False, minwidth=80)
		self.deployment_tree.column("Unreal", anchor="e", width=80, stretch=False, minwidth=80)
		self.deployment_tree.column("Real", anchor="e", width=80, stretch=False, minwidth=80)

		# NEW (replaces +50/-50)

		self.deployment_tree.column("BREV", width=50, anchor="center", stretch=False, minwidth=50)

		self.deployment_tree.column("NBBO", width=50, anchor="center", stretch=False, minwidth=50)

		self.deployment_tree.column("+25", width=50, stretch=False, minwidth=50)
		self.deployment_tree.column("-25", width=50, stretch=False, minwidth=50)
		self.deployment_tree.column("Flatten", width=70, stretch=False, minwidth=60)
		self.deployment_tree.column("A-Flat", width=70, stretch=False, minwidth=60)

		# Configure row tags with original light backgrounds. Foreground will be set by update_treeview_row_styles.
		self.deployment_tree.tag_configure("row_green", background="#e6ffe6")
		self.deployment_tree.tag_configure("row_red", background="#ffe6e6")
		# Initialize a tag for default text color that will be dynamically set
		self.deployment_tree.tag_configure("default_text") # No background here, just for foreground



		# self.deployment_tree.bind("<Button-1>", self._on_single_click_block_select)  # block selection
		# self.deployment_tree.bind("<Double-1>", self.on_treeview_activate)           # actions on double-click
		# self.deployment_tree.bind("<Motion>", self.on_treeview_motion)
		# self.deployment_tree.bind("<Leave>", self.on_treeview_leave)


		self.deployment_tree.bind("<Button-1>", self.on_treeview_click)   # NEW
		self.deployment_tree.bind("<Motion>", self.on_treeview_motion)
		self.deployment_tree.bind("<Leave>", self.on_treeview_leave)
		self.update_treeview_row_styles()


	# def on_treeview_click(self, event):
	# 	"""
	# 	Single-click handler that (1) lets header clicks behave normally (for sorting),
	# 	(2) triggers the action if the clicked column is in `clickable_cols`,
	# 	and (3) blocks row selection to keep the UI steady.
	# 	"""
	# 	tree = self.deployment_tree

	# 	# Let header/separator clicks pass through (so your column sort & resize still work)
	# 	region = tree.identify_region(event.x, event.y)
	# 	if region in ("heading", "separator"):
	# 		return  # don't block; header command handles sorting

	# 	item_id = tree.identify_row(event.y)
	# 	col = tree.identify_column(event.x)

	# 	# Always block the default selection behavior for body clicks
	# 	# (keeps the "no selection" UX you had)
	# 	result = "break"

	# 	if not item_id or not col:
	# 		return result

	# 	col_index = int(col[1:]) - 1
	# 	# Guard just in case
	# 	if not (0 <= col_index < len(self.headers)):
	# 		return result

	# 	col_name = self.headers[col_index]
	# 	if col_name not in self.clickable_cols:
	# 		return result

	# 	algo_data = self.deployment_algo_data_by_item_id.get(item_id)
	# 	if not algo_data:
	# 		return result

	# 	tp = algo_data['tp']

	# 	# Same actions as before (moved from double-click)
	# 	if col_name == "+25":
	# 		tp.change_percentage(0.25)
	# 	elif col_name == "-25":
	# 		tp.change_percentage(-0.25)
	# 	elif col_name == "Algo":
	# 		tp.create_clone()
	# 	elif col_name == "Status":
	# 		tp.print_info()
	# 	elif col_name == "Flatten":
	# 		tp.flatten_cmd()
	# 	elif col_name == "A-Flat":
	# 		tp.a_flatten_cmd()
	# 	elif col_name == "NBBO":
	# 		current = bool(getattr(tp, "nbbo_only", False))
	# 		setattr(tp, "nbbo_only", not current)
	# 		algo_data["NBBO"] = "ON" if tp.nbbo_only else "OFF"
	# 	elif col_name == "BREV":
	# 		algo_data["BREV"] = "ON" if getattr(tp, "break_even", False) else "OFF"
	# 		tp.break_even_function()

	# 	self._update_treeview_row(tree, item_id, algo_data)
	# 	return result


	# def on_treeview_click(self, event):
	# 	"""
	# 	Handles single-click:
	# 	1. Highlights the row.
	# 	2. If the row was already highlighted AND a clickable column is hit, triggers the action.
	# 	3. Always prevents the default Treeview selection.
	# 	"""
	# 	tree = self.deployment_tree
		
	# 	# 1. Let header/separator clicks pass through (for sorting & resizing)
	# 	region = tree.identify_region(event.x, event.y)
	# 	if region in ("heading", "separator"):
	# 		return  # don't block; header command handles sorting

	# 	item_id = tree.identify_row(event.y)
	# 	col = tree.identify_column(event.x)

	# 	# Always block the default Treeview selection behavior
	# 	result = "break"

	# 	if not item_id or not col:
	# 		return result

	# 	col_index = int(col[1:]) - 1
	# 	if not (0 <= col_index < len(self.headers)):
	# 		return result
		
	# 	col_name = self.headers[col_index]
	# 	algo_data = self.deployment_algo_data_by_item_id.get(item_id)

	# 	# --- Highlight/Selection Logic ---

	# 	# Check if the clicked row is ALREADY the highlighted row
	# 	was_already_highlighted = (item_id == self.current_highlighted_item)

	# 	# 1. Clear previous highlight (if any)
	# 	if self.current_highlighted_item:
	# 		tags = tree.item(self.current_highlighted_item, 'tags')
	# 		new_tags = [t for t in tags if t != "highlight_style"]
	# 		tree.item(self.current_highlighted_item, tags=tuple(new_tags))

	# 	# 2. Update and apply new highlight
	# 	if item_id:
	# 		# Get existing tags and add the highlight tag
	# 		tags = list(tree.item(item_id, 'tags'))
	# 		if "highlight_style" not in tags:
	# 			tags.append("highlight_style")
	# 		tree.item(item_id, tags=tuple(tags))
	# 		self.current_highlighted_item = item_id
	# 	else:
	# 		self.current_highlighted_item = None # Nothing highlighted

	# 	# --- Action Logic (Only on second click on clickable column) ---

	# 	# Only perform the action if:
	# 	# 1. The click was on a clickable column
	# 	# 2. The clicked row was ALREADY highlighted before this click (i.e., this is the second click)
	# 	if was_already_highlighted and col_name in self.clickable_cols and algo_data:

	# 		tp = algo_data['tp']

	# 		# NOTE: Your original logic for the action block
	# 		if col_name == "+25":
	# 			tp.change_percentage(0.25)
	# 		elif col_name == "-25":
	# 			tp.change_percentage(-0.25)
	# 		elif col_name == "Algo":
	# 			tp.create_clone()
	# 		elif col_name == "Status":
	# 			tp.print_info()
	# 		elif col_name == "Flatten":
	# 			tp.flatten_cmd()
	# 		elif col_name == "A-Flat":
	# 			tp.a_flatten_cmd()
	# 		elif col_name == "NBBO":
	# 			current = bool(getattr(tp, "nbbo_only", False))
	# 			setattr(tp, "nbbo_only", not current)
	# 			algo_data["NBBO"] = "ON" if tp.nbbo_only else "OFF"
	# 		elif col_name == "BREV":
	# 			algo_data["BREV"] = "ON" if getattr(tp, "break_even", False) else "OFF"
	# 			tp.break_even_function()

	# 		# Update the row after action
	# 		self._update_treeview_row(tree, item_id, algo_data)
			
	# 		# Optional: You might want to remove the highlight after action, or keep it.
	# 		# Keeping it makes a triple-click unnecessary for repeat actions.
	# 		# If you want to un-highlight, add: self.current_highlighted_item = None

	# 	return result

	def on_treeview_click(self, event):
		tree = self.deployment_tree
		item_id = tree.identify_row(event.y)
		col = tree.identify_column(event.x)
		if not item_id or not col:
			return

		# If user is doing multi-select, let Tk handle it and do nothing.
		SHIFT_MASK = 0x0001
		CTRL_MASK  = 0x0004   # (Cmd on macOS is different, but you're on Windows)
		if event.state & (SHIFT_MASK | CTRL_MASK):
			return

		col_index = int(col[1:]) - 1
		col_name = self.headers[col_index]

		# Only act on your action columns
		if col_name not in self.clickable_cols:
			return

		if item_id not in tree.selection():
			return

		selected_items = tree.selection()
		for sel_id in selected_items:
			algo_data = self.deployment_algo_data_by_item_id.get(sel_id)
			if not algo_data:
				continue
			tp = algo_data['tp']

			if col_name == "+25":
				tp.change_percentage(0.25)
			elif col_name == "-25":
				tp.change_percentage(-0.25)
			elif col_name == "Algo":
				tp.create_clone()
			elif col_name == "Status":
				tp.print_info()
			elif col_name == "Flatten":
				tp.flatten_cmd()
			elif col_name == "A-Flat":
				algo_data["Unrealized"] = 0.0
				algo_data["Status"] = "A-FLAT"
			# NEW: toggle NBBO_Mode
			elif col_name == "NBBO_Mode":
				current = bool(getattr(tp, "nbbo_only", False))
				setattr(tp, "nbbo_only", not current)
				algo_data["NBBO_Mode"] = "ON" if tp.nbbo_only else "OFF"

			self._update_treeview_row(tree, sel_id, algo_data)

	def on_treeview_click(self, event):
	    tree = self.deployment_tree

	    # allow header clicks (sorting/resizing)
	    region = tree.identify_region(event.x, event.y)
	    if region in ("heading", "separator"):
	        return

	    item_id = tree.identify_row(event.y)
	    col = tree.identify_column(event.x)
	    if not item_id or not col:
	        return "break"

	    # allow normal multi-select with Shift/Ctrl
	    SHIFT_MASK = 0x0001
	    CTRL_MASK  = 0x0004
	    if event.state & (SHIFT_MASK | CTRL_MASK):
	        return

	    # --- make it yellow: kill native selection + apply highlight tag ---
	    tree.selection_remove(tree.selection())
	    tree.focus("")

	    # clear old highlight
	    if self.current_highlighted_item and self.current_highlighted_item != item_id:
	        old_tags = tree.item(self.current_highlighted_item, "tags")
	        tree.item(self.current_highlighted_item,
	                  tags=tuple(t for t in old_tags if t != "highlight_style"))

	    # set new highlight
	    tags = list(tree.item(item_id, "tags"))
	    if "highlight_style" not in tags:
	        tags.append("highlight_style")
	    tree.item(item_id, tags=tuple(tags))
	    self.current_highlighted_item = item_id

	    # --- optional: if you want action on second click only, stop here ---
	    return "break"
    
	def toggle_deployment_2_panel(self,event=None):
		"""Toggles the visibility and layout of the deployment panel."""
		if not self.deployment_only_mode2:
			# Hide the dashboard and filter panels
			self.ui.deployment_panel.place_forget()
			self.ui.filter_panel.place_forget()

			self.deployment_clickable.place_forget()

			# Make deployment panel take more space
			self.ui.dashboard_panel.place(x=360, y=10, height=self.ui.root.winfo_height() - 20)
			self.deployment_clickablex.place(x=370, y=5)
			self.deployment_clickablex.config(text="▼ Dashboard")
			self.deployment_only_mode2 = True
		else:
			# Restore original layout
			self.ui.dashboard_panel.place(x=360, y=10, height=270, width=1200)
			self.ui.filter_panel.place(x=360, y=280, height=80, width=1200)
			self.ui.deployment_panel.place(x=360, y=365, height=880, width=1200)

			self.deployment_clickablex.place(x=370, y=10)
			self.deployment_clickablex.config(text="▶ Dashboard")

			self.deployment_clickable.place(x=370, y=360)
			self.deployment_clickable.config(text="▼ Algorithms Deployment")
			self.deployment_only_mode2 = False


	def toggle_deployment_panel(self, event=None):
		"""Toggles the visibility and layout of the deployment panel."""
		if not self.deployment_only_mode:
			# Hide the dashboard and filter panels
			self.ui.dashboard_panel.place_forget()
			self.ui.filter_panel.place_forget()

			# Make deployment panel take more space
			self.ui.deployment_panel.place(x=360, y=10, height=self.ui.root.winfo_height() - 20)
			self.deployment_clickable.place(x=370, y=5)
			self.deployment_clickable.config(text="▼ Algorithms Deployment")
			self.deployment_only_mode = True
		else:
			# Restore original layout
			self.ui.dashboard_panel.place(x=360, y=10, height=270, width=1200)
			self.ui.filter_panel.place(x=360, y=280, height=80, width=1200)
			self.ui.deployment_panel.place(x=360, y=365, height=880, width=1200)

			self.deployment_clickable.place(x=370, y=360)
			self.deployment_clickable.config(text="▶ Algorithms Deployment")
			self.deployment_only_mode = False

	def toggle_deployment_panel222(self, event=None):
		"""Toggles the visibility and layout of the deployment panel."""
		if not self.deployment_only_mode:
			# Hide the dashboard and filter panels
			# self.ui.dashboard_panel.place_forget()
			# self.ui.filter_panel.place_forget()

			# Make deployment panel take more space

			self.ui.dashboard_panel.place(x=360, y=10, height=270+300, width=1200)
			self.ui.filter_panel.place(x=360, y=280+300, height=80, width=1200)
			self.ui.deployment_panel.place(x=360, y=365+300, height=880-300, width=1200)

			#self.ui.deployment_panel.place(x=360, y=10, height=self.ui.root.winfo_height() - 20)
			self.deployment_clickable.place(x=370, y=365+300)



			self.deployment_clickable.config(text="▶ Algorithms Deployment")
			self.deployment_only_mode = True
		else:
			# Restore original layout
			self.ui.dashboard_panel.place(x=360, y=10, height=270, width=1200)
			self.ui.filter_panel.place(x=360, y=280, height=80, width=1200)
			self.ui.deployment_panel.place(x=360, y=365, height=880, width=1200)

			self.deployment_clickable.place(x=370, y=360)
			self.deployment_clickable.config(text="▶ Algorithms Deployment")
			self.deployment_only_mode = False


	def modify_algo_values(self, algo_name,algo_type, new_status=None, new_unreal=None, new_real=None,multiplier=None,positions=None,nbbo_mode=None):
		"""
		Modifies the data for an existing algorithm and updates its Treeview row.
		
		Args:
			algo_name (str): The 'Name' of the algorithm to modify.
			new_status (str, optional): The new status. Defaults to None.
			new_unreal (float, optional): The new unrealized value. Defaults to None.
			new_real (float, optional): The new realized value. Defaults to None.
		"""
		if algo_name not in self.algo_ids:
			print(f"Algorithm '{algo_name}' not found.")
			return

		item_id = self.algo_ids[algo_name]
		data_vars = self.deployment_algo_data_by_item_id[item_id]

		# Update the data dictionary with new values if provided
		if new_status is not None:
			data_vars["Status"] = new_status
		if new_unreal is not None:
			data_vars["Unrealized"] = new_unreal
		if new_real is not None:
			data_vars["Realized"] = new_real
		if multiplier is not None:
			data_vars['Multiplier'] = multiplier
		if positions is not None:
			data_vars['Positions'] = positions	
		if algo_type is not None:
			data_vars['Type'] = algo_type

		if nbbo_mode is not None:
			data_vars['NBBO'] =nbbo_mode
		# Call the helper method to refresh the UI with the updated data
		#self._update_treeview_row(self.deployment_tree, item_id, data_vars)
		self.ui.root.after(0, self._update_treeview_row, self.deployment_tree, item_id, data_vars)
		#print(f"Successfully updated data and row for algorithm '{algo_name}'.")

	def add_algo(self,tp):

		self.current_algo_id += 1
		algo_id = self.current_algo_id

		time_added_dt = datetime.now()
		time_added_str = time_added_dt.strftime("%H:%M:%S") # Changed to HH:MM:SS

		### need

		new_data = {
			"ID": algo_id,
			"Name": tp.algo_name,
			"Time Added": time_added_str,
			"Positions": tp.data['current_shares'],
			"Status": tp.data['status'],
			"Unrealized": tp.data['unreal'],
			"Realized": tp.data['realized'],
			"Multiplier": tp.data['multiplier'],
			"tp": tp,
			"Type": tp.algo_type,  # safe if attr missing
			"NBBO": "ON" if getattr(tp, "nbbo_only", False) else "OFF",
			"BREV": "ON" if getattr(tp, "break_even", False) else "OFF",

		}


		item_id = self.deployment_tree.insert("", 0)

		#print("ITEM_ID:",item_id,data['algo'])

		self.algo_ids[tp.algo_name] = item_id
		self.deployment_algo_data_by_item_id[item_id] = new_data
		self._update_treeview_row(self.deployment_tree, item_id, new_data)
		

	def _update_treeview_row(self, tree_widget, item_id, data_vars):
		algo_fixed_id = data_vars.get("ID", "")
		name = data_vars["Name"]
		time_added = data_vars["Time Added"]
		status = data_vars["Status"]
		unreal = data_vars["Unrealized"]
		real = data_vars["Realized"]
		position = data_vars["Positions"]

		# NEW
		nbbo_str = data_vars.get("NBBO")#  "ON" if data_vars.get("NBBO") else "OFF" #data_vars.get("NBBO", "OFF")
		type_str = data_vars['Type']

		mul = data_vars['Multiplier']

		brev = data_vars.get("BREV") #"ON" if data_vars.get("BREV") else "OFF"# data_vars['BREV']
		values = [
			algo_fixed_id,
			time_added,
			name,
			type_str,          # NEW "Type"
			status,
			position,
			f"{unreal}",
			f"{real}",
			brev,
			nbbo_str,          # NEW "NBBO"
			f"{mul}",
			f"{mul}",
			"Flatten",
			"A-Flat",
		]

		tags_to_apply = []

		if status == DONE:
			tags_to_apply.append("row_grey")
		elif status == IDLE:
			tags_to_apply.append("row_grey")
		elif status == REJECTED:
			tags_to_apply.append("row_pink")
		elif status == ORDERING:
			tags_to_apply.append("row_blue")
		else:
			tags_to_apply.append("row_green" if unreal >= 0 else "row_red")

		tags_to_apply.append("default_text")

		if item_id == getattr(self, "current_highlighted_item", None):
			tags_to_apply.append("highlight_style")
		tree_widget.item(item_id, values=values, tags=tuple(tags_to_apply))


	def sort_column(self, col, reverse, tree_widget):
		"""Sorts a Treeview column."""
		try:

		#if 1:
			if self.auto_clear_active:
				matching_ids =[]
				for item_id, data in self.deployment_algo_data_by_item_id.items():
					positions = str(data.get("Status", ""))
					if positions in [IDLE,ORDERING,RUNNING,FLATTENING]:
						matching_ids.append(item_id)
					else:
						self.deployment_tree.detach(item_id)
				print('matching:',matching_ids)
			else:
				matching_ids = self.deployment_algo_data_by_item_id.keys()


			self.auto_sorting=True
			items = []
			for k in tree_widget.get_children():

				if k in matching_ids:
					data_vars = self.deployment_algo_data_by_item_id.get(k)
					value_to_sort = None # Initialize

					if data_vars:
						if col == "#":
							value_to_sort = data_vars.get("ID", 0) # Use the fixed ID
						elif col == "Algo":
							value_to_sort = data_vars["Name"]
						elif col == "Time Added":
							value_to_sort = data_vars["Time Added"] # Sort by the datetime object
						elif col == "Unreal": # Specific handling for "Unreal"
							value_to_sort = data_vars["Unrealized"] # Access "Unrealized" and get its float value
						elif col == "Real": # Specific handling for "Real"
							value_to_sort = data_vars["Realized"] # Access "Realized" and get its float value
						elif col == "Status": # Specific handling for "Status"
							value_to_sort = self._status_sort_key(data_vars.get("Status", ""))
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

				#print(items)
				# Filter out items where value_to_sort is None if necessary (e.g., if data is truly missing)
				items = [item for item in items if item[0] is not None]


			#print(items,col,reverse,tree_widget)
			items.sort(key=lambda x: x[0], reverse=reverse)


			### REMOVE THE ONES.

			for index, (_, k) in enumerate(items):
				tree_widget.move(k, '', index)

			self.last_sort_column = col
			self.last_sort_reverse = reverse
			tree_widget.heading(col, command=lambda: self.sort_column(col, not reverse, tree_widget))


		except Exception as e:
			print(f"[Sort Error] {e}")

	def start_auto_sorting(self, interval_ms=5000):
		def auto_sort():
			# Only sort if: a column was chosen AND you're not hovering a row
			# AND you're not on a clickable hand-cursor cell (keeps your old behavior too)

			if (self.last_sort_column
				and not self.hover_lock and self.auto_sorting
				and self.current_cursor_is_hand == False):
				self.sort_column(self.last_sort_column, self.last_sort_reverse, self.deployment_tree)


			self.ui.root.after(interval_ms, auto_sort)

		self.ui.root.after(interval_ms, auto_sort)
			
	def on_treeview_activate(self, event):
		"""
		Double-click action handler.
		Works on the cell under the cursor; does NOT require selection.
		"""
		tree = self.deployment_tree
		item_id = tree.identify_row(event.y)
		col = tree.identify_column(event.x)
		if not item_id or not col:
			return

		col_index = int(col[1:]) - 1
		col_name = self.headers[col_index]

		# Only act on action columns
		if col_name not in self.clickable_cols:
			return

		algo_data = self.deployment_algo_data_by_item_id.get(item_id)
		if not algo_data:
			return

		tp = algo_data['tp']

		if col_name == "+25":
			tp.change_percentage(0.25)
		elif col_name == "-25":
			tp.change_percentage(-0.25)
		elif col_name == "Algo":
			tp.create_clone()

		elif col_name == "Status":
			tp.print_info()
		elif col_name == "Flatten":
			tp.flatten_cmd()
		elif col_name == "A-Flat":
			tp.a_flatten_cmd()
		elif col_name == "NBBO":
			current = bool(getattr(tp, "nbbo_only", False))
			setattr(tp, "nbbo_only", not current)
			algo_data["NBBO"] = "ON" if tp.nbbo_only else "OFF"
		elif col_name == "BREV":
			# keep your break-even behavior
			algo_data["BREV"] = "ON" if getattr(tp, "break_even", False) else "OFF"
			tp.break_even_function()

		self._update_treeview_row(tree, item_id, algo_data)


	def on_treeview_motion(self, event):
		motion_tree = self.deployment_tree
		data_source = self.deployment_algo_data_by_item_id

		item = motion_tree.identify_row(event.y)
		col = motion_tree.identify_column(event.x)

		# NEW: lock while hovering any cell in the body
		region = motion_tree.identify_region(event.x, event.y)
		self.hover_lock = (region == "cell" and bool(item))

		if self.tooltip and self.tooltip.tip_window:
			self.tooltip.hidetip()

		if item and col:
			idx = int(col[1:]) - 1
			col_name = self.headers[idx]

			# Tooltip on Algo -> show full Positions text
			if col_name == "Algo":
				algo_data = data_source.get(item)
				if algo_data and "Positions" in algo_data:
					full_position_text = str(algo_data["Positions"])
					if not self.tooltip:
						self.tooltip = Tooltip(motion_tree)
					self.tooltip.showtip(full_position_text, item, col)

			# Hand cursor on clickable cols
			if col_name in self.clickable_cols:
				motion_tree.config(cursor="hand2")
				self.current_cursor_is_hand = True
			else:
				motion_tree.config(cursor="")
				self.current_cursor_is_hand = False
		else:
			motion_tree.config(cursor="")
			self.current_cursor_is_hand = False

	def on_treeview_leave(self, event):
		left_tree = self.deployment_tree
		left_tree.config(cursor="")
		self.current_cursor_is_hand = False
		self.hover_lock = False  # NEW: release lock when leaving the widget
		if self.tooltip:
			self.tooltip.hidetip()

	def update_treeview_row_styles(self):
		"""
		Configures and applies Treeview row styles based on the current theme.
		This function is now included as part of your UI class.
		"""
		# Determine foreground colors based on current theme
		if self.ui.DARK_MODE.get() == 1 or self.ui.DISASTER_MODE.get() == 1:
			normal_text_color = "white" # For dark themes (darkly, vapor)
			
			# Background colors for row tags in DARK mode
			green_bg = "#2a662a"  # Darker green
			red_bg   = "#802b2b"  # Darker red
			grey_bg  = "#4d4d4d"  # Dark grey
			pink_bg  = "#802b55"  # Muted deep pink
			blue_bg  = "#2b3b80"  # Dark navy blue
		else:
			normal_text_color = "black" # For light themes (flatly)
			
			# Background colors for row tags in LIGHT mode
			green_bg = "#e6ffe6"  # Light green
			red_bg   = "#ffe6e6"  # Light red
			grey_bg  = "#f0f0f0"  # Very light grey
			pink_bg  = "#ffe6f2"  # Light pastel pink
			blue_bg  = "#e6f2ff"  # Light pastel blue

		# Reconfigure the default_text tag's foreground (this affects all cells with this tag)
		self.deployment_tree.tag_configure("default_text", foreground=normal_text_color)

		# Apply the determined background colors to the row tags
		self.deployment_tree.tag_configure("row_green", background=green_bg)
		self.deployment_tree.tag_configure("row_red", background=red_bg)
		self.deployment_tree.tag_configure("row_grey", background=grey_bg)
		self.deployment_tree.tag_configure("row_pink", background=pink_bg)
		self.deployment_tree.tag_configure("row_blue", background=blue_bg)

		# Iterate through all items and force a re-render of their style
		for item_id in self.deployment_tree.get_children():
			data_vars = self.deployment_algo_data_by_item_id.get(item_id)
			if data_vars:
				self._update_treeview_row(self.deployment_tree, item_id, data_vars) # Re-applies tags


	def show_only_ids(self, ids_to_show):
		"""
		Show only the items whose item_id is in ids_to_show. Hide the rest.
		"""
		all_items = self.deployment_tree.get_children()

		# Hide all items
		for item_id in all_items:
			self.deployment_tree.detach(item_id)

		# Show only matching items
		for item_id in ids_to_show:
			if item_id in self.deployment_algo_data_by_item_id:
				self.deployment_tree.reattach(item_id, '', 'end')  # use reattach instead of move

	def show_all(self):
		"""
		Show all items in the deployment Treeview.
		"""
		for item_id in self.deployment_algo_data_by_item_id:
			self.deployment_tree.move(item_id, '', 'end')

		self.auto_clear_active = False

	def clear_algos(self):

		# matching_ids =[]
		# for item_id, data in self.deployment_algo_data_by_item_id.items():
		# 	positions = str(data.get("Status", ""))
		# 	if positions in [ORDERING,RUNNING,FLATTENING]:
		# 		matching_ids.append(item_id)

		# self.show_only_ids(matching_ids)

		self.auto_clear_active= True

		self.auto_sorting=False

		self.sort_column(self.last_sort_column, self.last_sort_reverse, self.deployment_tree)


	def usr_only_algo(self):

		# matching_ids =[]
		# for item_id, data in self.deployment_algo_data_by_item_id.items():
		# 	positions = str(data.get("Algo", ""))
		# 	if "TFM" or "QH" in positions:
		# 		matching_ids.append(item_id)

		# self.show_only_ids(matching_ids)

		#self.show_only_ids(matching_ids)
		self.auto_clear_active= True
		self.auto_sorting=False

	def filter_by_symbol(self):
		"""
		Only show rows where Positions != 0
		"""
		filter_text = self.ui.symbol_filter_entry.get().strip().lower()
		matching_ids = []

		if filter_text:
			for item_id, data in self.deployment_algo_data_by_item_id.items():
				positions = str(data.get("Positions", "")).lower()
				if filter_text in positions:
					matching_ids.append(item_id)

		self.show_only_ids(matching_ids)

	def filter_by_algo(self):
		"""
		Only show rows whose algo name contains the filter keyword (case-insensitive)
		"""
		filter_text = self.ui.algo_filter_entry.get().strip().lower()
		matching_ids = []

		if filter_text:
			for item_id, data in self.deployment_algo_data_by_item_id.items():
				algo_name = data.get("Name", "").lower()
				if filter_text in algo_name:
					matching_ids.append(item_id)

		self.show_only_ids(matching_ids)

	def update_unreal_real_headers(self, unreal, real, *, precision=2):
		"""
		Update the headings to 'Unreal: x' and 'Real: x' without touching column IDs.
		Example: self.update_unreal_real_headers(154.62, 1435)
		"""
		def _fmt(v):
			try:
				return f"{float(v):,.{precision}f}"
			except Exception:
				return str(v)

		# Only set 'text' – existing heading commands (for sorting) remain intact
		self.deployment_tree.heading("Unreal", text=f"Unreal: {_fmt(unreal)}")
		self.deployment_tree.heading("Real",   text=f"Real: {_fmt(real)}")

	def _status_sort_key(self, status: str) -> int:
		# normalize: strip spaces, upper-case
		norm = (status or "").strip().upper()
		# rotate the order so that each click shifts which status appears first
		seq = self.STATUS_SEQUENCE
		# handle the stray space in ' FLATTENING' safely
		rot = seq[self.status_cycle_idx:] + seq[:self.status_cycle_idx]
		# normalize the rotated list too
		rot_norm = [s.strip().upper() for s in rot]
		try:
			return rot_norm.index(norm)
		except ValueError:
			# unknown statuses go to the end
			return len(rot_norm)

if __name__ == "__main__":
	import tkinter as tk
	import ttkbootstrap as tb
	from ttkbootstrap.constants import *

	# ---- minimal stub that your panel can interact with ----
	class MockTP:
		def __init__(self, name, *, nbbo_only=False, algo_type="MarketMaker",
					 shares=0, unreal=0.0, realized=0.0, status="IDLE", multiplier=1.0):
			self.algo_name = name
			self.nbbo_only = nbbo_only          # toggled by clicking NBBO
			self.algo_type = algo_type          # read-only "Type" column
			self.data = {
				"current_shares": shares,
				"unreal": unreal,
				"realized": realized,
				"status": status,
				"multiplier": multiplier,
			}

		# Click handlers used by the panel:
		def change_percentage(self, pct):
			# No-op demo: tweak unreal & status so you can see something change
			self.data["unreal"] = round(self.data.get("unreal", 0.0) + pct * 100, 2)
			self.data["status"] = f"Δ {int(pct*100)}%"

		def create_clone(self):
			print(f"[MockTP] create_clone() called for {self.algo_name}")

		def print_info(self):
			print(f"[MockTP] print_info(): {self.algo_name} | "
				  f"nbbo_only={self.nbbo_only} | type={self.algo_type} | data={self.data}")

		def flatten_cmd(self):
			self.data["current_shares"] = 0
			self.data["status"] = "FLATTEN"

	# ---- minimal 'ui' container your panel expects ----
	class _MiniUI:
		def __init__(self, root):
			self.root = root

	# ---- boot the demo window ----
	root = tb.Window(themename="flatly")  # or pick your preferred ttkbootstrap theme
	root.title("Algo Deployment – Mock Demo")
	root.geometry("1050x520")

	ui = _MiniUI(root)

	# Instantiate your panel (assumes Algo_Deployment_Panel is defined in this file)
	panel = Algo_Deployment_Panel(ui)

	# If your panel exposes a visible frame/container, you can pack/place it here.
	# Many of your panels call .place(...) internally; if yours doesn't, uncomment:
	# try:
	#     panel.frame.pack(fill="both", expand=True)
	# except Exception:
	#     pass

	# ---- seed a couple of mock algos ----
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

	# Add them to the table. If your class uses a different API, adjust here:
	try:
		panel.add_algo(tp1)
		panel.add_algo(tp2)
	except AttributeError:
		# Fallback: if your panel uses a different method name, try a common variant
		if hasattr(panel, "add_or_update_algo"):
			panel.add_or_update_algo(tp1)
			panel.add_or_update_algo(tp2)
		else:
			print("[Demo] Could not find add_algo/add_or_update_algo on panel.")

	# Optional: periodically refresh/redraw if your panel needs it
	# def _tick():
	#     # demo: nudge unreal on tp1 to see UI updates when you re-select the row
	#     tp1.data["unreal"] += 0.11
	#     root.after(1000, _tick)
	# root.after(1000, _tick)

	root.mainloop()
