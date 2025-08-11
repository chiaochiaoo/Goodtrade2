import tkinter as tk
from datetime import datetime, timedelta


REALIZED = 'realized'
UNREAL = 'unreal'

DEBUGGING = True 

class TradingPlan:
    def __init__(self,manager,algo_name,info={}):

        self.manager = manager
        self.source = "Symbol"
        self.source2 = 'Algo'
        self.algo_name = algo_name
        self.tradable = True

        self.shutdown = False 
        ## INTERNAL DATA ##


        ## UI RELATED DATA ##

        self.symbols ={}

        self.tkvars = {}
        self.data = {}



        self.datakey = {}


        ### PART FOR CENTRAL DISPACH ###
        # self.expected_shares = {}
        # self.current_shares = {}
        # self.current_request = {}

        self.current_request_timer = {}
        self.original_positions = {}

        self.current_exposure = {}
        self.average_price = {}
        #################################

        self.banned = []


        self.datakey['name'] = str 

        self.datakey[REALIZED] = float
        self.datakey[UNREAL] = float 

        self.datakey['expected_shares'] = dict  
        self.datakey['current_shares'] = dict 
        self.datakey['current_request'] = dict  




        self.datakey['flatten_order'] = bool

        self.data_init()

    def get_algo_status(self):
        return self.shutdown

    def flatten_cmd(self):

        for symbol,item in self.symbols.items():
            self.submit_expected_shares(symbol,0,0)
            #self.expected_shares[symbol] = 0
            self.recalculate_current_request(symbol)
        #self.tkvars[ALGO_MULTIPLIER].set(0)
        self.data['flatten_order']=True


    def get_current_expected(self,symbol):

        return self.data['expected_shares'][symbol]

    def get_current_share(self,symbol):

        return self.data['current_shares'][symbol]

    def get_current_request(self,symbol):

        return self.data['current_request'][symbol]

    def having_request(self,symbol):

        return self.data['current_request'][symbol]!=0

    def rejection_handling(self,symbol):


        self.data['expected_shares'][symbol] = 0
        #self.banned.append(symbol)

        #log_print(self.source," BANNED:",symbol)

        ## set the rest to 0 also.

        self.flatten_cmd()

    def calculate_avg_price(self,symbol):

        if self.data['current_shares'][symbol]!=0:
            self.average_price[symbol] = sum(self.current_exposure[symbol])/self.data['current_shares'][symbol]

    def holding_update(self,symbol,share_added,price):

        """
        update PNL structures.
        """

        if share_added<0:
            price=price*-1

        for i in range(abs(share_added)):

            if len(self.current_exposure[symbol])==0:
                self.current_exposure[symbol].append(price)

            elif self.current_exposure[symbol][-1]*price >0: #same side.
                self.current_exposure[symbol].append(price)

            elif self.current_exposure[symbol][-1]*price <0:

                self.data[REALIZED]+= -1*price - self.current_exposure[symbol].pop()
                
                #self.manager.new_record(self)
            else:
                #this is the senario where price is 0.
                print("HOLDING UPDATE ERROR",symbol,share_added,price)

        #self.sync_all()


    def request_fufill(self,symbol,share,price):

        preq = self.data['current_request'][symbol]
        debugging_line = f'{self.source},{symbol} :{self.source2} :{self.algo_name}, request_fulfill()'
        self.data['current_shares'][symbol] = self.data['current_shares'].get(symbol, 0) + share
    
        self.holding_update(symbol,share,price)
        self.calculate_avg_price(symbol)
        self.recalculate_current_request(symbol)

        req = self.data['current_request'][symbol]
        if DEBUGGING:
            print(debugging_line,f'incoming shares {share} @ {price}. now request {req} prev {preq}')



    def check_pnl(self):


        """
        Put this under inspection? 

        PNL, STOP TRIGGER.  ONLY CHECK EVERY 3 SECONDS 
        """

        now = datetime.now()
        ts = now.hour*60 + now.minute

        total_unreal = 0

        check = {}
        for symbol,share in self.data['current_shares'].items():

            bid,ask = self.symbols[symbol].get_price()
            
            if self.data['current_shares'][symbol]!=0 and bid!=0 and ask!=0 and self.average_price[symbol]!=0:

                if share>0:
                    total_unreal +=  ((bid - self.average_price[symbol])) * abs(self.data['current_shares'][symbol])  
                    check[symbol] = [bid,self.average_price[symbol],self.data['current_shares'][symbol],((bid - self.average_price[symbol])) * abs(self.data['current_shares'][symbol])]

                    # if ".TO" in symbol:
                    #   log_print(self.algo_name,symbol,"avg price",self.average_price[symbol],"cur price",cur_stock_price,"share",val,"result", (cur_stock_price - self.average_price[symbol]) * abs(self.current_shares[symbol]))
                else:
                    cur_stock_price = self.symbols[symbol].get_price()
                    total_unreal +=  ((self.average_price[symbol] - ask)) * abs(self.data['current_shares'][symbol])
                    check[symbol] = [ask,self.average_price[symbol],self.data['current_shares'][symbol],((self.average_price[symbol] - ask)) * abs(self.data['current_shares'][symbol])]
                    
                    # if ".TO" in symbol


        #self.sync_all()
