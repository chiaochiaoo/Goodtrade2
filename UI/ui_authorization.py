"""
Clerk-driven authorization panel.

Replaces the old custom_algos/*.txt -based panel. On Clerk sign-in (and whenever
Manager.ENV switches between TMS and LIVE) we hit
    GET {GOODTRADE_WEB_URL}/api/public/checkbox?email=<signed-in-email>
and render the approved checkboxes for the current env.

Per row:
  name | toggle | x<multiplier (read-only)> | Agg toggle

The active/agg state per (email, env, full_id) is persisted to
custom_algos_config/clerk_<email>_<env>.json so toggles survive a restart.

Public surface kept compatible with the old class:
  - class name `authorization`
  - pannel_name = 'Authorization'
  - method order_confirmation(basket_name, orders) -> (ok, orders, agg, mult, full_id)
"""

import os
import json
import threading
import tkinter as tk
import ttkbootstrap as tb

try:
    import requests
except ImportError:  # pragma: no cover
    requests = None

ACTIVE = 0
MULTIPLIER = 1
AGGRESSION = 2          # IntVar; -1 = Passive, 0 = Regular, 1 = Aggressive
DESCRIPTION = 3

# Stable codes <-> display labels for the aggression dropdown.
AGG_LABELS = {-1: "Passive", 0: "Regular", 1: "Aggressive"}
AGG_VALUES = {v: k for k, v in AGG_LABELS.items()}
AGG_ORDERED_LABELS = ["Passive", "Regular", "Aggressive"]
AGG_UI_VALUES = {-1, 0, 1}

# Saved-state schema version. Files written by older code (with "agg": bool)
# are ignored on load — clean reset, everyone starts at Regular.
SAVE_SCHEMA = 2

GOODTRADE_WEB_URL = os.environ.get(
    "GOODTRADE_WEB_URL",
    "https://goodtrade-terminal.up.railway.app",
)


def _state_path(email, env):
    safe_email = (email or "anon").replace("@", "_at_").replace("/", "_")
    safe_env = (env or "TMS").upper()
    return f"custom_algos_config/clerk_{safe_email}_{safe_env}.json"


