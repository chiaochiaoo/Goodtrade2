import tkinter as tk
import requests
import threading
# from datetime import datetime
from constants import *
import time
import traceback
from TradingPlan import *
from logging_module import *
from datetime import datetime, timedelta
from collections import deque
from statistics import mean
DEBUGGING = True 


TRANSITION_STATES = {'Accepted','Accepted by GW','Partially Filled'}
TERMINAL_STATES = {"Filled", "Multi Filled", "Cancelled","Rejected"}
FILL_STATES = {"Filled", "Multi Filled","Partially Filled"}


SYMBOL_STATES = {'Open','Close','MOO','MOC'}

OPEN = 'Open'
CLOSE = 'Close'
MOO = 'MOO'
MOC = 'MOC'

def get_all_states_with_update():
    """
    Initializes an empty set and updates it with all states.
    """
    all_states = set()  # Initializes an empty set
    all_states.update(TRANSITION_STATES)
    all_states.update(TERMINAL_STATES)
    all_states.update(FILL_STATES)
    return all_states

ALL_STATES = get_all_states_with_update()



class Symbol:
    def __init__(self,manager,symbol):
        self.source = 'Symbol'
        self.manager = manager
        self.symbol_name = symbol

        self.tradable = True

        ## INTERNAL DATA ##
        self.ask = 0
        self.bid = 0
        self.bid_change = False
        self.ask_change = False

        self.inspection_lock = threading.Lock()


        self.inspection_timestamp =0


        self.tradingplans = {}

        self.expected_tp = {}
        self.current_tp = {}


        self.order_out = False
        self.order_pid = ""
        self.order_id = ""
        self.order_timing = 0

        self.order_details = {}
        self.fill_details = {}

        self.central_dispatching_order_request = {}
        self.cumulative_fills_by_price = {}
        self.current_new_fills = {}


        self.adjustment_holding = 0 

        self.spread_offset = 0
        self.prev_spread_offset = 0

        self.order_price =0

        self.fill_timer = 30
        ##################
        self.rejections = []

        self.cancel_sent = False


        self.aggresive_ordering = False

        self.request =0

        self.prev_request =0
        self.expected=0
        self.tp_current_shares=0

        self.moo_request = 0
        self.moc_request = 0

        self.moo_out = False
        self.moc_out = False

        self.moo_order_out = False 
        self.moc_order_out = False 

        self.moo_order_venue = ""
        self.moc_order_venue = ""
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

        self.spread_list = []

        self.datakey['timestamp'] = int 


        self.dashboard = {}
        self.price_check = deque(maxlen=5)

        self.price_check_successful = True
        self.data_init()

    def symbol_inspection(self):


        # step 0 update l1 infos.

        ## if have more than 0. 


        ### How many things i need to check here?
        ### 1. if there is any central dispatch order.
        ### ?

        debug_line = f'{self.source} {self.symbol_name} :symbol_inspection()'

        if DEBUGGING:
            print('\n')
        if not self.inspection_lock.locked():

            now = datetime.now()

            ts = now.hour*3600 + now.minute*60 + now.second

            inspection_time_d = ts-self.inspection_timestamp

            #print(debug_line,' inspection duration:',inspection_time_d)
            # if inspection_time_d==0:
            #   return 
            
            self.inspection_timestamp = ts 

            self.cancel_sent = False

            ### Check if there exist a moudule              
            # if self.data['active_algo_count']>0:
            #   self.l1_update_module()
            # else:
            #   # nothing to inspect really. 
            #   return 1


            if DEBUGGING:
                message(f"""{debug_line}, inspection begins!,{ts} tradable:,{self.data['tradable']}""",LOG)
                self.status_message()

            if self.moo_out:

                if DEBUGGING:
                    message(f"""{debug_line}, 'inspection moo:',{self.data['tradable']}""",LOG)
                # 1) if we haven’t sent the OPG yet and no live order, send it
                if (not self.moo_order_out) and (not self.order_out):
                    # stop any last-minute expectations for this symbol
                    self.algo_as_is()       # push expected=0 for THIS symbol only
                    self.aggragate_phase()   # recompute tp_current_shares
                    self.send_moo_order()
            elif self.moc_out:
                ### Two condition needed before MOC goes out.
                ### 1. no remaining order.
                ### 2. request = 0. as is states.
                if DEBUGGING:
                    message(f"""{debug_line}, 'inspection moc:',{self.data['tradable']}""",LOG)
                self.fill_check_phase()

                if self.order_out and self.moc_order_out==False:
                    self.cancel_previous_order()

                if self.moc_order_out==False and self.order_out==False:
                    if self.tp_current_shares != 0:
                        self.flatten_all()
                        self.aggragate_phase()
                    self.send_moc_order()

            else:

                if DEBUGGING:
                    message(f"""{debug_line}, inspection regular routine:,{self.data['tradable']}""",LOG)
                if self.data['tradable'] == False:
                    self.l1_update_module()
                if self.data['tradable'] == True:

                    self.fill_check_phase()

                    self.aggragate_phase()

                    self.order_update_phase()

                    #print(self.cancel_sent)
                    self.limit_inspection_block()

                    #print(self.order_out==False , self.request!=0 , self.manager.open_order_check==True , ts<=57540 ,ts, self.data['tradable'])
                    if self.order_out==False and self.request!=0 and self.manager.open_order_check==True and ts<=57540 and self.data['tradable']:
                        return self.ordering_phase()

                    if DEBUGGING:
                        self.status_message()

                        if self.cancel_sent:
                            message(f'{debug_line}, inspection complete. Cancel previous order.',LOG)
                        else:
                            message(f'{debug_line}, inspection complete. No action.',LOG)
                else:
                    if DEBUGGING:
                        message(f'{debug_line}, untradable at the moment.',LOG)
                
            return 0
                #####   ORDERING PHASE   #####
        else:
            message(f"""{self.source},{self.symbol_name},Inspection LOCKED""",LOG)
            return 0 

            ### IDEALLY, move this to the ems. any symbol have a position on it should have update anyway. 

    def limit_inspection_block(self):
        """
        Implements the flowchart for per-TP explicit LIMIT orders:

        Decision tree:
          - If there is an active limit request for this symbol (from any TP), process one at a time.
          - If no live order exists -> send order.
          - If live order exists:
               * if TERMINAL -> if filled: allocate and finish; else: finish
               * else if timer expired -> cancel
               * else if price changed -> cancel
               * else do nothing this tick
        """

            # 0) gather pending limit requests for this symbol
            #    We process one TP per symbol at a time, FIFO by TP name for determinism.
        def _now_s(): 
            n = datetime.now(); return n.hour*60 + n.minute

        def _lookup_oid_by_pid(pid: str) -> str:
            if not pid: return ''
            try:
                r = requests.get(f'http://127.0.0.1:5000/papi/{pid}', timeout=0.25)
                d = r.json()
                return d.get('order', '') if d.get('ret') else ''
            except Exception as e:
                message(f"[{self.symbol_name}] pid→oid error:", e, traceback.print_exc(),LOG)
                return ''

        def _lookup_order(oid: str) -> dict:
            if not oid: return {}
            try:
                r = requests.get(f'http://127.0.0.1:5000/order/{oid}', timeout=0.25)

                #{"average_price":292.407,"fees":-0.1795,"fill":{"292.4":30,"292.41":70},"shares":100,"status":"Filled","target_price":292.42,"target_share":100}
                return r.json()
            except Exception as e:
                message(f'[{self.symbol_name}] lookup order error:", {e}, {traceback.print_exc()}',LOG)
                return {}

        def _cancel(oid: str):
            if not oid: return
            try:
                message(f'Cancel Limit order ,{oid}',LOG)
                url = f'http://127.0.0.1:8080/CancelOrder?type=ordernumber&ordernumber={oid}'
                requests.post(url, timeout=0.25)
                requests.get(url, timeout=0.25)
            except Exception as e:
                message(f'[{self.symbol_name}] cancel error:", {e}, {traceback.print_exc()}',LOG)

        def _send_limit(shares: int, limit_price: float) -> tuple[str, float]:
            side = BUY if shares > 0 else SELL
            venue = f"ARCA {side} ARCX Limit DAY"   # match your venue pattern
            try:
                req = (
                    f"http://127.0.0.1:8080/ExecuteOrder"
                    f"?symbol={self.symbol_name}"
                    f"&ordername={venue}"
                    f"&shares={abs(shares)}"
                    f"&limitprice={limit_price}"
                    f"&priceadjust=0"
                )
                r = requests.get(req, timeout=0.25)
                d = r.json().get("Responce", {})
                if str(d.get("Success", "")).lower() == "true":
                    return d.get("Content", ""), limit_price  # pid, order_price
            except Exception as e:
                message(f'{self.symbol_name} send limit error:, {e}, {traceback.print_exc()}',LOG)
            return "", 0.0

        def _newly_filled_since(last: dict, nowfills: dict) -> tuple[int, float]:
            """
            Compute delta shares and avg price vs the TP's stored cumulative 'fills' map.
            """
            newly = {}
            for px, sh in (nowfills or {}).items():
                prev = last.get(px, 0)
                delta = sh - prev
                if delta:
                    newly[px] = delta

            if not newly:
                return 0, 0.0
            total = sum(newly.values())
            # weighted average from deltas
            wsum = sum(float(px) * sh for px, sh in newly.items())
            avg = (wsum / total) if total != 0 else 0.0
            return total, avg


        # --- iterate all TPs bound to this symbol ---
        for tp_name, tp in list(self.tradingplans.items()):
            limit_request = tp.data['limit_request'].get(self.symbol_name)


            if not limit_request:
                continue

            # normalize fields (support older 'tgt_price' key)
            tgt_price = limit_request.get('target_price', limit_request.get('tgt_price', ''))
            shares    = int(limit_request.get('shares', 0) or 0)
            pid       = limit_request.get('pid', '')
            oid       = limit_request.get('oid', '')
            status = limit_request.get('status', '')
            order_px  = float(limit_request.get('order_price', 0) or 0.0)
            cumfills  = dict(limit_request.get('fills', {}))


            total_filled = sum(int(q) for q in cumfills.values())  # API signs qty already (±)
            outstanding  = shares - total_filled                   # what we still need
            # skip empty requests. But when a request is redrawn.?


            no_target   = (shares == 0) or (tgt_price in ("", None))
            has_handles = bool(pid or oid)

            # If target is cleared (flatten/retarget) but a broker order still exists -> CANCEL IT
            if no_target and has_handles:
                # try to resolve OID if we only have PID
                if not oid and pid:
                    new_oid = _lookup_oid_by_pid(pid)
                    if new_oid:
                        oid = new_oid
                        limit_request['oid'] = new_oid
                        tp.data['limit_request'][self.symbol_name] = limit_request

                if oid:
                    _cancel(oid)
                    # don't wipe pid/oid yet; wait for terminal status
                    limit_request['cancel_requested'] = True
                    tp.data['limit_request'][self.symbol_name] = limit_request
                # nothing else to do on this tick
                continue

            # If there is truly no target and no live order, skip
            if no_target and not has_handles:
                continue

            # 1) If no live order yet -> SEND ORDER (only when we have a valid target)
            if (pid == '' and oid == '' and shares != 0 and tgt_price not in ("", None)
                    and outstanding != 0 and _now_s() <= tp.info['timer']):
                new_pid, order_price = _send_limit(shares, float(tgt_price))
                if new_pid:
                    limit_request.update({
                        'pid': new_pid,
                        'oid': '',
                        'order_price': order_price,
                        'ts': _now_s(),
                        'fills': {} if not cumfills else cumfills
                    })
                    tp.data['limit_request'][self.symbol_name] = limit_request


            # 2) If we have PID but no OID -> look it up
            if pid and not oid:
                new_oid = _lookup_oid_by_pid(pid)
                if new_oid:
                    limit_request['oid'] = new_oid
                    oid = new_oid
                    tp.data['limit_request'][self.symbol_name] = limit_request
                    #continue               # ← re-enable this to wait one tick

            if not oid:
                continue

            # 3) With OID: fetch order state & fills
            data = _lookup_order(oid)
            #{"average_price":292.407,"fees":-0.1795,"fill":{"292.4":30,"292.41":70},"shares":100,"status":"Filled","target_price":292.42,"target_share":100}
            if not data:
                if DEBUGGING:
                    print('no data, cont')
                continue

            # Allocate any newly arrived fills directly to this TP
            newly_shares, newly_avg = _newly_filled_since(cumfills, data.get('fill', {}))
            if newly_shares:
                # positive shares = net long; negative = net short (API already signs)
                tp.submit_expected_shares(self.symbol_name,tp.get_current_share(self.symbol_name)+newly_shares)
                tp.request_fufill(self.symbol_name, newly_shares, newly_avg)  # your existing TP allocator
                limit_request['fills'] = data.get('fill', {})   # update cumulative
                tp.data['limit_request'][self.symbol_name] = limit_request

            # TERMINAL?

            status = data.get('status', '')
            limit_request['status'] = status
            tp.data['limit_request'][self.symbol_name] = limit_request


            # print('UPDATE MY STATUS',data)
            # recompute outstanding after any new fills
            total_filled = sum(int(q) for q in limit_request['fills'].values())
            outstanding  = shares - total_filled

            
            if status in TERMINAL_STATES:

                # finish regardless of final flavor (Filled/Partial/Cancelled/Rejected)
                limit_request['pid'] = ''
                limit_request['oid'] = ''
                tp.data['limit_request'][self.symbol_name] = limit_request
                        
                if status in ('Rejected'):#
                    tp.clear_limit_request(self.symbol_name)
                continue

            # 4) Still LIVE: timer expiry?
            if outstanding != 0 and _now_s() >= tp.info['timer']:
                _cancel(oid)

                limit_request['cancel_requested'] = True
                tp.data['limit_request'][self.symbol_name] = limit_request
                
                continue

            # 5) Still LIVE: has the price changed?
            #    - TP retargeted vs the original order px
            #    - or relevant side of the book moved (you already track bid_change/ask_change)
            tp_retargeted = (abs(float(tgt_price) - order_px) >= 0.01)

            if tp_retargeted or shares==0:
                _cancel(oid)
                continue

        if DEBUGGING:
            for tp_name, tp in list(self.tradingplans.items()):
                debug_line =  f'{self.source} {self.symbol_name} :{tp_name} limit_inspection():'
                limit_request = tp.data['limit_request'].get(self.symbol_name)

                #if limit_request['shares']!=0:
                message(f'{debug_line},{limit_request}',LOG)

    def time_to_moo(self,venue):
        
        message(f'{self.symbol_name} MOO in progress.',NOTIFICATION)
        self.moo_out = True 
        self.moo_order_venue = venue

    def time_to_moc(self,venue):


        message(f'{self.symbol_name} MOC in progress.',NOTIFICATION)
        self.moc_out = True 
        self.moc_order_venue = venue

    def register_tradingplan(self,algoname,tradingplan):

        self.tradingplans[algoname] = tradingplan

    def get_price(self):

        return self.data['bid'],self.data['ask']
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


    # one and only one being processed.
    #{"average_price":292.408,"fees":-0.08975,"fill":{"292.4":10,"292.41":40},"shares":50,"status":"Partially Filled","target_price":292.42,"target_share":100}
    #{"average_price":292.407,"fees":-0.1795,"fill":{"292.4":30,"292.41":70},"shares":100,"status":"Filled","target_price":292.42,"target_share":100}

    def status_message(self):


        debug_line =  f'{self.source} {self.symbol_name} :status message'

        req = self.data['current_holding']
        message(f'{debug_line} current {req} tp {self.tp_current_shares} exepect {self.expected} request {self.request}',LOG)


    def update_dashboard_data(self):


        #{"Symbol": "AAPL","Tradable":'Open', "Net Pos": 120, "#Algos": 3, "Unreal": 235.42, "Real": 1020.00, "Risk": 1500.00},
        tps = list(self.tradingplans.keys())
        unreal =0
        real=0
        for tp in tps:
            unreal += self.tradingplans[tp].get_unreal(self.symbol_name)
            real += self.tradingplans[tp].get_real(self.symbol_name)
        self.dashboard['Symbol'] = self.symbol_name
        self.dashboard['Tradable'] = self.data['tradable']
        self.dashboard['Net Pos'] = self.tp_current_shares
        self.dashboard['#Algos'] =  len(tps)
        self.dashboard['Unreal'] = unreal
        self.dashboard['Real'] = real
        self.dashboard['Risk'] = 0

        return self.dashboard


