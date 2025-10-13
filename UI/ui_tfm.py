# ui_tfm_panel_narrow_v8.py
import os
import json
import requests
import tkinter as tk
import ttkbootstrap as tb
from ttkbootstrap.constants import *
from datetime import datetime
import traceback

LABEL_FONT = ("Segoe UI", 10)
TITLE_FONT = ("Segoe UI", 12, "bold")
MONO_FONT  = ("Consolas", 9)

class TFMPanel(tb.Frame):
    def __init__(self, ui, *, title=""):

        self.ui=ui
        super().__init__(ui.user_panels, padding=10)

        # load fullsymbol cache before building UI
        self.suffix_cache = self._load_suffix_cache()

        # load recent tickers MRU before building UI
        self.recent_tickers = self._load_recent_tickers()

        self._build_vars()
        self._build_ui(title)
        self._wire_events()
        self._refresh_preview()

        self.algo_count = {}

    # ---------------- Vars ----------------
    def _build_vars(self):
        self.var_ticker   = tk.StringVar()              # letters only
        self.var_shares   = tk.StringVar(value="100")
        self.var_side     = tk.StringVar(value="LONG")
        self.var_limit_px = tk.StringVar(value="")
        self.var_profit   = tk.StringVar(value="")              # USD per share
        self.var_risk     = tk.StringVar(value="")              # USD per share (formerly stop)
        self.var_timeout  = tk.StringVar(value="")

        # inline errors
        self._err_ticker = tk.StringVar(value="")
        self._form_error = tk.StringVar(value="")

        self.var_nbbo = tk.BooleanVar(value=False)
        self.var_aggresive = tk.BooleanVar(value=False)
        self.timeslots = {}

    def _build_ui(self, title):
        # ---------------- Scrollable shell (inside this panel only) ----------------
        shell = tb.Frame(self)                 # stays inside the TFM panel
        shell.pack(fill=BOTH, expand=YES)

        canvas = tk.Canvas(shell, highlightthickness=0, bd=0)
        vbar   = tb.Scrollbar(shell, orient="vertical", command=canvas.yview)
        canvas.configure(yscrollcommand=vbar.set)

        canvas.pack(side=LEFT, fill=BOTH, expand=YES)
        vbar.pack(side=LEFT, fill=Y)

        # All UI goes into `parent` (a real Frame living inside the canvas)
        parent = tb.Frame(canvas, padding=0)
        win_id = canvas.create_window((0, 0), window=parent, anchor="nw")

        # keep scrollregion & width synced
        parent.bind("<Configure>", lambda e: canvas.configure(scrollregion=canvas.bbox("all")))
        canvas.bind("<Configure>", lambda e: canvas.itemconfigure(win_id, width=e.width))

        # ---------------- Mouse wheel support (Windows / macOS / Linux) ----------------
        def _wheel_bind(_):
            canvas.bind_all("<MouseWheel>", _on_wheel)          # Windows/macOS
            canvas.bind_all("<Button-4>",  _on_wheel_linux_up)  # Linux
            canvas.bind_all("<Button-5>",  _on_wheel_linux_down)

        def _wheel_unbind(_):
            canvas.unbind_all("<MouseWheel>")
            canvas.unbind_all("<Button-4>")
            canvas.unbind_all("<Button-5>")

        def _on_wheel(e):            canvas.yview_scroll(int(-e.delta / 120), "units")
        def _on_wheel_linux_up(e):   canvas.yview_scroll(-1, "units")
        def _on_wheel_linux_down(e): canvas.yview_scroll( 1, "units")

        canvas.bind("<Enter>", _wheel_bind)
        canvas.bind("<Leave>", _wheel_unbind)

        # ---------------- Your original UI (parent replaced where needed) ----------------
        # Header
        head = tb.Frame(parent)
        head.pack(fill=X, pady=(0,6))
        # tb.Label(head, text=title, bootstyle="inverse-primary", font=TITLE_FONT).pack(side=LEFT)

        # Card-like order block
        frm = tb.Labelframe(parent, text="Order", padding=8)
        frm.pack(fill=BOTH, expand=YES)

        vcmd_ticker = (self.register(self._validate_ticker), "%P")
        vcmd_int    = (self.register(self._validate_int),    "%P")
        vcmd_float  = (self.register(self._validate_float),  "%P")

        # --- Ticker (letters-only) + Recent dropdown ---
        tb.Label(frm, text="Ticker *", font=LABEL_FONT).pack(anchor=W)
        trow = tb.Frame(frm); trow.pack(fill=X)

        self.ent_ticker = tb.Entry(
            trow,
            textvariable=self.var_ticker,
            justify=LEFT,
            validate="key",
            validatecommand=vcmd_ticker
        )
        self.ent_ticker.pack(side=LEFT, fill=X, expand=YES, pady=(0,2))

        # Recent MRU combobox (most recent first)
        self.cbo_recent = tb.Combobox(
            trow,
            state="readonly",
            values=self.recent_tickers,
            width=12,
            bootstyle="secondary"
        )
        self.cbo_recent.pack(side=LEFT, padx=(6,0))
        self.cbo_recent.bind(
            "<<ComboboxSelected>>",
            lambda e: (self.var_ticker.set(self.cbo_recent.get()),
                       self.ent_shares.focus_set())
        )

        tb.Label(frm, textvariable=self._err_ticker, bootstyle="danger").pack(anchor=W, pady=(0,4))

        # --- Shares ---
        tb.Label(frm, text="Shares", font=LABEL_FONT).pack(anchor=W)
        self.ent_shares = tb.Entry(frm, textvariable=self.var_shares,
                                   justify=LEFT, validate="key", validatecommand=vcmd_int)
        self.ent_shares.pack(fill=X, pady=(0,6))

        # --- Side chip buttons ---
        tb.Label(frm, text="Side", font=LABEL_FONT).pack(anchor=W)
        row = tb.Frame(frm); row.pack(fill=X, pady=(2,6))
        tb.Radiobutton(row, text="Long (Ctrl+Q)",  value="LONG",
                       variable=self.var_side, bootstyle="success-toolbutton", takefocus=True).pack(side=LEFT, expand=YES, fill=X, padx=(0,4))
        tb.Radiobutton(row, text="Short (Ctrl+W)", value="SHORT",
                       variable=self.var_side, bootstyle="danger-toolbutton", takefocus=True).pack(side=LEFT, expand=YES, fill=X)

        tb.Separator(frm).pack(fill=X, pady=6)

        # --- Limit Price ---
        tb.Label(frm, text="Limit Price", font=LABEL_FONT).pack(anchor=W)
        self.ent_limit = tb.Entry(frm, textvariable=self.var_limit_px,
                                  justify=LEFT, validate="key", validatecommand=vcmd_float)
        self.ent_limit.pack(fill=X, pady=(0,6))

        # --- Profit ---
        tb.Label(frm, text="Profit", font=LABEL_FONT).pack(anchor=W)
        self.ent_profit = tb.Entry(frm, textvariable=self.var_profit,
                                   justify=LEFT, validate="key", validatecommand=vcmd_float)
        self.ent_profit.pack(fill=X, pady=(0,6))

        # --- Risk (formerly Stop $) ---
        tb.Label(frm, text="Stop", font=LABEL_FONT).pack(anchor=W)
        self.ent_risk = tb.Entry(frm, textvariable=self.var_risk,
                                 justify=LEFT, validate="key", validatecommand=vcmd_float)
        self.ent_risk.pack(fill=X, pady=(0,6))

        # --- Timeout (09:40 → 15:50, 10-min) ---
        tb.Label(frm, text="Timeout", font=LABEL_FONT).pack(anchor=W)
        self.cbo_timeout = tb.Combobox(frm, textvariable=self.var_timeout, state="readonly",
                                       values=self._market_slots(), bootstyle="secondary")
        self.cbo_timeout.pack(fill=X, pady=(0,2))

        # any form-level error
        tb.Label(frm, textvariable=self._form_error, bootstyle="danger").pack(anchor=W, pady=(2,0))

        tb.Checkbutton(frm, text="NBBO only",
                       variable=self.var_nbbo, bootstyle="round-toggle").pack(anchor=W, pady=(6,6))

        tb.Separator(frm).pack(fill=X, pady=6)

        # --- Preview card ---
        prev = tb.Labelframe(parent, text="Preview", padding=8)
        prev.pack(fill=BOTH, expand=YES, pady=(8,0))
        self.txt_preview = tk.Text(prev, height=11, wrap="word", font=MONO_FONT,
                                   relief="flat", bd=0, padx=4, pady=4)
        self.txt_preview.pack(fill=BOTH, expand=YES)

        # --- Buttons ---
        btns = tb.Frame(parent); btns.pack(fill=X, pady=(8,0))
        self.btn_submit = tb.Button(btns, text="Submit Algo (Ctrl+Enter)", bootstyle="primary", command=self._noop_submit)
        self.btn_submit.pack(fill=X)
        tb.Button(btns, text="Reset", bootstyle="light", command=self._reset).pack(fill=X, pady=(6,0))

    # -------- Slots for 09:40 → 15:50 every 10 min --------
    def _market_slots(self):
        vals = ["—"]
        start_h, start_m = 9, 40
        end_h, end_m     = 15, 50
        hh, mm = start_h, start_m
        while (hh < end_h) or (hh == end_h and mm <= end_m):
            vals.append(f"{hh:02d}:{mm:02d}")
            self.timeslots[f"{hh:02d}:{mm:02d}"] = hh*60+mm
            mm += 10
            if mm >= 60:
                mm = 0
                hh += 1
        return vals

    # ---------- Fullsymbol cache helpers ----------
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

    # ---------- Recent tickers MRU (persisted) ----------
    def _recent_path(self):
        return os.path.join(os.path.dirname(__file__), "recent_tickers.json")

    def _load_recent_tickers(self) -> list[str]:
        try:
            with open(self._recent_path(), "r", encoding="utf-8") as f:
                data = json.load(f)
                if isinstance(data, list):
                    # normalize, dedupe (preserve order), cap 15
                    mru = []
                    for s in data:
                        if isinstance(s, str):
                            u = s.strip().upper()
                            if u and u.isalpha() and u not in mru:
                                mru.append(u)
                                if len(mru) >= 15:
                                    break
                    return mru
        except Exception:
            pass
        return []

    def _save_recent_tickers(self):
        try:
            with open(self._recent_path(), "w", encoding="utf-8") as f:
                json.dump(self.recent_tickers[:15], f, ensure_ascii=False, indent=2)
        except Exception as e:
            print("recent tickers save error:", e)

    def _remember_ticker(self, base: str):
        """
        Put BASE at the front of the MRU (dedupe), cap at 15, persist,
        and refresh the combobox values.
        """
        base = (base or "").strip().upper()
        if not base or not base.isalpha():
            return
        # dedupe then insert at front
        self.recent_tickers = [t for t in self.recent_tickers if t != base]
        self.recent_tickers.insert(0, base)
        self.recent_tickers = self.recent_tickers[:15]
        self._save_recent_tickers()
        # update UI combobox if it exists
        try:
            self.cbo_recent.configure(values=self.recent_tickers)
        except Exception:
            pass

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
        url = f"http://10.29.10.143/api/Symbol/fullsymbol/{base}?chartPeriod=1&chartType=m"
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

    # ------------ Validation funcs ------------
    def _validate_ticker(self, newval: str) -> bool:
        # allow empty; letters only otherwise
        ok = (newval == "" or newval.isalpha())
        self._err_ticker.set("" if (ok or newval == "") else "Letters only (A–Z).")
        return ok

    def _validate_int(self, newval: str) -> bool:
        return newval == "" or newval.isdigit()

    def _validate_float(self, newval: str) -> bool:
        if newval == "": return True
        if newval.count(".") > 1: return False
        return all(p.isdigit() for p in newval.split(".") if p != "")

    def _wire_events(self):
        # Auto-capitalize ticker (letters-only already enforced)
        def _upper(*_):
            v = self.var_ticker.get()
            u = v.upper()
            if v != u:
                self.var_ticker.set(u)
        self.var_ticker.trace_add("write", _upper)

        # Refresh preview on changes
        for v in (self.var_ticker, self.var_shares, self.var_side,
                  self.var_limit_px, self.var_profit, self.var_risk,
                  self.var_timeout):
            v.trace_add("write", lambda *_: self._refresh_preview())

        # Enter key flow
        self.ent_ticker.bind("<Return>", lambda e: self.ent_shares.focus_set())

        top = self.winfo_toplevel()

        # Side: Ctrl+Q -> LONG, Ctrl+W -> SHORT
        top.bind_all("<Control-Q>", lambda e: self.var_side.set("LONG"))
        top.bind_all("<Control-W>", lambda e: self.var_side.set("SHORT"))

        # QoL
        top.bind_all("<Alt-Return>", lambda e: self.btn_submit.invoke())  # Alt+Enter to submit
        top.bind_all("<Alt-r>",      lambda e: self._reset())

    def _is_int(self, s): return s.isdigit()
    def _is_float(self, s):
        try: float(s); return True
        except: return False

    def _validate_form(self):
        if not self.var_ticker.get().strip():
            self._err_ticker.set("Ticker required.")
            return False, ""
        self._err_ticker.set("")

        if not self._is_int(self.var_shares.get()):
            return False, "Shares must be a whole number."
        if self.var_limit_px.get().strip() and not self._is_float(self.var_limit_px.get()):
            return False, "Limit Price must be a number."
        if self.var_profit.get().strip() and not self._is_float(self.var_profit.get()):
            return False, "Profit must be a number."
        if self.var_risk.get().strip() and not self._is_float(self.var_risk.get()):
            return False, "Risk must be a number."
        return True, ""

    def _combined_symbol(self):
        # Just the base ticker for preview; actual submit resolves to fullsymbol
        base = self.var_ticker.get().strip().upper()
        return f"{base}" if base else base

    def _risk_reward_ratio(self):
        """Return RRR as float (Profit / Risk) or None if not computable."""
        if self.var_profit.get().strip() and self.var_risk.get().strip():
            try:
                risk = float(self.var_risk.get())
                profit = float(self.var_profit.get())
                if risk > 0:
                    return profit / risk
            except:
                pass
        return None

    def total_risk(self):
        try:
            if self.var_risk.get():
                return float(self.var_risk.get())*int(self.var_shares.get())
        except:
            return 0
        return None

    def _refresh_preview(self):
        ok, msg = self._validate_form()
        self._form_error.set(msg)

        # Try resolve (non-blocking; no error shown here)
        resolved = ""
        base = self.var_ticker.get().strip().upper()
        if base:
            fs = self.suffix_cache.get(base)
            if fs:
                resolved = f" (resolved: {fs})"

        rrr = self._risk_reward_ratio()
        preview = {
            "ticker": self._combined_symbol(),
            "shares": int(self.var_shares.get()) if self._is_int(self.var_shares.get()) else self.var_shares.get(),
            "side": self.var_side.get(),
            "limit_price": float(self.var_limit_px.get()) if (self.var_limit_px.get().strip() and self._is_float(self.var_limit_px.get())) else None,
            "profit_usd": float(self.var_profit.get()) if (self.var_profit.get().strip() and self._is_float(self.var_profit.get())) else None,
            "risk_usd": float(self.var_risk.get()) if (self.var_risk.get().strip() and self._is_float(self.var_risk.get())) else None,
            "timeout": self.var_timeout.get(),
            "rrr": rrr,
        }

        lines = [
            "TFM Order Preview",
            "=================",
            f"Ticker:           {preview['ticker'] or '—'}{resolved}",
            f"Shares:           {preview['shares']}",
            f"Side:             {preview['side']}",
            f"Limit Price:      {preview['limit_price'] if preview['limit_price'] is not None else '—'}",
            f"Profit ($/shr):   {preview['profit_usd'] if preview['profit_usd'] is not None else '—'}",
            f"Risk ($/shr):     {preview['risk_usd'] if preview['risk_usd'] is not None else '—'}",
            f"Timeout:          {preview['timeout']}",
        ]

        tr = self.total_risk()
        if tr is not None:
            lines.append(f"Total Risk:       {tr:.0f} $")
        if rrr is not None:
            lines.append(f"Risk-Reward Ratio: {rrr:.2f}  (Profit ÷ Risk)")

        self.txt_preview.configure(state="normal")
        self.txt_preview.delete("1.0", "end")
        self.txt_preview.insert("1.0", "\n".join(lines))
        self.txt_preview.configure(state="disabled")

        self.btn_submit.configure(state=(NORMAL if ok else DISABLED))

    def _reset(self):
        self.var_ticker.set("")
        self.var_shares.set("100")
        self.var_side.set("LONG")
        self.var_limit_px.set("")
        self.var_profit.set("")
        self.var_risk.set("")
        self.var_timeout.set("")
        self._err_ticker.set("")
        self._form_error.set("")
        self._refresh_preview()

    def _noop_submit(self):
        # Final validation
        try:
            ok, msg = self._validate_form()
            if not ok:
                self._form_error.set(msg)
                return

            user   = self.ui.manager.USER.get()
            base   = self.var_ticker.get().strip().upper()

            # --- resolve full symbol ---
            fullsymbol = self.get_suffix(base)
            if not fullsymbol:
                # service either returned no suffix or the symbol doesn't exist
                self._err_ticker.set("Ticker does not exist.")
                self._form_error.set("Ticker does not exist.")
                return
            self._err_ticker.set("")

            share  = self.var_shares.get()
            limit  = self.var_limit_px.get()
            profit = self.var_profit.get()
            risk   = self.var_risk.get()
            timeout = self.var_timeout.get()

            algo_name = f'TFM_{fullsymbol}:{timeout}'

            side = self.var_side.get()
            if side == "SHORT":
                share = int(share) * -1

            orders1 = {fullsymbol: {'share': int(share)}}
            info = {}

            if limit != "":
                limit = float(limit)
                algo_name = f'TFM_{fullsymbol} @ {limit}:{timeout}'
                orders1[fullsymbol]['limit'] = limit

            if timeout != "":
                info['Timer'] = self.timeslots.get(timeout, None)

            if profit != "":
                # profit/risk are USD per share in UI; convert to total USD
                p = int(round(float(profit), 2) * abs(int(share)))
                info['Profit'] = p
            if risk != "":
                s = int(round(float(risk), 2) * abs(int(share)))
                info['Stop'] = s

            info['Tag'] = 'TFM'
            # ensure unique name if resubmitted quickly
            if not hasattr(self, "algo_count"):
                self.algo_count = {}
            if algo_name not in self.algo_count:
                self.algo_count[algo_name] = 0
            else:
                self.algo_count[algo_name] += 1
                algo_name += str(self.algo_count[algo_name])

            # send
            self.ui.manager.apply_basket_cmd(algo_name, orders1, info)

            # remember the base ticker in MRU if the send didn't raise
            self._remember_ticker(base)

            self._form_error.set("Algo Placed.")

        except Exception as e:
            print(e, traceback.print_exc())
            self._form_error.set("Unexpected error — see console.")

# ----- Standalone demo -----
if __name__ == "__main__":
    import tkinter as tk
    import ttkbootstrap as tb
    from ttkbootstrap.constants import *

    # --- tiny shim so TFMPanel has what it expects ---
    class DummyManager:
        def __init__(self, root):
            self.USER = tk.StringVar(value="DEMOUSER")

        def apply_basket_cmd(self, algo_name, orders, info):
            # just print so you can see what would be sent
            print("\n[apply_basket_cmd]")
            print("  algo_name:", algo_name)
            print("  orders   :", orders)
            print("  info     :", info)

    class DummyUI:
        def __init__(self, root):
            self.manager = DummyManager(root)
            # container (acts like your real ui.user_panels)
            self.user_panels = tb.Frame(root)
            self.user_panels.pack(fill=BOTH, expand=YES, padx=10, pady=10)

    app = tb.Window(themename="flatly")
    app.title("TFM — Trade For Me (UI Demo)")
    app.geometry("360x820")

    ui = DummyUI(app)
    panel = TFMPanel(ui, title="TFM")
    panel.pack(fill=BOTH, expand=YES)

    app.mainloop()
