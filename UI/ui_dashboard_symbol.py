# ui_dashboard_symbol.py
import tkinter as tk
import ttkbootstrap as tb
from ttkbootstrap.constants import *
from tkinter import ttk

# Final headers with your requested inserts:
#   - Data-Correct after Tradable
#   - Intend Pos after Net Pos
#   - Flatten after Risk
HEADERS = [
    "Symbol",
    "Tradable",
    "Data-Correct",
    "Net Pos",
    "Intend Pos",
    "#Algos",
    "Unreal",
    "Real",
    "Risk",
    "Flatten",
]

class Symbol_Dashboard_Panel(tb.Frame):
    """
    Compact, sortable symbol dashboard table.

    Key features in this version:
      • Adds 'Data-Correct', 'Intend Pos', and 'Flatten'
      • 'Flatten' is an action cell: hover -> hand cursor; click -> self.ui.on_symbol_flatten(symbol)
      • Stable, idempotent set_data() that only updates changed cells
      • Numeric-aware sorting
      • Minimal neutral row background (keeps subtle separation from the window)
    """
    def __init__(self, parent, *, height=18, ui=None, headers=None):
        super().__init__(parent)
        self.ui = ui
        self.height = height
        self.columns = list(headers) if headers else None
        self.last_sort_column = None
        self.last_sort_reverse = False
        self._rows: dict[str, str] = {}  # symbol -> iid

        # Action columns — hover hand + click
        self._action_cols = {"Flatten"}
        self._hovering_action = False

        # ---- Container
        container = tb.Frame(self)
        container.pack(fill="both", expand=True, padx=5, pady=5)

        # ---- Tree + scrollbars
        self.tree = tb.Treeview(
            container,
            columns=self.columns if self.columns else (),
            show="headings",
            height=height,
            bootstyle="Treeview",
            selectmode="extended",
        )
        vsb = tb.Scrollbar(container, orient="vertical", command=self.tree.yview)
        hsb = tb.Scrollbar(container, orient="horizontal", command=self.tree.xview)
        self.tree.configure(yscrollcommand=vsb.set, xscrollcommand=hsb.set)

        self.tree.grid(row=0, column=0, sticky="nsew")
        vsb.grid(row=0, column=1, sticky="ns")
        hsb.grid(row=1, column=0, sticky="ew")
        container.rowconfigure(0, weight=1)
        container.columnconfigure(0, weight=1)

        # ---- Row tag: subtle neutral bg + proper foreground
        self.tree.tag_configure("default_text", foreground="black", background="#f4f4f4")

        # If headers provided up-front, set columns now
        if self.columns:
            self._setup_columns(self.columns)

        # ---- Hover + click bindings for action columns
        self.tree.bind("<Motion>", self._on_motion)
        self.tree.bind("<Leave>", self._on_leave)
        self.tree.bind("<Button-1>", self._on_click)

    # ---------------- Public API ----------------
    def set_headers(self, headers):
        """Explicitly set headers at runtime and rebuild the columns."""
        self.columns = list(headers)
        self._setup_columns(self.columns)
        self.clear()

    def set_data(self, rows, *, header_unreal=None, header_real=None):
        """
        Idempotent, no-flash update:
          - updates only changed cells
          - inserts new rows
          - deletes rows no longer present
          - preserves yview and selection
          - reapplies active sort
          - updates 'Unreal'/'Real' header badges if provided

        'rows' can be list[dict] or dict[str, dict] (must include or imply 'Symbol').
        """
        items = self._normalize_rows(rows)
        if not items and not self._rows:
            self._update_header_numbers(header_unreal, header_real)
            return

        if not self.columns and items:
            self.columns = self._infer_headers_from_items(items)
            self._setup_columns(self.columns)

        incoming_by_sym = {}
        for d in items:
            sym = d.get("Symbol")
            if not sym:
                continue
            # Ensure default values exist for new columns if caller didn't pass them
            if "Intend Pos" in (self.columns or []) and "Intend Pos" not in d:
                d["Intend Pos"] = 0
            if "Flatten" in (self.columns or []) and "Flatten" not in d:
                d["Flatten"] = "FLATTEN"
            if "Data-Correct" in (self.columns or []) and "Data-Correct" not in d:
                d["Data-Correct"] = ""  # or 'Y'/'N' if you prefer
            incoming_by_sym[sym] = d

        try:
            y0 = self.tree.yview()[0]
        except Exception:
            y0 = 0.0
        prev_selection = tuple(self.tree.selection())

        # Upserts
        for sym, new_row_dict in incoming_by_sym.items():
            if sym in self._rows:
                iid = self._rows[sym]
                aligned = {k: new_row_dict.get(k, "") for k in self.columns}
                new_vals = tuple(self._format_value(k, aligned[k]) for k in self.columns)
                old_vals = self.tree.item(iid, "values")
                if new_vals != old_vals:
                    for i, (old_v, new_v) in enumerate(zip(old_vals, new_vals)):
                        if old_v != new_v:
                            self.tree.set(iid, self.columns[i], new_v)
                    self.tree.item(iid, tags=("default_text",))
            else:
                self._insert_or_update(new_row_dict)

        # Deletes
        for sym in list(self._rows.keys()):
            if sym not in incoming_by_sym:
                iid = self._rows.pop(sym)
                self.tree.delete(iid)

        # Reapply sort if active
        if self.last_sort_column:
            self._sort_by(self.last_sort_column, self.last_sort_reverse)

        # Update header badges if provided
        self._update_header_numbers(header_unreal, header_real)

        # Restore viewport & selection
        try:
            self.tree.yview_moveto(y0)
        except Exception:
            pass
        self.tree.selection_set([iid for iid in prev_selection if self.tree.exists(iid)])

    def bulk_update(self, rows):
        """Convenience mass upsert (no diffing)."""
        items = self._normalize_rows(rows)
        if not self.columns and items:
            self.columns = self._infer_headers_from_items(items)
            self._setup_columns(self.columns)
        for d in items:
            self._insert_or_update(d)

    def update_row(self, symbol, **fields):
        """Upsert by symbol; pass any fields to overwrite."""
        cur = self._current_row(symbol)
        if not cur:
            cur = {"Symbol": symbol}
        cur.update(fields)
        self._insert_or_update(cur)

    def update_from_dict(self, row_dict):
        """Upsert from a dict that includes 'Symbol'."""
        if "Symbol" not in row_dict:
            return
        if not self.columns:
            self.columns = self._infer_headers_from_items([row_dict])
            self._setup_columns(self.columns)
        self._insert_or_update(row_dict)

    def clear(self):
        self.tree.delete(*self.tree.get_children())
        self._rows.clear()

    def get_selected_symbol(self):
        sel = self.tree.selection()
        if not sel:
            return None
        vals = self.tree.item(sel[0], "values")
        if "Symbol" in (self.columns or []):
            return vals[self.columns.index("Symbol")]
        return None

    def apply_style_from_ui(self, ui):
        self.ui = ui
        # Example hook if you want to auto-switch dark/light in the future.

    # ---------------- Sorting ----------------
    def _sort_by(self, col, descending):
        data = [(self.tree.set(k, col), k) for k in self.tree.get_children("")]
        # numeric-aware
        if self._is_numeric_column(col):
            try:
                data = [(self._to_float(v), k) for v, k in data]
            except Exception:
                pass
        else:
            data = [(str(v).lower(), k) for v, k in data]

        data.sort(reverse=descending)
        for idx, (_, k) in enumerate(data):
            self.tree.move(k, "", idx)
        self.last_sort_column = col
        self.last_sort_reverse = descending
        self.tree.heading(col, command=lambda c=col: self._sort_by(c, not descending))

    # ---------------- Internals ----------------
    def _setup_columns(self, headers):
        self.tree["columns"] = headers
        for h in headers:
            self.tree.heading(h, text=h, anchor="center",
                              command=lambda col=h: self._sort_by(col, False))
            width = self._default_width_for(h)
            anchor = self._default_anchor_for(h)
            self.tree.column(h, width=width, minwidth=width, stretch=False, anchor=anchor)

    def _normalize_rows(self, rows):
        """Return list[dict], each with at least 'Symbol' key if present in headers."""
        if not rows:
            return []
        out = []
        if isinstance(rows, dict):
            for sym, d in rows.items():
                if isinstance(d, dict):
                    if "Symbol" not in d:
                        d = {"Symbol": sym, **d}
                    out.append(d)
        else:
            for d in rows:
                if isinstance(d, dict):
                    out.append(d)
        return out

    def _infer_headers_from_items(self, items):
        first = items[0]
        keys = list(first.keys())
        # Ensure Symbol is first if present
        if "Symbol" in keys:
            keys = ["Symbol"] + [k for k in keys if k != "Symbol"]
        return keys

    def _insert_or_update(self, row_dict):
        # ensure headers are set
        if not self.columns:
            self.columns = self._infer_headers_from_items([row_dict])
            self._setup_columns(self.columns)

        # fill missing keys with ""
        row = {k: row_dict.get(k, "") for k in self.columns}

        # Ensure defaults for our new columns
        if "Intend Pos" in self.columns and row.get("Intend Pos", "") == "":
            row["Intend Pos"] = 0
        if "Flatten" in self.columns and row.get("Flatten", "") == "":
            row["Flatten"] = "FLATTEN"
        if "Data-Correct" in self.columns and row.get("Data-Correct", "") == "":
            row["Data-Correct"] = ""

        symbol = row.get("Symbol", "")
        values = tuple(self._format_value(k, row[k]) for k in self.columns)

        if symbol in self._rows:
            iid = self._rows[symbol]
            self.tree.item(iid, values=values, tags=("default_text",))
        else:
            iid = self.tree.insert("", "end", values=values, tags=("default_text",))
            if symbol:
                self._rows[symbol] = iid

    def _current_row(self, symbol):
        if symbol not in self._rows:
            return {}
        vals = self.tree.item(self._rows[symbol], "values")
        return dict(zip(self.columns, vals))

    # --- formatting / heuristics ---
    def _format_value(self, col, v):
        if self._is_numeric_column(col):
            try:
                return f"{float(str(v).replace(',', '')):,.2f}"
            except Exception:
                return str(v)
        return str(v)

    def _is_numeric_column(self, col):
        numeric_like = {"Net Pos", "Intend Pos", "#Algos", "Unreal", "Real", "Risk", "Positions"}
        if col in numeric_like:
            return True
        # Probe existing values to guess
        for iid in self.tree.get_children(""):
            v = self.tree.set(iid, col)
            if v not in ("", None):
                try:
                    float(str(v).replace(",", ""))
                    return True
                except Exception:
                    return False
        return False

    def _default_anchor_for(self, col):
        if col == "Symbol":
            return "w"
        # center typical boolean / flags
        if col.lower() in ("tradable", "enabled", "active", "data-correct", "flatten"):
            return "center"
        return "e" if self._is_numeric_column(col) else "w"

    def _default_width_for(self, col):
        if col == "Symbol":
            return 160
        lc = col.lower()
        if lc in ("tradable", "enabled", "active", "data-correct", "flatten"):
            return 100
        if col in ("Net Pos", "Intend Pos"):
            return 110
        if col in ("#Algos",):
            return 86
        if col in ("Unreal", "Real", "Risk"):
            return 120
        return 100

    def _to_float(self, v):
        try:
            return float(str(v).replace(",", ""))
        except Exception:
            return 0.0

    def _col_index(self, name):
        if not self.columns:
            return None
        try:
            return self.columns.index(name)
        except ValueError:
            return None

    def _update_header_numbers(self, unreal=None, real=None, *, uppercase=True, fmt="{name}: {value:,.2f}"):
        """Update heading text for 'Unreal' and 'Real' without changing column IDs."""
        for base_name, val in (("Unreal", unreal), ("Real", real)):
            idx = self._col_index(base_name)
            if idx is None:
                continue
            label = base_name.upper() if uppercase else base_name
            if val is not None:
                try:
                    label = fmt.format(name=label, value=float(val))
                except Exception:
                    label = f"{label}: {val}"
            self.tree.heading(self.columns[idx], text=label)

    # ---------------- Action cell UX ----------------
    def _on_motion(self, event):
        """Show hand cursor when hovering an action column (Flatten)."""
        region = self.tree.identify("region", event.x, event.y)
        if region != "cell":
            if self._hovering_action:
                self.tree.configure(cursor="")
                self._hovering_action = False
            return

        col_id = self.tree.identify_column(event.x)  # e.g., '#1'
        try:
            col_index = int(col_id.replace("#", "")) - 1
        except Exception:
            col_index = -1

        if 0 <= col_index < len(self.columns):
            col_name = self.columns[col_index]
            if col_name in self._action_cols:
                if not self._hovering_action:
                    self.tree.configure(cursor="hand2")
                    self._hovering_action = True
                return

        if self._hovering_action:
            self.tree.configure(cursor="")
            self._hovering_action = False

    def _on_leave(self, _event):
        if self._hovering_action:
            self.tree.configure(cursor="")
            self._hovering_action = False

    def _on_click(self, event):
        """Handle clicks on action columns."""
        region = self.tree.identify("region", event.x, event.y)
        if region != "cell":
            return

        row_iid = self.tree.identify_row(event.y)
        if not row_iid:
            return

        col_id = self.tree.identify_column(event.x)  # '#N'
        try:
            col_index = int(col_id.replace("#", "")) - 1
        except Exception:
            return

        if not (0 <= col_index < len(self.columns)):
            return

        col_name = self.columns[col_index]
        if col_name not in self._action_cols:
            return

        # Get symbol from the row to pass to UI handler
        try:
            vals = self.tree.item(row_iid, "values")
            sym_idx = self._col_index("Symbol")
            symbol = vals[sym_idx] if sym_idx is not None else None
        except Exception:
            symbol = None

        if col_name == "Flatten":
            if self.ui and hasattr(self.ui, "on_symbol_flatten"):
                try:
                    self.ui.manager.symbol_flatten(symbol)
                except Exception as e:
                    print(f"[Flatten] handler error for {symbol}: {e}")
            else:
                print(f"[Flatten] {symbol}")