class authorization:
    def __init__(self, ui):
        self.ui = ui
        self.pannel_name = "Authorization"

        # Ensure dashboard_panel exists (defensive, copied from old class)
        if not hasattr(self.ui, "user_panels"):
            self.ui.user_panel = tb.LabelFrame(self.ui, text="User", bootstyle="info")
            self.ui.user_panel.place(relx=0, rely=0, relheight=1, relwidth=1)
            self.ui.user_panels = tb.Notebook(self.ui.user_panel)
            self.ui.user_panels.place(relx=0, rely=0, relheight=1, relwidth=1)

        self.ui.auth_panel = tb.Frame(self.ui.user_panels)
        self.ui.user_panels.add(self.ui.auth_panel, text=self.pannel_name)

        # Top bar: status + manual refresh
        topbar = tb.Frame(self.ui.auth_panel)
        topbar.pack(fill="x", padx=8, pady=(8, 4))
        self.status_var = tk.StringVar(value="Sign in to load your checkboxes.")
        tb.Label(topbar, textvariable=self.status_var,
                 font=("Segoe UI", 9), bootstyle="secondary").pack(side="left")
        tb.Button(topbar, text="Refresh", bootstyle="primary-outline",
                  command=self.refresh).pack(side="right")

        # Scrollable list area
        outer = tb.Frame(self.ui.auth_panel)
        outer.pack(fill="both", expand=True, padx=8, pady=(0, 8))
        self.canvas = tk.Canvas(outer, highlightthickness=0, bd=0)
        vscroll = tb.Scrollbar(outer, orient="vertical", command=self.canvas.yview)
        self.canvas.configure(yscrollcommand=vscroll.set)
        self.list_frame = tb.Frame(self.canvas, padding=(4, 2))
        self.list_frame.bind(
            "<Configure>",
            lambda e: self.canvas.configure(scrollregion=self.canvas.bbox("all")),
        )
        self.canvas.create_window((0, 0), window=self.list_frame, anchor="nw")
        vscroll.pack(side="right", fill="y")
        self.canvas.pack(side="left", fill="both", expand=True)
        self.list_frame.bind(
            "<Enter>",
            lambda e: self.canvas.bind_all(
                "<MouseWheel>",
                lambda ev: self.canvas.yview_scroll(int(-1 * (ev.delta / 120)), "units"),
            ),
        )
        self.list_frame.bind(
            "<Leave>", lambda e: self.canvas.unbind_all("<MouseWheel>")
        )

        # algos[full_id] = [ACTIVE BoolVar, multiplier float, PASSIVE BoolVar,
        #                   DESCRIPTION StringVar, name, env]
        self.algos = {}
        self._current_email = None
        self._current_env = None

        # Watch ENV — if Ppro flips env after sign-in, re-fetch for that env.
        if hasattr(self.ui, "ENV"):
            self.ui.ENV.trace_add("write", lambda *a: self._on_env_change())

        # Inject into main UI so old call sites still resolve.
        self.ui.algos = self.algos
        self.ui.algo_groups = []  # legacy attr; nothing iterates it now
        self.ui.save_all = self._save_state
        self.ui.load_all = self.refresh

    # ---------------------------------------------------------------- #
    # Public hooks                                                       #
    # ---------------------------------------------------------------- #

    def on_signed_in(self):
        """Called from Manager.clerk_login on the Tk thread after sign-in."""
        self.refresh()

    def refresh(self):
        """Fetch checkboxes for the currently-signed-in user and current env."""
        email = self._email_from_manager()
        env = self._env_from_manager()

        if not email:
            self.status_var.set("Not signed in.")
            self.algos.clear()
            self._render()
            return
        if requests is None:
            self.status_var.set("Missing 'requests' package.")
            return

        self._current_email = email
        self._current_env = env
        self.status_var.set(f"Loading {env} checkboxes for {email}…")

        # Fetch off the Tk thread; render via ui_bus.
        def _worker():
            try:
                r = requests.get(
                    f"{GOODTRADE_WEB_URL}/api/public/checkbox",
                    params={"email": email},
                    timeout=10,
                )
                r.raise_for_status()
                payload = r.json()
                env_key = "live" if (env or "").upper() == "LIVE" else "tms"
                rows = payload.get(env_key, []) or []
            except Exception as e:
                self._post(lambda: self.status_var.set(f"Fetch failed: {e}"))
                return

            self._post(lambda: self._apply(rows, email, env))

        threading.Thread(target=_worker, daemon=True).start()

    # ---------------------------------------------------------------- #
    # Order-time hook (same signature as the old class)                  #
    # ---------------------------------------------------------------- #

    def order_confirmation(self, basket_name, orders):
        """Look up basket_name by prefix match against active checkboxes.
        Returns (ok, orders, aggression, multiplier, full_id) where
        aggression is -1 (passive) / 0 (regular) / 1 (aggressive)."""
        for full_id, item in self.algos.items():
            if full_id == basket_name[: len(full_id)] and item[ACTIVE].get():
                multiplier = float(item[MULTIPLIER])
                for key in orders.keys():
                    orders[key]["share"] = orders[key]["share"] * multiplier
                aggression = int(item[AGGRESSION].get())
                return True, orders, aggression, multiplier, full_id
        return False, None, 0, 1, ""

    # ---------------------------------------------------------------- #
    # Internals                                                          #
    # ---------------------------------------------------------------- #

    def _email_from_manager(self):
        info = getattr(self.ui.manager, "clerk_user_info", None) if self.ui.manager else None
        if isinstance(info, dict):
            return info.get("email")
        return None

    def _env_from_manager(self):
        env = (self.ui.ENV.get() if hasattr(self.ui, "ENV") else "") or ""
        env = env.upper()
        if env in ("TMS", "LIVE"):
            return env
        # Ppro is "DISCONNECTED" until connected; default to TMS for display.
        return "TMS"

    def _post(self, fn):
        if self.ui.manager and getattr(self.ui.manager, "ui_bus", None):
            self.ui.manager.ui_bus.post(fn)
        else:
            try:
                self.ui.root.after(0, fn)
            except Exception:
                fn()

    def _attach_tooltip(self, widget, text):
        """Lightweight hover tooltip. Shows after 400ms, hides on leave."""
        if not text:
            return
        state = {"tip": None, "after_id": None}

        def show():
            if state["tip"] is not None:
                return
            x = widget.winfo_rootx() + 20
            y = widget.winfo_rooty() + widget.winfo_height() + 4
            tw = tk.Toplevel(widget)
            tw.wm_overrideredirect(True)
            tw.wm_geometry(f"+{x}+{y}")
            tk.Label(tw, text=text, background="#FFFDD0", foreground="#222",
                     relief="solid", borderwidth=1, font=("Segoe UI", 9),
                     justify="left", wraplength=320).pack(ipadx=6, ipady=3)
            state["tip"] = tw

        def schedule(_event=None):
            cancel()
            state["after_id"] = widget.after(400, show)

        def cancel(_event=None):
            if state["after_id"] is not None:
                try:
                    widget.after_cancel(state["after_id"])
                except Exception:
                    pass
                state["after_id"] = None
            if state["tip"] is not None:
                try:
                    state["tip"].destroy()
                except Exception:
                    pass
                state["tip"] = None

        widget.bind("<Enter>", schedule, add="+")
        widget.bind("<Leave>", cancel, add="+")
        widget.bind("<ButtonPress>", cancel, add="+")

    def _on_env_change(self):
        # Only re-fetch if signed in *and* env actually changed.
        new_env = self._env_from_manager()
        if self._current_email and new_env != self._current_env:
            self.refresh()

    def _apply(self, rows, email, env):
        self.algos.clear()
        saved = self._load_state(email, env)

        for r in rows:
            full_id = r.get("full_id") or r.get("shortcode") or ""
            if not full_id:
                continue
            mult = r.get("risk_multiplier", 1.0)
            try:
                mult = float(mult)
            except (TypeError, ValueError):
                mult = 1.0
            state = saved.get(full_id, {})
            agg_raw = state.get("aggression", 0)
            try:
                agg_init = int(agg_raw)
            except (TypeError, ValueError):
                agg_init = 0
            if agg_init not in AGG_UI_VALUES:
                # Passive (-1) is reserved but not exposed yet — fall back to
                # Regular so the combobox has a valid selection.
                agg_init = 0
            self.algos[full_id] = [
                tk.BooleanVar(value=bool(state.get("active", False))),
                mult,
                tk.IntVar(value=agg_init),
                tk.StringVar(value=r.get("description") or r.get("name") or ""),
                r.get("name") or full_id,
                env,
            ]

        # Wire change traces so toggles autosave.
        for full_id, item in self.algos.items():
            item[ACTIVE].trace_add("write", lambda *a: self._save_state())
            item[AGGRESSION].trace_add("write", lambda *a: self._save_state())

        self._render()
        self.status_var.set(
            f"{env} · {len(self.algos)} checkboxes · {email}"
            if self.algos
            else f"{env} · no approved checkboxes for {email}"
        )
        # Push into legacy ui attribute for any consumer still reading it.
        self.ui.algos = self.algos

    def _render(self):
        for w in self.list_frame.winfo_children():
            w.destroy()

        tiny_font = ("Segoe UI", 9)
        if not self.algos:
            tb.Label(self.list_frame,
                     text="No checkboxes loaded.",
                     font=tiny_font, bootstyle="secondary").grid(
                row=0, column=0, sticky="w", padx=4, pady=4)
            return

        # Column headers
        hdr = ("ID", "On", "×", "Aggressiveness")
        for i, h in enumerate(hdr):
            tb.Label(self.list_frame, text=h, font=("Segoe UI", 9, "bold"),
                     bootstyle="primary").grid(row=0, column=i, sticky="w",
                                               padx=(1, 6), pady=(0, 4))

        for row, (full_id, item) in enumerate(sorted(self.algos.items()), start=1):
            display_name = item[4]
            description = item[DESCRIPTION].get()

            tip_lines = []
            if display_name and display_name != full_id:
                tip_lines.append(display_name)
            if description and description != display_name:
                tip_lines.append(description)
            tip_text = "\n".join(tip_lines) or full_id

            lbl = tb.Label(self.list_frame, text=full_id, cursor="hand2",
                           font=tiny_font, width=14, anchor="w")
            lbl.grid(sticky="w", column=0, row=row, padx=(1, 6), pady=(0, 1))
            lbl.bind("<Button-1>", lambda e, v=item[ACTIVE]: v.set(not v.get()))
            self._attach_tooltip(lbl, tip_text)

            tb.Checkbutton(self.list_frame, variable=item[ACTIVE],
                           bootstyle="round-toggle").grid(
                sticky="w", column=1, row=row, padx=(0, 6), pady=(0, 1))

            pct = item[MULTIPLIER] * 100
            pct_text = f"×{pct:g}%" if pct == int(pct) else f"×{pct:.1f}%"
            tb.Label(self.list_frame, text=pct_text,
                     font=tiny_font, bootstyle="secondary").grid(
                sticky="w", column=2, row=row, padx=(0, 6), pady=(0, 1))

            # Aggressiveness dropdown. The combobox shows the label, but we
            # keep the IntVar (-1/0/1) as the source of truth — bind a write
            # handler on the StringVar to project label -> int back into it.
            # Only Regular/Aggressive are exposed for now; clamp anything else
            # (e.g. legacy Passive=-1) to Regular for display.
            agg_var = item[AGGRESSION]
            current = int(agg_var.get())
            if current not in AGG_UI_VALUES:
                current = 0
                agg_var.set(0)
            label_var = tk.StringVar(value=AGG_LABELS[current])

            def _sync(label_v=label_var, int_v=agg_var):
                int_v.set(AGG_VALUES.get(label_v.get(), 0))

            label_var.trace_add("write", lambda *a, fn=_sync: fn())

            cb = tb.Combobox(
                self.list_frame,
                textvariable=label_var,
                values=AGG_ORDERED_LABELS,
                state="readonly",
                width=11,
                font=tiny_font,
            )
            cb.grid(sticky="w", column=3, row=row, padx=(0, 1), pady=(0, 1))

    # ---------------------------------------------------------------- #
    # Persistence (active/agg toggles only — multiplier comes from API)  #
    # ---------------------------------------------------------------- #

    def _load_state(self, email, env):
        try:
            with open(_state_path(email, env), "r", encoding="utf-8") as f:
                raw = json.load(f)
        except FileNotFoundError:
            return {}
        except Exception as e:
            print("authorization: load state failed:", e)
            return {}

        # Schema-2 wraps entries under {"schema": 2, "entries": {...}}. Old
        # files were a flat dict of {full_id: {"active": bool, "agg": bool}};
        # we ignore them so everyone starts fresh on Regular.
        if isinstance(raw, dict) and raw.get("schema") == SAVE_SCHEMA:
            entries = raw.get("entries") or {}
            return entries if isinstance(entries, dict) else {}
        return {}

    def _save_state(self, *_):
        if not self._current_email or not self._current_env:
            return
        path = _state_path(self._current_email, self._current_env)
        os.makedirs(os.path.dirname(path), exist_ok=True)
        try:
            entries = {}
            for full_id, item in self.algos.items():
                agg_val = int(item[AGGRESSION].get())
                if agg_val not in (-1, 0, 1):
                    agg_val = 0
                entries[full_id] = {
                    "active": bool(item[ACTIVE].get()),
                    "aggression": agg_val,
                }
            payload = {"schema": SAVE_SCHEMA, "entries": entries}
            with open(path, "w", encoding="utf-8") as f:
                json.dump(payload, f, indent=2)
        except Exception as e:
            print("authorization: save state failed:", e)
