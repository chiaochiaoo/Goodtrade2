# ui_dashboard_chart.py
import tkinter as tk
import ttkbootstrap as tb
from ttkbootstrap.constants import *
import pandas as pd
import numpy as np
from collections import deque
from datetime import date, datetime, time, timezone, timedelta
import matplotlib
matplotlib.use("TkAgg")
from matplotlib.figure import Figure
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
import mplfinance as mpf
import pytz
import threading
import requests

LOCAL_TZ = pytz.timezone("America/Toronto")

def polygon_agg_to_ohlcv(payload: dict, to_local_tz: bool = True) -> pd.DataFrame:
    if payload.get("status") != "OK" or "results" not in payload:
        return pd.DataFrame(columns=["Date","Open","High","Low","Close","Volume"])

    df = pd.DataFrame(payload["results"])
    if df.empty:
        return pd.DataFrame(columns=["Date","Open","High","Low","Close","Volume"])

    ts = pd.to_datetime(df["t"], unit="ms", utc=True)
    if to_local_tz:
        ts = ts.dt.tz_convert(LOCAL_TZ).dt.tz_localize(None)
    else:
        ts = ts.dt.tz_convert(timezone.utc).dt.tz_localize(None)

    df["Date"] = ts
    df = df.rename(columns={"o":"Open","h":"High","l":"Low","c":"Close","v":"Volume"})
    df = df[["Date","Open","High","Low","Close","Volume"]].astype(
        {"Open":"float64","High":"float64","Low":"float64","Close":"float64","Volume":"int64"}
    )
    df = df.sort_values("Date")
    df = df[(df["Date"].dt.time >= time(9,30)) & (df["Date"].dt.time <= time(16,0))]
    return df.reset_index(drop=True)

