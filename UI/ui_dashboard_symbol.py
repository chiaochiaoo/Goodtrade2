import tkinter as tk
import ttkbootstrap as tb
from ttkbootstrap.constants import *

class Symbol_Dashboard_Panel:
    HEADERS = ["Symbol", "Net Pos", "#Algos", "Long", "Short", "Unreal", "Real", "Risk"]

    def __init__(self, parent, ui=None, on_symbol_open=None, on_symbol_double_click=None):
        """
        parent: container to mount into (e.g., a Notebook tab)
        ui: optional object with DARK_MODE/DISASTER_MODE IntVars for style linking
        on_symbol_open/on_symbol_double_click: callback(symbol:str) on double-click
        """
        self.ui = ui
        self.frame = tb.Frame(parent)              # << expose a frame for external .add(...)
        self.on_symbol_open = on_symbol_double_click or on_symbol_open

        self._data_source = lambda: {}
        self._row_ids = {}
        self.last_sort_column = None
        self.last_sort_reverse = False

        self._build_tree(self.frame)               # build inside self.frame
        self._link_style_changes()
        self.update_treeview_row_styles()
    def set_data_source(self, getter_callable):
        self._data_source = getter_callable or (lambda: {})

    def set_data(self, data_or_getter):
        """
        Accepts:
          - dict: snapshot of your algo data
          - callable: returns the dict when called
        """
        if callable(data_or_getter):
            self._data_source = data_or_getter
        else:
            # wrap dict in a lambda so refresh() can still call it
            self._data_source = lambda: data_or_getter
    # ---------- UI build ----------
    def _build_tree(self, parent_frame):
        container = tb.Frame(parent_frame)
        container.pack(fill="both", expand=True, padx=5, pady=5)

        sy_scroll_y = tb.Scrollbar(container)
        sy_scroll_y.pack(side="right", fill="y")
        sy_scroll_x = tb.Scrollbar(container, orient="horizontal")
        sy_scroll_x.pack(side="bottom", fill="x")

        self.tree = tb.Treeview(
            container,
            columns=self.HEADERS,
            show="headings",
            yscrollcommand=sy_scroll_y.set,
            xscrollcommand=sy_scroll_x.set,
            bootstyle="Treeview",
            selectmode="browse",
        )
        self.tree.pack(fill="both", expand=True)
        sy_scroll_y.config(command=self.tree.yview)
        sy_scroll_x.config(command=self.tree.xview)

        for col in self.HEADERS:
            self.tree.heading(col, text=col, anchor="center",
                              command=lambda c=col: self.sort_column(c, False, self.tree))
            self.tree.column(col, anchor=("w" if col == "Symbol" else "e"),
                             width=100, stretch=False, minwidth=70)

        # same tags as deployment tree
        self.tree.tag_configure("row_green", background="#e6ffe6")
        self.tree.tag_configure("row_red", background="#ffe6e6")
        self.tree.tag_configure("default_text")

        if self.on_symbol_open:
            self.tree.bind("<Double-Button-1>", self._handle_open)

    # ---------- public hooks ----------
    def set_data_source(self, getter_callable):
        self._data_source = getter_callable or (lambda: {})

    def start_auto_refresh(self, interval_ms=1000):
        def tick():
            self.refresh()
            self.frame.after(interval_ms, tick)    # use our own frame for .after
        self.frame.after(interval_ms, tick)

    # ---------- events ----------
    def _handle_open(self, _evt):
        iid = self.tree.focus()
        if not iid or not self.on_symbol_open:
            return
        sym = self.tree.set(iid, "Symbol")
        if sym:
            self.on_symbol_open(sym)

    # ---------- data aggregation + paint ----------
    def refresh(self):
        data = self._data_source() or {}
        try:
            ACTIVE_STATES = {RUNNING, ORDERING, FLATTENING}
        except NameError:
            ACTIVE_STATES = {'RUNNING', 'ORDERING', ' FLATTENING'}

        agg = {}
        for d in data.values():
            if d.get("Status") not in ACTIVE_STATES:
                continue

            positions = d.get("Positions", {})
            unreal = float(d.get("Unrealized", 0) or 0)
            real   = float(d.get("Realized", 0) or 0)

            # normalize positions into {sym: qty}
            if isinstance(positions, dict):
                pos_map = positions
            else:
                pos_map = {}
                for chunk in str(positions).replace(",", ";").split(";"):
                    if ":" in chunk:
                        k, v = chunk.split(":", 1)
                        try:
                            pos_map[k.strip()] = int(float(v))
                        except:
                            pass

            for sym, qty in pos_map.items():
                a = agg.setdefault(sym, {"Symbol": sym, "Net Pos": 0, "#Algos": 0,
                                         "Long": 0, "Short": 0, "Unreal": 0.0, "Real": 0.0})
                a["Net Pos"] += qty
                if qty > 0:  a["Long"]  += qty
                if qty < 0:  a["Short"] += abs(qty)
                a["Unreal"] += unreal
                a["Real"]   += real
                a["#Algos"] += 1

        for a in agg.values():
            base = abs(a["Unreal"] / max(a["#Algos"], 1))
            a["Risk"] = round(abs(a["Net Pos"]) * (abs(base) + 1), 2)

        seen = set()
        for sym, a in sorted(agg.items()):
            values = [
                a["Symbol"], str(a["Net Pos"]), str(a["#Algos"]),
                str(a["Long"]), str(a["Short"]),
                f"{a['Unreal']:.2f}", f"{a['Real']:.2f}", f"{a['Risk']:.2f}"
            ]
            tag = "row_green" if a["Unreal"] >= 0 else "row_red"
            tags = (tag, "default_text")

            if sym in self._row_ids:
                iid = self._row_ids[sym]
                self.tree.item(iid, values=values, tags=tags)
            else:
                iid = self.tree.insert("", "end", values=values, tags=tags)
                self._row_ids[sym] = iid
            seen.add(sym)

        for sym, iid in list(self._row_ids.items()):
            if sym not in seen:
                self.tree.delete(iid)
                del self._row_ids[sym]

        if self.last_sort_column:
            self.sort_column(self.last_sort_column, self.last_sort_reverse, self.tree)

    # ---------- styling ----------
    def _link_style_changes(self):
        if self.ui and hasattr(self.ui, "DARK_MODE") and hasattr(self.ui, "DISASTER_MODE"):
            self.ui.DARK_MODE.trace_add('write', lambda *_: self.update_treeview_row_styles())
            self.ui.DISASTER_MODE.trace_add('write', lambda *_: self.update_treeview_row_styles())

    def update_treeview_row_styles(self):
        dark = False
        if self.ui and hasattr(self.ui, "DARK_MODE") and hasattr(self.ui, "DISASTER_MODE"):
            try:
                dark = (self.ui.DARK_MODE.get() == 1 or self.ui.DISASTER_MODE.get() == 1)
            except Exception:
                dark = False

        if dark:
            normal_text_color = "white"
            green_bg = "#2a662a"
            red_bg = "#802b2b"
        else:
            normal_text_color = "black"
            green_bg = "#e6ffe6"
            red_bg = "#ffe6e6"

        self.tree.tag_configure("default_text", foreground=normal_text_color)
        self.tree.tag_configure("row_green", background=green_bg)
        self.tree.tag_configure("row_red", background=red_bg)

        for iid in self.tree.get_children():
            vals = self.tree.item(iid, "values")
            try:
                unreal = float(vals[5])
            except Exception:
                unreal = 0.0
            tag = "row_green" if unreal >= 0 else "row_red"
            self.tree.item(iid, tags=(tag, "default_text"))

    # ---------- sorting ----------
    def sort_column(self, col, reverse, tree_widget):
        try:
            items = []
            for k in tree_widget.get_children():
                v = tree_widget.set(k, col)
                try:
                    v = float(v)
                except ValueError:
                    pass
                items.append((v, k))

            items.sort(key=lambda x: x[0], reverse=reverse)
            for idx, (_, k) in enumerate(items):
                tree_widget.move(k, '', idx)

            self.last_sort_column = col
            self.last_sort_reverse = reverse
            tree_widget.heading(col, command=lambda: self.sort_column(col, not reverse, tree_widget))
        except Exception as e:
            print(f"[Symbol Sort Error] {e}")

    # convenience
    def get_selected_symbol(self):
        iid = self.tree.focus()
        return self.tree.set(iid, "Symbol") if iid else None
