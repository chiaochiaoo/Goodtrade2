# ui_dashboard_algo.py
import tkinter as tk
import ttkbootstrap as tb
from ttkbootstrap.constants import *

HEADERS = ["Algos", "#Algos", "Unreal", "Real"]

class Algo_Dashboard_Panel(tb.Frame):
    """
    A compact Treeview that shows aggregate PnL by TradingPlan.tag.

    Public API:
      - set_headers(headers: list[str])
      - set_data(rows: list[dict], header_unreal: float|None = None, header_real: float|None = None)
      - clear()
      - apply_style_from_ui(ui)  # optional, for dark/disaster modes
    """
    def __init__(self, parent, *, height=12, ui=None, headers=None):
        super().__init__(parent)
        self.ui = ui
        self.height = height
        self.columns = list(headers) if headers else list(HEADERS)
        self.last_sort_column = None
        self.last_sort_reverse = False
        self._rows_by_tag = {}  # tag -> iid

        container = tb.Frame(self)
        container.pack(fill="both", expand=True, padx=5, pady=5)

        self.tree = tb.Treeview(
            container,
            columns=self.columns,
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

        # subtle row background so the table stands out from page bg
        self.tree.tag_configure("row_default", background="#f5f5f7")
        self.tree.tag_configure("row_green", background="#e6ffe6")
        self.tree.tag_configure("row_red", background="#ffe6e6")
        self.tree.tag_configure("default_text", foreground="black")

        self._setup_columns(self.columns)

    # -------- Public API --------
    def set_headers(self, headers):
        self.columns = list(headers)
        self._setup_columns(self.columns)
        self.clear()

    def set_data(self, rows, *, header_unreal=None, header_real=None):
        """
        rows = [
          {"Algos": "TAG1", "#Algos": 3, "Unreal": 123.45, "Real": -50.0},
          ...
        ]
        """
        rows = rows or []
        incoming = {str(d.get("Algos", "")).strip(): d for d in rows if isinstance(d, dict)}

        # remember viewport
        try:
            y0 = self.tree.yview()[0]
        except Exception:
            y0 = 0.0
        prev_sel = tuple(self.tree.selection())

        # upsert / update
        for tag, d in incoming.items():
            aligned = {k: d.get(k, "") for k in self.columns}
            if tag in self._rows_by_tag:
                iid = self._rows_by_tag[tag]
                old_vals = self.tree.item(iid, "values")
                new_vals = tuple(self._format_value(k, aligned[k]) for k in self.columns)
                if new_vals != old_vals:
                    for i, (ov, nv) in enumerate(zip(old_vals, new_vals)):
                        if ov != nv:
                            self.tree.set(iid, self.columns[i], nv)
                    self.tree.item(iid, tags=self._tags_for_row(aligned))
            else:
                iid = self.tree.insert("", "end",
                    values=tuple(self._format_value(k, aligned[k]) for k in self.columns),
                    tags=self._tags_for_row(aligned))
                self._rows_by_tag[tag] = iid

        # delete missing
        for tag in list(self._rows_by_tag.keys()):
            if tag not in incoming:
                self.tree.delete(self._rows_by_tag.pop(tag))

        # keep current sort
        if self.last_sort_column:
            self._sort_by(self.last_sort_column, self.last_sort_reverse)

        # update header badges
        self._update_header_numbers(header_unreal, header_real)

        # restore viewport/selection
        try:
            self.tree.yview_moveto(y0)
        except Exception:
            pass
        self.tree.selection_set([iid for iid in prev_sel if self.tree.exists(iid)])

    def clear(self):
        self.tree.delete(*self.tree.get_children())
        self._rows_by_tag.clear()

    def apply_style_from_ui(self, ui):
        """Optional: infer dark/disaster mode for text color."""
        self.ui = ui
        try:
            dark = (
                (hasattr(ui, "DARK_MODE") and ui.DARK_MODE.get() == 1) or
                (hasattr(ui, "DISASTER_MODE") and ui.DISASTER_MODE.get() == 1)
            )
        except Exception:
            dark = False
        self.tree.tag_configure("default_text", foreground=("white" if dark else "black"))

    # -------- Internals --------
    def _setup_columns(self, headers):
        self.tree["columns"] = headers
        for h in headers:
            self.tree.heading(h, text=h, anchor="center",
                              command=lambda col=h: self._sort_by(col, False))
            width = self._default_width(h)
            anchor = "center" if h in ("#Algos", "Unreal", "Real") else "w"
            self.tree.column(h, width=width, minwidth=width, stretch=False, anchor=anchor)

    def _default_width(self, h):
        return {
            "Algos": 180,
            "#Algos": 80,
            "Unreal": 120,
            "Real": 120,
        }.get(h, 120)

    def _sort_by(self, col, descending):
        data = [(self.tree.set(k, col), k) for k in self.tree.get_children("")]
        if col in ("#Algos", "Unreal", "Real"):
            def _to_float(v):
                try:
                    return float(str(v).replace(",", ""))
                except Exception:
                    return 0.0
            data = [(_to_float(v), k) for v, k in data]
        else:
            data = [(str(v).lower(), k) for v, k in data]
        data.sort(reverse=descending)
        for idx, (_, k) in enumerate(data):
            self.tree.move(k, "", idx)
        self.last_sort_column = col
        self.last_sort_reverse = descending
        self.tree.heading(col, command=lambda c=col: self._sort_by(c, not descending))

    def _format_value(self, key, val):
        if key in ("Unreal", "Real"):
            try:
                return f"{float(val):,.2f}"
            except Exception:
                return val
        if key == "#Algos":
            try:
                return int(val)
            except Exception:
                return val
        return val

    def _tags_for_row(self, row_dict):
        # colorize by Unreal
        try:
            unreal = float(row_dict.get("Unreal", 0) or 0)
        except Exception:
            unreal = 0.0
        base = "row_green" if unreal >= 0 else "row_red"
        return (base, "default_text")

    def _update_header_numbers(self, unreal=None, real=None, fmt="{name}: {value:,.2f}"):
        for base_name, val in (("Unreal", unreal), ("Real", real)):
            if base_name not in self.columns:
                continue
            label = base_name.upper()
            if val is not None:
                try:
                    label = fmt.format(name=label, value=float(val))
                except Exception:
                    label = f"{label}: {val}"
            self.tree.heading(base_name, text=label)
