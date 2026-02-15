# ui_dashboard_algos.py
import tkinter as tk
import ttkbootstrap as tb
from ttkbootstrap.constants import *
from tkinter import ttk

try:
    from UI.ui_tooltips import Tooltip
except:
    from ui_tooltips import Tooltip

HEADERS = [
    "Algo",
    "#Algos",
    "Pos",
    "Unreal",
    "Real",
    "Flatten",
]

class Algo_Dashboard_Panel(tb.Frame):
    """
    Algo dashboard with DARK_MODE support, Flatten action, and tooltips on 'Pos' cells.

    - Hover 'Flatten' -> hand cursor; click -> self.ui.manager.flatten_symbol(algo)
    - Hover 'Pos' -> tooltip using ui_tooltips.Tooltip
      * If self.ui.get_pos_tooltip(algo, pos_value, row_dict) exists, its return is used.
      * Otherwise shows the 'Pos' cell value.
    """
    def __init__(self, parent, *, height=18, ui=None, headers=None):
        super().__init__(parent)
        self.ui = ui
        self.height = height
        self.columns = list(headers) if headers else None
        self.last_sort_column = None
        self.last_sort_reverse = False
        self._rows: dict[str, str] = {}  # algo -> iid

        # Action columns — hover hand + click
        self._action_cols = {"Flatten"}
        self._hovering_action = False

        # Tooltip (Pos column only)
        self._tooltip_col = "Pos"
        self._tooltip = Tooltip  # class ref
        self._pos_tooltip = None  # instance
        self._tip_visible_for = (None, None)  # (row_iid, col_name)

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

        # Row tag
        self._ROW_TAG = "row_default"

        # If headers provided up-front, set columns now
        if self.columns:
            self._setup_columns(self.columns)

        # ---- Bindings
        self.tree.bind("<Motion>", self._on_motion)   # hover (hand + tooltip)
        self.tree.bind("<Leave>", self._on_leave)     # hide tooltip, reset cursor
        self.tree.bind("<Button-1>", self._on_click)  # click Flatten

        # Initial style
        self.update_treeview_row_styles()

    # ---------------- Public API ----------------
    def set_headers(self, headers):
        self.columns = list(headers)
        self._setup_columns(self.columns)
        self.clear()
        self.update_treeview_row_styles()

    def set_data(self, rows, *, header_unreal=None, header_real=None):
        items = self._normalize_rows(rows)
        if not items and not self._rows:
            self._update_header_numbers(header_unreal, header_real)
            self.update_treeview_row_styles()
            return

        if not self.columns and items:
            self.columns = self._infer_headers_from_items(items)
            self._setup_columns(self.columns)

        incoming_by_key = {}
        for d in items:
            algo = d.get("Algo")
            if not algo:
                continue
            # Ensure defaults
            if "Flatten" in (self.columns or []) and "Flatten" not in d:
                d["Flatten"] = "FLATTEN"
            incoming_by_key[algo] = d

        try:
            y0 = self.tree.yview()[0]
        except Exception:
            y0 = 0.0
        prev_selection = tuple(self.tree.selection())

        # Upserts
        for algo, new_row in incoming_by_key.items():
            if algo in self._rows:
                iid = self._rows[algo]
                aligned = {k: new_row.get(k, "") for k in self.columns}
                new_vals = tuple(self._format_value(k, aligned[k]) for k in self.columns)
                old_vals = self.tree.item(iid, "values")
                if new_vals != old_vals:
                    for i, (old_v, new_v) in enumerate(zip(old_vals, new_vals)):
                        if old_v != new_v:
                            self.tree.set(iid, self.columns[i], new_v)
                    self.tree.item(iid, tags=(self._ROW_TAG,))
            else:
                self._insert_or_update(new_row)

        # Deletes
        for algo in list(self._rows.keys()):
            if algo not in incoming_by_key:
                iid = self._rows.pop(algo)
                self.tree.delete(iid)

        # Sort, badges, viewport, selection
        if self.last_sort_column:
            self._sort_by(self.last_sort_column, self.last_sort_reverse)

        self._update_header_numbers(header_unreal, header_real)
        try:
            self.tree.yview_moveto(y0)
        except Exception:
            pass
        self.tree.selection_set([iid for iid in prev_selection if self.tree.exists(iid)])

        self.update_treeview_row_styles()

    def bulk_update(self, rows):
        items = self._normalize_rows(rows)
        if not self.columns and items:
            self.columns = self._infer_headers_from_items(items)
            self._setup_columns(self.columns)
        for d in items:
            self._insert_or_update(d)
        self.update_treeview_row_styles()

    def update_row(self, algo, **fields):
        cur = self._current_row(algo)
        if not cur:
            cur = {"Algo": algo}
        cur.update(fields)
        self._insert_or_update(cur)
        self.update_treeview_row_styles()

    def update_from_dict(self, row_dict):
        if "Algo" not in row_dict:
            return
        if not self.columns:
            self.columns = self._infer_headers_from_items([row_dict])
            self._setup_columns(self.columns)
        self._insert_or_update(row_dict)
        self.update_treeview_row_styles()

    def clear(self):
        self._hide_pos_tooltip()
        self.tree.delete(*self.tree.get_children())
        self._rows.clear()

    def get_selected_symbol(self):
        sel = self.tree.selection()
        if not sel:
            return None
        vals = self.tree.item(sel[0], "values")
        if "Algo" in (self.columns or []):
            return vals[self.columns.index("Algo")]
        return None

    def apply_style_from_ui(self, ui):
        self.ui = ui
        self.update_treeview_row_styles()

    # ---------------- DARK MODE ----------------
    def _is_dark(self) -> bool:
        try:
            if self.ui and (
                (hasattr(self.ui, "DARK_MODE") and int(self.ui.DARK_MODE.get()) == 1) or
                (hasattr(self.ui, "DISASTER_MODE") and int(self.ui.DISASTER_MODE.get()) == 1)
            ):
                return True
        except Exception:
            pass
        return False

    def update_treeview_row_styles(self, *, dark: bool | None = None, normal_text: str | None = None, row_bg: str | None = None):
        if dark is None:
            dark = self._is_dark()
        if normal_text is None:
            normal_text = "white" if dark else "black"
        if row_bg is None:
            row_bg = "#2b2b2b" if dark else "#f4f4f4"

        self.tree.tag_configure(self._ROW_TAG, foreground=normal_text, background=row_bg)
        for iid in self.tree.get_children(""):
            self.tree.item(iid, tags=(self._ROW_TAG,))

    # ---------------- Sorting ----------------
    def _sort_by(self, col, descending):
        data = [(self.tree.set(k, col), k) for k in self.tree.get_children("")]
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
            self.tree.heading(h, text=h, anchor="center", command=lambda col=h: self._sort_by(col, False))
            width = self._default_width_for(h)
            anchor = self._default_anchor_for(h)
            self.tree.column(h, width=width, minwidth=width, stretch=False, anchor=anchor)

    def _normalize_rows(self, rows):
        if not rows:
            return []
        out = []
        if isinstance(rows, dict):
            for algo, d in rows.items():
                if isinstance(d, dict):
                    if "Algo" not in d:
                        d = {"Algo": algo, **d}
                    out.append(d)
        else:
            for d in rows:
                if isinstance(d, dict):
                    out.append(d)
        return out

    def _infer_headers_from_items(self, items):
        first = items[0]
        keys = list(first.keys())
        if "Algo" in keys:
            keys = ["Algo"] + [k for k in keys if k != "Algo"]
        return keys

    def _insert_or_update(self, row_dict):
        if not self.columns:
            self.columns = self._infer_headers_from_items([row_dict])
            self._setup_columns(self.columns)

        row = {k: row_dict.get(k, "") for k in self.columns}
        if "Flatten" in self.columns and row.get("Flatten", "") == "":
            row["Flatten"] = "FLATTEN"

        algo = row.get("Algo", "")
        values = tuple(self._format_value(k, row[k]) for k in self.columns)

        if algo in self._rows:
            iid = self._rows[algo]
            self.tree.item(iid, values=values, tags=(self._ROW_TAG,))
        else:
            iid = self.tree.insert("", "end", values=values, tags=(self._ROW_TAG,))
            if algo:
                self._rows[algo] = iid

    def _current_row(self, algo):
        if algo not in self._rows:
            return {}
        vals = self.tree.item(self._rows[algo], "values")
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
        numeric_like = {"#Algos", "Unreal", "Real"}
        if col in numeric_like:
            return True
        # Probe existing values
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
        if col == "Algo":
            return "w"
        if col.lower() in ("flatten",):
            return "center"
        return "e" if self._is_numeric_column(col) else "w"

    def _default_width_for(self, col):
        if col == "Algo":
            return 200
        if col == "Pos":
            return 140
        if col in ("Flatten",):
            return 100
        if col in ("#Algos",):
            return 86
        if col in ("Unreal", "Real"):
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

    # ---------------- Hover / Click handlers ----------------
    def _on_motion(self, event):
        """
        Hand cursor on 'Flatten' cells; tooltip on 'Pos' cells.
        Tooltip expects Pos like: 'AAPL:5,EGE:3,GEGE:0,GE:0'.
        """
        # lazy-init tooltip state so this works even if the attrs weren't set in __init__
        if not hasattr(self, "_pos_tooltip"):
            self._pos_tooltip = None
        if not hasattr(self, "_tip_visible_for"):
            self._tip_visible_for = (None, None)  # (row_iid, col_name)

        region = self.tree.identify("region", event.x, event.y)
        if region != "cell":
            # not over a cell → reset cursor + hide tooltip
            if getattr(self, "_hovering_action", False):
                self.tree.configure(cursor="")
                self._hovering_action = False
            if self._pos_tooltip:
                try:
                    self._pos_tooltip.hidetip()
                except Exception:
                    pass
                self._pos_tooltip = None
            self._tip_visible_for = (None, None)
            return

        row_iid = self.tree.identify_row(event.y)
        col_id  = self.tree.identify_column(event.x)  # '#N'
        try:
            col_index = int(col_id.replace("#", "")) - 1
        except Exception:
            # invalid column → cleanup & bail
            if getattr(self, "_hovering_action", False):
                self.tree.configure(cursor="")
                self._hovering_action = False
            if self._pos_tooltip:
                try:
                    self._pos_tooltip.hidetip()
                except Exception:
                    pass
                self._pos_tooltip = None
            self._tip_visible_for = (None, None)
            return

        if not (0 <= col_index < len(self.columns)) or not row_iid:
            # out of bounds → cleanup
            if getattr(self, "_hovering_action", False):
                self.tree.configure(cursor="")
                self._hovering_action = False
            if self._pos_tooltip:
                try:
                    self._pos_tooltip.hidetip()
                except Exception:
                    pass
                self._pos_tooltip = None
            self._tip_visible_for = (None, None)
            return

        col_name = self.columns[col_index]

        # ---- 1) Action column (Flatten) => hand cursor
        if not hasattr(self, "_action_cols"):
            self._action_cols = {"Flatten"}
        if col_name in self._action_cols:
            if not getattr(self, "_hovering_action", False):
                self.tree.configure(cursor="hand2")
                self._hovering_action = True
        else:
            if getattr(self, "_hovering_action", False):
                self.tree.configure(cursor="")
                self._hovering_action = False

        # ---- 2) Tooltip on Pos column
        if col_name == "Pos":
            vals = self.tree.item(row_iid, "values")
            # defensive: guard against missing column
            try:
                raw_pos = vals[col_index]
            except Exception:
                raw_pos = ""

            # format: "AAPL:5,EGE:3,GEGE:0,GE:0" -> lines
            # also trim whitespace, normalize ":" spacing
            parts = []
            for token in str(raw_pos).split(","):
                token = token.strip()
                if not token:
                    continue
                if ":" in token:
                    k, v = token.split(":", 1)
                    parts.append(f"{k.strip()}: {v.strip()}")
                else:
                    parts.append(token)
            tip_text = "\n".join(parts) if parts else str(raw_pos)

            # only recreate tooltip if cell changed
            if self._tip_visible_for != (row_iid, col_name):
                # hide old
                if self._pos_tooltip:
                    try:
                        self._pos_tooltip.hidetip()
                    except Exception:
                        pass
                    self._pos_tooltip = None
                # show new
                try:
                    self._pos_tooltip = Tooltip(self.tree)
                    self._pos_tooltip.showtip(tip_text, row_iid, col_id)
                    self._tip_visible_for = (row_iid, col_name)
                except Exception:
                    # if tooltip fails, don't crash hover
                    self._pos_tooltip = None
                    self._tip_visible_for = (None, None)
        else:
            # left Pos column → hide tooltip if showing
            if self._pos_tooltip:
                try:
                    self._pos_tooltip.hidetip()
                except Exception:
                    pass
                self._pos_tooltip = None
            self._tip_visible_for = (None, None)

    def _on_leave(self, _event):
        self._reset_cursor_and_tooltip()

    def _on_click(self, event):
        """Click on Flatten -> call self.ui.manager.flatten_symbol(algo)."""
        region = self.tree.identify("region", event.x, event.y)
        if region != "cell":
            return

        row_iid = self.tree.identify_row(event.y)
        if not row_iid:
            return
        col_id = self.tree.identify_column(event.x)
        try:
            col_index = int(col_id.replace("#", "")) - 1
        except Exception:
            return
        if not (0 <= col_index < len(self.columns)):
            return

        col_name = self.columns[col_index]
        if col_name not in self._action_cols:
            return

        try:
            vals = self.tree.item(row_iid, "values")
            algo_idx = self._col_index("Algo")
            algo = vals[algo_idx] if algo_idx is not None else None
        except Exception:
            algo = None

        if col_name == "Flatten":
            try:
                # your original handler path
                self.ui.manager.flatten_algo(algo)
            except Exception as e:
                print(f"[Flatten] handler error for {algo}: {e}")

    # ---------------- Tooltip helpers ----------------
    def _hide_pos_tooltip(self):
        if self._pos_tooltip:
            try:
                self._pos_tooltip.hidetip()
            except Exception:
                pass
            self._pos_tooltip = None
        self._tip_visible_for = (None, None)

    def _reset_cursor_and_tooltip(self):
        if self._hovering_action:
            self.tree.configure(cursor="")
            self._hovering_action = False
        self._hide_pos_tooltip()

