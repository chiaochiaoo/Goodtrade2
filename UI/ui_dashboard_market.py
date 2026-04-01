import os
import json
from datetime import datetime, time
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
    'EU': ['.PA', '.LS', '.BR', '.MI', '.DE', '.CH', '.CO', '.AS','.MA','.ST','.HE','.NO'],
    'Crypto' :['.CR']
}




MARKET_TMS = {
    # --- US ---
    'NQ': {
        'Entry': [
            "ARCA ACTION ARCX Limit DAY",
            "BATS ACTION BATSOnly Limit DAY",
            "EDGA ACTION EDGA Limit DAY",

        ],
        'Exit': [
            "ARCA ACTION ARCX Limit DAY",
            "BATS ACTION BATSOnly Limit DAY",
            "EDGA ACTION EDGA Limit DAY",
        ],
    },
    'NY': {
        'Entry': [
            "ARCA ACTION ARCX Limit DAY",
            "BATS ACTION BATSOnly Limit DAY",
            "EDGA ACTION EDGA Limit DAY",

        ],
        'Exit': [
            "ARCA ACTION ARCX Limit DAY",
            "BATS ACTION BATSOnly Limit DAY",
            "EDGA ACTION EDGA Limit DAY",
        ],
    },
    'AM': {
        'Entry': [
            "ARCA ACTION ARCX Limit DAY",
            "BATS ACTION BATSOnly Limit DAY",
            "EDGA ACTION EDGA Limit DAY",
            #EDGA Buy ROUC Limit DAY
        ],
        'Exit': [
            "ARCA ACTION ARCX Limit DAY",
            "BATS ACTION BATSOnly Limit DAY",
            "EDGA ACTION EDGA Limit DAY",
        ],
    },

    # --- CA ---
    'TO': {
        'Entry': [
            "AEQN ACTION AequitasLIT Limit DAY",
            "ALPH ACTION ALPHA Limit Broker DAY",
            "CHIX ACTION SMART Limit DAY",
            "CX2 ACTION SMART Limit DAY",
            "LYNX ACTION LYNXSOR Limit DAY",
            "OMGA ACTION OMEGASOR Limit DAY",
            "TSX ACTION SweepSOR Limit ANON DAY",
        ],
        'Exit': [
            "AEQN ACTION AequitasLIT Limit DAY",
            "ALPH ACTION ALPHA Limit Broker DAY",
            "CHIX ACTION SMART Limit DAY",
            "CX2 ACTION SMART Limit DAY",
            "LYNX ACTION LYNXSOR Limit DAY",
            "OMGA ACTION OMEGASOR Limit DAY",
            "TSX ACTION SweepSOR Limit ANON DAY",
        ],
    },
    'VN': {
        'Entry': [
            "AEQN ACTION AequitasLIT Limit DAY",
            "AEQN ACTION AequitasNEO Limit DAY",
            "ALPH ACTION ALPHA Limit Broker DAY",
            "CHIX ACTION SMART Limit Broker DAY",
            "CX2 ACTION SMART Limit DAY",
            "LYNX ACTION LYNXSOR Limit DAY",
            "OMGA ACTION OMEGASOR Limit DAY",
            "TSX ACTION SweepSOR Limit ANON DAY",
        ],
        'Exit': [
            "AEQN ACTION AequitasLIT Limit DAY",
            "AEQN ACTION AequitasNEO Limit DAY",
            "ALPH ACTION ALPHA Limit Broker DAY",
            "CHIX ACTION SMART Limit Broker DAY",
            "CX2 ACTION SMART Limit DAY",
            "LYNX ACTION LYNXSOR Limit DAY",
            "OMGA ACTION OMEGASOR Limit DAY",
            "TSX ACTION SweepSOR Limit ANON DAY",
        ],
    },
    'CC': {
        'Entry': [
            "AEQN ACTION AequitasLIT Limit DAY",
            "CHIX ACTION SMART Limit Broker DAY",
            "CX2 ACTION SMART Limit DAY",
            "OMGA ACTION OMEGASOR Limit DAY",
        ],
        'Exit': [
            "AEQN ACTION AequitasLIT Limit DAY",
            "CHIX ACTION SMART Limit Broker DAY",
            "CX2 ACTION SMART Limit DAY",
            "OMGA ACTION OMEGASOR Limit DAY",
        ],
    },

    # --- EU ---
    'PA': {
        'Entry': [
            "ERNX ACTION PARIS Limit DAY",
            "TRQS ACTION TRQSPARIS Limit DAY",
            "CBOX ACTION DXEPARIS Limit DAY",
        ],
        'Exit': [
            "ERNX ACTION PARIS Limit DAY",
            "TRQS ACTION TRQSPARIS Limit DAY",
            "CBOX ACTION DXEPARIS Limit DAY",
        ],
    },
    'LS': {
        'Entry': [
            "ERNX ACTION LISBON Limit DAY",
            "TRQS ACTION TRQSLISBON Limit DAY",
            "CBOX ACTION DXELISBON Limit DAY",
        ],
        'Exit': [
            "ERNX ACTION LISBON Limit DAY",
            "TRQS ACTION TRQSLISBON Limit DAY",
            "CBOX ACTION DXELISBON Limit DAY",
        ],
    },
    'BR': {
        'Entry': [
            "ERNX ACTION BRUSSELS Limit DAY",
            "TRQS ACTION TRQSBRUSSELS Limit DAY",
            "CBOX ACTION DXEBRUSSELS Limit DAY",
        ],
        'Exit': [
            "ERNX ACTION BRUSSELS Limit DAY",
            "TRQS ACTION TRQSBRUSSELS Limit DAY",
            "CBOX ACTION DXEBRUSSELS Limit DAY",
        ],
    },
    'MI': {
        'Entry': [
            "MILA ACTION MILAN Limit DAY",
            "TRQS ACTION TRQSMILAN Limit DAY",
            "CBOX ACTION DXEMILAN Limit DAY",
        ],
        'Exit': [
            "MILA ACTION MILAN Limit DAY",
            "TRQS ACTION TRQSMILAN Limit DAY",
            "CBOX ACTION DXEMILAN Limit DAY",
        ],
    },
    'DE': {
        'Entry': [
            "TRQS ACTION TRQSXETRA Limit DAY",
            "XETR ACTION XETRA Limit DAY",
            "CBOX ACTION DXEXETRA Limit DAY",
        ],
        'Exit': [
            "TRQS ACTION TRQSXETRA Limit DAY",
            "XETR ACTION XETRA Limit DAY",
            "CBOX ACTION DXEXETRA Limit DAY",
        ],
    },
    'CH': {
        'Entry': [
            "SWX ACTION Swiss Limit DAY",
            "TRQS ACTION TRQXSWISS Limit DAY",
            "CBOX ACTION CHIXSWISS Limit DAY",
        ],
        'Exit': [
            "SWX ACTION Swiss Limit DAY",
            "TRQS ACTION TRQXSWISS Limit DAY",
            "CBOX ACTION CHIXSWISS Limit DAY",
        ],
    },
    'CO': {
        'Entry': [
            "NORX ACTION COPENHAGEN Limit DAY",
            "TRQS ACTION TRQSCOPENHAGEN Limit DAY",
            "CBOX ACTION DXECOPENHAGEN Limit DAY",
        ],
        'Exit': [
            "NORX ACTION COPENHAGEN Limit DAY",
            "TRQS ACTION TRQSCOPENHAGEN Limit DAY",
            "CBOX ACTION DXECOPENHAGEN Limit DAY",
        ],
    },
    'AS': {
        'Entry': [
            "ERNX ACTION AMSTERDAM Limit DAY",
            "TRQS ACTION TRQSAMSTERDAM Limit DAY",
            "CBOX ACTION DXEAMSTERDAM Limit DAY",
        ],
        'Exit': [
            "ERNX ACTION AMSTERDAM Limit DAY",
            "TRQS ACTION TRQSAMSTERDAM Limit DAY",
            "CBOX ACTION DXEAMSTERDAM Limit DAY",
        ],
    },
    'MA': {
        'Entry': [
            "CBOX ACTION DXEMADRID Limit DAY",
            "TRQS ACTION TRQSMADRID Limit DAY",
            "CBOX ACTION DXEMADRID Limit DAY",
            ""
        ],
        'Exit': [
            "CBOX ACTION DXEMADRID Limit DAY",
            "TRQS ACTION TRQSMADRID Limit DAY",
            "CBOX ACTION DXEMADRID Limit DAY",
        ],
    },

    'ST': {
        'Entry': [
            "CBOX ACTION DXESTOCKHOLM Limit DAY",
            "TRQS ACTION TRQSSTOCKHOLM Limit DAY",
        ],
        'Exit': [
            "CBOX ACTION DXESTOCKHOLM Limit DAY",
            "TRQS ACTION TRQSSTOCKHOLM Limit DAY",
        ],
    },

    'HE': {
        'Entry': [
            "CBOX ACTION DXEHELSINKI Limit DAY",
            "TRQS ACTION TRQSHELSINKI Limit DAY",
        ],
        'Exit': [
            "CBOX ACTION DXEHELSINKI Limit DAY",
            "TRQS ACTION TRQSHELSINKI Limit DAY",
        ],
    },

    'NO': {
        'Entry': [
            "CBOX ACTION DXEOSLO Limit DAY",
            "TRQS ACTION TRQSOSLO Limit DAY",
        ],
        'Exit': [
            "CBOX ACTION DXEOSLO Limit DAY",
            "TRQS ACTION TRQSOSLO Limit DAY",
        ],
    },
    # --- Crypto ---
    'CR': {
        'Entry': ["CRYP ACTION BitfinexDMA Limit DAY"],
        'Exit':  ["CRYP ACTION BitfinexDMA Limit DAY"],
    },
}




