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

        self.datakey['active_algo_count'] = int
        self.datakey['total_algo_count'] = int

        self.datakey['bid'] = float 
        self.datakey['ask'] = float  
        self.datakey['spread'] = float 

        self.datakey['timestamp'] = int 
        self.data_init()

    def data_init(self):

        def create_tk_var(typ, default):
            if typ == str:
                return tk.StringVar(value=default)
            elif typ == int:0
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


    # one and only one being processed.
    #{"average_price":292.408,"fees":-0.08975,"fill":{"292.4":10,"292.41":40},"shares":50,"status":"Partially Filled","target_price":292.42,"target_share":100}
    #{"average_price":292.407,"fees":-0.1795,"fill":{"292.4":30,"292.41":70},"shares":100,"status":"Filled","target_price":292.42,"target_share":100}

    def sysmbol_inspection(self):


        # step 0 update l1 infos.

        ## if have more than 0. 

        if self.datakey['tradable'] == False:
            self.l1_update_module()
        if self.datakey['tradable'] == True:
            if self.datakey['active_algo_count']>0:
                self.l1_update_module()
            else:
                # nothing to inspect really. 
                return 1

            # step 1 check the status of each order of tp..

            # step 2 update the FSM of each TP. 


    ### IDEALLY, move this to the ems. any symbol have a position on it should have update anyway. 

    def l1_update_module(self):

        ### tell the system if there is any bid ask changes since last time.

        try:
            postbody = "http://127.0.0.1:8080/GetLv1?symbol=" + self.symbol_name 

            r= requests.get(postbody)

            stream_data = r.text

            bid = float(find_between(stream_data, "BidPrice=\"", "\""))
            ask = float(find_between(stream_data, "AskPrice=\"", "\""))
            ts = find_between(stream_data, "MarketTime=\"", "\"")
            state = find_between(stream_data,"InstrumentState=\"", "\"") 

            if state =="Open":
                self.datakey['tradable']=True
            else:
                self.datakey['tradable']=False 
                print(self.symbol_name,"State:",state,self.datakey['tradable'])

            if self.datakey['bid']!=bid:
                self.bid_change = True 
            else:
                self.bid_change = False 


            if self.datakey['ask']!=ask:
                self.ask_change = True 
            else:
                self.ask_change = False 

            self.datakey['ask'] = ask
            self.datakey['bid'] = bid

            self.datakey['spread'] = round(ask-bid,2)
            self.datakey['timestamp'] = ts

            log_print(self.symbol_name,"SPREAD:",self.datakey['spread'],self.data[BID],self.bid_change,self.data[ASK],self.ask_change)

            return 
        except Exception as e:

            PrintException(self.symbol_name,"Init L1 Update")

            self.ask_change = True 
            self.bid_change = True 

if __name__ == "__main__":
    root = tk.Tk()

    #parakeys = {'1':'a','b':1,}

    #print({*parakeys})
    s = Symbol(None,"test")
    s.print_all_data()