######################################################################################################

    def data_init(self):

        def create_tk_var(typ, default):
            if typ == str or typ ==dict:
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
            elif typ == dict:
                default = {}
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

    def recalculate_current_request(self,symbol):
        diff = self.data['expected_shares'][symbol] - self.data['current_shares'][symbol]

        if self.data['current_request'][symbol]!=diff:
            now = datetime.now()
            ts = now.hour*3600 + now.minute*60+ now.second
            self.data['current_request'][symbol] = diff
            self.current_request_timer[symbol] = ts

    def get_request_time(self,symbol):

        return self.current_request_timer[symbol] 
    def add_to_original_position(self,symbol_name,share):

        if symbol_name not in self.original_positions:
            self.original_positions[symbol_name] = share 


    def register_symbol(self,symbol_name,symbol):

        if symbol_name not in self.symbols:

            self.symbols[symbol_name] = symbol
            self.symbols[symbol_name].register_tradingplan(self.algo_name,self)

            self.data['expected_shares'][symbol_name] = 0
            self.data['current_shares'][symbol_name] = 0
            self.data['current_request'][symbol_name] = 0
            self.current_request_timer[symbol_name] = 0

            self.current_exposure[symbol_name] = []
            self.average_price[symbol_name] = 0



    def submit_expected_shares(self,symbol,shares,aggresive=0):

        ### SLIPPAGE CONTROL ###
        # spread = round(self.manager.get_spread(symbol[:-3]),2)
        # sliperage = abs(round(shares*spread,2))

        # log_print(self.source,self.algo_name,"expect",symbol,shares," aggressive ", aggresive,"spread",spread,'slippage',sliperage,"current have",self.current_shares[symbol])

        # ##################################################################################################
        # ##############     I THINK THIS IS WHY. ORDER STILL PROCESS UNTIL 1600   #########################
        # ##################################################################################################

        # ## check slipperage . self.sliperage_controlsp

        # #if self.tkvars[STATUS]

        # check = True 
        # if self.sliperage_control:

        #     if sliperage>self.spread_limit:
        #         self.tkvars[STATUS].set("STH:"+str(round((sliperage/self.spread_limit),1)))

        #         #check = False 
        #         shares = int(shares) // (sliperage/self.spread_limit)

        # if spread >0.5 and aggresive:
        #     aggresive = 0 
        #     log_print(self.source,self.algo_name,symbol," spread too high. aggresive off")

        print(self.source,self.algo_name,symbol,shares,aggresive)


        if shares==0:
            self.data['expected_shares'][symbol] = shares
            self.add_to_original_position(symbol,shares)
            self.recalculate_current_request(symbol)

        if symbol not in self.banned and self.data['flatten_order']!=True:

            now = datetime.now()
            ts = now.hour*3600 + now.minute*60 + now.second


            self.data['expected_shares'][symbol] = shares

            self.add_to_original_position(symbol,shares)
            self.recalculate_current_request(symbol)
            
            
            if aggresive:
                pass
            #     if ts - self.recent_action_ts[symbol] >= 1 and ts<57600-30:
            #         self.recent_action_ts[symbol] = ts
            #         self.symbols[symbol].immediate_request(self.current_request[symbol])
            #     else:
            #         log_print(self.source,self.algo_name,symbol," AGGRESIVE TOO FREQUENT : ",ts - self.recent_action_ts[symbol])
            # # self.notify_request(symbol)
if __name__ == "__main__":
    root = tk.Tk()

    #parakeys = {'1':'a','b':1,}

    #print({*parakeys})
    s = TradingPlan(None,"test")
    s.print_all_data()


    s.submit_expected_shares("AMD.NQ",5)
