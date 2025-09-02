# ui_dashboard_risk.py
import os, json
import tkinter as tk
import ttkbootstrap as tb
from ttkbootstrap.constants import *

# ---------- reusable scroll container ----------
class ScrollFrame(tb.Frame):
    def __init__(self, parent, *args, **kwargs):
        super().__init__(parent, *args, **kwargs)
        self.columnconfigure(0, weight=1)
        self.rowconfigure(0, weight=1)

        self._canvas = tk.Canvas(self, highlightthickness=0)
        self._vsb = tb.Scrollbar(self, orient="vertical", command=self._canvas.yview)
        self._canvas.configure(yscrollcommand=self._vsb.set)

        self._inner = tb.Frame(self._canvas)
        self._inner.bind("<Configure>", lambda e: self._canvas.configure(scrollregion=self._canvas.bbox("all")))
        self._canvas.bind("<Configure>", lambda e: self._canvas.itemconfigure(self._win, width=e.width))

        self._win = self._canvas.create_window((0, 0), window=self._inner, anchor="nw")

        self._canvas.grid(row=0, column=0, sticky="nsew")
        self._vsb.grid(row=0, column=1, sticky="ns")

        self._inner.bind("<Enter>", self._bind_mousewheel)
        self._inner.bind("<Leave>", self._unbind_mousewheel)

    @property
    def body(self):
        return self._inner

    def _on_mousewheel(self, event):
        if hasattr(event, "delta") and event.delta:
            delta = -1 if event.delta > 0 else 1
        else:
            delta = -1 if getattr(event, "num", 5) == 4 else 1
        self._canvas.yview_scroll(delta, "units")

    def _bind_mousewheel(self, _):
        self._canvas.bind_all("<MouseWheel>", self._on_mousewheel)
        self._canvas.bind_all("<Button-4>", self._on_mousewheel)
        self._canvas.bind_all("<Button-5>", self._on_mousewheel)

    def _unbind_mousewheel(self, _):
        self._canvas.unbind_all("<MouseWheel>")
        self._canvas.unbind_all("<Button-4>")
        self._canvas.unbind_all("<Button-5>")