# ---------------- Demo ----------------
if __name__ == "__main__":
    root = tb.Window(themename="flatly")
    root.title("Symbol Dashboard Example")

    class DummyUI:
        def on_symbol_flatten(self, symbol):
            print(f"DummyUI: FLATTEN request for {symbol}")

    panel = Symbol_Dashboard_Panel(root, headers=HEADERS, ui=DummyUI())
    panel.pack(fill="both", expand=True)

    sample_data = [
        {"Symbol": "AAPL", "Tradable": "Y", "Data-Correct": "Y", "Net Pos": 100, "Intend Pos": 120,
         "#Algos": 3, "Unreal": 1250.55, "Real": 400.0, "Risk": 1200, "Flatten": "FLATTEN"},
        {"Symbol": "MSFT", "Tradable": "Y", "Data-Correct": "N", "Net Pos": -50, "Intend Pos": -20,
         "#Algos": 2, "Unreal": -320.40, "Real": 150.0, "Risk": 600, "Flatten": "FLATTEN"},
        {"Symbol": "TSLA", "Tradable": "N", "Data-Correct": "", "Net Pos": 0, "Intend Pos": 0,
         "#Algos": 0, "Unreal": 0.0, "Real": 0.0, "Risk": 0, "Flatten": "FLATTEN"},
    ]

    panel.set_data(sample_data)

    root.mainloop()
