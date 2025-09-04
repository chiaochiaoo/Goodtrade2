# ui_tfm_panel_narrow_v8.py
import tkinter as tk
import ttkbootstrap as tb
from ttkbootstrap.constants import *

LABEL_FONT = ("Segoe UI", 10)
TITLE_FONT = ("Segoe UI", 12, "bold")
MONO_FONT  = ("Consolas", 9)

SUFFIX_OPTIONS = [".NQ", ".NY", ".AM"]  # quick market suffixes

class TFMPanel(tb.Frame):
    def __init__(self, master, *, title=""):
        super().__init__(master, padding=10)
        self._build_vars()
        self._build_ui(title)
        self._wire_events()
        self._refresh_preview()

    # ---------------- Vars ----------------
    def _build_vars(self):
        self.var_ticker   = tk.StringVar()              # letters only
        self.var_suffix   = tk.StringVar(value=".NQ")   # dropdown
        self.var_shares   = tk.StringVar(value="100")
        self.var_side     = tk.StringVar(value="LONG")
        self.var_limit_px = tk.StringVar()
        self.var_profit   = tk.StringVar()              # whole number
        self.var_risk     = tk.StringVar()              # whole number (formerly stop)
        self.var_timeout  = tk.StringVar(value="—")

        # inline errors
        self._err_ticker = tk.StringVar(value="")
        self._form_error = tk.StringVar(value="")

    # ------------- UI (compact) -------------
    def _build_ui(self, title):
        # Header
        head = tb.Frame(self)
        head.pack(fill=X, pady=(0,6))
        #tb.Label(head, text=title, bootstyle="inverse-primary", font=TITLE_FONT).pack(side=LEFT)

        # Card-like order block
        frm = tb.Labelframe(self, text="Order", padding=8)
        frm.pack(fill=BOTH, expand=YES)

        vcmd_ticker = (self.register(self._validate_ticker), "%P")
        vcmd_int    = (self.register(self._validate_int),    "%P")
        vcmd_float  = (self.register(self._validate_float),  "%P")

        # --- Ticker + Suffix (inline) ---
        tb.Label(frm, text="Ticker *", font=LABEL_FONT).pack(anchor=W)
        trow = tb.Frame(frm); trow.pack(fill=X)
        self.ent_ticker = tb.Entry(trow, textvariable=self.var_ticker,
                                   justify=LEFT, validate="key", validatecommand=vcmd_ticker)
        self.ent_ticker.pack(side=LEFT, fill=X, expand=YES, pady=(0,2))
        self.cbo_suffix = tb.Combobox(trow, textvariable=self.var_suffix, state="readonly",
                                      values=SUFFIX_OPTIONS, width=6, bootstyle="secondary")
        self.cbo_suffix.pack(side=LEFT, padx=(6,0), pady=(0,2))
        tb.Label(frm, textvariable=self._err_ticker, bootstyle="danger").pack(anchor=W, pady=(0,4))

        # --- Shares ---
        tb.Label(frm, text="Shares", font=LABEL_FONT).pack(anchor=W)
        self.ent_shares = tb.Entry(frm, textvariable=self.var_shares,
                                   justify=LEFT, validate="key", validatecommand=vcmd_int)
        self.ent_shares.pack(fill=X, pady=(0,6))

        # --- Side chip buttons ---
        tb.Label(frm, text="Side", font=LABEL_FONT).pack(anchor=W)
        row = tb.Frame(frm); row.pack(fill=X, pady=(2,6))
        tb.Radiobutton(row, text="Long",  value="LONG",
                       variable=self.var_side, bootstyle="success-toolbutton").pack(side=LEFT, expand=YES, fill=X, padx=(0,4))
        tb.Radiobutton(row, text="Short", value="SHORT",
                       variable=self.var_side, bootstyle="danger-toolbutton").pack(side=LEFT, expand=YES, fill=X)

        tb.Separator(frm).pack(fill=X, pady=6)

        # --- Limit Price ---
        tb.Label(frm, text="Limit Price", font=LABEL_FONT).pack(anchor=W)
        self.ent_limit = tb.Entry(frm, textvariable=self.var_limit_px,
                                  justify=LEFT, validate="key", validatecommand=vcmd_float)
        self.ent_limit.pack(fill=X, pady=(0,6))

        # --- Profit ---
        tb.Label(frm, text="Profit", font=LABEL_FONT).pack(anchor=W)
        self.ent_profit = tb.Entry(frm, textvariable=self.var_profit,
                                   justify=LEFT, validate="key", validatecommand=vcmd_int)
        self.ent_profit.pack(fill=X, pady=(0,6))

        # --- Risk (formerly Stop $) ---
        tb.Label(frm, text="Risk", font=LABEL_FONT).pack(anchor=W)
        self.ent_risk = tb.Entry(frm, textvariable=self.var_risk,
                                 justify=LEFT, validate="key", validatecommand=vcmd_int)
        self.ent_risk.pack(fill=X, pady=(0,6))

        # --- Timeout (09:40 → 15:50, 10-min) ---
        tb.Label(frm, text="Timeout", font=LABEL_FONT).pack(anchor=W)
        self.cbo_timeout = tb.Combobox(frm, textvariable=self.var_timeout, state="readonly",
                                       values=self._market_slots(), bootstyle="secondary")
        self.cbo_timeout.pack(fill=X, pady=(0,2))

        # any form-level error
        tb.Label(frm, textvariable=self._form_error, bootstyle="danger").pack(anchor=W, pady=(2,0))

        # --- Preview card ---
        prev = tb.Labelframe(self, text="Preview", padding=8)
        prev.pack(fill=BOTH, expand=YES, pady=(8,0))
        self.txt_preview = tk.Text(prev, height=11, wrap="word", font=MONO_FONT,
                                   relief="flat", bd=0, padx=4, pady=4)
        self.txt_preview.pack(fill=BOTH, expand=YES)

        # --- Buttons ---
        btns = tb.Frame(self); btns.pack(fill=X, pady=(8,0))
        self.btn_submit = tb.Button(btns, text="Queue Order", bootstyle="primary", command=self._noop_submit)
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
            mm += 10
            if mm >= 60:
                mm = 0
                hh += 1
        return vals

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
        for v in (self.var_ticker, self.var_suffix, self.var_shares, self.var_side,
                  self.var_limit_px, self.var_profit, self.var_risk,
                  self.var_timeout):
            v.trace_add("write", lambda *_: self._refresh_preview())

        # Enter key flow
        self.ent_ticker.bind("<Return>", lambda e: self.ent_shares.focus_set())

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
        if self.var_profit.get().strip() and not self._is_int(self.var_profit.get()):
            return False, "Profit must be a whole number."
        if self.var_risk.get().strip() and not self._is_int(self.var_risk.get()):
            return False, "Risk must be a whole number."
        return True, ""

    def _combined_symbol(self):
        base = self.var_ticker.get().strip().upper()
        suf  = self.var_suffix.get().strip()
        return f"{base}{suf}" if base else base

    def _risk_reward_ratio(self):
        """Return RRR as float (Profit / Risk) or None if not computable."""
        if self.var_profit.get().strip() and self.var_risk.get().strip():
            if self._is_int(self.var_profit.get()) and self._is_int(self.var_risk.get()):
                risk = int(self.var_risk.get())
                profit = int(self.var_profit.get())
                if risk > 0:
                    return profit / risk
        return None

    def _refresh_preview(self):
        ok, msg = self._validate_form()
        self._form_error.set(msg)

        rrr = self._risk_reward_ratio()
        preview = {
            "ticker": self._combined_symbol(),
            "shares": int(self.var_shares.get()) if self._is_int(self.var_shares.get()) else self.var_shares.get(),
            "side": self.var_side.get(),
            "limit_price": float(self.var_limit_px.get()) if (self.var_limit_px.get().strip() and self._is_float(self.var_limit_px.get())) else None,
            "profit_usd": int(self.var_profit.get()) if (self.var_profit.get().strip() and self._is_int(self.var_profit.get())) else None,
            "risk_usd": int(self.var_risk.get()) if (self.var_risk.get().strip() and self._is_int(self.var_risk.get())) else None,
            "timeout": self.var_timeout.get(),
            "rrr": rrr,
        }

        lines = [
            "TFM Order Preview",
            "=================",
            f"Ticker:           {preview['ticker'] or '—'}",
            f"Shares:           {preview['shares']}",
            f"Side:             {preview['side']}",
            f"Limit Price:      {preview['limit_price'] if preview['limit_price'] is not None else '—'}",
            f"Profit:           {preview['profit_usd'] if preview['profit_usd'] is not None else '—'}",
            f"Risk:             {preview['risk_usd'] if preview['risk_usd'] is not None else '—'}",
            f"Timeout:          {preview['timeout']}",
        ]
        if rrr is not None:
            lines.append(f"Risk-Reward Ratio: {rrr:.2f}  (Profit ÷ Risk)")

        self.txt_preview.configure(state="normal")
        self.txt_preview.delete("1.0", "end")
        self.txt_preview.insert("1.0", "\n".join(lines))
        self.txt_preview.configure(state="disabled")

        self.btn_submit.configure(state=(NORMAL if ok else DISABLED))

    def _reset(self):
        self.var_ticker.set("")
        self.var_suffix.set(".NQ")
        self.var_shares.set("100")
        self.var_side.set("LONG")
        self.var_limit_px.set("")
        self.var_profit.set("")
        self.var_risk.set("")
        self.var_timeout.set("—")
        self._err_ticker.set("")
        self._form_error.set("")
        self._refresh_preview()

    def _noop_submit(self):
        self._form_error.set("Looks good. (UI only)")

# ----- Standalone demo -----
if __name__ == "__main__":
    app = tb.Window(themename="flatly")
    app.title("TFM — Trade For Me (UI Demo)")
    app.geometry("340x880")
    nb = tb.Notebook(app); nb.pack(fill=BOTH, expand=YES)
    nb.add(TFMPanel(nb), text="TFM")
    app.mainloop()