MARKET_LIVE = {
    # --- US ---
    ## ALL REQ RESERVE. 
    'NQ': {
        'Entry': [
            "ARCA ACTION ARCX Limit DAY",
            "ARCA ACTION ARCX Limit DAY PostOnly",
            "BATS ACTION BATSPostOnly Limit DAY",
            "BATS ACTION Parallel-T Limit DAY",
            "FREX ACTION FREX Limit DAY",
            "CITX ACTION CitiONE Limit DAY",
            "EDGA ACTION ROUC Limit DAY",
            "NSDQ ACTION LIST Limit DAY",
            "MEMX ACTION MEMX Limit Visible DAY",
            "MEMX ACTION MEMX Limit Hidden DAY",
            "MEMX ACTION MEMX Limit Visible DAY PostOnly",

        ],
        'Exit': [
            "ARCA ACTION ARCX Limit DAY",
            "ARCA ACTION ARCX Limit DAY PostOnly",
            "BATS ACTION BATSPostOnly Limit DAY",
            "BATS ACTION Parallel-T Limit DAY",
            "FREX ACTION FREX Limit DAY",
            "EDGA ACTION ROUC Limit DAY",
            "CITX ACTION CitiONE Limit DAY",
            "NSDQ ACTION LIST Limit DAY",
            "MEMX ACTION MEMX Limit Visible DAY",
            "MEMX ACTION MEMX Limit Hidden DAY",
            "MEMX ACTION MEMX Limit Visible DAY PostOnly",
        ],
    },
    'NY': {
        'Entry': [
            "ARCA ACTION ARCX Limit DAY",
            "ARCA ACTION ARCX Limit DAY PostOnly",
            "BATS ACTION BATSPostOnly Limit DAY",
            "BATS ACTION Parallel-T Limit DAY",
            "FREX ACTION FREX Limit DAY",
            "CITX ACTION CitiONE Limit DAY",
            "EDGA ACTION ROUC Limit DAY",
            "MEMX ACTION MEMX Limit Visible DAY",
            "MEMX ACTION MEMX Limit Hidden DAY",
            "MEMX ACTION MEMX Limit Visible DAY PostOnly",
        ],
        'Exit': [
            "ARCA ACTION ARCX Limit DAY",
            "ARCA ACTION ARCX Limit DAY PostOnly",
            "BATS ACTION BATSPostOnly Limit DAY",
            "BATS ACTION Parallel-T Limit DAY",
            "FREX ACTION FREX Limit DAY",
            "EDGA ACTION ROUC Limit DAY",
            "CITX ACTION CitiONE Limit DAY",
            "MEMX ACTION MEMX Limit Visible DAY",
            "MEMX ACTION MEMX Limit Hidden DAY",
            "MEMX ACTION MEMX Limit Visible DAY PostOnly",
        ],
    },
    'AM': {
        'Entry': [
            "ARCA ACTION ARCX Limit DAY",
            "ARCA ACTION ARCX Limit DAY PostOnly",
            "BATS ACTION BATSPostOnly Limit DAY",
            "BATS ACTION Parallel-T Limit DAY",
            "FREX ACTION FREX Limit DAY",
            "CITX ACTION CitiONE Limit DAY",
            "EDGA ACTION ROUC Limit DAY",
            "MEMX ACTION MEMX Limit Visible DAY",
            "MEMX ACTION MEMX Limit Hidden DAY",
            "MEMX ACTION MEMX Limit Visible DAY PostOnly",
            "DARK ACTION DARKLIQUIDITYSEEKER Limit Passive DAY",
        ],
        'Exit': [
            "ARCA ACTION ARCX Limit DAY",
            "ARCA ACTION ARCX Limit DAY PostOnly",
            "BATS ACTION BATSPostOnly Limit DAY",
            "BATS ACTION Parallel-T Limit DAY",
            "FREX ACTION FREX Limit DAY",
            "EDGA ACTION ROUC Limit DAY",
            "CITX ACTION CitiONE Limit DAY",
            "MEMX ACTION MEMX Limit Visible DAY",
            "MEMX ACTION MEMX Limit Hidden DAY",
            "MEMX ACTION MEMX Limit Visible DAY PostOnly",
            "DARK ACTION DARKLIQUIDITYSEEKER Limit Passive DAY",
        ],
    },

    # --- CA ---
    'TO': {
        'Entry': [
            "AEQN ACTION AequitasLIT Limit Broker DAY",
            "AEQN ACTION AequitasNEO Limit Broker DAY",
            "CHIX ACTION SMART Limit Broker DAY",
            "CX2 ACTION SMART Limit Broker DAY",
            "LYNX ACTION LYNXSOR Limit Broker DAY",
            "OMGA ACTION OMEGASOR Limit Broker DAY",
            "TSX ACTION SweepSOR Limit ANON DAY",
        ],
        'Exit': [
            "AEQN ACTION AequitasLIT Limit Broker DAY",
            "AEQN ACTION AequitasNEO Limit Broker DAY",
            "CHIX ACTION SMART Limit Broker DAY",
            "CX2 ACTION SMART Limit Broker DAY",
            "LYNX ACTION LYNXSOR Limit Broker DAY",
            "OMGA ACTION OMEGASOR Limit Broker DAY",
            "TSX ACTION SweepSOR Limit ANON DAY",
        ],
    },
    'VN': {
        'Entry': [
            "AEQN ACTION AequitasLIT Limit Broker DAY",
            "AEQN ACTION AequitasNEO Limit Broker DAY",
            "CHIX ACTION SMART Limit Broker DAY",
            "CX2 ACTION SMART Limit Broker DAY",
            "LYNX ACTION LYNXSOR Limit Broker DAY",
            "OMGA ACTION OMEGASOR Limit Broker DAY",
            "TSX ACTION SweepSOR Limit ANON DAY",
        ],
        'Exit': [
            "AEQN ACTION AequitasLIT Limit Broker DAY",
            "AEQN ACTION AequitasNEO Limit Broker DAY",
            "CHIX ACTION SMART Limit Broker DAY",
            "CX2 ACTION SMART Limit Broker DAY",
            "LYNX ACTION LYNXSOR Limit Broker DAY",
            "OMGA ACTION OMEGASOR Limit Broker DAY",
            "TSX ACTION SweepSOR Limit ANON DAY",
        ],
    },
    'CC': {
        'Entry': [
            "AEQN ACTION AequitasLIT Limit Broker DAY",
            "CHIX ACTION SMART Limit Broker DAYY",
            "CX2 ACTION SMART Limit Broker DAY",
            "OMGA ACTION OMEGASOR Limit Broker DAY",
        ],
        'Exit': [
            "AEQN ACTION AequitasLIT Limit Broker DAY",
            "CHIX ACTION SMART Limit Broker DAYY",
            "CX2 ACTION SMART Limit Broker DAY",
            "OMGA ACTION OMEGASOR Limit Broker DAY",
        ],
    },

    # --- EU ---
    'PA': {
        'Entry': [
            "AQXE ACTION AquisParis Limit DAY",
            "ERNX ACTION PARIS Limit DAY",
            "TRQS ACTION TRQSPARIS Limit DAY",
        ],
        'Exit': [
            "AQXE ACTION AquisParis Limit DAY",
            "ERNX ACTION PARIS Limit DAY",
            "TRQS ACTION TRQSPARIS Limit DAY",
        ],
    },
    'LS': {
        'Entry': [
            "AQXE ACTION AquisParis Limit DAY",
            "ERNX ACTION LISBON Limit DAY",
            "TRQS ACTION TRQSLISBON Limit DAY",
        ],
        'Exit': [
            "AQXE ACTION AquisParis Limit DAY",
            "ERNX ACTION LISBON Limit DAY",
            "TRQS ACTION TRQSLISBON Limit DAY",
        ],
    },
    'BR': {
        'Entry': [
            "ERNX ACTION BRUSSELS Limit DAY",
            "ERNX ACTION BRUSSELSSweep Limit DAY",
            "TRQS ACTION TRQSBRUSSELS Limit DAY",
        ],
        'Exit': [
            "ERNX ACTION BRUSSELS Limit DAY",
            "ERNX ACTION BRUSSELSSweep Limit DAY",
            "TRQS ACTION TRQSBRUSSELS Limit DAY",
        ],
    },
    'MI': {
        'Entry': [
            "MILA ACTION MILAN Limit DAY",
            "MILA ACTION MILANSweep Limit DAY",
            "TRQS ACTION TRQSMILAN Limit DAY",
            "CBOX ACTION DXEMILAN Limit DAY",
        ],
        'Exit': [
            "MILA ACTION MILAN Limit DAY",
            "MILA ACTION MILANSweep Limit DAY",
            "TRQS ACTION TRQSMILAN Limit DAY",
            "CBOX ACTION DXEMILAN Limit DAY",
        ],
    },
    'DE': {
        'Entry': [
            "CBOX ACTION DXEXETRA Limit DAY",
            "TRQS ACTION TRQSXETRA Limit DAY",
            "XETR ACTION XETRA Limit DAY",
        ],
        'Exit': [
            "CBOX ACTION DXEXETRA Limit DAY",
            "TRQS ACTION TRQSXETRA Limit DAY",
            "XETR ACTION XETRA Limit DAY",
        ],
    },
    'CH': {
        'Entry': [
            "SWX ACTION Swiss Limit DAY",
            "SWX ACTION SwissSweep Limit DAY",
            "TRQS ACTION TRQXSWISS Limit DAY",
            "CBOX ACTION CHIXSWISS Limit DAY",
        ],
        'Exit': [
            "SWX ACTION Swiss Limit DAY",
            "SWX ACTION SwissSweep Limit DAY",
            "TRQS ACTION TRQXSWISS Limit DAY",
            "CBOX ACTION CHIXSWISS Limit DAY",
        ],
    },
    'CO': {
        'Entry': [
            "NORX ACTION COPENHAGEN Limit DAY",
            "NORX ACTION COPENHAGENSweep Limit DAY",
            "TRQS ACTION TRQSCOPENHAGEN Limit DAY",

        ],
        'Exit': [
            "NORX ACTION COPENHAGEN Limit DAY",
            "NORX ACTION COPENHAGENSweep Limit DAY",
            "TRQS ACTION TRQSCOPENHAGEN Limit DAY",
        ],
    },
    'AS': {
        'Entry': [
            "AQXE ACTION AquisAmsterdam Limit DAY",
            "ERNX ACTION AMSTERDAM Limit DAY",
            "TRQS ACTION TRQSAMSTERDAM Limit DAY",
        ],
        'Exit': [
            "AQXE ACTION AquisAmsterdam Limit DAY",
            "ERNX ACTION AMSTERDAM Limit DAY",
            "TRQS ACTION TRQSAMSTERDAM Limit DAY",
        ],
    },
    'MA': {
        'Entry': [
            "CBOX ACTION DXEMADRID Limit DAY",
            "TRQS ACTION TRQSMADRID Limit DAY",
            "XMAD ACTION Madrid Limit DAY",
            "XMAD ACTION MadridSweep Limit DAY",
        ],
        'Exit': [
            "CBOX ACTION DXEMADRID Limit DAY",
            "TRQS ACTION TRQSMADRID Limit DAY",
            "XMAD ACTION Madrid Limit DAY",
            "XMAD ACTION MadridSweep Limit DAY",
        ],
    },

    'ST': {
        'Entry': [
            "CBOX ACTION DXESTOCKHOLM Limit DAY",
            "TRQS ACTION TRQSSTOCKHOLM Limit DAY",
        ],
        'Exit': [
            "CBOX ACTION DXESTOCKHOLM Limit DAY",
            "TRQS ACTION TRQSSTOCKHOLM Limit DAY",
        ],
    },

    'HE': {
        'Entry': [
            "CBOX ACTION DXEHELSINKI Limit DAY",
            "TRQS ACTION TRQSHELSINKI Limit DAY",
        ],
        'Exit': [
            "CBOX ACTION DXEHELSINKI Limit DAY",
            "TRQS ACTION TRQSHELSINKI Limit DAY",
        ],
    },

    'NO': {
        'Entry': [
            "CBOX ACTION DXEOSLO Limit DAY",
            "TRQS ACTION TRQSOSLO Limit DAY",
        ],
        'Exit': [
            "CBOX ACTION DXEOSLO Limit DAY",
            "TRQS ACTION TRQSOSLO Limit DAY",
        ],
    },
    # --- Crypto ---
    'CR': {
        'Entry': [ "CRYP ACTION CoinBaseDMA Limit DayCrypto",
                   "CRYP ACTION CoinBaseDMA Limit IOCCrypto",
                   "CRYP ACTION CoinBaseDMA Limit POCrypto" ],
        'Exit':   [ "CRYP ACTION CoinBaseDMA Limit DayCrypto",
                   "CRYP ACTION CoinBaseDMA Limit IOCCrypto",
                   "CRYP ACTION CoinBaseDMA Limit POCrypto" ],
    },
}



