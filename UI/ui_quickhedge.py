# ui_quick_hedge_panel.py
# -*- coding: utf-8 -*-
import json
import tkinter as tk
import ttkbootstrap as tb
from ttkbootstrap.constants import *
from datetime import datetime
from math import isfinite

try:
    import requests
except Exception:
    requests = None  # allow demo without requests

LABEL_FONT = ("Segoe UI", 10)
TITLE_FONT = ("Segoe UI", 12, "bold")
MONO_FONT  = ("Consolas", 9)

HEDGE_TIERS = ("25", "50", "75", "100")  # percent

API_BASE = "http://10.29.10.143/api/Returns/getmultiplelogvalues"  # you provided

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
    def __init__(self, ui, *, title="Quick Hedge", recent_pairs=None):
        self.ui = ui
        super().__init__(ui.user_panels, padding=10)

        # ---------------- State ----------------
        self.recent_pairs = list(recent_pairs or [])[:20]  # list[tuple[str,str]]
        self._logvals = {}  # symbol -> {"todaysOpen": float, "stdDevLogValues": float, ...}

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
        tb.Label(head, text=title, font=TITLE_FONT).pack(side=LEFT)

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
        tb.Button(tools, text="Swap (Ctrl+S)", bootstyle="secondary", command=self._swap).pack(side=LEFT)
        tb.Button(tools, text="Refresh Ratios (Alt+R)", bootstyle="light", command=self._refresh_logvalues).pack(side=LEFT, padx=6)
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

        tb.Label(siz, text="Hedging Tier", font=LABEL_FONT).pack(anchor=W)
        tier_row = tb.Frame(siz); tier_row.pack(fill=X, pady=(2,6))
        for pct in HEDGE_TIERS:
            tb.Radiobutton(tier_row, text=f"{pct}%", value=pct,
                           variable=self.var_tier, bootstyle="secondary-toolbutton").pack(side=LEFT, expand=YES, fill=X, padx=2)

        # ---- Risk controls ----
        row2 = tb.Frame(siz); row2.pack(fill=X)
        colTP = tb.Frame(row2); colTP.pack(side=LEFT, expand=YES, fill=X, padx=(0,4))
        colSL = tb.Frame(row2); colSL.pack(side=LEFT, expand=YES, fill=X, padx=(4,0))

        tb.Label(colTP, text="Take Profit (spread pts)", font=LABEL_FONT).pack(anchor=W)
        self.ent_tp = tb.Entry(colTP, textvariable=self.var_tp_pts, justify=LEFT, validate="key", validatecommand=vcmd_float)
        self.ent_tp.pack(fill=X)

        tb.Label(colSL, text="Stop Loss (spread pts)", font=LABEL_FONT).pack(anchor=W)
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

        tier_fraction = max(0.01, min(1.0, (float(self.var_tier.get() or "100") / 100.0)))

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
        if hasattr(self, "cbo_recent"):
            self.cbo_recent.configure(values=[f"{a}/{b}" for a,b in self.recent_pairs])

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
            f"Main (open,std):       {m_open if m_open is not None else '—'} , {m_std if m_std is not None else '—'}",
            f"Hedge (open,std):      {h_open if h_open is not None else '—'} , {h_std if h_std is not None else '—'}",
            f"Main Ticker Risk Exposure:{pv['exposure_main']:.6f}" if isinstance(pv['exposure_main'], (int,float)) else "Exposure (main): —",
            f"Denominator:           {pv['denominator']:.6f}" if isinstance(pv['denominator'], (int,float)) else "Denominator: —",
            f"TP (spread pts):       {pv['tp_spread'] if pv['tp_spread'] is not None else '—'}",
            f"SL (spread pts):       {pv['sl_spread'] if pv['sl_spread'] is not None else '—'}",
            f"NBBO only:             {pv['nbbo_only']}",
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
        A, B = self.var_main.get().strip().upper(), self.var_hedge.get().strip().upper()
        ts = datetime.now().strftime("%H:%M")

        algo_name = f"QH_{A}-{B}:{pv['main_side']}"
        orders = {
            A: {"share": int(pv["shares"]["main"])},
            B: {"share": int(pv["shares"]["hedge"])},
        }
        # Attach limit price to MAIN order if provided
        if pv["limit_price"] is not None:
            orders[A]["limit"] = pv["limit_price"]

        info = {
            "Pair": f"{A}/{B}",
            "MainSide": pv["main_side"],
            "HedgeTierPct": pv["hedge_tier_pct"],
            "TP_spread": pv["tp_spread"],
            "SL_spread": pv["sl_spread"],
            "NBBO": pv["nbbo_only"],
            "ExposureMain": pv["exposure_main"],
            "Denominator": pv["denominator"],
            "MainVals": pv["main_vals"],
            "HedgeVals": pv["hedge_vals"],
            "ts": ts
        }

        # persist MRU ≤20
        self._persist_recent((A, B))

        try:
            self.ui.manager.apply_basket_cmd(algo_name, orders, info)
            self._form_err.set("Hedge submitted.")
        except Exception as e:
            self._form_err.set(f"Submit failed: {e}")
        self._refresh_preview()


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
    panel = QuickHedgePanel(ui, recent_pairs=[("AAPL","MSFT"), ("SPY","QQQ")])
    panel.pack(fill=BOTH, expand=YES)
    app.mainloop()