######################################## PHASE 1 fill_check_phase  ###########################################
    def send_moc_order(self):

        #"NSDQ Sell->Short NSDQ MOC DAY"
        #Sell->Short

        #       v = v.replace('ACTION',self.action)

        debug_line = f'{self.source} {self.symbol_name} :send_moc_order()'

        base_template = self.moc_order_venue  # keep the template with "ACTION" intact
        net = -self.tp_current_shares         # shares needed to FLAT

        if net == 0:
            message(f'{debug_line}, Nothing to flatten; skipping MOC.',LOG)
            self.moc_order_out = True

            return 0

        action = BUY if net > 0 else SELL    # +net means Buy->Cover, -net means Sell
        ordername = base_template.replace('ACTION', action)

        shares = abs(net)
        req = f'http://127.0.0.1:8080/ExecuteOrder?symbol={self.symbol_name}&ordername={ordername}&shares={shares}'
        try:
            r = requests.get(req, timeout=0.25)
            r.raise_for_status()

            data = r.json()
            resp = data.get("Responce", {})
            success = resp.get("Success", "").lower() == "true"

            if success:
                self.order_pid = resp.get("Content", "")
                self.order_id = ''
                if len(self.order_pid) > 0:
                    self.order_out = True
                    self.moc_order_out = True 
                message(f'{debug_line}, "MOC Ordering successful: pid:", {self.order_pid} on {self.request}',LOG)

                return 1
            else:
                message(f'{debug_line}, "MOC Ordering sending failed.", {req}',LOG)
                return 0

        except Exception as e:
            # This block catches all exceptions, including network errors,
            # JSON decoding errors, and unexpected system errors.
            message(f'{debug_line}, An unexpected error occurred: {e}m{traceback.print_exc()}',LOG)
            return 0


    def cancel_previous_order(self):

        debug_line = f'{self.source} {self.symbol_name} :cancel_previous_order()'

        req = f'http://127.0.0.1:8080/CancelOrder?type=ordernumber&ordernumber={self.order_id}'
        
        r = requests.post(req)

        r = requests.get(req, timeout=0.25)
        r.raise_for_status()

        if not self.order_id:
            try: self.look_up_orderid()
            except Exception: pass
        if not self.order_id:
            message(f'{debug_line},no order_id; skip cancel',LOG)
            return 0
        req = f'http://127.0.0.1:8080/CancelOrder?type=ordernumber&ordernumber={self.order_id}'
        try:
            requests.post(req, timeout=0.25)
            r = requests.get(req, timeout=0.25)
            r.raise_for_status()
        except Exception as e:
            message(f"""{debug_line} cancel request failed:, {e}, {traceback.print_exc()}""",LOG)
            return 0
        data = r.json()
        resp = data.get("Responce", {})
        success = resp.get("Success", "").lower() == "true"

        if success:
            message(f"""{debug_line},order cancel succesful""",LOG)
        else:
            message(f"""{debug_line},order cancel failed""",LOG)


    def flatten_all(self):
        """
        Legacy helper: now ensure we *also* call TP.flatten_cmd() so they
        stop generating fresh expectations while MOC is running.
        """
        for tp in list(self.tradingplans.values()):
            try:
                #tp.flatten_cmd()
                tp.submit_expected_shares(self.symbol_name, 0, 0)
            except Exception:
                pass

    def as_is(self,tag=""):

        # tell all register trading plan the state as is. 
        tps = list(self.tradingplans.keys())

        #### FOR THE TP TRYING TO START THE POSITION. IGNORE. 
        for tp in tps:
            if self.tradingplans[tp].having_request(self.symbol_name) and self.tradingplans[tp].get_current_share(self.symbol_name)!=0:
                self.tradingplans[tp].algo_as_is(tag) 

    # def algo_update_pnl(self):

    #   tps = list(self.tradingplans.keys())

    #   for tp in tps:
    #       self.tradingplans[tp].get_current_expected(self.symbol_name)

    def order_update_phase(self):

        ### 3 CONDITIONS LEAD TO CANCELLATION.
        ### 1. Change of BID/ASK
        ### 2. Change of Request -> (Be replaced by #)
        ### 3. Need to be more Aggresive. 'spreadoffset change.'

        debug_line = f'{self.source} {self.symbol_name} :order_update_phase()'

        #self.order_timing
        now = datetime.now()

        ts = now.hour*3600 + now.minute*60 + now.second

        if self.order_out and  ts>=self.order_timing+5:


            cancellation = False 
            reason = ''
            if self.request>0 and self.bid_change:
                cancellation = True 
                reason = 'bid change'
            elif self.request<0 and self.ask_change:
                cancellation = True 
                reason = 'ask change'
            elif self.prev_request!=self.request:
                cancellation = True 
                reason = 'request change'
            elif self.prev_spread_offset!=self.spread_offset:
                cancellation = True 
                reason = 'aggresiveness change'
            ### calc the current offset level. ###

            self.prev_request=self.request

            ### NOW AGGRESIVENESS CHECK. Cancel, and then update the aggresiveness bar. ###
            # para needed ->

            if cancellation:

                req = f'http://127.0.0.1:8080/CancelOrder?type=ordernumber&ordernumber={self.order_id}'
                
                r = requests.post(req)

                r = requests.get(req, timeout=0.25)
                r.raise_for_status()

                data = r.json()
                resp = data.get("Responce", {})
                success = resp.get("Success", "").lower() == "true"

                self.cancel_sent = True 

                if success:
                    message(f"""{debug_line}, order cancel succesful on ,{reason},""",LOG)
                else:
                    message(f"""{debug_line}, order cancel failed""",LOG)


            # if cancellation == False and self.prev_request!=self.request and self.request!=0:
            #   # just replace the share lot.

            #   req = f'http://localhost:8080/OrderCancelReplace?ordernumber={self.order_id}&shares={str(abs(self.request))}'

            #   r = requests.get(req, timeout=0.25)
            #   r.raise_for_status()

            #   data = r.json()
            #   resp = data.get("Responce", {})
            #   success = resp.get("Success", "").lower() == "true"

    def fill_check_phase(self):

        ### THERE IS REQUEST, order out.

        ### THERE IS REQUEST, no order

        ### THERE IS REQUEST, order fill

        ### THERE IS REQUEST, order partially fill.

        ### THERE IS NO REQUEST (anymore),order out.

        ### THERE IS CHAGING REQUEST , order filled

        debug_line = f'{self.source} {self.symbol_name} :fill_check_phase()'

        if self.order_out:
            if self.order_id=='':
                self.look_up_orderid()

            if self.order_id=='':
                message(f"""{debug_line},WARNING,Cannot locate order id.""",LOG)

            data = self.look_up_order()
            self.order_details = data


            message(f"""{debug_line}, order details updated: {self.order_id} {self.order_details}.""",LOG)


            ###
            if data['ret']==True and self.order_id!='':

                if data['status'] not in ALL_STATES:
                    message(f"""{debug_line},WARNING,{data['status']}, UNSEEN STATUS.""",LOG)
                # is it filled

                if data['status'] in FILL_STATES:
                    self.process_fills(data)

                # is it terminated 
                
                if data['status'] in TERMINAL_STATES:
                    self.order_status_closed()

                if data['status'] == 'Rejected':
                    self.rejection_handling()

                ### CANCEL PHASE ###

                # ACCEPTED,FILLED,Parital, CANCEL,REJECTED. 

                # tp .request_fufill

            if data['ret']==False and self.order_id!='':

                message(f"""{self.symbol_name} Order Lost: {self.order_id}. Attempting to locate and fix. """,NOTIFICATION)

                self.cancel_previous_order()

        else:
            # no order. 
            pass

    def process_fills(self,data):
        # security check.
        # Fills <= Actual Request?
        # If overfill, still need to assign it to one TP. 


        # format:
        # self.central_dispatching_order_request: {tp1:int,tp2:int}
        # fills = {99.5:int,99.6:int}
        # {"637.57":-5,"637.58":-10}

        # total_fills = sum(data['fill'].values())

        # print(debug_line,f'Requested: {self.request} total fill {total_fills}')
        # pass

        #print('DATA:',data)
        debug_line = f'{self.source} {self.symbol_name} :process_fills()'
        # 1. Get the new fills from the API data
        incoming_fills = data.get('fill', {})
        
        # 2. Calculate newly filled shares by comparing with cumulative records
        newly_filled_shares_by_price = {}
        for price, shares in incoming_fills.items():
            previously_filled_shares = self.cumulative_fills_by_price.get(self.order_id, {}).get(price, 0)
            new_shares = shares - previously_filled_shares
            if abs(new_shares) > 0:
                newly_filled_shares_by_price[price] = new_shares
        
        total_new_fills = sum(newly_filled_shares_by_price.values())
        total_fills = sum(incoming_fills.values())
        self.current_new_fills = newly_filled_shares_by_price
        # 3. Update the central cumulative fills record
        
        self.cumulative_fills_by_price[self.order_id] =incoming_fills
        
        # 4. Allocate new fills to trading plans based on requests

        # newly_filled_shares_by_price : dict   {'105.25': 5, '105.26': 5}
        # total_new_fills : int , Total #.  10 
        # central_dispatching_order_request : dict {'tp1': 5, 'tp2': 10}
        
        # Sort TPs by priority or a stable order to ensure consistent allocation
        tp_names = sorted(self.central_dispatching_order_request.keys())

        if DEBUGGING:
            message(f"""{debug_line}, Identified {total_new_fills} new shares. detail: {newly_filled_shares_by_price}. total fill:{incoming_fills}""",LOG)

        rest_fills = total_new_fills
        for tp_name in tp_names:
            request_shares = self.central_dispatching_order_request.get(tp_name, 0)

            if abs(request_shares) > 0 and abs(rest_fills) > 0:
                # Determine how many shares to allocate to this TP
                #shares_to_allocate = min(request_shares, total_new_fills)
                last_tp = tp_name
                newly_filled_shares_by_price,rest_fills =self.allocate_shares(tp_name,request_shares,newly_filled_shares_by_price)
            if abs(rest_fills)==0:
                break

        # if still remianing. fill it to the last tp.
        if abs(rest_fills)>0:
            avg_price,shares = calculate_average_price(newly_filled_shares_by_price)

            message(f"""{debug_line},' Remaining order detected. forcefully fullfill tp {last_tp} with {shares} @ {avg_price}""",LOG)
            self.tradingplans[last_tp].request_fufill(self.symbol_name,shares,avg_price)        # Update current holding

        self.data['current_holding'] += total_new_fills


        message(f"""debug_line, f'Requested: {self.request} new fill {total_new_fills} total fill {total_fills}""",LOG)

    def allocate_shares(self,tp,request_shares, available_fills):
        """
            # INPUT->  request_shares of tp.  & fills dict. 
            # RETURN -> new fills dict & how many left. 

            # step 0 , checkout what case is this.  UnderFill, MatchFill,OverFill.
            # step 1 , set a dict for fills.
            # step 2 , iterate though the avaialbe_fills.
            # step 3 , update the dict until its done. 
            # step 4 , calc avg price, and fill the tp.
        """

        debug_line = f'{self.source} {self.symbol_name} :allocate_shares()'

        tp_fills = {}
        remaining_fills = available_fills.copy()  # Work on a copy to not modify the original input
        total_remaining_fills = sum(available_fills.values())  
        sorted_prices = sorted(remaining_fills.keys())

        for price in sorted_prices:

            shares_at_price = remaining_fills.get(price, 0)
            
            # Determine how many shares to take from this price point

            if abs(request_shares) <= abs(shares_at_price):
                shares_to_take = request_shares
            else:
                shares_to_take = shares_at_price

            message(f"""{debug_line} shares to take,{shares_to_take},'reqest',{request_shares},'shares_at_price',{shares_at_price}""",LOG)

            if shares_to_take != 0:
                tp_fills[price] = tp_fills.get(price, 0) + shares_to_take
                request_shares -= shares_to_take
                remaining_fills[price] -= shares_to_take
                if remaining_fills[price] == 0:
                    del remaining_fills[price]


        avg_price,shares = calculate_average_price(tp_fills)

        self.tradingplans[tp].request_fufill(self.symbol_name,shares,avg_price)
        remain = sum(remaining_fills.values())

        if DEBUGGING:
            message(f"""{debug_line},{tp} for {tp_fills} and total {shares} @ {avg_price}.  Left in stock {remaining_fills}""",LOG)
        
        # remianing 
        
        return remaining_fills,remain