class MarketPanel:
    MODES = ("Live-Premarket","Live", "TMS")
    PHASES = ("Entry", "Exit")

    def __init__(self, parent):
        self.frame = tb.Frame(parent)
        self.frame.pack(fill="both", expand=True)

        # mode -> {(suffix, phase): tk.StringVar}
        self.vars: dict[str, dict[tuple[str, str], tk.StringVar]] = {m: {} for m in self.MODES}
        # widgets -> keep references to rebind vars/values when mode changes
        # (suffix, phase) -> ttk.Combobox
        self.widgets: dict[tuple[str, str], tb.Combobox] = {}

        self.group_frames = {}
        self._ready = False
        self._state_path = os.path.join(os.path.expanduser("~"), ".goodtrade", "market_panel.json")

        # Top toolbar: Mode (Live/TMS)
        bar = tb.Frame(self.frame)
        bar.pack(fill="x", padx=10, pady=(10, 0))
        tb.Label(bar, text="Mode:").pack(side="left", padx=(0, 8))
        self.mode_var = tk.StringVar(value="Live")
        for m in self.MODES:
            tb.Radiobutton(
                bar, text=m, variable=self.mode_var, value=m, bootstyle="info-toolbutton",
                command=self._on_mode_change
            ).pack(side="left", padx=4)

        nb = tb.Notebook(self.frame)
        nb.pack(fill='both', expand=True, padx=10, pady=10)
        self.nb = nb

        # Build tabs
        for group_key in GROUP_MAP:
            sub = tb.Frame(nb)
            nb.add(sub, text=group_key)
            self.group_frames[group_key] = sub
            self._populate_group(sub, group_key)

        # Load & apply saved selections
        state = self._load_state()
        if state:
            self._apply_state(state)

        self.state = state

        self._ready = True
        # initial populate of combobox choices/vars
        # print(state)
        self._refresh_all_widgets_for_mode()

    def get_order(self, suffix, env, type_):
        resolved_env = env
        if isinstance(resolved_env, str) and resolved_env.strip().lower() == "live":
            if datetime.now().time() < time(9, 30, 0):
                resolved_env = "Live-Premarket"
            else:
                resolved_env = "Live"

        t = f'{suffix}|{resolved_env}|{type_}'
        if t in self.state:
            return self.state[t]
        else:
            return ''
    # ---------- BUILD ----------
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

        # headers
        tb.Label(widget_parent, text="").grid(row=row_idx, column=0, sticky='w', padx=6, pady=(6, 2))
        tb.Label(widget_parent, text="Entry").grid(row=row_idx, column=1, sticky='w', padx=6, pady=(6, 2))
        tb.Label(widget_parent, text="Exit").grid(row=row_idx, column=2, sticky='w', padx=6, pady=(6, 2))
        for c in range(3):
            widget_parent.grid_columnconfigure(c, weight=1 if c else 0)
        row_idx += 1

        # rows
        for full_suffix in children:
            suffix = self._norm(full_suffix)
            # init vars for both modes, both phases
            for mode in self.MODES:
                for phase in self.PHASES:
                    self.vars[mode].setdefault((suffix, phase), tk.StringVar(widget_parent, value=""))
                    # bind save on write
                    self.vars[mode][(suffix, phase)].trace_add(
                        'write', lambda *_,
                        m=mode, s=suffix, p=phase: self._on_var_change(m, s, p)
                    )

            # label + two comboboxes
            tb.Label(widget_parent, text=full_suffix).grid(
                row=row_idx, column=0, sticky='w', padx=6, pady=(2, 8)
            )

            for col, phase in enumerate(self.PHASES, start=1):
                cb = tb.Combobox(
                    widget_parent,
                    state='readonly',
                    bootstyle='info'
                )
                cb.grid(row=row_idx, column=col, sticky='ew', padx=6, pady=(2, 8))
                # remember widget; bind selection event to save state eagerly
                self.widgets[(suffix, phase)] = cb
                cb.bind("<<ComboboxSelected>>", lambda e: self._save_state())

            row_idx += 1

    # ---------- MODE / VALUES ----------
    def _on_mode_change(self):
        self._refresh_all_widgets_for_mode()
        # saving here is optional; vars themselves didn’t change, only bindings.
        self._save_state()

    def _refresh_all_widgets_for_mode(self):
        """Rebind each combobox's values and textvariable for the current mode."""
        cur_mode = self.mode_var.get()
        market_dict = self._get_market_dict(cur_mode)

        for (suffix, phase), cb in self.widgets.items():
            values = market_dict.get(suffix, {}).get(phase, [])
            cb.configure(values=values)

            # rebind the textvariable to the current mode's var
            var = self.vars[cur_mode][(suffix, phase)]
            cb.configure(textvariable=var)

            # ensure value consistency
            if var.get() not in values:
                # if nothing selected but options exist, pick the first one automatically
                if values:
                    var.set(values[0])
                else:
                    var.set("")

        # save once after all auto-selections to persist default picks
        if self._ready:
            self._save_state()
    def _get_market_dict(self, mode: str) -> dict:
        return MARKET_LIVE if (mode == "Live") or (mode =="Live-Premarket") else MARKET_TMS

    # ---------- STATE ----------
    def _on_var_change(self, mode: str, suffix: str, phase: str):
        if self._ready:
            self._save_state()

    def _ensure_state_dir(self):
        d = os.path.dirname(self._state_path)
        if d and not os.path.isdir(d):
            os.makedirs(d, exist_ok=True)

    def _save_state(self):
        try:
            self._ensure_state_dir()
            # Persist all modes so switching tabs doesn’t lose the other mode’s selection
            state = {}
            for mode in self.MODES:
                for (suffix, phase), var in self.vars[mode].items():
                    key = f"{suffix}|{mode}|{phase}"
                    state[key] = var.get()

            self.state = state
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

    def _apply_state(self, state: dict):
        # Load any saved choice per (mode, suffix, phase) if still valid
        for key, val in state.items():
            try:
                suffix, mode, phase = key.split("|", 2)
            except ValueError:
                continue
            if mode not in self.MODES or phase not in self.PHASES:
                continue

            market_dict = self._get_market_dict(mode)
            valid = market_dict.get(suffix, {}).get(phase, [])
            if val == "" or val in valid:
                # ensure var exists (widgets created in _populate_group)
                if (suffix, phase) in self.vars[mode]:
                    self.vars[mode][(suffix, phase)].set(val)

        # After loading, make sure current mode widgets reflect their mode’s vars/values
        self._refresh_all_widgets_for_mode()

    # ---------- Utils ----------
    @staticmethod
    def _norm(s: str) -> str:
        return s.lstrip(".").strip()

