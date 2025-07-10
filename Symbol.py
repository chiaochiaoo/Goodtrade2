import tkinter as tk
import requests

class Symbol:
    def __init__(self,manager,symbol):

        self.manager = manager
        self.symbol_name = symbol

        self.tradable = True

        ## INTERNAL DATA ##
        self.ask = 0
        self.bid = 0
        self.bid_change = False
        self.ask_change = False

        ## UI RELATED DATA ##

        self.tkvars = {}
        self.data = {}

        self.u2d_keys = {
            "name": str,
            "age": int,
            "height": float,
            "is_active": bool,
        }

        self.d2u_keys = {
            "status": str,
            "calculated": int,
            "shortable":bool,
            "tradable": bool,
        }

        self.data_init()

    def data_init(self):
        all_keys = {**self.u2d_keys, **self.d2u_keys}

        def create_tk_var(typ, default):
            if typ == str:
                return tk.StringVar(value=default)
            elif typ == int:
                return tk.IntVar(value=default)
            elif typ == float:
                return tk.DoubleVar(value=default)
            elif typ == bool:
                return tk.BooleanVar(value=default)
            else:
                raise ValueError(f"Unsupported type: {typ}")

        for key, typ in all_keys.items():
            if typ == str:
                default = ""
            elif typ == int:
                default = 0
            elif typ == float:
                default = 0.0
            elif typ == bool:
                default = False
            else:
                raise ValueError(f"Unsupported type: {typ}")

            self.data[key] = default
            self.tkvars[key] = create_tk_var(typ, default)

    def print_all_data(self):
        print("=== Data & Tk Variables ===")
        for key in self.data:
            primitive = self.data[key]
            tkvar = self.tkvars.get(key)
            tk_type = type(tkvar).__name__ if tkvar else "None"
            tk_value = tkvar.get() if tkvar else "N/A"
            print(f"{key:<12} | data: {primitive!r:<10} | tkvar: {tk_type:<12} = {tk_value!r}")
        print("===========================")

    def var_sync(self):
        # UI → Data
        for key in self.u2d_keys:
            ui_val = self.tkvars[key].get()
            if self.data.get(key) != ui_val:
                #print(f"[UI→Data] {key}: {self.data[key]} → {ui_val}")
                self.data[key] = ui_val

        # Data → UI
        for key in self.d2u_keys:
            data_val = self.data.get(key)
            if self.tkvars[key].get() != data_val:
                #print(f"[Data→UI] {key}: {self.vars[key].get()} → {data_val}")
                self.tkvars[key].set(data_val)

if __name__ == "__main__":
    root = tk.Tk()


    s = Symbol(None,"test")
    s.print_all_data()