class CandlePanel(tb.Frame):
    """
    Read-only candlestick panel with an inbox queue.

    Public API:
      submit_and_go(algo_name, orders, info)
    Behavior:
      - If nothing is showing -> show immediately after data download
      - Else enqueue; Approve/Reject advances to the next
      - If nothing left, clear the chart and reset info
    """
    def __init__(self, master, ui=None, **kwargs):
        super().__init__(master, **kwargs)
        self.ui = ui

        # ---------- State ----------
        self.queue = deque()         # pending items (dicts)
        self.current = None          # item currently shown
        self.df = None               # dataframe currently plotted
        self._inbox_n = 0
        self._algo = "-"
        self._position = "-"

        # ---------- Top bar ----------
        bar = tb.Frame(self, padding=(10, 8))
        bar.pack(side=tk.TOP, fill=tk.X)

        self.info_var = tk.StringVar(value="Inbox: 0  Time: --:--:--   Algo: -   Position: -")
        self.lbl_info = tb.Label(bar, textvariable=self.info_var, anchor="w")
        self.lbl_info.pack(side=tk.LEFT, fill=tk.X, expand=True)



        self.btn_reject  = tb.Button(bar, text="Reject",  bootstyle=DANGER,  command=self._on_reject)
        self.btn_approve = tb.Button(bar, text="Approve", bootstyle=SUCCESS, command=self._on_approve)
        self.btn_reject.pack(side=tk.RIGHT, padx=(6, 0))
        self.btn_approve.pack(side=tk.RIGHT)


        self.btn_add_tp = tb.Button(bar, text="Add Target",
                                     command=self._on_add_target)
        self.btn_add_sl = tb.Button(bar, text="Add Stop",
                                     command=self._on_add_stop)
        self.btn_add_sl.pack(side=tk.RIGHT, padx=(6, 0))
        self.btn_add_tp.pack(side=tk.RIGHT, padx=(6, 0))

        # ---------- Figure ----------
        self.fig = Figure(figsize=(8, 5), dpi=100, layout="constrained")
        self.ax_price = self.fig.add_subplot(1, 1, 1)
        self.canvas = FigureCanvasTkAgg(self.fig, master=self)
        self.canvas.draw()
        self.canvas.get_tk_widget().pack(side=tk.TOP, fill=tk.BOTH, expand=True)


        # --- header label handle (symbol/pos + Profit/Stop) ---
        self._hdr_label = None

        # --- draggable TP/SL state ---
        self._tp = {"line": None, "label": None}
        self._sl = {"line": None, "label": None}
        self._drag = {"target": None}
        self._hovering = False  # for cursor update

        # mouse events
        self.canvas.mpl_connect("button_press_event", self._on_press)
        self.canvas.mpl_connect("button_release_event", self._on_release)
        self.canvas.mpl_connect("motion_notify_event", self._on_motion)
        # start the clock for the info line
        self.after(1000, self._tick_clock)

    def _default_per_share_step(self):
        """Reasonable default distance per share if none provided."""
        # 0.5% of price, min $0.05 (works well for equities/ETFs)
        last_close = float(self.df["Close"].iloc[-1]) if self.df is not None else 1.0
        return round(max(last_close * 0.005, 0.05), 2)

    def _on_add_target(self):
        self._add_level_if_missing("Profit")

    def _on_add_stop(self):
        self._add_level_if_missing("Stop")

    def _add_level_if_missing(self, kind: str):
        """
        kind: 'Profit' or 'Stop'
        Creates info[kind] (total $) if absent, based on default per-share step.
        Then redraws so the line appears and header updates.
        """
        if not self.current or self.df is None:
            return
        info = self.current.setdefault("info", {})
        if kind in info and isinstance(info[kind], (int, float)):
            return  # already present -> do nothing

        sym_key = next(iter(self.current["orders"].keys()))
        shares = int(self.current["orders"][sym_key].get("share", 0))
        if shares == 0:
            return
        per_share = self._default_per_share_step()
        info[kind] = round(per_share * abs(shares), 2)

        # redraw so TP/SL renders + header refreshes
        self._draw(self.current["position"])

    # ================== Core API ==================
    def submit_and_go(self, algo_name: str, orders: dict, info: dict):
        """
        1) Build a job
        2) Spawn a downloader thread
        3) On finish, either display immediately (if idle) or enqueue
        """
        # infer symbol and position
        sym_key = next(iter(orders.keys()))
        symbol = sym_key.rsplit(".", 1)[0]  # "SPY.AM" -> "SPY"
        shares = orders[sym_key].get("share", 0)
        position = "LONG" if shares > 0 else "SHORT"

        job = {
            "algo": algo_name,
            "orders": orders,
            "info": info,
            "symbol": symbol,
            "position": position,
            "data": None,
            "ready": False,
            "error": None,
        }

        # downloader
        def _dl():
            try:
                today = date.today().strftime("%Y-%m-%d")
                url = (f"https://api.polygon.io/v2/aggs/ticker/{symbol}/range/1/minute/"
                       f"{today}/{today}?adjusted=True&sort=asc&limit=1000&apiKey=ezY3uX1jsxve3yZIbw2IjbNi5X7uhp1H")
                r = requests.get(url, timeout=30)
                r.raise_for_status()
                payload = r.json()
                df = polygon_agg_to_ohlcv(payload, to_local_tz=True)
                job["data"] = df
                job["ready"] = True
            except Exception as e:
                job["error"] = str(e)
                job["ready"] = True
            finally:
                # marshal back to UI thread
                self.after(0, self._on_job_ready, job)

        threading.Thread(target=_dl, daemon=True).start()

        # If nothing is showing (idle + no queue), we tentatively expect to show this next
        # but actual display only happens after _on_job_ready (so we don't block UI).
        # If something is showing, just wait for ready and enqueue in _on_job_ready.
        return

    # Called on the UI thread when a job finishes downloading
    def _on_job_ready(self, job: dict):
        if self.current is None and len(self.queue) == 0:
            # show immediately
            self._show_job(job)
        else:
            # enqueue (FIFO)
            self.queue.append(job)
            self._inbox_n = len(self.queue) + (1 if self.current else 0)
            self._refresh_info_line()

    # ================== UI Helpers ==================
    def _show_job(self, job: dict):
        """Draws the job (already 'ready'), sets current, updates info line."""
        self.current = job
        self._inbox_n = len(self.queue) + 1  # current + rest
        self._algo = job["algo"]
        self._position = f"{job['position']}:   {job['symbol']} {next(iter(job['orders'].values()))['share']}"

        df = job.get("data")
        if df is None or df.empty:
            # render empty + error message
            self.ax_price.clear()
            self.ax_price.text(0.5, 0.5,
                job.get("error") or "No data",
                transform=self.ax_price.transAxes, ha="center", va="center")
            self.canvas.draw_idle()
        else:
            self.df = df.copy()
            self._hdr_label = None
            self._draw(position=job["position"])

        self._refresh_info_line()

    def _advance(self):
        """Move to next job or clear if none."""
        # pop next ready job from queue; if some are not ready yet, skip until a ready one is found
        next_job = None
        while self.queue:
            cand = self.queue.popleft()
            if cand.get("ready"):
                next_job = cand
                break
            else:
                # not ready yet; keep it at the end
                self.queue.append(cand)
                break

        if next_job:
            self._show_job(next_job)
        else:
            self._clear_panel()

    def _clear_panel(self):
        self.current = None
        self.df = None
        self._inbox_n = len(self.queue)  # usually 0
        self._algo = "-"
        self._position = "-"
        self.ax_price.clear()
        self.canvas.draw_idle()
        self._refresh_info_line()



    def _draw(self, position: str):

            # ---- kill stale header artist before clearing ----
        if self._hdr_label is not None:
            try:
                self._hdr_label.remove()
            except Exception:
                pass
            self._hdr_label = None


        self.ax_price.clear()

        df_plot = self.df.set_index("Date") if "Date" in self.df.columns else self.df
        mpf.plot(df_plot, type="candle", ax=self.ax_price, style="charles", show_nontrading=False)

        # ----- margin padding -----
        self.ax_price.margins(x=0.06, y=0.08)

        # ----- anchor last candle -----
        x = len(df_plot) - 1
        last_low  = float(df_plot["Low"].iloc[-1])
        last_high = float(df_plot["High"].iloc[-1])
        last_close = float(df_plot["Close"].iloc[-1])

        ymin, ymax = self.ax_price.get_ylim()
        pad = (ymax - ymin) * 0.03

        if position.upper() == "LONG":
            y, marker, color, va = last_low - pad * 0.6, "^", "limegreen", "top"
            dir_sign_profit = +1
            dir_sign_stop   = -1
        else:
            y, marker, color, va = last_high + pad * 0.6, "v", "red", "bottom"
            dir_sign_profit = -1
            dir_sign_stop   = +1

        # ----- draw triangle + ? -----
        self.ax_price.scatter(x, y, s=260, marker=marker, zorder=10, clip_on=False,
                              edgecolors="black", linewidths=0.5, c=color)
        self.ax_price.annotate(
            "?", xy=(x, y), xytext=(12, 0), textcoords="offset points",
            ha="left", va=va, fontsize=22, fontweight="bold", color=color,
            bbox=dict(boxstyle="round,pad=0.15", facecolor="white", alpha=0.65, edgecolor="none"),
            zorder=11, clip_on=False
        )

        # ----- Profit / Stop dotted levels (if provided) -----
        sym_key = next(iter(self.current["orders"].keys()))
        shares = int(self.current["orders"][sym_key].get("share", 0))
        info   = self.current.get("info", {}) or {}

        # clear old handles
        self._tp = {"line": None, "label": None}
        self._sl = {"line": None, "label": None}

        def _label_at(y_value, txt, color):
            yfrac = (y_value - ymin) / (ymax - ymin)
            yfrac = float(np.clip(yfrac, 0.02, 0.98))
            return self.ax_price.text(
                0.995, yfrac, txt, transform=self.ax_price.transAxes,
                ha="right", va="center", fontsize=10, color=color,
                bbox=dict(boxstyle="round,pad=0.2", facecolor="white", alpha=0.6, edgecolor="none"),
                zorder=7
            )

        if shares != 0:
            abs_sh = abs(shares)
            # signs for LONG/SHORT directions
            if position.upper() == "LONG":
                prof_dir = +1  # profit above
                stop_dir = -1  # stop below
            else:
                prof_dir = -1  # profit below
                stop_dir = +1  # stop above

            # PROFIT line
            if "Profit" in info and isinstance(info["Profit"], (int, float)):
                profit_ps = float(info["Profit"]) / abs_sh
                tp_level  = last_close + prof_dir * profit_ps
                tp = self.ax_price.axhline(tp_level, linestyle=(0, (4, 4)), linewidth=1.4,
                                           color="limegreen", alpha=0.9, zorder=6)
                tp.set_picker(True); tp.set_pickradius(5)  # enable picking
                tp.set_gid("TP")
                tplab = _label_at(tp_level, f"TP {tp_level:.2f}", "limegreen")
                self._tp = {"line": tp, "label": tplab}

            # STOP line
            if "Stop" in info and isinstance(info["Stop"], (int, float)):
                stop_ps = float(info["Stop"]) / abs_sh
                sl_level = last_close + stop_dir * stop_ps
                sl = self.ax_price.axhline(sl_level, linestyle=(0, (4, 4)), linewidth=1.4,
                                           color="red", alpha=0.9, zorder=6)
                sl.set_picker(True); sl.set_pickradius(5)
                sl.set_gid("SL")
                sllab = _label_at(sl_level, f"SL {sl_level:.2f}", "red")
                self._sl = {"line": sl, "label": sllab}
        # ----- TOP-RIGHT info label -----
        # sym_key = next(iter(self.current["orders"].keys()))
        # symbol = sym_key.rsplit(".", 1)[0]
        # shares = self.current["orders"][sym_key].get("share", 0)
        # pos_str = "LONG" if shares > 0 else "SHORT"

        # info_text = f"{symbol} | {pos_str} {abs(shares)}"
        # self.ax_price.text(
        #     0.99, 0.97, info_text,
        #     transform=self.ax_price.transAxes,
        #     ha="right", va="top",
        #     fontsize=20, color=color, fontweight="bold",
        #     bbox=dict(boxstyle="round,pad=0.2", facecolor="white", alpha=0.5, edgecolor="none"),
        #     zorder=15,
        # )

        self._update_header_label(color)
        self.canvas.draw_idle()

    def _update_header_label(self, color):
        # Build strings
        sym_key = next(iter(self.current["orders"].keys()))
        symbol  = sym_key.rsplit(".", 1)[0]
        shares  = int(self.current["orders"][sym_key].get("share", 0))
        pos_str = "LONG" if shares > 0 else "SHORT"

        info = self.current.get("info", {}) or {}
        p = info.get("Profit", None)
        s = info.get("Stop",   None)

        # Format clean text
        line1 = f"{symbol} | {pos_str} {abs(shares)}"
        if isinstance(p, (int, float)) or isinstance(s, (int, float)):
            p_txt = f"P:{p:.2f}" if isinstance(p, (int, float)) else "P:-"
            s_txt = f"S:{s:.2f}" if isinstance(s, (int, float)) else "S:-"
            text  = f"{line1}\n{p_txt}   {s_txt}"
        else:
            text = line1

        # Create or update the header label
        if self._hdr_label is None:
            self._hdr_label = self.ax_price.text(
                0.99, 0.97, text,
                transform=self.ax_price.transAxes,
                ha="right", va="top",
                fontsize=14, color=color, fontweight="bold",
                bbox=dict(boxstyle="round,pad=0.2", facecolor="white", alpha=0.5, edgecolor="none"),
                zorder=15,
            )
        else:
            self._hdr_label.set_text(text)
            self._hdr_label.set_color(color)

    # --- mouse interactions for draggable TP/SL ---
    def _on_press(self, event):
        if event.inaxes != self.ax_price or not self.current:
            return
        if event.ydata is None:
            return

        tol = (self.ax_price.get_ylim()[1] - self.ax_price.get_ylim()[0]) * 0.01  # 1% tolerance

        def near(line):
            if line is None:
                return False
            y = float(line.get_ydata()[0])  # horizontal line -> two identical y's
            return abs(event.ydata - y) <= tol

        if near(self._tp["line"]):
            self._drag["target"] = "TP"
        elif near(self._sl["line"]):
            self._drag["target"] = "SL"
        else:
            self._drag["target"] = None

    def _on_motion(self, event):
        tgt = self._drag.get("target")
        if not tgt or event.inaxes != self.ax_price or event.ydata is None:
            return

        # keep y inside limits
        ymin, ymax = self.ax_price.get_ylim()
        y = float(np.clip(event.ydata, ymin, ymax))

        # move the chosen line
        bundle = self._tp if tgt == "TP" else self._sl
        if bundle["line"] is None:
            return

        line = bundle["line"]
        line.set_ydata([y, y])

        # move/update label
        if bundle["label"] is not None:
            yfrac = (y - ymin) / (ymax - ymin)
            yfrac = float(np.clip(yfrac, 0.02, 0.98))
            bundle["label"].set_position((0.995, yfrac))
            txt = ("TP" if tgt == "TP" else "SL") + f" {y:.2f}"
            bundle["label"].set_text(txt)

        # live-update info['Profit']/['Stop'] to reflect new level
        sym_key = next(iter(self.current["orders"].keys()))
        shares = int(self.current["orders"][sym_key].get("share", 0))
        if shares != 0:
            abs_sh = abs(shares)
            last_close = float(self.df["Close"].iloc[-1])
            pos_long = (shares > 0)

            if tgt == "TP":
                # LONG: profit_ps = y - last_close ; SHORT: profit_ps = last_close - y
                profit_ps = (y - last_close) if pos_long else (last_close - y)
                self.current["info"]["Profit"] = round(max(0.0, profit_ps) * abs_sh, 2)
            else:
                # LONG: stop_ps = last_close - y ; SHORT: stop_ps = y - last_close
                stop_ps = (last_close - y) if pos_long else (y - last_close)
                self.current["info"]["Stop"] = round(max(0.0, stop_ps) * abs_sh, 2)

        self.canvas.draw_idle()

    def _on_motion(self, event):
        # cursor hover feedback
        def _hit(event):
            if event.inaxes != self.ax_price or event.ydata is None:
                return False
            tol = (self.ax_price.get_ylim()[1] - self.ax_price.get_ylim()[0]) * 0.01
            def near(line):
                if line is None: return False
                y = float(line.get_ydata()[0])
                return abs((event.ydata or 0) - y) <= tol
            return near(self._tp["line"]) or near(self._sl["line"])

        over = _hit(event)
        if over != self._hovering and hasattr(self.canvas, "get_tk_widget"):
            self._hovering = over
            self.canvas.get_tk_widget().configure(cursor="hand2" if over else "arrow")

        # dragging?
        tgt = self._drag.get("target")
        if not tgt or event.inaxes != self.ax_price or event.ydata is None:
            return

        ymin, ymax = self.ax_price.get_ylim()
        y = float(np.clip(event.ydata, ymin, ymax))

        bundle = self._tp if tgt == "TP" else self._sl
        if bundle["line"] is None:
            return

        # move line
        bundle["line"].set_ydata([y, y])

        # move/update side label
        if bundle["label"] is not None:
            yfrac = (y - ymin) / (ymax - ymin)
            yfrac = float(np.clip(yfrac, 0.02, 0.98))
            bundle["label"].set_position((0.995, yfrac))
            bundle["label"].set_text(("TP" if tgt == "TP" else "SL") + f" {y:.2f}")

        # recompute Profit/Stop (dollars) based on new level
        sym_key = next(iter(self.current["orders"].keys()))
        shares = int(self.current["orders"][sym_key].get("share", 0))
        if shares != 0:
            abs_sh = abs(shares)
            last_close = float(self.df["Close"].iloc[-1])
            pos_long = (shares > 0)

            if tgt == "TP":
                profit_ps = (y - last_close) if pos_long else (last_close - y)
                self.current["info"]["Profit"] = round(max(0.0, profit_ps) * abs_sh, 2)
            else:
                stop_ps = (last_close - y) if pos_long else (y - last_close)
                self.current["info"]["Stop"] = round(max(0.0, stop_ps) * abs_sh, 2)

        # refresh header + top strip
        color = "limegreen" if shares > 0 else "red"
        self._update_header_label(color)
        self._refresh_info_line()
        self.canvas.draw_idle()

    def _on_release(self, event):
        self._drag["target"] = None

    # ================== Info line ==================
    def _tick_clock(self):
        self._refresh_info_line()
        self.after(1000, self._tick_clock)

    def _refresh_info_line(self):
        now_str = datetime.now().strftime("%H:%M:%S")
        self.info_var.set(
            f"Inbox: {self._inbox_n}  Time: {now_str}   "
            f"Algo: {self._algo}   Position: {self._position}"
        )

    # ================== Buttons ==================
    def _on_approve(self):
        # send to manager first (if available & current exists)
        print(self.current["algo"],self.current["orders"],self.current["info"])
        if self.ui and self.current:
            try:
                
                self.ui.manager.apply_basket_cmd(
                    self.current["algo"],
                    self.current["orders"],
                    self.current["info"]
                )
            except Exception as e:
                # don't crash UI; just log
                print(f"[approve] apply_basket_cmd error: {e}")

        # then advance
        self._advance()

    def _on_reject(self):
        self._advance()