def _ensure_group_map():
    """Use existing GROUP_MAP if available; otherwise provide a minimal fallback."""
    try:
        _ = GROUP_MAP  # noqa: F401
        return
    except NameError:
        pass
    # Minimal fallback so the panel can render even if GROUP_MAP wasn't imported
    globals()['GROUP_MAP'] = {
        'US': ['.NQ', '.NY', '.AM'],
        'CA': ['.TO', '.VN', '.CC'],
        'EU': ['.PA', '.LS', '.BR', '.MI', '.DE', '.CH', '.CO', '.AS'],
        'Crypto': ['.CR'],
    }

def _try_import_markets():
    """Import MARKET_LIVE and MARKET_TMS; raise clear error if missing."""
    try:
        from market_live import MARKET_LIVE  # noqa: F401
        from market_tms import MARKET_TMS    # noqa: F401
        return globals()['MARKET_LIVE'], globals()['MARKET_TMS']
    except Exception as e:
        raise RuntimeError(
            "Could not import MARKET_LIVE / MARKET_TMS. "
            "Make sure market_live.py and market_tms.py are on PYTHONPATH."
        ) from e

def _attach_debug_toolbar(root, panel: 'MarketPanel'):
    """Adds a small toolbar to print current selections for the active mode."""
    bar = tb.Frame(root)
    bar.pack(fill="x", padx=10, pady=(0, 10))

    def print_current():
        mode = panel.mode_var.get()
        picks = {}
        for (suffix, phase), var in panel.vars[mode].items():
            v = var.get()
            if v:
                picks.setdefault(suffix, {})[phase] = v
        print(f"[DEBUG] Mode={mode} selections:")
        for sfx in sorted(picks):
            entry = picks[sfx].get('Entry', '')
            exit_ = picks[sfx].get('Exit', '')
            print(f"  {sfx}: Entry={entry!r} | Exit={exit_!r}")

    tb.Button(bar, text="Print Current Selections (Ctrl+S)", command=print_current, bootstyle="secondary").pack(side="left")

    # Hotkey
    root.bind_all("<Control-s>", lambda e: (print_current(), "break"))

