# ui_quick_hedge_panel.py
# -*- coding: utf-8 -*-
import json
import tkinter as tk
import ttkbootstrap as tb
from ttkbootstrap.constants import *
from datetime import datetime
from math import isfinite
import os  


try:
    import requests
except Exception:
    requests = None  # allow demo without requests

LABEL_FONT = ("Segoe UI", 10)
TITLE_FONT = ("Segoe UI", 12, "bold")
MONO_FONT  = ("Consolas", 9)

HEDGE_TIERS = ("25", "50", "75", "100","150","200")  # percent

API_BASE = "http://10.29.10.174/api/Returns/getmultiplelogvalues"  # you provided

RECENT_PAIRS_PATH = os.path.join(os.path.dirname(__file__), "recent_pairs.json")

class QuickHedgePanel(tb.Frame):
    """
    QuickHedgePanel — Main/Hedge pair entry sized by risk exposure.

    Inputs
    - Main Ticker, Hedging Ticker
    - Shares of Main Ticker
    - Limit Price (optional)  <-- NEW
    - Main Side (Long/Short)
    - Hedge tier: 25/50/75/100 (%)
    - TP/SL (spread points), NBBO

    Ratios / Hedge sizing (per spec)
      exposure_main = main_shares * main.stdDevLogValues * main.todaysOpen
      hedge_shares  = exposure_main / (hedge.todaysOpen * hedge.stdDevLogValues * hedge_tier_fraction)
      Signs:
        - If main is LONG:   main +, hedge -
        - If main is SHORT:  main -, hedge +

    Fetch
      Calls:
        GET {API_BASE}?symbols={A},{B}&logPeriod=60
      Expects JSON array with objects:
        {"symbol","todaysOpen","stdDevLogValues","currentPrice", ...}
    """
    def __init__(self, ui, *, title=""):
        self.ui = ui
        super().__init__(ui.user_panels, padding=10)


        # ---------------- State ----------------
        disk_pairs = self._load_recent_pairs()

        if disk_pairs ==[]:
            disk_pairs = [("AAPL","QQQ"), ("SPY","QQQ")]

        self.recent_pairs = disk_pairs[:20]  # list[tuple[str,str]]
        self._logvals = {}


        self.suffix_cache = self._load_suffix_cache()
        # ---------------- Vars ----------------
        self.var_main     = tk.StringVar()
        self.var_hedge    = tk.StringVar()
        self.var_recent   = tk.StringVar(value="")
        self.var_side     = tk.StringVar(value="LONG")       # LONG / SHORT (for main)
        self.var_main_sh  = tk.StringVar(value="100")        # shares of main ticker
        self.var_limit_px = tk.StringVar(value="")           # <-- NEW
        self.var_tier     = tk.StringVar(value="100")        # 25 / 50 / 75 / 100
        self.var_tp_pts   = tk.StringVar(value="")
        self.var_sl_pts   = tk.StringVar(value="")
        self.var_nbbo     = tk.BooleanVar(value=True)

        # inline errors
        self._err_main  = tk.StringVar(value="")
        self._err_hedge = tk.StringVar(value="")
        self._form_err  = tk.StringVar(value="")
        self._fetch_ts  = tk.StringVar(value="")  # "Fetched 13:41"

        # build UI
        self._build_ui(title)
        self._wire_events()
        self._refresh_preview()

    # ===================== UI =====================
    def _build_ui(self, title):
        # Scrollable shell (like your TFM)
        shell = tb.Frame(self); shell.pack(fill=BOTH, expand=YES)
        canvas = tk.Canvas(shell, highlightthickness=0, bd=0)
        vbar   = tb.Scrollbar(shell, orient="vertical", command=canvas.yview)
        canvas.configure(yscrollcommand=vbar.set)
        canvas.pack(side=LEFT, fill=BOTH, expand=YES); vbar.pack(side=LEFT, fill=Y)

        parent = tb.Frame(canvas, padding=0)
        win_id = canvas.create_window((0, 0), window=parent, anchor="nw")
        parent.bind("<Configure>", lambda e: canvas.configure(scrollregion=canvas.bbox("all")))
        canvas.bind("<Configure>", lambda e: canvas.itemconfigure(win_id, width=e.width))

        def _onwheel(e): canvas.yview_scroll(int(-e.delta/120), "units")
        def _up(_):  canvas.yview_scroll(-1, "units")
        def _dn(_):  canvas.yview_scroll(+1, "units")
        canvas.bind("<Enter>", lambda _: (canvas.bind_all("<MouseWheel>", _onwheel),
                                          canvas.bind_all("<Button-4>", _up),
                                          canvas.bind_all("<Button-5>", _dn)))
        canvas.bind("<Leave>", lambda _: (canvas.unbind_all("<MouseWheel>"),
                                          canvas.unbind_all("<Button-4>"),
                                          canvas.unbind_all("<Button-5>")))

        # ---- Header ----
        head = tb.Frame(parent); head.pack(fill=X, pady=(0,6))
        #tb.Label(head, text=title, font=TITLE_FONT).pack(side=LEFT)

        # ---- Pair block ----
        frm = tb.Labelframe(parent, text="Pair", padding=8)
        frm.pack(fill=BOTH, expand=YES)

        vcmd_tkr   = (self.register(self._validate_ticker), "%P", "%W")
        vcmd_int   = (self.register(self._validate_int), "%P")
        vcmd_float = (self.register(self._validate_float), "%P")

        # Recent pairs
        if self.recent_pairs:
            tb.Label(frm, text="Recent Pairs", font=LABEL_FONT).pack(anchor=W)
            self.cbo_recent = tb.Combobox(frm, textvariable=self.var_recent, state="readonly",
                                          values=[f"{a}/{b}" for a,b in self.recent_pairs],
                                          bootstyle="secondary")
            self.cbo_recent.pack(fill=X, pady=(0,6))

        # Main / Hedge tickers (inline)
        row = tb.Frame(frm); row.pack(fill=X)
        colA = tb.Frame(row); colA.pack(side=LEFT, expand=YES, fill=X, padx=(0,4))
        colB = tb.Frame(row); colB.pack(side=LEFT, expand=YES, fill=X, padx=(4,0))

        tb.Label(colA, text="Main Ticker", font=LABEL_FONT).pack(anchor=W)
        self.ent_main = tb.Entry(colA, textvariable=self.var_main, justify=LEFT,
                                 validate="key", validatecommand=vcmd_tkr)
        self.ent_main.pack(fill=X)
        tb.Label(colA, textvariable=self._err_main, bootstyle="danger").pack(anchor=W)

        tb.Label(colB, text="Hedging Ticker", font=LABEL_FONT).pack(anchor=W)
        self.ent_hedge = tb.Entry(colB, textvariable=self.var_hedge, justify=LEFT,
                                  validate="key", validatecommand=vcmd_tkr)
        self.ent_hedge.pack(fill=X)
        tb.Label(colB, textvariable=self._err_hedge, bootstyle="danger").pack(anchor=W)

        tools = tb.Frame(frm); tools.pack(fill=X, pady=(6,0))
        # tb.Button(tools, text="Swap (Ctrl+S)", bootstyle="secondary", command=self._swap).pack(side=LEFT)
        tb.Button(colB, text="Refresh Ratios (Alt+R)", bootstyle="light", command=self._refresh_logvalues).pack(anchor=W)#.pack(side=LEFT, padx=6)
        tb.Label(tools, textvariable=self._fetch_ts, bootstyle="secondary").pack(side=LEFT, padx=6)

        # ---- Sizing & Side ----
        siz = tb.Labelframe(parent, text="Sizing & Hedge", padding=8)
        siz.pack(fill=BOTH, expand=YES)

        tb.Label(siz, text="Shares of Main Ticker", font=LABEL_FONT).pack(anchor=W)
        self.ent_main_sh = tb.Entry(siz, textvariable=self.var_main_sh, justify=LEFT, validate="key", validatecommand=vcmd_int)
        self.ent_main_sh.pack(fill=X, pady=(0,6))

        # NEW: Limit Price (optional) just below shares
        tb.Label(siz, text="Limit Price (optional)", font=LABEL_FONT).pack(anchor=W)
        self.ent_limit = tb.Entry(siz, textvariable=self.var_limit_px, justify=LEFT, validate="key", validatecommand=vcmd_float)
        self.ent_limit.pack(fill=X, pady=(0,6))

        tb.Label(siz, text="Main Position Side", font=LABEL_FONT).pack(anchor=W)
        side_row = tb.Frame(siz); side_row.pack(fill=X, pady=(2,6))
        tb.Radiobutton(side_row, text="Long",  value="LONG",
                       variable=self.var_side, bootstyle="success-toolbutton").pack(side=LEFT, expand=YES, fill=X, padx=(0,4))
        tb.Radiobutton(side_row, text="Short", value="SHORT",
                       variable=self.var_side, bootstyle="danger-toolbutton").pack(side=LEFT, expand=YES, fill=X)

        tb.Label(siz, text="Hedging Coverage", font=LABEL_FONT).pack(anchor=W)
        tier_row = tb.Frame(siz); tier_row.pack(fill=X, pady=(2,6))
        for pct in HEDGE_TIERS:
            tb.Radiobutton(tier_row, text=f"{pct}%", value=pct,
                           variable=self.var_tier, bootstyle="secondary-toolbutton").pack(side=LEFT, expand=YES, fill=X, padx=2)

        # ---- Risk controls ----
        row2 = tb.Frame(siz); row2.pack(fill=X)
        colTP = tb.Frame(row2); colTP.pack(side=LEFT, expand=YES, fill=X, padx=(0,4))
        colSL = tb.Frame(row2); colSL.pack(side=LEFT, expand=YES, fill=X, padx=(4,0))

        tb.Label(colTP, text="Profit (Total $)", font=LABEL_FONT).pack(anchor=W)
        self.ent_tp = tb.Entry(colTP, textvariable=self.var_tp_pts, justify=LEFT, validate="key", validatecommand=vcmd_float)
        self.ent_tp.pack(fill=X)

        tb.Label(colSL, text="Stop (Total $)", font=LABEL_FONT).pack(anchor=W)
        self.ent_sl = tb.Entry(colSL, textvariable=self.var_sl_pts, justify=LEFT, validate="key", validatecommand=vcmd_float)
        self.ent_sl.pack(fill=X)

        # form-level error
        tb.Label(siz, textvariable=self._form_err, bootstyle="danger").pack(anchor=W, pady=(6,0))

        # ---- Preview ----
        prev = tb.Labelframe(parent, text="Preview", padding=8)
        prev.pack(fill=BOTH, expand=YES, pady=(8,0))
        self.txt_preview = tk.Text(prev, height=13, wrap="word", font=MONO_FONT, relief="flat", bd=0, padx=4, pady=4)
        self.txt_preview.pack(fill=BOTH, expand=YES)

        # ---- Buttons ----
        btns = tb.Frame(parent); btns.pack(fill=X, pady=(8,0))
        self.btn_submit = tb.Button(btns, text="Submit Hedge (Ctrl+Enter)", bootstyle="primary", command=self._noop_submit)
        self.btn_submit.pack(fill=X)
        tb.Button(btns, text="Reset", bootstyle="light", command=self._reset).pack(fill=X, pady=(6,0))

    def _build_ui(self, title):
        # Scrollable shell (like your TFM)
        shell = tb.Frame(self); shell.pack(fill=BOTH, expand=YES)
        canvas = tk.Canvas(shell, highlightthickness=0, bd=0)
        vbar   = tb.Scrollbar(shell, orient="vertical", command=canvas.yview)
        canvas.configure(yscrollcommand=vbar.set)
        canvas.pack(side=LEFT, fill=BOTH, expand=YES); vbar.pack(side=LEFT, fill=Y)

        parent = tb.Frame(canvas, padding=0)
        win_id = canvas.create_window((0, 0), window=parent, anchor="nw")
        parent.bind("<Configure>", lambda e: canvas.configure(scrollregion=canvas.bbox("all")))
        canvas.bind("<Configure>", lambda e: canvas.itemconfigure(win_id, width=e.width))

        def _onwheel(e): canvas.yview_scroll(int(-e.delta/120), "units")
        def _up(_):  canvas.yview_scroll(-1, "units")
        def _dn(_):  canvas.yview_scroll(+1, "units")
        canvas.bind("<Enter>", lambda _: (canvas.bind_all("<MouseWheel>", _onwheel),
                                          canvas.bind_all("<Button-4>", _up),
                                          canvas.bind_all("<Button-5>", _dn)))
        canvas.bind("<Leave>", lambda _: (canvas.unbind_all("<MouseWheel>"),
                                          canvas.unbind_all("<Button-4>"),
                                          canvas.unbind_all("<Button-5>")))

        # ---- Header ----
        head = tb.Frame(parent); head.pack(fill=X, pady=(0,6))
        # tb.Label(head, text=title, font=TITLE_FONT).pack(side=LEFT)

        # ---- Pair block ----
        frm = tb.Labelframe(parent, text="Pair", padding=8)
        frm.pack(fill=BOTH, expand=YES)

        vcmd_tkr   = (self.register(self._validate_ticker), "%P", "%W")
        vcmd_int   = (self.register(self._validate_int), "%P")
        vcmd_float = (self.register(self._validate_float), "%P")

        # Recent pairs
        if self.recent_pairs:
            tb.Label(frm, text="Recent Pairs", font=LABEL_FONT).pack(anchor=W)
            self.cbo_recent = tb.Combobox(
                frm, textvariable=self.var_recent, state="readonly",
                values=[f"{a}/{b}" for a,b in self.recent_pairs],
                bootstyle="secondary"
            )
            self.cbo_recent.pack(fill=X, pady=(0,6))

        # --- Main/Hedge/Refresh in ONE ROW (aligned heights) ---
        row = tb.Frame(frm); row.pack(fill=X)
        for c in (0, 1):  # let the two entry columns expand
            row.columnconfigure(c, weight=1, uniform="mh")
        row.columnconfigure(2, weight=0)  # refresh button column

        # row layout: r0 labels, r1 entries+button (aligned), r2 error/status
        # Main
        tb.Label(row, text="Main Ticker", font=LABEL_FONT).grid(row=0, column=0, sticky=W)
        self.ent_main = tb.Entry(row, textvariable=self.var_main, justify=LEFT,
                                 validate="key", validatecommand=vcmd_tkr)
        self.ent_main.grid(row=1, column=0, sticky=EW, padx=(0,4))
        tb.Label(row, textvariable=self._err_main, bootstyle="danger").grid(row=2, column=0, sticky=W)

        # Hedge
        tb.Label(row, text="Hedging Ticker", font=LABEL_FONT).grid(row=0, column=1, sticky=W)
        self.ent_hedge = tb.Entry(row, textvariable=self.var_hedge, justify=LEFT,
                                  validate="key", validatecommand=vcmd_tkr)
        self.ent_hedge.grid(row=1, column=1, sticky=EW, padx=(4,0))
        tb.Label(row, textvariable=self._err_hedge, bootstyle="danger").grid(row=2, column=1, sticky=W)

        # Refresh (same height as entries)
        self.btn_refresh = tb.Button(
            row, text="Refresh Ratios (Alt+R)", bootstyle="light",
            command=self._refresh_logvalues
        )
        # align vertically with the entry row
        self.btn_refresh.grid(row=1, column=2, sticky=EW, padx=(8,0))
        tb.Label(row, textvariable=self._fetch_ts, bootstyle="secondary").grid(row=2, column=2, sticky=W, padx=(8,0))

        # ---- Sizing & Side ----
        siz = tb.Labelframe(parent, text="Sizing & Hedge", padding=8)
        siz.pack(fill=BOTH, expand=YES)

        tb.Label(siz, text="Shares of Main Ticker", font=LABEL_FONT).pack(anchor=W)
        self.ent_main_sh = tb.Entry(siz, textvariable=self.var_main_sh, justify=LEFT,
                                    validate="key", validatecommand=vcmd_int)
        self.ent_main_sh.pack(fill=X, pady=(0,6))

        # NEW: Limit Price (optional) just below shares
        tb.Label(siz, text="Limit Price (optional)", font=LABEL_FONT).pack(anchor=W)
        self.ent_limit = tb.Entry(siz, textvariable=self.var_limit_px, justify=LEFT,
                                  validate="key", validatecommand=vcmd_float)
        self.ent_limit.pack(fill=X, pady=(0,6))

        tb.Label(siz, text="Main Position Side", font=LABEL_FONT).pack(anchor=W)
        side_row = tb.Frame(siz); side_row.pack(fill=X, pady=(2,6))
        tb.Radiobutton(side_row, text="Long",  value="LONG",
                       variable=self.var_side, bootstyle="success-toolbutton").pack(side=LEFT, expand=YES, fill=X, padx=(0,4))
        tb.Radiobutton(side_row, text="Short", value="SHORT",
                       variable=self.var_side, bootstyle="danger-toolbutton").pack(side=LEFT, expand=YES, fill=X)

        tb.Label(siz, text="Hedging Percentage", font=LABEL_FONT).pack(anchor=W)
        tier_row = tb.Frame(siz); tier_row.pack(fill=X, pady=(2,6))
        for pct in HEDGE_TIERS:
            tb.Radiobutton(tier_row, text=f"{pct}%", value=pct,
                           variable=self.var_tier, bootstyle="secondary-toolbutton").pack(side=LEFT, expand=YES, fill=X, padx=2)

        # ---- Risk controls ----
        row2 = tb.Frame(siz); row2.pack(fill=X)
        colTP = tb.Frame(row2); colTP.pack(side=LEFT, expand=YES, fill=X, padx=(0,4))
        colSL = tb.Frame(row2); colSL.pack(side=LEFT, expand=YES, fill=X, padx=(4,0))

        tb.Label(colTP, text="Profit (Total $)", font=LABEL_FONT).pack(anchor=W)
        self.ent_tp = tb.Entry(colTP, textvariable=self.var_tp_pts, justify=LEFT,
                               validate="key", validatecommand=vcmd_float)
        self.ent_tp.pack(fill=X)

        tb.Label(colSL, text="Stop (Total $)", font=LABEL_FONT).pack(anchor=W)
        self.ent_sl = tb.Entry(colSL, textvariable=self.var_sl_pts, justify=LEFT,
                               validate="key", validatecommand=vcmd_float)
        self.ent_sl.pack(fill=X)

        # form-level error
        tb.Label(siz, textvariable=self._form_err, bootstyle="danger").pack(anchor=W, pady=(6,0))

        # ---- Preview ----
        prev = tb.Labelframe(parent, text="Preview", padding=8)
        prev.pack(fill=BOTH, expand=YES, pady=(8,0))
        self.txt_preview = tk.Text(prev, height=13, wrap="word", font=MONO_FONT,
                                   relief="flat", bd=0, padx=4, pady=4)
        self.txt_preview.pack(fill=BOTH, expand=YES)

        # ---- Buttons ----
        btns = tb.Frame(parent); btns.pack(fill=X, pady=(8,0))
        self.btn_submit = tb.Button(btns, text="Submit Hedge (Ctrl+Enter)",
                                    bootstyle="primary", command=self._noop_submit)
        self.btn_submit.pack(fill=X)
        tb.Button(btns, text="Reset", bootstyle="light", command=self._reset).pack(fill=X, pady=(6,0))

    # ===================== Events / Validation =====================
    def _wire_events(self):
        # auto-uppercase tickers
        self.var_main.trace_add("write", lambda *_: self._upper(self.var_main))
        self.var_hedge.trace_add("write", lambda *_: self._upper(self.var_hedge))

        # refresh preview whenever inputs change
        for v in (self.var_main, self.var_hedge, self.var_side, self.var_main_sh,
                  self.var_limit_px,  # <-- NEW
                  self.var_tier, self.var_tp_pts, self.var_sl_pts, self.var_nbbo):
            v.trace_add("write", lambda *_: self._refresh_preview())

        # recent pairs select -> populate
        if hasattr(self, "cbo_recent"):
            self.cbo_recent.bind("<<ComboboxSelected>>", self._apply_recent)

        # enter flow
        self.ent_main.bind("<Return>", lambda e: self.ent_hedge.focus_set())
        self.ent_hedge.bind("<Return>", lambda e: self.ent_main_sh.focus_set())
        self.ent_main_sh.bind("<Return>", lambda e: self.ent_limit.focus_set())  # handy step into limit

        # hotkeys
        top = self.winfo_toplevel()
        top.bind_all("<Control-s>", lambda e: self._swap())
        top.bind_all("<Alt-Return>", lambda e: self.btn_submit.invoke())
        top.bind_all("<Alt-r>", lambda e: self._refresh_logvalues())

    def _upper(self, var):
        v = var.get(); u = v.upper()
        if v != u: var.set(u)

    def _validate_ticker(self, newval: str, widget: str) -> bool:
        ok = (newval == "" or newval.isalpha())
        if "main" in widget.lower():
            self._err_main.set("" if (ok or newval == "") else "Letters only (A–Z).")
        else:
            self._err_hedge.set("" if (ok or newval == "") else "Letters only (A–Z).")
        return ok

    def _validate_int(self, s: str) -> bool:
        return s == "" or s.isdigit()

    def _validate_float(self, s: str) -> bool:
        if s == "": return True
        if s.count(".") > 1: return False
        return all(p.isdigit() for p in s.split(".") if p != "")

    def _is_float(self, s):
        try: float(s); return True
        except: return False

    def _form_ok(self):
        A = self.var_main.get().strip()
        B = self.var_hedge.get().strip()
        if not A:
            self._err_main.set("Main ticker required."); return False
        if not B:
            self._err_hedge.set("Hedging ticker required."); return False
        if A == B:
            self._form_err.set("Main and Hedging tickers must differ."); return False
        if not (self.var_main_sh.get().isdigit() and int(self.var_main_sh.get()) > 0):
            self._form_err.set("Shares of Main must be a positive whole number."); return False
        # require fetched log values
        if A not in self._logvals or B not in self._logvals:
            self._form_err.set("Fetch ratios first (Alt+R)."); return False

        # limit price validation (optional)
        lp = self.var_limit_px.get().strip()
        if lp and not self._is_float(lp):
            self._form_err.set("Limit Price must be a number (or leave blank)."); return False

        self._form_err.set("")
        return True

    # ===================== Fetch & Math =====================
    def _refresh_logvalues(self):
        """Fetch today's open and stdDev for both tickers and cache them."""
        main = self.var_main.get().strip().upper()
        hedge = self.var_hedge.get().strip().upper()
        if not main or not hedge:
            self._form_err.set("Enter both tickers before refresh."); 
            self._refresh_preview()
            return

        try:
            data = self._fetch_log_values([main, hedge])
            for rec in data:
                sym = rec.get("symbol", "").upper()
                if not sym: 
                    continue
                self._logvals[sym] = {
                    "todaysOpen": float(rec.get("todaysOpen", 0) or 0.0),
                    "stdDevLogValues": float(rec.get("stdDevLogValues", 0) or 0.0),
                    "currentPrice": float(rec.get("currentPrice", 0) or 0.0),
                    "normalized": float(rec.get("normalized", 0) or 0.0),
                }
            self._fetch_ts.set("Fetched " + datetime.now().strftime("%H:%M"))
        except Exception as e:
            self._form_err.set(f"Refresh failed: {e}")
        self._refresh_preview()

    def _fetch_log_values(self, symbols):
        """
        symbols: list[str] -> calls the API and returns parsed JSON list.
        """
        if requests is None:
            # fallback for environments without requests (demo)
            # you can remove this block in production
            fallback = []
            for s in symbols:
                fallback.append({
                    "symbol": s,
                    "currentPrice": 100.0,
                    "todaysOpen": 100.0,
                    "stdDevLogValues": 0.01,
                    "currentLogValue": 0.0,
                    "normalized": 0.0,
                    "normalizedHigh": 0.0,
                    "normalizedLow": 0.0,
                })
            return fallback

        qs = ",".join(symbols)
        url = f"{API_BASE}?symbols={qs}&logPeriod=60"
        resp = requests.get(url, timeout=2.5)
        resp.raise_for_status()
        data = resp.json()
        if not isinstance(data, list):
            raise ValueError("Unexpected API response (not a list).")
        return data

    def _calc_shares(self):
        """
        exposure_main = main_shares * main.stdDevLogValues * main.todaysOpen
        hedge_shares  = exposure_main / (hedge.todaysOpen * hedge.stdDevLogValues * tier_fraction)

        Returns signed (main_shares_signed, hedge_shares_signed).
        """
        A = self.var_main.get().strip().upper()
        B = self.var_hedge.get().strip().upper()
        main_info  = self._logvals.get(A, {})
        hedge_info = self._logvals.get(B, {})

        m_open = float(main_info.get("todaysOpen", 0) or 0.0)
        m_std  = float(main_info.get("stdDevLogValues", 0) or 0.0)
        h_open = float(hedge_info.get("todaysOpen", 0) or 0.0)
        h_std  = float(hedge_info.get("stdDevLogValues", 0) or 0.0)

        try:
            main_shares = int(self.var_main_sh.get() or "0")
        except:
            main_shares = 0

        tier_fraction = max(0.01, min(2.0, (float(self.var_tier.get() or "100") / 100.0)))


        # guard: avoid division by zero, non-finite values
        exposure = main_shares * m_std * m_open if (main_shares and m_std and m_open) else 0.0
        denom    = (h_open * h_std) if (h_open and h_std and tier_fraction) else 0.0
        hedge_abs = 0
        if denom and isfinite(exposure * tier_fraction / denom):
            hedge_abs = int(round(exposure * tier_fraction / denom))
            if hedge_abs < 1: hedge_abs = 1  # at least 1 share if hedging is requested

        if self.var_side.get() == "LONG":
            main_signed  = +main_shares
            hedge_signed = -hedge_abs
        else:
            main_signed  = -main_shares
            hedge_signed = +hedge_abs

        return (main_signed, hedge_signed, exposure, denom)

    # ===================== Helpers / UI actions =====================
    def _apply_recent(self, *_):
        s = self.var_recent.get()
        try:
            A,B = s.split("/")
            self.var_main.set(A.strip()); self.var_hedge.set(B.strip())
            self._refresh_logvalues()
        except Exception:
            pass

    def _swap(self):
        A = self.var_main.get(); B = self.var_hedge.get()
        self.var_main.set(B); self.var_hedge.set(A)
        # Keep side the same (side applies to "Main"). Swap implies same side now applies to the new main.
        self._refresh_logvalues()

    def _reset(self):
        self.var_main.set(""); self.var_hedge.set("")
        self.var_side.set("LONG")
        self.var_main_sh.set("100")
        self.var_limit_px.set("")  # <-- NEW
        self.var_tier.set("100")
        self.var_tp_pts.set(""); self.var_sl_pts.set("")
        self._err_main.set(""); self._err_hedge.set(""); self._form_err.set("")
        self._fetch_ts.set("")
        self._refresh_preview()

    def _persist_recent(self, pair):
        # move-to-front MRU; cap 20
        self.recent_pairs = [p for p in self.recent_pairs if p != pair]
        self.recent_pairs.insert(0, pair)
        if len(self.recent_pairs) > 20:
            self.recent_pairs = self.recent_pairs[:20]

        # refresh combobox (create if needed)
        if hasattr(self, "cbo_recent"):
            self.cbo_recent.configure(values=[f"""{a.split(".")[0]}/{b.split(".")[0]}""" for a, b in self.recent_pairs])
        else:
            # If there was none because list was empty at init, add it now
            # (optional QoL: only if you want it to appear dynamically)
            pass

        # save to disk
        self._save_recent_pairs()

    # ===================== Preview / Submit =====================
    def _preview_dict(self):
        A = self.var_main.get().strip().upper()
        B = self.var_hedge.get().strip().upper()
        main_signed, hedge_signed, exposure, denom = self._calc_shares()

        main = self._logvals.get(A, {})
        hedge = self._logvals.get(B, {})

        pv = {
            "pair": f"{A}/{B}",
            "main_side": self.var_side.get(),
            "shares": {"main": main_signed, "hedge": hedge_signed},
            "limit_price": (float(self.var_limit_px.get()) if self.var_limit_px.get().strip() else None),  # <-- NEW
            "hedge_tier_pct": int(self.var_tier.get() or "100"),
            "tp_spread": float(self.var_tp_pts.get()) if self.var_tp_pts.get().strip() else None,
            "sl_spread": float(self.var_sl_pts.get()) if self.var_sl_pts.get().strip() else None,
            "nbbo_only": bool(self.var_nbbo.get()),
            "exposure_main": exposure,
            "denominator": denom,
            "main_vals": {"todaysOpen": main.get("todaysOpen"), "stdDevLogValues": main.get("stdDevLogValues")},
            "hedge_vals":{"todaysOpen": hedge.get("todaysOpen"), "stdDevLogValues": hedge.get("stdDevLogValues")},
        }
        return pv

    def _refresh_preview(self):
        ok = self._form_ok()  # sets _form_err
        pv = self._preview_dict()

        m_open = pv["main_vals"]["todaysOpen"]
        m_std  = pv["main_vals"]["stdDevLogValues"]
        h_open = pv["hedge_vals"]["todaysOpen"]
        h_std  = pv["hedge_vals"]["stdDevLogValues"]

        lines = [
            "Quick Hedge Preview",
            "===================",
            f"Pair:                  {pv['pair']}",
            f"Main Side:             {pv['main_side']}",
            f"Shares (Main/Hedge):   {pv['shares']['main']} / {pv['shares']['hedge']}",
            f"Limit Price:           {pv['limit_price'] if pv['limit_price'] is not None else '—'}",  # <-- NEW
            f"Hedging Percentage:          {pv['hedge_tier_pct']}%",
            f"Main (open,std):       {m_open if m_open is not None else '—'} , {str(round(m_std*100,2))+'%' if m_std is not None else '—'}",
            f"Hedge (open,std):      {h_open if h_open is not None else '—'} , {str(round(h_std*100,2))+'%' if h_std is not None else '—'}",
            # f"Main Ticker Risk Exposure:{pv['exposure_main']:.1f} $" if isinstance(pv['exposure_main'], (int,float)) else "Exposure (main): —",
            # f"Estimate Total Risk Exposure:{pv['exposure_main']:.1f} $" if isinstance(pv['exposure_main'], (int,float)) else "Exposure (main): —",
            f"Profit:       {pv['tp_spread'] if pv['tp_spread'] is not None else '—'}",
            f"Stop:       {pv['sl_spread'] if pv['sl_spread'] is not None else '—'}",

        ]
        if self._form_err.get():
            lines.append("")
            lines.append(self._form_err.get())

        self.txt_preview.configure(state="normal")
        self.txt_preview.delete("1.0", "end")
        self.txt_preview.insert("1.0", "\n".join(lines))
        self.txt_preview.configure(state="disabled")
        self.btn_submit.configure(state=(NORMAL if ok else DISABLED))

    def _noop_submit(self):
        if not self._form_ok():
            self._refresh_preview()
            return

        pv = self._preview_dict()
        # print(pv)
        # print(pv['tp_spread'])
        # Raw inputs (keep originals for tie-break)
        A_raw = self.var_main.get().strip()
        B_raw = self.var_hedge.get().strip()
        A = A_raw.upper()
        B = B_raw.upper()


        A = self.get_suffix(A)
        B = self.get_suffix(B)
        if not A or not B:
            # service either returned no suffix or the symbol doesn't exist
            self._err_ticker.set("Ticker does not exist.")
            self._form_err.set("Ticker does not exist.")
            return
        # Shares as computed by preview (could be ±)
        sh_main  = int(pv["shares"]["main"])
        sh_hedge = int(pv["shares"]["hedge"])

        # Map shares to symbols as-entered
        shares_by_symbol = {
            A: sh_main,
            B: sh_hedge,
        }

        # Choose MAIN = larger |shares| ; tie -> keep user's original "Main"
        if abs(shares_by_symbol[B]) > abs(shares_by_symbol[A]):
            main_sym, hedge_sym = B, A
        else:
            main_sym, hedge_sym = A, B

        # Build orders: send only MAIN (as per your current flow), with optional limit
        orders = {
            main_sym: {"share": int(shares_by_symbol[main_sym])}
        }
        
        if pv.get("limit_price") is not None:
            orders[main_sym]["limit"] = pv["limit_price"]

        # Info block: include both legs
        info = {"hedge": {}}
        info["hedge"][A] = sh_main     # preserve original casing if you prefer
        info["hedge"][B] = sh_hedge
        info["Tag"] = "QuickHedge"
        info["hedge"] = dict(sorted(info["hedge"] .items(), key=lambda kv: abs(kv[1]), reverse=True))



        if pv['tp_spread']:
            info['Profit'] = pv['tp_spread']
            info['Fullout'] = 1
        if pv['sl_spread']:
            info['Stop'] = pv['sl_spread']
        # Algo name uses chosen MAIN first
        algo_name = f"QH_{self.var_main.get()}-{self.var_hedge.get()}"
        
        if not hasattr(self, "algo_count"):
            self.algo_count = {}
        if algo_name not in self.algo_count:
            self.algo_count[algo_name] = 0
        else:
            self.algo_count[algo_name] += 1
            algo_name += str(self.algo_count[algo_name])
        # Persist MRU (MAIN first)
        self._persist_recent((main_sym, hedge_sym))

        try:
            print(algo_name, orders, info)
            
            self.ui.manager.apply_basket_cmd(algo_name, orders, info)
            self._form_err.set("Hedge submitted.")
        except Exception as e:
            self._form_err.set(f"Submit failed: {e}")

        self._refresh_preview()

    def _pairs_to_json(self):
        """Return JSON-serializable list like [['AAPL','QQQ'], ['SPY','QQQ']]"""
        return [[a, b] for (a, b) in self.recent_pairs]

    def _json_to_pairs(self, data):
        out = []
        for item in (data or []):
            try:
                a, b = item[0].strip().upper(), item[1].strip().upper()
                if a and b and a.isalpha() and b.isalpha() and a != b:
                    out.append((a, b))
            except Exception:
                continue
        return out

    def _load_recent_pairs(self):
        try:
            if os.path.exists(RECENT_PAIRS_PATH):
                with open(RECENT_PAIRS_PATH, "r", encoding="utf-8") as f:
                    data = json.load(f)
                return self._json_to_pairs(data)
        except Exception:
            pass
        return []

    def _save_recent_pairs(self):
        try:
            with open(RECENT_PAIRS_PATH, "w", encoding="utf-8") as f:
                json.dump(self._pairs_to_json(), f, ensure_ascii=False, indent=2)
        except Exception:
            # Non-fatal: ignore disk errors for trading UI
            pass

    # ---------- Fullsymbol cache helpers ----------


    def get_suffix(self, base_symbol: str) -> str | None:
        """
        Resolve a bare ticker to fullsymbol via cache or HTTP.
        Returns fullsymbol like 'SPY.AM' or None if invalid/non-existent.
        """
        base = (base_symbol or "").strip().upper()
        if not base:
            return None

        # 1) cache hit?
        fs = self.suffix_cache.get(base)
        if isinstance(fs, str) and "." in fs and fs.startswith(base):
            return fs

        # 2) query the service
        url = f"http://10.29.10.174/api/Symbol/fullsymbol/{base}?chartPeriod=1&chartType=m"
        try:
            r = requests.get(url, timeout=2.5)
            if not r.ok:
                return None
            fullsymbol = (r.text or "").strip().upper()
            # valid if it includes a market suffix and begins with the base ticker
            if "." in fullsymbol and fullsymbol.startswith(base):
                self.suffix_cache[base] = fullsymbol
                self._save_suffix_cache()
                return fullsymbol
            # if service comes back WITHOUT a suffix -> treat as invalid
            return None
        except Exception as e:
            print("get_suffix error:", e)
            return None

    def _cache_path(self):
        # local file beside this module; adjust if desired
        return os.path.join(os.path.dirname(__file__), "suffix_cache.json")

    def _load_suffix_cache(self):
        try:
            with open(self._cache_path(), "r", encoding="utf-8") as f:
                data = json.load(f)
                # sanity: keep only "AAA":"AAA.XY" mappings
                if isinstance(data, dict):
                    return {k.upper(): str(v).upper() for k, v in data.items() if isinstance(k, str)}
        except Exception:
            pass
        return {}

    def _save_suffix_cache(self):
        try:
            with open(self._cache_path(), "w", encoding="utf-8") as f:
                json.dump(self.suffix_cache, f, ensure_ascii=False, indent=2)
        except Exception as e:
            # non-fatal: cache write failure shouldn't block orders
            print("suffix cache save error:", e)
# ----- Standalone demo -----
if __name__ == "__main__":
    class DummyManager:
        def __init__(self, root):
            self.USER = tk.StringVar(value="DEMOUSER")
        def ratio(self, symbol):
            # dummy: pretend ratio ≈ price proxy
            return {"AAPL": 190.0, "MSFT": 420.0, "SPY": 560.0, "QQQ": 490.0}.get(symbol, 100.0)
        def apply_basket_cmd(self, algo_name, orders, info):
            print("\n[apply_basket_cmd]")
            print("  algo_name:", algo_name)
            print("  orders   :", orders)
            print("  info     :", info)

    class DummyUI:
        def __init__(self, root):
            self.manager = DummyManager(root)
            self.user_panels = tb.Frame(root); self.user_panels.pack(fill=BOTH, expand=YES, padx=10, pady=10)

    app = tb.Window(themename="flatly")
    app.title("Quick Spread (UI Demo)")
    app.geometry("380x900")
    ui = DummyUI(app)
    panel = QuickHedgePanel(ui)
    panel.pack(fill=BOTH, expand=YES)
    app.mainloop()