XXX=0
# Standalone runner (optional demo)
if __name__ == "__main__":
    import sys, pathlib
    win = tb.Window(themename="darkly")
    win.title("CandlePanel — Queue Demo")
    win.geometry("1000x650")

    panel = CandlePanel(win)
    panel.pack(fill="both", expand=True)

    # quick demo buttons to simulate submissions
    def demo_submit_long():
        global XXX
        XXX+=1

        if XXX==3:
            panel.submit_and_go("ALG_LONG_BITO",
                                {"BITO.AM": {"share": 10}},
                                {"Tag": "DEMO"})
        if XXX==4:
            panel.submit_and_go("ALG_SHORT_SPY",
                                {"SPY.AM": {"share": -5}},
                                {"Tag": "DEMO"})
        if XXX==1:
            panel.submit_and_go("ALG_LONG_BITO2",
                                {"BITO.AM": {"share": 100}},
                                {"Tag": "DEMO","Profit":10,"Stop":10})
        if XXX==2:
            panel.submit_and_go("ALG_SHORT_SPY2",
                                {"SPY.AM": {"share": -5}},
                                {"Tag": "DEMO","Profit":10,"Stop":10})

    tb.Button(win, text="DEMO ALGO", command=demo_submit_long).pack(side=tk.LEFT, padx=6, pady=6)

    win.mainloop()