def run_demo(theme: str = "flatly", geometry: str = "980x620"):
    """
    Launch the MarketPanel in a standalone window.
    - theme: any ttkbootstrap theme (e.g., 'flatly', 'cosmo', 'darkly', 'superhero', etc.)
    - geometry: standard Tk geometry string 'WIDTHxHEIGHT'
    """
    _ensure_group_map()
    #_ = _try_import_markets()  # just to fail early if missing

    # ttkbootstrap window
    try:
        # Preferred in ttkbootstrap >= 1.10
        root = tb.Window(themename=theme)
    except Exception:
        # Fallback for older ttkbootstrap versions
        root = tk.Tk()
        try:
            tb.Style(theme=theme)
        except Exception:
            tb.Style()  # default theme

    root.title("MarketPanel Demo")
    try:
        root.geometry(geometry)
    except Exception:
        pass
    root.minsize(760, 420)

    # ESC to quit
    root.bind_all("<Escape>", lambda e: root.quit())

    # Host the panel
    host = tb.Frame(root, padding=10)
    host.pack(fill="both", expand=True)
    panel = MarketPanel(host)

    # Optional: small toolbar to print picks
    _attach_debug_toolbar(root, panel)

    root.mainloop()

if __name__ == "__main__":
    run_demo()
if __name__ == "__main__":
    try:
        validate_all(GROUP_MAP, MARKET_LIVE, MARKET_TMS)
        print("✔ Market configuration OK: every suffix has at least one Entry and Exit in both Live and TMS.")

    except ValueError as e:
        print(str(e))
