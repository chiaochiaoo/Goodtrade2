import tkinter as tk
import ttkbootstrap as tb
from ttkbootstrap.constants import *
from tkinter import ttk

# Optional default. You can still pass headers=... to the constructor or let it infer.
HEADERS = ["Algos", "#Algos", "Unreal", "Real"]

class Algo_Dashboard_Panel(tb.Frame):
    def __init__(self, parent, *, height=18, ui=None, headers=None):
        super().__init__(parent)
        self.ui = ui
        self.height = height
        self.columns = list(headers) if headers else None  # becomes list of strings
        self.last_sort_column = None
        self.last_sort_reverse = False
        self._rows = {}  # symbol -> iid

        # container
        container = tb.Frame(self)
        container.pack(fill="both", expand=True, padx=5, pady=5)

        # tree + scrollbars
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

        # style tags
        self.tree.tag_configure("row_green", background="#e6ffe6")
        self.tree.tag_configure("row_red", background="#ffe6e6")
        self.tree.tag_configure("default_text")

        # if headers were given, finish the columns now
        if self.columns:
            self._setup_columns(self.columns)

        self.update_treeview_row_styles()

    # ---------------- Public API ----------------

    def set_headers(self, headers):
        """Explicitly set headers at runtime and rebuild the columns."""
        self.columns = list(headers)
        self._setup_columns(self.columns)
        # keep existing rows but remap values if possible
        # (safer to clear, since key order changed)
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
        rows can be list[dict] or dict[str, dict] (must include or imply 'Symbol').
        """
        items = self._normalize_rows(rows)
        if not items and not self._rows:
            # still allow header update even if there are no rows yet
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
            incoming_by_sym[sym] = d

        try:
            y0 = self.tree.yview()[0]
        except Exception:
            y0 = 0.0
        prev_selection = tuple(self.tree.selection())

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
                    self.tree.item(iid, tags=self._tags_for_row(aligned))
            else:
                self._insert_or_update(new_row_dict)

        for sym in list(self._rows.keys()):
            if sym not in incoming_by_sym:
                iid = self._rows.pop(sym)
                self.tree.delete(iid)

        if self.last_sort_column:
            self._sort_by(self.last_sort_column, self.last_sort_reverse)

        # ⬇️ Set the header badges you passed in
        self._update_header_numbers(header_unreal, header_real)

        try:
            self.tree.yview_moveto(y0)
        except Exception:
            pass
        self.tree.selection_set([iid for iid in prev_selection if self.tree.exists(iid)])
        
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

    def bulk_update(self, rows):
        items = self._normalize_rows(rows)
        if not self.columns and items:
            self.columns = self._infer_headers_from_items(items)
            self._setup_columns(self.columns)
        for d in items:
            self._insert_or_update(d)

    def update_row(self, symbol, **fields):
        """
        Upsert by symbol; pass any fields to overwrite.
        Example: update_row("AAPL", Unreal=123.4, Risk=900)
        """
        cur = self._current_row(symbol)
        if not cur:
            cur = {"Symbol": symbol}
        cur.update(fields)
        self._insert_or_update(cur)

    def update_from_dict(self, row_dict):
        """
        Upsert from a dict that includes 'Symbol'.
        Example: update_from_dict({"Symbol":"AAPL","Unreal":10,"Tradable":"N"})
        """
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
        self.update_treeview_row_styles()

    # ---------------- Style ----------------

    def update_treeview_row_styles(self, *, dark: bool | None = None,
                                   normal_text: str | None = None,
                                   green_bg: str | None = None,
                                   red_bg: str | None = None):
        if dark is None:
            inferred_dark = False
            try:
                if self.ui and (
                    (hasattr(self.ui, "DARK_MODE") and self.ui.DARK_MODE.get() == 1) or
                    (hasattr(self.ui, "DISASTER_MODE") and self.ui.DISASTER_MODE.get() == 1)
                ):
                    inferred_dark = True
            except Exception:
                inferred_dark = False
            dark = inferred_dark

        normal_text = ("white" if dark else "black") if normal_text is None else normal_text
        green_bg = ("#2a662a" if dark else "#e6ffe6") if green_bg is None else green_bg
        red_bg = ("#802b2b" if dark else "#ffe6e6") if red_bg is None else red_bg

        self.tree.tag_configure("default_text", foreground=normal_text)
        self.tree.tag_configure("row_green", background=green_bg)
        self.tree.tag_configure("row_red", background=red_bg)

        unreal_idx = self._col_index("Unreal")
        for iid in self.tree.get_children(""):
            tags = []
            if unreal_idx is not None:
                raw = self.tree.item(iid, "values")[unreal_idx]
                unreal = self._to_float(raw)
                tags.append("row_green" if unreal >= 0 else "row_red")
            tags.append("default_text")
            self.tree.item(iid, tags=tuple(tags))


    def update_treeview_row_styles(self, *, dark: bool | None = None,
                                   normal_text: str | None = None,
                                   row_bg: str | None = None):
        # detect dark
        if dark is None:
            dark = False
            try:
                if self.ui and (
                    (hasattr(self.ui, "DARK_MODE") and self.ui.DARK_MODE.get() == 1) or
                    (hasattr(self.ui, "DISASTER_MODE") and self.ui.DISASTER_MODE.get() == 1)
                ):
                    dark = True
            except Exception:
                dark = False

        normal_text = ("white" if dark else "black") if normal_text is None else normal_text

        # pick a subtle neutral background
        if row_bg is None:
            row_bg = "#4d4d4d" if dark else "#f2f2f2"   # soft dark grey or soft light grey

        # define style
        self.tree.tag_configure("default_text", foreground=normal_text, background=row_bg)

        # apply to all rows
        for iid in self.tree.get_children(""):
            self.tree.item(iid, tags=("default_text",))
        # ---------------- Sorting ----------------



    # ---------------- Internals ----------------
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

    def _setup_columns(self, headers):
        self.tree["columns"] = headers
        # remove any previous heading configs
        for h in headers:
            self.tree.heading(h, text=h, anchor="center",
                              command=lambda col=h: self._sort_by(col, False))

            # width & alignment heuristics
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
        # prefer user-provided HEADERS if global exists and subset of item keys
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

        symbol = row.get("Symbol", "")
        values = tuple(self._format_value(k, row[k]) for k in self.columns)
        tags = self._tags_for_row(row)

        if symbol in self._rows:
            iid = self._rows[symbol]
            self.tree.item(iid, values=values, tags=tags)
        else:
            iid = self.tree.insert("", "end", values=values, tags=tags)
            if symbol:
                self._rows[symbol] = iid

    def _current_row(self, symbol):
        if symbol not in self._rows:
            return {}
        vals = self.tree.item(self._rows[symbol], "values")
        return dict(zip(self.columns, vals))

    # --- formatting / heuristics ---

    def _format_value(self, col, v):
        # keep Symbol/text as-is
        if self._is_numeric_column(col):
            try:
                return f"{float(str(v).replace(',', '')):,.2f}"
            except Exception:
                return str(v)
        return str(v)

    def _tags_for_row(self, row):
        unreal_idx = self._col_index("Unreal")
        if unreal_idx is None:
            return ("default_text",)
        val = row.get("Unreal", "0")
        unreal = self._to_float(val)
        tag = "row_green" if unreal >= 0 else "row_red"
        return (tag, "default_text")

    def _tags_for_row(self, row):
        # Always return default text, no color-coding
        return ("default_text",)
    # --- heuristics helpers ---

    def _is_numeric_column(self, col):
        # Heuristic: common numeric names or anything not Symbol that often holds numbers
        numeric_like = {"Net Pos", "#Algos", "Unreal", "Real", "Risk", "Positions"}
        if col in numeric_like:
            return True
        # otherwise probe first few rows
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
        # center if looks boolean/Y/N
        if col.lower() in ("tradable", "enabled", "active"):
            return "center"
        return "e" if self._is_numeric_column(col) else "w"

    def _default_width_for(self, col):
        if col == "Symbol":
            return 160
        if col.lower() in ("tradable", "enabled", "active"):
            return 86
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

if __name__ == "__main__":
    root = tb.Window(themename="flatly")   # ttkbootstrap themed window
    root.title("Symbol Dashboard Example")

    panel = Symbol_Dashboard_Panel(root, headers=HEADERS)
    panel.pack(fill="both", expand=True)

    # Example rows
    sample_data = [
        {"Symbol": "AAPL", "Tradable": "Y", "Net Pos": 100, "#Algos": 3, "Unreal": 1250.55, "Real": 400.0, "Risk": 1200},
        {"Symbol": "MSFT", "Tradable": "Y", "Net Pos": -50, "#Algos": 2, "Unreal": -320.40, "Real": 150.0, "Risk": 600},
        {"Symbol": "TSLA", "Tradable": "N", "Net Pos": 0, "#Algos": 0, "Unreal": 0.0, "Real": 0.0, "Risk": 0},
    ]

    panel.set_data(sample_data)

    root.mainloop()