# ---------------- Demo ----------------
if __name__ == "__main__":
    root = tb.Window(themename="flatly")
    root.title("Algo Dashboard Example")

    class DummyManager:
        def flatten_symbol(self, algo):
            print(f"DummyManager: FLATTEN {algo}")

    class DummyUI:
        def __init__(self):
            self.DARK_MODE = tk.IntVar(value=0)
            self.DISASTER_MODE = tk.IntVar(value=0)
            self.manager = DummyManager()

        def get_pos_tooltip(self, algo, pos_value, row):
            return f"Algo: {algo}\nPos detail: {pos_value}\nUnreal: {row.get('Unreal')}  Real: {row.get('Real')}"

    ui = DummyUI()

    def flip_dark():
        ui.DARK_MODE.set(1 if ui.DARK_MODE.get() == 0 else 0)
        panel.update_treeview_row_styles()

    root.after(2000, flip_dark)

    panel = Algo_Dashboard_Panel(root, headers=HEADERS, ui=ui)
    panel.pack(fill="both", expand=True)

    sample_data = [
        {'Algo': 'BC_RAV_EXTR', '#Algos': 15, 'Pos': "AAPl:5,EGE:3,GEGE:0,GE:0", 'Unreal': -27.39, 'Real': 0.0, 'Flatten': 'Flat!'},
        {'Algo': 'BB_UMOM',     '#Algos':  3, 'Pos': "AAPl:5,EGE:3,GEGE:0,GE:0", 'Unreal': -0.40,  'Real': 0.0, 'Flatten': 'Flat!'},
        {'Algo': 'BB_DIST',     '#Algos':  2, 'Pos': "AAPl:5,EGE:3,GEGE:0,GE:0", 'Unreal': -1.10,  'Real': 0.0, 'Flatten': 'Flat!'},
        {'Algo': 'BB_RAV',      '#Algos':  5, 'Pos': "AAPl:5,EGE:3,GEGE:0,GE:0", 'Unreal':  3.20,  'Real': 0.0, 'Flatten': 'Flat!'},
    ]
    panel.set_data(sample_data)
    root.mainloop()
