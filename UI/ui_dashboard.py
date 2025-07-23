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
    'EU DEFAULT': ['.PA', '.LS', '.BR', '.MI', '.DE', '.CH', '.CO', '.AS'],
}

# Venue definitions per market and grouping (as provided)
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
    'EU DEFAULT': [
        "AEQN ACTION AequitasLIT Limit Broker DAY",
        "AEQN ACTION AequitasNEO Limit Broker DAY",
        "LIT ACTION EuroLIT Limit Broker DAY", # Added some more for demonstration
        "NEO ACTION EuroNEO Limit Broker DAY",
        "PAR ACTION ParisEX Limit Broker DAY",
        "LIS ACTION LisbonEX Limit Broker DAY",
        "BRU ACTION BrusselsEX Limit Broker DAY",
        "MIL ACTION MilanEX Limit Broker DAY",
        "FRK ACTION FrankfurtEX Limit Broker DAY",
        "ZUR ACTION ZurichEX Limit Broker DAY",
        "COP ACTION CopenhagenEX Limit Broker DAY",
        "AMS ACTION AmsterdamEX Limit Broker DAY",
        "VIE ACTION ViennaEX Limit Broker DAY",
        "OSL ACTION OsloEX Limit Broker DAY",
        "HEL ACTION HelsinkiEX Limit Broker DAY",
        "STO ACTION StockholmEX Limit Broker DAY",
    ],
    '.PA': [
        "AEQN ACTION AequitasLIT Limit Broker DAY",
        "AEQN ACTION AequitasNEO Limit Broker DAY",
    ],
    '.LS': [
        "AEQN ACTION AequitasLIT Limit Broker DAY",
        "AEQN ACTION AequitasNEO Limit Broker DAY",
    ],
    '.BR': [
        "AEQN ACTION AequitasLIT Limit Broker DAY",
        "AEQN ACTION AequitasNEO Limit Broker DAY",
    ],
    '.MI': [
        "AEQN ACTION AequitasLIT Limit Broker DAY",
        "AEQN ACTION AequitasNEO Limit Broker DAY",
    ],
    '.DE': [
        "AEQN ACTION AequitasLIT Limit Broker DAY",
        "AEQN ACTION AequitasNEO Limit Broker DAY",
    ],
    '.CH': [
        "AEQN ACTION AequitasLIT Limit Broker DAY",
        "AEQN ACTION AequitasNEO Limit Broker DAY",
    ],
    '.CO': [
        "AEQN ACTION AequitasLIT Limit Broker DAY",
        "AEQN ACTION AequitasNEO Limit Broker DAY",
    ],
    '.AS': [
        "AEQN ACTION AequitasLIT Limit Broker DAY",
        "AEQN ACTION AequitasNEO Limit Broker DAY",
    ],
}

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
        self.create_market_panel()

    def create_market_panel(self):
        """
        Build a nested Notebook under the 'Market' tab, one page per group.
        """
        market_tab_frame = self.frames['Market'] # Get the frame for the 'Market' tab

        self.market_vars = {}
        
        # Create the nested notebook for US, CA, EU within the Market tab
        self.group_notebook = tb.Notebook(market_tab_frame)
        # Apply padding here, so it's consistent for all inner tabs
        self.group_notebook.pack(fill='both', expand=True, padx=10, pady=10) 

        # Create frames for each group and add them to the nested notebook
        self.group_frames = {} 
        for group_key in GROUP_MAP: 
            subframe = tb.Frame(self.group_notebook)
            self.group_frames[group_key] = subframe 
            self.group_notebook.add(subframe, text=group_key.split(' ')[0]) 

            # Populate each group's frame
            self._populate_group(subframe, group_key)
            self._bind_group(group_key)

    def _populate_group(self, parent, group_key):
        row_idx = 0

        # Determine the effective parent for grid layout (scrollable_frame for EU, else parent)
        if group_key == 'EU DEFAULT':
            # Create a Canvas and a Scrollbar
            canvas = tk.Canvas(parent, highlightthickness=0) # Set highlightthickness to 0 to remove border
            scrollbar = tb.Scrollbar(parent, orient='vertical', command=canvas.yview)
            
            # The scrollable_frame will hold all the content and will be placed inside the canvas
            scrollable_frame = tb.Frame(canvas)

            # Bind the scrollable_frame's size to update the canvas scrollregion
            scrollable_frame.bind(
                "<Configure>",
                lambda e: canvas.configure(
                    scrollregion=canvas.bbox("all")
                )
            )
            
            # Place the scrollable_frame inside the canvas window.
            # Do NOT set a fixed width here. Let the canvas's binding handle it.
            canvas_window_id = canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")

            # Bind Canvas width to scrollable_frame's width to ensure it fills
            # This is key to ensuring the inner content stretches with the canvas
            canvas.bind(
                "<Configure>", 
                lambda e: canvas.itemconfigure(canvas_window_id, width=e.width)
            )

            canvas.configure(yscrollcommand=scrollbar.set)

            # Pack the scrollbar and canvas within the parent tab frame
            scrollbar.pack(side="right", fill="y")
            canvas.pack(side="left", fill="both", expand=True)

            # All widgets for EU will be placed into scrollable_frame
            widget_parent = scrollable_frame
            
        else:
            # For other groups, use the 'parent' frame directly
            widget_parent = parent

        # Configure columns for the current widget_parent
        # This needs to be done *after* widget_parent is determined
        for i in range(4): 
            widget_parent.grid_columnconfigure(i, weight=0)
        widget_parent.grid_columnconfigure(1, weight=1) 
        widget_parent.grid_columnconfigure(3, weight=1) 

        # Group selector (e.g., 'US DEFAULT', 'CA DEFAULT', 'EU DEFAULT')
        venues = MARKET[group_key]
        var = tk.StringVar(widget_parent, value=venues[0])
        self.market_vars[group_key] = var

        # Label and Combobox for the "DEFAULT" group itself
        # Add consistent padx/pady here
        tb.Label(widget_parent, text=group_key, bootstyle='warning').grid(row=row_idx, column=0, sticky='w', padx=5, pady=(5, 2))
        tb.Combobox(widget_parent, textvariable=var, values=venues, state='readonly', bootstyle='warning').grid(row=row_idx, column=1, columnspan=3, sticky='ew', padx=5, pady=(5, 2))
        row_idx += 1

        # Child selectors
        children = GROUP_MAP[group_key]
        
        if group_key == 'US DEFAULT':
            if '.NQ' in children:
                child = '.NQ'
                child_venues = MARKET[child]
                cvar = tk.StringVar(widget_parent, value=child_venues[0])
                self.market_vars[child] = cvar
                tb.Label(widget_parent, text=child).grid(row=row_idx, column=0, sticky='w', padx=5, pady=(2, 0))
                tb.Combobox(widget_parent, textvariable=cvar, values=child_venues, state='readonly', bootstyle='info').grid(row=row_idx, column=1, sticky='ew', padx=5, pady=(2, 8))

            if '.NY' in children:
                child = '.NY'
                child_venues = MARKET[child]
                cvar = tk.StringVar(widget_parent, value=child_venues[0])
                self.market_vars[child] = cvar
                tb.Label(widget_parent, text=child).grid(row=row_idx, column=2, sticky='w', padx=5, pady=(2, 0))
                tb.Combobox(widget_parent, textvariable=cvar, values=child_venues, state='readonly', bootstyle='info').grid(row=row_idx, column=3, sticky='ew', padx=5, pady=(2, 8))
            
            row_idx += 1 

            if '.AM' in children:
                child = '.AM'
                child_venues = MARKET[child]
                cvar = tk.StringVar(widget_parent, value=child_venues[0])
                self.market_vars[child] = cvar
                tb.Label(widget_parent, text=child).grid(row=row_idx, column=0, sticky='w', padx=5, pady=(2, 0))
                tb.Combobox(widget_parent, textvariable=cvar, values=child_venues, state='readonly', bootstyle='info').grid(row=row_idx, column=1, columnspan=3, sticky='ew', padx=5, pady=(2, 8)) 
            row_idx += 1

        elif group_key == 'CA DEFAULT':
            if '.TO' in children:
                child = '.TO'
                child_venues = MARKET[child]
                cvar = tk.StringVar(widget_parent, value=child_venues[0])
                self.market_vars[child] = cvar
                tb.Label(widget_parent, text=child).grid(row=row_idx, column=0, sticky='w', padx=5, pady=(2, 0))
                tb.Combobox(widget_parent, textvariable=cvar, values=child_venues, state='readonly', bootstyle='info').grid(row=row_idx, column=1, sticky='ew', padx=5, pady=(2, 8))

            if '.VN' in children:
                child = '.VN'
                child_venues = MARKET[child]
                cvar = tk.StringVar(widget_parent, value=child_venues[0])
                self.market_vars[child] = cvar
                tb.Label(widget_parent, text=child).grid(row=row_idx, column=2, sticky='w', padx=5, pady=(2, 0))
                tb.Combobox(widget_parent, textvariable=cvar, values=child_venues, state='readonly', bootstyle='info').grid(row=row_idx, column=3, sticky='ew', padx=5, pady=(2, 8))
            
            row_idx += 1 

            if '.CC' in children:
                child = '.CC'
                child_venues = MARKET[child]
                cvar = tk.StringVar(widget_parent, value=child_venues[0])
                self.market_vars[child] = cvar
                tb.Label(widget_parent, text=child).grid(row=row_idx, column=0, sticky='w', padx=5, pady=(2, 0))
                tb.Combobox(widget_parent, textvariable=cvar, values=child_venues, state='readonly', bootstyle='info').grid(row=row_idx, column=1, columnspan=3, sticky='ew', padx=5, pady=(2, 8))
            row_idx += 1
            
        elif group_key == 'EU DEFAULT':
            col_counter = 0
            for child in children:
                child_venues = MARKET[child]
                cvar = tk.StringVar(widget_parent, value=child_venues[0])
                self.market_vars[child] = cvar

                # Use padx/pady for consistent spacing
                tb.Label(widget_parent, text=child).grid(row=row_idx, column=col_counter, sticky='w', padx=5, pady=(2, 0))
                tb.Combobox(widget_parent, textvariable=cvar, values=child_venues, state='readonly', bootstyle='info').grid(row=row_idx, column=col_counter+1, sticky='ew', padx=5, pady=(2, 8))

                col_counter += 2 
                if col_counter >= 4: 
                    col_counter = 0
                    row_idx += 1
            if col_counter != 0: 
                row_idx += 1

    def _bind_group(self, key):
        def callback(*args):
            val = self.market_vars[key].get()
            for child in GROUP_MAP[key]:
                if val in MARKET[child]:
                    self.market_vars[child].set(val)
        self.market_vars[key].trace_add('write', callback)

    def init_system_design_map(self):
        self.system_panel_design = {'System': {'var': None, 'type': 'label'}} 

if __name__ == '__main__':
    root = tb.Window(themename='flatly')
    root.title('GoodTrade AMS')
    root.geometry('1000x700')
    dashboard = Dashboard(root)
    root.mainloop()