######################################## PHASE 5 aggragate_phase ########################################
    def order_status_closed(self):
        self.order_out = False
        self.order_id =''
        self.order_pid =''
        self.order_details={}
        self.spread_offset=0
        

    def adjust_aggresiveness(self):

        self.l1_update_module()

        debug_line = f'{self.source} {self.symbol_name} :adjust_aggresiveness()'

        self.prev_spread_offset = self.spread_offset

        # cur_spread_level = int(self.fill_time_remaining*10)

        # if cur_spread_level>=len(self.spread_list):
        #   cur_spread_level = len(self.spread_list)-1

        # self.spread_offset = self.spread_list[cur_spread_level]

        adjustment = 0 

        if self.data['spread']>=0.01:
            adjustment = round((self.fill_time_remaining)*self.data['spread'],2) # % of spread.

            if adjustment <0.01:
                adjustment = 0 


        self.spread_offset = adjustment

        if DEBUGGING:
            message(f"""{debug_line},current fill timer percentage {self.fill_time_remaining} total fill-time {self.fill_timer}  current offset {self.spread_offset} & {self.data['spread']} . aggresive:{self.aggresive_ordering}""",LOG)

    def aggragate_phase(self):

        #self.prev_request = self.request
        #self.tp_current_shares,self.expired,self.tp_total_current_shares = self.get_all_current(tps)
        debug_line = f'{self.source} {self.symbol_name} :aggragate_phase()'
        tps = list(self.tradingplans.keys())
        self.central_dispatching_order_request= {}

        ## PAIR OFF BEFORE SENDING THE REQUESTS. ##

        self.order_pair_off(tps)

        self.tp_current_shares = self.get_all_current(tps)
        self.expected = self.get_all_expected(tps)
        
        self.request =  self.expected - self.tp_current_shares

        ### ALSO THE TIME HAS BEEN. 
        self.adjust_aggresiveness()

        #if DEBUG_MODE:

        if DEBUGGING:
            message(f"""{debug_line} ,"have",{self.tp_current_shares}," want",{self.expected}," request",{self.request},{self.central_dispatching_order_request},'Tp have:',{self.current_tp},'Tp want:',{self.expected_tp}""",LOG)

    def order_pair_off(self,tps):

        # give t

        debug_line = f'{self.source} {self.symbol_name} :order_pair_off()'
        want = {}

        for tp in tps:
            want[tp] = (self.tradingplans[tp].get_current_request(self.symbol_name))


        pair_off_results = pair_off(want)

        if DEBUGGING:

            if len(pair_off_results)>0:

                message(f"""{debug_line},pair off:,{want}, paired,{pair_off_results}""",LOG)



        for tp,granted_shares in pair_off_results.items():

            if granted_shares>0:
                self.tradingplans[tp].request_fufill(self.symbol_name,granted_shares,self.data['bid'])
            else:
                self.tradingplans[tp].request_fufill(self.symbol_name,granted_shares,self.data['ask'])





    def get_all_expected(self,tps):

        """
        Doesnt matter if the TP is running or not, having request or not. it runs through. 
        The less the parameter, the more generalizability 
        """

        self.expected_tp = {}

        now = datetime.now()

        ts = now.hour*3600 + now.minute*60 + now.second

        if self.data['spread']>=0.1:
            self.fill_timer = 60 

        if self.data['spread']<=0.05:
            self.fill_timer = 30 

        if self.data['spread']<=0.03:
            self.fill_timer = 20

        if now.hour*60+now.minute<575 or now.hour*60+now.minute>950:
            self.fill_timer = 10

        cur_time = 0

        self.expected = 0
        nbbo_only = False 
        for tp in tps:
            exp =  self.tradingplans[tp].get_current_expected(self.symbol_name)

            self.expected_tp[tp] = exp
            self.expected +=  exp

            self.central_dispatching_order_request[tp] = self.tradingplans[tp].get_current_request(self.symbol_name)

            if self.central_dispatching_order_request[tp]!=0:

                if self.tradingplans[tp].get_nbbo_only():
                    nbbo_only = True
                if self.tradingplans[tp].get_request_time(self.symbol_name)>cur_time:
                    cur_time = self.tradingplans[tp].get_request_time(self.symbol_name)

            ## HERE. If there is request; and amonst them , NBBO is true, then stay true to that.

        self.fill_time_remaining = round((ts-cur_time)/self.fill_timer,2)
        self.fill_time_remaining = min(self.fill_time_remaining,1)

        if self.fill_time_remaining>=1:
            self.aggresive_ordering = True
        else:
            self.aggresive_ordering = False 

        if nbbo_only:
            self.fill_time_remaining =0

        return self.expected

    def get_all_current(self,tps):

        # note, can we skip checking epired stuff. move this process to ordering process.

        self.current_tp = {}
        current_shares=0
        for tp in tps:
            cur = self.tradingplans[tp].get_current_share(self.symbol_name)
            current_shares +=  cur 
            self.current_tp[tp] = cur
                
        return current_shares