class RiskPanel(tb.Frame):
    def __init__(self, parent, master=None, autosave_file: str = None, *args, **kwargs):
        super().__init__(parent, *args, **kwargs)
        self._vm = self.winfo_toplevel()
        self._autosave_file = autosave_file or os.path.join(os.getcwd(), "risk_settings.json")
        self._save_after_id = None

        m = self._vm
        self.RISK_CFG = {
            "global": {
                "max_gross_pos": tk.IntVar(m, 21000),
                "max_symbols": tk.IntVar(m, 60),
                "max_open_orders": tk.IntVar(m, 200),
                "max_order_buying_power": tk.DoubleVar(m, 1_000_000.0),
                "daily_unreal_soft_stop": tk.DoubleVar(m, -5000.0),
                "daily_unreal_hard_stop": tk.DoubleVar(m, -10000.0),
            },
            "per_algo": {
                "max_distinct_algos": tk.IntVar(m, 50),
                "algo_soft_stop": tk.DoubleVar(m, -2000.0),
                "algo_hard_stop": tk.DoubleVar(m, -5000.0),
            },
            "per_suffix": {
                ".NQ": {"max_gross_pos": tk.IntVar(m, 10000), "max_symbol_pos": tk.IntVar(m, 2000)},
                ".NY": {"max_gross_pos": tk.IntVar(m,  8000), "max_symbol_pos": tk.IntVar(m, 1500)},
                ".AM": {"max_gross_pos": tk.IntVar(m,  4000), "max_symbol_pos": tk.IntVar(m, 1000)},
                ".EU": {"max_gross_pos": tk.IntVar(m,  2000), "max_symbol_pos": tk.IntVar(m,  800)},
            },
        }

        self.RISK_CFG_TOGGLE = {
            "global": {
                "max_gross_pos": tk.BooleanVar(m, True),
                "max_symbols": tk.BooleanVar(m, True),
                "max_open_orders": tk.BooleanVar(m, True),
                "max_order_buying_power": tk.BooleanVar(m, True),
                "daily_unreal_soft_stop": tk.BooleanVar(m, True),
                "daily_unreal_hard_stop": tk.BooleanVar(m, True),
            },
            "per_algo": {
                "max_distinct_algos": tk.BooleanVar(m, True),
                "algo_soft_stop": tk.BooleanVar(m, True),
                "algo_hard_stop": tk.BooleanVar(m, True),
            },
            "per_suffix": {
                ".NQ": {"max_gross_pos": tk.BooleanVar(m, True), "max_symbol_pos": tk.BooleanVar(m, True)},
                ".NY": {"max_gross_pos": tk.BooleanVar(m, True), "max_symbol_pos": tk.BooleanVar(m, True)},
                ".AM": {"max_gross_pos": tk.BooleanVar(m, True), "max_symbol_pos": tk.BooleanVar(m, True)},
                ".EU": {"max_gross_pos": tk.BooleanVar(m, True), "max_symbol_pos": tk.BooleanVar(m, True)},
            },
        }

        self.columnconfigure(0, weight=1)
        self.rowconfigure(0, weight=1)
        self._build_ui()
        self.load_from_disk(silent=True)
        self._bind_traces_for_autosave()

    def _int_spin(self, parent, var, step=1, width=14):
        return tb.Spinbox(parent, from_=-9_999_999, to=9_999_999, increment=step, width=width, textvariable=var)

    def _dbl_spin(self, parent, var, step=100.0, width=14):
        return tb.Spinbox(parent, from_=-1e9, to=1e9, increment=step, width=width, textvariable=var)

    def _bind_toggle_to_widget(self, toggle_var: tk.BooleanVar, widget):
        def apply_state(*_): widget.configure(state=("normal" if toggle_var.get() else "disabled"))
        toggle_var.trace_add("write", apply_state); apply_state()

    def _build_ui(self):
        sc = ScrollFrame(self)
        sc.grid(row=0, column=0, sticky="nsew")
        content = sc.body
        content.columnconfigure(0, weight=1)
        content.columnconfigure(1, weight=1)

        # --- Global Limits (left) ---
        g, tg = self.RISK_CFG["global"], self.RISK_CFG_TOGGLE["global"]
        global_frame = tb.LabelFrame(content, text="Global Limits", padding=8)
        global_frame.grid(row=0, column=0, sticky="nsew", padx=10, pady=10)
        rows = [
            ("Max gross position", "max_gross_pos", lambda p: self._int_spin(p, g["max_gross_pos"], 100)),
            ("Max distinct symbols", "max_symbols", lambda p: self._int_spin(p, g["max_symbols"], 1)),
            ("Max open orders", "max_open_orders", lambda p: self._int_spin(p, g["max_open_orders"], 5)),
            ("Max per-order buying power", "max_order_buying_power", lambda p: self._dbl_spin(p, g["max_order_buying_power"], 1000.0)),
            ("Daily unreal soft stop", "daily_unreal_soft_stop", lambda p: self._dbl_spin(p, g["daily_unreal_soft_stop"], 100.0)),
            ("Daily unreal hard stop", "daily_unreal_hard_stop", lambda p: self._dbl_spin(p, g["daily_unreal_hard_stop"], 100.0)),
        ]
        for i, (label, key, mkspin) in enumerate(rows):
            row = tb.Frame(global_frame); row.grid(row=i, column=0, sticky="w", pady=3)
            tb.Checkbutton(row, variable=tg[key], text="").pack(side="left", padx=(4,8))
            tb.Label(row, text=label, width=26, anchor="w").pack(side="left")
            spin = mkspin(row); spin.pack(side="left"); self._bind_toggle_to_widget(tg[key], spin)

        # --- Per-suffix Limits (left) ---
        suffix_frame = tb.LabelFrame(content, text="Per-suffix Limits", padding=8)
        suffix_frame.grid(row=1, column=0, sticky="nsew", padx=10, pady=10)
        header = tb.Frame(suffix_frame); header.grid(row=0, column=0, sticky="w", pady=(0,6))
        tb.Label(header, text="Suffix", width=8).pack(side="left", padx=4)
        tb.Label(header, text="Use", width=5).pack(side="left")
        tb.Label(header, text="Max gross pos", width=16).pack(side="left", padx=8)
        tb.Label(header, text="Use", width=5).pack(side="left")
        tb.Label(header, text="Max symbol pos", width=16).pack(side="left", padx=8)
        r=1
        for suf in [".NQ",".NY",".AM",".EU"]:
            row = tb.Frame(suffix_frame); row.grid(row=r, column=0, sticky="w", pady=2)
            tb.Label(row, text=suf, width=8).pack(side="left", padx=4)
            cbg = tb.Checkbutton(row, variable=self.RISK_CFG_TOGGLE["per_suffix"][suf]["max_gross_pos"], text=""); cbg.pack(side="left")
            spin_g = self._int_spin(row, self.RISK_CFG["per_suffix"][suf]["max_gross_pos"], 100, 12); spin_g.pack(side="left", padx=(8,8))
            self._bind_toggle_to_widget(self.RISK_CFG_TOGGLE["per_suffix"][suf]["max_gross_pos"], spin_g)
            cbs = tb.Checkbutton(row, variable=self.RISK_CFG_TOGGLE["per_suffix"][suf]["max_symbol_pos"], text=""); cbs.pack(side="left")
            spin_s = self._int_spin(row, self.RISK_CFG["per_suffix"][suf]["max_symbol_pos"], 50, 12); spin_s.pack(side="left", padx=(8,8))
            self._bind_toggle_to_widget(self.RISK_CFG_TOGGLE["per_suffix"][suf]["max_symbol_pos"], spin_s)
            r+=1

        # --- Per-algo Limits (right) ---
        a, ta = self.RISK_CFG["per_algo"], self.RISK_CFG_TOGGLE["per_algo"]
        algo_frame = tb.LabelFrame(content, text="Per-algo Limits", padding=8)
        algo_frame.grid(row=0, column=1, rowspan=2, sticky="nsew", padx=10, pady=10)
        rows = [
            ("Max distinct algos", "max_distinct_algos", lambda p: self._int_spin(p, a["max_distinct_algos"], 1)),
            ("Algo soft stop", "algo_soft_stop", lambda p: self._dbl_spin(p, a["algo_soft_stop"], 100.0)),
            ("Algo hard stop", "algo_hard_stop", lambda p: self._dbl_spin(p, a["algo_hard_stop"], 100.0)),
        ]
        for i, (label, key, mkspin) in enumerate(rows):
            row = tb.Frame(algo_frame); row.grid(row=i, column=0, sticky="w", pady=3)
            tb.Checkbutton(row, variable=ta[key], text="").pack(side="left", padx=(4,8))
            tb.Label(row, text=label, width=20, anchor="w").pack(side="left")
            spin = mkspin(row); spin.pack(side="left"); self._bind_toggle_to_widget(ta[key], spin)

        # Save/load buttons
        btns = tb.Frame(algo_frame); btns.grid(row=3, column=0, columnspan=2, sticky="ew", padx=6, pady=6)
        tb.Button(btns, text="Save Now", command=self.save_to_disk).pack(side="left", padx=4)
        tb.Button(btns, text="Load Now", command=self.load_from_disk).pack(side="left", padx=4)

    # --- autosave, serialize, save/load, helpers remain unchanged ---
    def _walk_vars(self, mapping: dict):
        for _, v in mapping.items():
            if isinstance(v, dict): yield from self._walk_vars(v)
            else: yield v
    def _bind_traces_for_autosave(self):
        def bind(v): 
            if isinstance(v, tk.Variable): v.trace_add("write", self._debounced_save)
        for v in self._walk_vars(self.RISK_CFG): bind(v)
        for v in self._walk_vars(self.RISK_CFG_TOGGLE): bind(v)
    def _debounced_save(self,*a):
        if self._save_after_id:
            try: self.after_cancel(self._save_after_id)
            except: pass
        self._save_after_id=self.after(500,self.save_to_disk)
    def _serialize(self, mapping: dict):
        out={}; 
        for k,v in mapping.items():
            out[k]=self._serialize(v) if isinstance(v,dict) else (v.get() if isinstance(v,tk.Variable) else v)
        return out
    def _apply(self,dst:dict,payload:dict):
        for k,v in payload.items():
            if k not in dst: continue
            if isinstance(dst[k],dict) and isinstance(v,dict): self._apply(dst[k],v)
            elif isinstance(dst[k],tk.Variable):
                try: dst[k].set(v)
                except: pass
    def save_to_disk(self):
        data={"_schema":"RiskPanel.v3","RISK_CFG":self._serialize(self.RISK_CFG),"RISK_CFG_TOGGLE":self._serialize(self.RISK_CFG_TOGGLE)}
        try:
            with open(self._autosave_file,"w",encoding="utf-8") as f: json.dump(data,f,indent=2)
        except Exception as e: print("[RiskPanel] save error:",e)
    def load_from_disk(self,silent=False):
        if not os.path.exists(self._autosave_file):
            if not silent: print("[RiskPanel] no file to load"); return
        try:
            with open(self._autosave_file,"r",encoding="utf-8") as f: data=json.load(f)
            self._apply(self.RISK_CFG,data.get("RISK_CFG",{}))
            self._apply(self.RISK_CFG_TOGGLE,data.get("RISK_CFG_TOGGLE",{}))
        except Exception as e: print("[RiskPanel] load error:",e)
    def effective_global(self,key,default=None):
        en=self.RISK_CFG_TOGGLE["global"][key].get(); val=self.RISK_CFG["global"][key].get()
        return val if en else default
    def effective_per_algo(self,key,default=None):
        en=self.RISK_CFG_TOGGLE["per_algo"][key].get(); val=self.RISK_CFG["per_algo"][key].get()
        return val if en else default
    def effective_per_suffix(self,suffix,key,default=None):
        en=self.RISK_CFG_TOGGLE["per_suffix"][suffix][key].get(); val=self.RISK_CFG["per_suffix"][suffix][key].get()
        return val if en else default
