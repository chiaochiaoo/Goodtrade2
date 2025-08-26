import os
import json
import tkinter as tk
import ttkbootstrap as tb
from ttkbootstrap.constants import *

ACTIVE = 0
MULTIPLIER = 1
PASSIVE = 2
DESCRIPTION = 3

# --- Groupings (no DEFAULT rows) ---
GROUP_MAP = {
    'US': ['.NQ', '.NY', '.AM'],
    'CA': ['.TO', '.VN', '.CC'],
    'EU': ['.PA', '.LS', '.BR', '.MI', '.DE', '.CH', '.CO', '.AS'],
}

MARKET = {
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
    '.PA': ["AEQN ACTION AequitasLIT Limit Broker DAY", "AEQN ACTION AequitasNEO Limit Broker DAY"],
    '.LS': ["AEQN ACTION AequitasLIT Limit Broker DAY", "AEQN ACTION AequitasNEO Limit Broker DAY"],
    '.BR': ["AEQN ACTION AequitasLIT Limit Broker DAY", "AEQN ACTION AequitasNEO Limit Broker DAY"],
    '.MI': ["AEQN ACTION AequitasLIT Limit Broker DAY", "AEQN ACTION AequitasNEO Limit Broker DAY"],
    '.DE': ["AEQN ACTION AequitasLIT Limit Broker DAY", "AEQN ACTION AequitasNEO Limit Broker DAY"],
    '.CH': ["AEQN ACTION AequitasLIT Limit Broker DAY", "AEQN ACTION AequitasNEO Limit Broker DAY"],
    '.CO': ["AEQN ACTION AequitasLIT Limit Broker DAY", "AEQN ACTION AequitasNEO Limit Broker DAY"],
    '.AS': ["AEQN ACTION AequitasLIT Limit Broker DAY", "AEQN ACTION AequitasNEO Limit Broker DAY"],
}

class MarketPanel:
    def __init__(self, parent):
        self.frame = tb.Frame(parent)
        self.frame.pack(fill="both", expand=True)

        self.market_vars = {}
        self.group_frames = {}
        self._ready = False
        self._state_path = os.path.join(os.path.expanduser("~"), ".goodtrade", "market_panel.json")

        self._build()

        # Load previously saved state and apply it
        state = self._load_state()
        if state:
            self._apply_state(state)

        self._ready = True

    def _build(self):
        nb = tb.Notebook(self.frame)
        nb.pack(fill='both', expand=True, padx=10, pady=10)

        for group_key in GROUP_MAP:
            sub = tb.Frame(nb)
            nb.add(sub, text=group_key)
            self.group_frames[group_key] = sub
            self._populate_group(sub, group_key)

    def _populate_group(self, parent, group_key):
        row_idx = 0
        children = GROUP_MAP[group_key]

        # Scrollable EU (wide)
        if group_key == 'EU':
            canvas = tk.Canvas(parent, highlightthickness=0)
            scrollbar = tb.Scrollbar(parent, orient='vertical', command=canvas.yview)
            scrollable = tb.Frame(canvas)
            scrollable.bind("<Configure>", lambda e: canvas.configure(scrollregion=canvas.bbox("all")))
            win_id = canvas.create_window((0, 0), window=scrollable, anchor='nw')
            canvas.bind("<Configure>", lambda e: canvas.itemconfigure(win_id, width=e.width))
            canvas.configure(yscrollcommand=scrollbar.set)
            scrollbar.pack(side="right", fill="y")
            canvas.pack(side="left", fill="both", expand=True)
            widget_parent = scrollable
        else:
            widget_parent = parent

        for i in range(4):
            widget_parent.grid_columnconfigure(i, weight=0)
        widget_parent.grid_columnconfigure(1, weight=1)
        widget_parent.grid_columnconfigure(3, weight=1)

        col_counter = 0
        for child in children:
            # No blank in values; start empty via StringVar("")
            venues = MARKET[child]
            var = tk.StringVar(widget_parent, value="")  # start blank
            self.market_vars[child] = var

            tb.Label(widget_parent, text=child).grid(row=row_idx, column=col_counter, sticky='w', padx=5, pady=(5, 2))
            tb.Combobox(widget_parent, textvariable=var, values=venues,
                        state='readonly', bootstyle='info').grid(row=row_idx, column=col_counter+1,
                                                                sticky='ew', padx=5, pady=(5, 8))
            self._bind_var(child)

            col_counter += 2
            if col_counter >= 4:
                col_counter = 0
                row_idx += 1

    def _bind_var(self, name):
        self.market_vars[name].trace_add('write', lambda *_, n=name: self._on_var_change(n))

    def _on_var_change(self, _):
        if self._ready:
            self._save_state()

    # -------- Persistence --------
    def _ensure_state_dir(self):
        d = os.path.dirname(self._state_path)
        if d and not os.path.isdir(d):
            os.makedirs(d, exist_ok=True)

    def _save_state(self):
        try:
            self._ensure_state_dir()
            state = {k: v.get() for k, v in self.market_vars.items()}
            with open(self._state_path, "w", encoding="utf-8") as f:
                json.dump(state, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print("MarketPanel: save error", e)

    def _load_state(self):
        try:
            if os.path.isfile(self._state_path):
                with open(self._state_path, "r", encoding="utf-8") as f:
                    return json.load(f)
        except Exception as e:
            print("MarketPanel: load error", e)
        return {}

    def _apply_state(self, state):
        for key, val in state.items():
            if key in self.market_vars:
                valid = MARKET.get(key, [])
                # allow restoring "" (from first run), or any valid venue
                if val == "" or val in valid:
                    self.market_vars[key].set(val)