######################################## PHASE 6  ORDERING PHASE ########################################

    def get_venue(self):

        #ARCA Sell->Short ARCX Limit Near DAY
        venue = [
        "ARCA ACTION ARCX Limit DAY",
        "BATS ACTION Parallel-2D Limit DAY",
        "EDGA ACTION ROUC Limit DAY",
        "MEMX ACTION MEMX Limit DAY",
        ]

        v = venue[0]
        #TEMP ACTIN TEMP

        # replace ACTION according to symbol suffix.

        v = v.replace('ACTION',self.action)
        # add Near to the end.
        v = v.replace('DAY','Near DAY')

        return v



    def ordering_phase(self):

        """ 
        Must make sure the previous order is canceled first before it can order. 
        ==
        self.order_pid = ''
        self.order_id =''

        """
        debug_line = f'{self.source} {self.symbol_name} :ordering_phase()'

        self.recent_rejection_check()

        if self.rejection_counts>=2:
            message(f"""{debug_line}, too much recent rejection detected. wait 1.""",LOG)
            return 0

        # if self.market_out!=0:
        #   self.market_out = 0
        #   log_print(self.source,self.symbol_name, " just marked out. wait 1. skipping passive management")
        #   return 0

        now = datetime.now()
        ts = now.hour*3600 + now.minute*60 + now.second

        
        if self.aggresive_ordering:
            self.spread_offset+=0.02

        if self.request>0:
            self.action = BUY
            spread_offset = self.spread_offset
        else:
            self.action = SELL
            spread_offset = self.spread_offset*-1

        # adjust the price based on aggressiveness. 
        # Note. Spread is capped at 1% ot the stock price. and Min 0.01
        # Variable 1. Has the bid/ask change.
        # Variable 2. Has the timer reduced. 
        # self.data['spread']
        
        ################################

        ## send orders. get id .##

        venue = self.get_venue()
        req = f'http://127.0.0.1:8080/ExecuteOrder?symbol={self.symbol_name}&limitprice=0.01&priceadjust={str(spread_offset)}&ordername={venue}&shares={str(abs(self.request))}'


        if self.request>0:
            self.order_price = self.data['bid']+self.spread_offset
        else:
            self.order_price = self.data['ask']-self.spread_offset


        try:
            r = requests.get(req, timeout=0.25)
            r.raise_for_status()

            data = r.json()
            resp = data.get("Responce", {})
            success = resp.get("Success", "").lower() == "true"

            if success:
                self.order_pid = resp.get("Content", "")
                self.order_id = ''
                if len(self.order_pid) > 0:
                    self.order_out = True
                    self.order_timing = ts
                message(f"""{debug_line}, Ordering successful: pid:, {self.order_pid},'on',{self.request},agg:{self.aggresive_ordering} spread offset: {self.spread_offset}' @',{self.order_price},' filltimer',{self.fill_time_remaining}""",LOG)

                    
                return 1
            else:
                message(f"""{debug_line}, "Ordering sending failed.", {req}""",LOG)
                return 0

        except Exception as e:
            # This block catches all exceptions, including network errors,
            # JSON decoding errors, and unexpected system errors.
            message(f"""{debug_line}, An unexpected error occurred: {e},{traceback.print_exc()}""",LOG)
            return 0


        ## look up and get the id now?



