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

        self.datakey = {}


        self.datakey['name'] = str 
        self.datakey['shortable'] = bool 
        self.datakey['tradable'] = bool
        self.datakey['current_holding'] = int 


        self.data_init()

    def data_init(self):


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

        for key, typ in self.datakey.items():
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

    def sync_all(self):
        for key, var in self.tkvars.items():
            var.set(self.data.get(key, var.get()))

    def print_all_data(self):
        print("=== Data & Tk Variables ===")
        for key in self.data:
            primitive = self.data[key]
            tkvar = self.tkvars.get(key)
            tk_type = type(tkvar).__name__ if tkvar else "None"
            tk_value = tkvar.get() if tkvar else "N/A"
            print(f"{key:<12} | data: {primitive!r:<10} | tkvar: {tk_type:<12} = {tk_value!r}")
        print("===========================")

if __name__ == "__main__":
    root = tk.Tk()

    #parakeys = {'1':'a','b':1,}

    #print({*parakeys})
    s = Symbol(None,"test")
    s.print_all_data()