### EMS API PART ####

    def look_up_orderid(self):


        if self.order_pid!="":

            req = f'http://127.0.0.1:5000/papi/{self.order_pid}'
            r = requests.get(req,timeout=0.25)

            data=r.json()
            

            if data['ret']==True:
                self.order_id = data['order']
            else:
                self.order_id = ''

            if self.order_id not in self.cumulative_fills_by_price:
                self.cumulative_fills_by_price[self.order_id] = {}

            # if DEBUGGING:
            #   print(self.source,self.symbol_name,':look_up_orderid',data,self.order_id)

    def look_up_order(self):

        if self.order_id!="":
            req = f'http://127.0.0.1:5000/order/{self.order_id}'
            r = requests.get(req,timeout=0.25)

            data=r.json()

            return data

### REJECTION HANDLING MOUDULE ####

    def recent_rejection_check(self):
        now = datetime.now()
        timestamp = now.hour*60 + now.minute 
        
        self.rejection_counts =  sum(1 for num in self.rejections if num > timestamp-2)

    def rejection_handling(self):


        debug_line = f'{self.source} {self.symbol_name} :rejection_handling(),requested : {self.request}'


        now = datetime.now()
        timestamp = now.hour*60 + now.minute 
        #######################################################
        tps = list(self.tradingplans.keys())


        #### FOR THE TP TRYING TO START THE POSITION. IGNORE.  

        # Step 1: Flatten initializing Tps.
        for tp in tps:
            if self.tradingplans[tp].having_request(self.symbol_name) and self.tradingplans[tp].get_current_share(self.symbol_name)==0:
                if DEBUGGING:
                    print(debug_line,' rejection detected. flattening intializing algo:',tp)

                self.tradingplans[tp].rejection_handling(self.symbol_name)
        self.rejections.append(timestamp)

        # Step 2: If position is 0. and request is short. Flatten all short positions.

        if self.tp_current_shares ==0 and self.request <0:

            for tp in tps:
                if self.tradingplans[tp].get_current_share(self.symbol_name)<0:
                    if DEBUGGING:
                        print(debug_line,' rejection on init short position detected. flattening short positions:',tp)
                        self.tradingplans[tp].submit_expected_shares(self.symbol_name,0,0)

        self.recent_rejection_check()

    def rejection_message(self,side):

        now = datetime.now()
        timestamp = now.hour*60 + now.minute 

        ## iterate through all the TPs request. check who is requesting. if it is not running withdraw and cancel it. 
        
        if side == "Long":
            coefficient = 1
        elif side =="Short":
            coefficient = -1

        tps = list(self.tradingplans.keys())

        #### FOR THE TP TRYING TO START THE POSITION. IGNORE.  
        for tp in tps:
            if self.tradingplans[tp].having_request(self.symbol_name) and self.tradingplans[tp].get_current_share(self.symbol_name)==0:
                self.tradingplans[tp].rejection_handling(self.symbol_name)

        ####### BUT IF IT IS DISCREPANCY? ##### ADD IT TO THE TP.  OR IGNORE? ####

        self.rejections.append(timestamp)

        self.recent_rejection_check()

    ### L1 UPDATE ######################

    # def check_price_validity(self,bid,ask):

    #   # no more than 2% increment. all of a sudden.

    def time_to_moo(self, venue: str):
        """Manager calls this inside the MOO window [send, cut)."""
        message(f'{self.symbol_name} MOO in progress.', NOTIFICATION)
        self.moo_out = True
        self.moo_order_out = False
        self.moo_order_venue = venue  # keep ACTION placeholder intact
        # Freeze only THIS symbol on each TP
        for tp in self.tradingplans.values():
            try: tp.freeze_symbol(self.symbol_name)
            except Exception: pass
        # Clean pre-open: no stray live orders
        try: self.cancel_previous_order()
        except Exception: pass

    def collect_moo_target(self) -> int:
        """Aggregate all TPs' MOO targets for this symbol."""
        total = 0
        for tp in self.tradingplans.values():
            try: total += int(tp.get_moo_target(self.symbol_name))
            except Exception: pass
        self.moo_final_target = int(total)
        return self.moo_final_target

    def send_moo_order(self):
        """Place one OPG order to move from current -> aggregated target at the open."""
        debug_line = f'{self.source} {self.symbol_name} :send_moo_order()'

        # Guard: do not send after cut
        if self._past_moo_cut():
            print(debug_line, "Past MOO cut; skipping.")
            self.moo_order_out = True
            return 0

        target = self.collect_moo_target()
        current = int(self.tp_current_shares)  # your consolidated live position
        net = target - current                 # how many shares we need to add/remove

        if net == 0:
            print(debug_line, "Already at target; no MOO order needed.")
            self.moo_order_out = True
            return 0

        action = BUY if net > 0 else SELL
        ordername = self.moo_order_venue.replace('ACTION', action)
        shares = abs(net)

        req = (f"http://127.0.0.1:8080/ExecuteOrder?"
               f"symbol={self.symbol_name}&ordername={ordername}&shares={shares}")
        try:
            r = requests.get(req, timeout=0.25)
            data = r.json()
            if r.ok and data.get("Success"):
                self.order_pid = data.get("Content", "")
                self.order_id = ""            # will be filled by fill-check later
                self.order_out = True
                self.order_timing = time.time()
                self.moo_order_out = True
                print(debug_line, " MOO order sent.")
            else:
                print(debug_line, " MOO order rejected:", data)
                self.moo_order_out = False
        except Exception as e:
            print(debug_line, " MOO send failed:", e)
            self.moo_order_out = False
            return 0

    def end_moo(self):
        """Called once open is done / target reached / terminal state."""
        self.moo_out = False
        self.moo_order_out = False
        for tp in self.tradingplans.values():
            try:
                tp.clear_moo_target(self.symbol_name)
                tp.unfreeze_symbol(self.symbol_name)
            except Exception:
                pass

    # --- helpers mirroring your MOC helpers ---
    def _market_suffix(self) -> str:
        parts = self.symbol_name.rsplit('.', 1)
        return f".{parts[1]}" if len(parts) == 2 else ""

    def _moo_cut_sec(self) -> int:
        try:
            entry = self.manager.MKT_TIMINGS.get(self._market_suffix(), {}).get("MOO", {})
            return int(entry.get("cut", 0))
        except Exception:
            return 0

    def _now_sec(self) -> int:
        now = datetime.now()
        return now.hour*3600 + now.minute*60 + now.second

    def _past_moo_cut(self) -> bool:
        cut = self._moo_cut_sec()
        return bool(cut and self._now_sec() >= cut)


    def calculate_spread_levels(self,ask, bid):
        """
        Calculates the spread between ask and bid prices and divides it into 10 levels.

        Args:
            ask (float): The ask price.
            bid (float): The bid price.

        Returns:
            list: A list of 10 floats representing the spread levels.
        """
        spread = round(ask - bid, 2)
        
        # Handle zero or negative spread case
        if spread <= 0:
            return [0.0] * 10

        level_size = round(spread / 9, 2)
        
        spread_list = [0.0] * 10
        current_value = 0.0
        
        # The first element is always 0
        spread_list[0] = 0.0
        
        for i in range(1, 9):
            current_value += level_size
            spread_list[i] = round(current_value, 2)
            
        # The last element is always the total spread
        spread_list[9] = spread
        
        return spread_list

    def l1_update_module(self):

        ### tell the system if there is any bid ask changes since last time.

        debug_line = f'{self.source} {self.symbol_name} :l1_update_module()'
        try:
            postbody = "http://127.0.0.1:8080/GetLv1?symbol=" + self.symbol_name 

            r= requests.get(postbody)
            data = r.json()
            resp = data.get("Responce", {})
            success = resp.get("Success", "").lower() == "true"
            
            if success:
                stream_data = resp.get("Content", "")

                #print(stream_data)

                if type(stream_data)==str:
                    message("""'l1_update_module : Data problem:',{stream_data}""",LOG)

                bid = float(stream_data['BidPrice']) #float(find_between(stream_data, "BidPrice=\"", "\""))
                ask = float(stream_data['AskPrice']) #float(find_between(stream_data, "AskPrice=\"", "\""))
                ts = stream_data['MarketTime'] # find_between(stream_data, "MarketTime=\"", "\"")
                state = stream_data['InstrumentState'] # find_between(stream_data,"InstrumentState=\"", "\"") 

                if state =="Open":
                    self.data['tradable']=True
                else:
                    self.data['tradable']=False 


                    #print(debug_line,"State:",state,self.data['tradable'])

                if self.data['bid']!=bid:
                    self.bid_change = True 
                else:
                    self.bid_change = False 


                if self.data['ask']!=ask:
                    self.ask_change = True 
                else:
                    self.ask_change = False 

                self.data['ask'] = ask
                self.data['bid'] = bid

                self.data['spread'] = round(ask-bid,2)

                #self.spread_list = self.calculate_spread_levels(ask,bid)
                self.data['timestamp'] = ts

                if DEBUGGING:
                    message(f"{debug_line} SPREAD: {self.data['spread']} {self.data['bid']} {self.bid_change} {self.data['ask']} {self.ask_change} Tradeable: {self.data['tradable']} spread_list {self.spread_list}",LOG)

            else:
                message(f"""L1 Error:,{data}""",LOG)
                postbody = 'http://127.0.0.1:8080/Register?symbol='+self.symbol_name +'&feedtype=L1'
                r= requests.get(postbody)
                raise RuntimeError()
            return 
        except Exception as e:

            message(f"""{self.symbol_name},"Init L1 Update",{e},{traceback.print_exc()}""",LOG)

            self.ask_change = True 
            self.bid_change = True 

    def check_price_validity(self,bid,ask):




       # print(len(self.price_check))


        # if 10% move.
        # for i in self.price_check:
        #     d+=abs(bid-i)
        #     c+=1



        if bid!=self.bid and len(self.price_check)>2:
            avg1 = mean(self.price_check)
            mid_ = (bid+ask)/2

            if avg1!=0:
                if abs((mid_-avg1)/avg1)>=0.05:
                    message(f'{self.symbol} l1 update UNSUCCES, {avg_diff} current bid {bid}  and ask {ask} , pool {self.price_check} please check',NOTIFICATION)
                    self.price_check_successful=False
                else:
                    #message(f'{self.symbol} l1 update success, {avg_diff} current bid {bid}  and ask {ask} , pool {self.price_check}',LOG)
                    self.price_check_successful=True

        self.price_check.append(bid)
    def l1_update_module(self):
        debug_line = f'{self.source} {self.symbol_name} :l1_update_module()'
        try:
            postbody = "http://127.0.0.1:8080/GetLv1?symbol=" + self.symbol_name
            r = requests.get(postbody, timeout=0.5)  # add a small timeout
            data = r.json()
            resp = data.get("Responce", {})
            success = resp.get("Success", "").lower() == "true"

            if success:
                stream_data = resp.get("Content", "")
                if isinstance(stream_data, str):
                    message("'l1_update_module : Data problem:',{stream_data}", LOG)

                bid = float(stream_data['BidPrice'])
                ask = float(stream_data['AskPrice'])

                self.check_price_validity(bid,ask)

                if self.price_check_successful and bid!=0 and ask!=0:
                    ts  = stream_data['MarketTime']
                    state = stream_data['InstrumentState']

                    self.data['tradable'] = (state == "Open")

                    self.bid_change = (self.data['bid'] != bid)
                    self.ask_change = (self.data['ask'] != ask)

                    self.data['ask'] = ask
                    self.data['bid'] = bid
                    self.data['spread'] = round(ask - bid, 2)
                    self.data['timestamp'] = ts

                    if DEBUGGING:
                        message(f"{debug_line} SPREAD: {self.data['spread']} {self.data['bid']} {self.bid_change} "
                                f"{self.data['ask']} {self.ask_change} Tradeable: {self.data['tradable']} "
                                f"spread_list {self.spread_list}", LOG)
            else:
                # Normal path: symbol must be registered before L1 appears.
                message(f"L1 Error:,{data}", LOG)  # observed in your logs
                reg = f'http://127.0.0.1:8080/Register?symbol={self.symbol_name}&feedtype=L1'
                try:
                    requests.get(reg, timeout=0.5)
                except Exception as _:
                    pass
                self.data['tradable'] = False
                self.bid_change = self.ask_change = False
                return  # ← do NOT raise here
            return

        except Exception as e:
            # Connection refused / EMS down / bad JSON etc. — not fatal; just back off.
            message(f'{self.symbol_name},"Init L1 Update",{e}', LOG)
            self.data['tradable'] = False
            self.bid_change = self.ask_change = False
            return


def calculate_average_price(price_quantity_dict):
    """
    Calculates the weighted average price from a dictionary where
    keys are prices and values are quantities.

    Args:
        price_quantity_dict: A dictionary of {price: quantity}.

    Returns:
        The weighted average price, or 0 if the dictionary is empty.
    """
    if not price_quantity_dict or len(price_quantity_dict)<0:
        return 0

    if sum(price_quantity_dict.values())==0:
        return 0
    
    total_value = 0
    total_quantity = 0

    for price, quantity in price_quantity_dict.items():
        total_value += float(price) * quantity
        total_quantity += quantity
    
    return round(total_value / total_quantity,3),total_quantity


def pair_off(data):
    # Separate positives and negatives (keep abs values for pairing math)
    positives = {k: v for k, v in data.items() if v > 0}
    negatives = {k: -v for k, v in data.items() if v < 0}
    
    result = {}
    
    for pk, pv in list(positives.items()):
        remaining = pv
        for nk, nv in list(negatives.items()):
            if remaining <= 0:
                break
            if nv > 0:
                amount = min(remaining, nv)
                positives[pk] -= amount
                negatives[nk] -= amount
                remaining -= amount
                # Keep original sign
                result[pk] = result.get(pk, 0) + amount   # positive stays positive
                result[nk] = result.get(nk, 0) - amount   # negative stays negative
    
    return result

if __name__ == "__main__":

    pass

    x = {"t1": 5, "t2": 6, "t3": -4, "t4": -7}
    y = pair_off(x)
    print(y,sum(x.values()),sum(y.values()))



    x = {"t1": 5, "t2": 10, "t3": -4, "t4": -7}
    y = pair_off(x)
    print(y,sum(x.values()),sum(y.values()))

    x = {"t1": 5, "t2": 2, "t3": -4, "t4": -7}
    y = pair_off(x)
    print(y,sum(x.values()),sum(y.values()))



    # test_cases = [
    #     # Case 1: Standard spread, divides evenly
    #     {"ask": 100.05, "bid": 100.00},
        
    #     # Case 2: Smallest possible spread (0.01)
    #     {"ask": 100.01, "bid": 100.00},
        
    #     # Case 3: Larger spread
    #     {"ask": 10.25, "bid": 10.20},

    #     # Case 4: Even larger spread
    #     {"ask": 120.00, "bid": 100.00},
        
    #     # Case 5: Spread that doesn't divide evenly
    #     {"ask": 100.08, "bid": 100.00},
        
    #     # Case 6: Zero spread
    #     {"ask": 100.00, "bid": 100.00},
        
    #     # Case 7: Larger odd-numbered spread
    #     {"ask": 50.07, "bid": 50.00},
    # ]

    # # Assuming calculate_spread_levels is already defined
    # for i, case in enumerate(test_cases, 1):
    #     ask_price = case["ask"]
    #     bid_price = case["bid"]
    #     levels = calculate_spread_levels(ask_price, bid_price)
    #     print(f"Test Case {i}: ask={ask_price}, bid={bid_price} -> Levels: {levels}")


    #parakeys = {'1':'a','b':1,}

    #print({*parakeys})
    # s = Symbol(None,"AMD.NQ")
    # s.print_all_data()

    # s.request=10

    # c=0
    # while True:

    #   s.sysmbol_inspection()

    #   c+=1
    #   time.sleep(3)
    #s.ordering_phase()
