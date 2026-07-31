import psutil
import socket
import time

import threading
import queue
import requests
from flask import Flask, jsonify
from collections import defaultdict
import traceback
import json
from datetime import date

from logging_module import *

### vision for this ###
### return all kinds of json files once set up ###


# --- edge-triggered logging -------------------------------------------------
# Several code paths here are polled ~1/s by the Manager, so logging a failure
# unconditionally produces one identical line per second for the whole outage.
# _log_once emits only when the message for a given key *changes* (the falling
# edge), then stays quiet until _reset_log_once clears it on recovery.
_log_once_state = {}

def _log_once(key, content, mtype=LOG):
    """Log `content` only if it differs from the last message for `key`."""
    if _log_once_state.get(key) == content:
        return False
    _log_once_state[key] = content
    message(content, mtype)
    return True

def _reset_log_once(*keys):
    """Forget `keys` so the next failure logs again."""
    for key in keys:
        _log_once_state.pop(key, None)

def force_close_port(port, process_name=None):

    for proc in psutil.process_iter():
        for conn in proc.connections():
            if conn.laddr[1] == port:
                #Don't close if it belongs to SYSTEM
                #On windows using .username() results in AccessDenied
                #TODO: Needs testing on other operating systems
                try:
                    proc.username()
                except psutil.AccessDenied:
                    pass
                else:
                    if process_name is None or proc.name().startswith(process_name):
                        try:
                            proc.kill()
                        except (psutil.NoSuchProcess, psutil.AccessDenied):
                            pass 

def flush_socket(sock):
    sock.setblocking(False)
    try:
        while True:
            sock.recvfrom(4096)
    except BlockingIOError:
        pass  # Nothing more to read
    finally:
        sock.setblocking(True)




def ppro_in():

    force_close_port(5000)
    force_close_port(PORT)

    url = 'http://127.0.0.1:8080/SetJSonOn?'

    try:
        r = requests.get(url,timeout=0.25)
    except:
        pass

    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_RCVBUF, 128 * 1024 * 1024)
    actual = sock.getsockopt(socket.SOL_SOCKET, socket.SO_RCVBUF)
    message(f"EMS: actual RCVBUF size: {actual}", LOG)
    sock.bind(("localhost", PORT))
    flush_socket(sock)

    msg_queue = queue.Queue(maxsize=10000)

    # Start worker thread
    threading.Thread(target=processor, args=(msg_queue,), daemon=True).start()

    check_connectivity()


    # Main loop — fast reading
    while True:
        try:
            data, addr = sock.recvfrom(2048)
            try:
                stream_data = data.decode(errors="ignore").strip()
                info = json.loads(stream_data)
            except Exception as e:
                message(f"EMS: bad packet: {e}", LOG)
                continue  # skip this packet

            try:
                msg_queue.put_nowait(info)
            except queue.Full:
                # Dropping fills silently would be invisible in the UI, so this
                # one is worth surfacing even though it sits in the hot loop.
                message("EMS: message queue full, dropping packet", NOTIFICATION)
        except Exception as e:
            message(f"EMS: socket read loop error: {e}", LOG)
            time.sleep(0.1)  # avoid tight crash loop


def processor(msg_queue):


    papi_lock     = threading.Lock()
    order_locks    = defaultdict(threading.Lock)
    symbol_locks  = defaultdict(threading.Lock)

    papi_book = {}  # papi id : order
    order_book = {} # order : {}
    symbol_book = {}

    open_symbols = set()
    open_orders = set()


    # Start Flask in a sub-thread inside processor
    threading.Thread(target=run_flask,args=(papi_lock,order_locks,symbol_locks,papi_book,order_book,symbol_book), daemon=True).start()

    #{"average_price":292.408,"fees":-0.08975,"fill":{"292.4":10,"292.41":40},"shares":50,"status":"Partially Filled","target_price":292.42,"target_share":100}
    #{"average_price":292.407,"fees":-0.1795,"fill":{"292.4":30,"292.41":70},"shares":100,"status":"Filled","target_price":292.42,"target_share":100}

    def order_processor(order_book,order_num, info_dict):

        symbol = info_dict['Symbol']
        price = float(info_dict['Price'])
        shares = int(info_dict['Shares'])
        side = info_dict['Side']

        if side !='B':
            side =-1
        else:
            side =1
        shares = shares*side
        OrderState = info_dict['OrderState']

        ### Then fees related stuff. ###
        ChargeGway = float(info_dict['ChargeGway'])
        ChargeSec  = float(info_dict['ChargeSec'])
        ChargeAct  = float(info_dict['ChargeAct'])
        ChargeClr  = float(info_dict['ChargeClr'])
        ChargeExec = float(info_dict['ChargeExec'])

        fees = ChargeGway+ChargeSec+ChargeAct+ChargeClr+ChargeExec
        ###############################

        
        TRANSITION_STATES = {'Accepted','Accepted by GW','Partially Filled'}
        TERMINAL_STATES = {"Filled", "Multi Filled", "Canceled",'Cancelled','Cancel Request',"Rejected"}

        INIT_STATES = {'Accepted','Accepted by GW'}
        FILL_STATES = {'Filled','Partially Filled','Multi Filled'}

        if OrderState in TRANSITION_STATES:
            open_orders.add(order_num)
        elif OrderState in TERMINAL_STATES:
            open_orders.discard(order_num)
        else:
            message(f"EMS: unknown order state: {OrderState}", NOTIFICATION)

            if 'Rejected' in OrderState:
                message(f"EMS: order rejected {order_num} {info_dict}", NOTIFICATION)
                open_orders.discard(order_num)


        with order_locks[order_num]:
            order = order_book.setdefault(order_num, {'symbol':symbol,'target_price':0, 'target_share':0, 'status':OrderState, 'fill':{}, 'average_price':0, 'shares':0, 'fees':0})



            ############################
            order['status'] = OrderState

            if OrderState in INIT_STATES:
                order['target_price'] = price
                order['target_share'] = shares
            if OrderState in FILL_STATES:

                if price not in order['fill']:
                    order['fill'][price] = shares
                else:
                    order['fill'][price] +=shares

                total_shares = sum(order['fill'].values())
                weighted_total = sum(price * shares for price, shares in order['fill'].items())
                average_price = weighted_total / total_shares if total_shares else 0

                order['average_price'] = average_price
                order['shares'] = total_shares
                order['fees'] += fees


            #print('order_book update:',order_num)

    # Process queue messages
    while True:
        try:
            info = msg_queue.get()
            #with lock:
 
            #print(info['Message'],info)
            if 'Message' in info:
                if 'OrderStatus' in info['Message']:

                    order_number = info['OrderNumber']
                    order_processor(order_book,order_number,info)

                elif info['Message']=='PAPIORDER':
                    api_number = info['PProApiIndex']
                    order_number = info['OrderNumber']
                    with papi_lock:
                        papi_book[api_number] = order_number

                        # this is only for when main software looks it up. it knows it.

                        #print('papi_book update:',api_number)
                        #print('PAPI update:',papi_book)
        except Exception as e:
            message(f"EMS: processor error: {e},{traceback.format_exc()}", NOTIFICATION)

# SAMPLE MESSAGE.
# {'LocalTime': '11:25:35.171', 'Message': 'PAPIORDER', 'PProApiIndex': '4144', 'OrderNumber': 'QIAOSUN_00000028M17D272100000'}
# {'LocalTime': '11:25:35.314', 'Message': 'OrderStatus', 'MarketDateTime': '20250626-11:25:36.000', 'Currency': '1', 'Symbol': 'SQQQ.NQ', \
# 'Gateway': '2030', 'Side': 'B', 'OrderNumber': 'QIAOSUN_00000028M17D272100000', 'Price': '20.000000', 'Shares': '100', 'Position': '1', 'OrderState': 'Accepted by GW', \
# 'CurrencyChargeGway': '0', 'ChargeGway': '0', 'CurrencyChargeAct': '0', 'ChargeAct': '0', 'CurrencyChargeSec': '0', 'ChargeSec': '0', 'CurrencyChargeExec': '0', 'ChargeExec': '0', \
# 'CurrencyChargeClr': '0', 'ChargeClr': '0', 'OrderFlags': '128', 'CurrencyCharge': '0', 'Account': '1TRUENV001TNVQIAOSUN_USD1', 'InfoCode': '255', 'InfoText': ''}

# <Level1Data Message="L1DB" MarketTime="10:15:26.505" Symbol="SUGP.NQ" BidPrice="1.8000000" AskPrice="1.00000000" BidSize="100" AskSize="20" Volume="94804275" MinPrice="0.45960000" MaxPrice="1.8400000" LowPrice="0.45960000" HighPrice="1.8400000" FirstPrice="0.92470000" OpenPrice="0.92470000" ClosePrice="0.44950000" MaxPermittedPrice="0" MinPermittedPrice="0" LotSize="10" LastPrice="1.5100000" InstrumentState="Halted" AssetClass="Equity" TickValue="0" TickSize="0.0001000000" Currency="USD" Tick="?" TAP="0" TAV="0" TAT="" SSR="E"/>

def get_user():
    try:
        url = 'http://127.0.0.1:8080/GetEnvironment?'
        r = requests.get(url,timeout=0.25)
        data = r.json()

        # Accessing misspelled key
        resp = data.get("Responce", {})
        success = resp.get("Success", "").lower() == "true"
        content = resp.get("Content", {})
        user = content.get("User", "")
        environment = content.get("Environment", "")

        if success:
            # Polled ~1/s, so only log when the identity actually changes.
            _log_once("getuser", f"EMS: get_user success: {user},{environment}", LOG)
            return user,environment
        else:
            raise RuntimeError()

    except Exception:
        _log_once("getuser", "EMS: get_user error occurred", LOG)
        return 'x','x'


def portbinding():

    try:
        r=f'http://127.0.0.1:8080/SetOutput?region=1&feedtype=OSTAT&output={PORT}&status=on'
        x=requests.post(r, timeout=REQUEST_TIMEOUT).status_code

        r=f'http://127.0.0.1:8080/SetOutput?region=1&feedtype=PAPIORDER&output={PORT}&status=on'
        y=requests.post(r, timeout=REQUEST_TIMEOUT).status_code
    except Exception:
        # /register is polled once a second, so a refused PPro must return a
        # clean False here instead of 500ing the route. Logged on the falling
        # edge only -- see _log_once.
        _reset_log_once("portbinding_ok")
        _log_once("portbinding", "EMS: portbinding failed, PPro unreachable", LOG)
        return False

    if x==200 and y==200:
        # Success is also polled ~1/s, so announce it once per outage cycle
        # rather than every tick.
        _reset_log_once("portbinding")
        _log_once("portbinding_ok", f"EMS: register complete on {PORT}", NOTIFICATION)
        return True
    else:
        _reset_log_once("portbinding_ok")
        _log_once("portbinding", f"EMS: portbinding rejected by PPro (OSTAT={x}, PAPIORDER={y})", LOG)
        return False

    


def register_feeds():
    """Bind the OSTAT/PAPIORDER feeds for both regions to our UDP PORT.

    Returns a list of "region/feed=status" strings, or None if PPro was
    unreachable. Shared by the reconnect edge and the periodic refresh.
    """
    codes = []
    try:
        for region, feedtype in (
            (1, 'OSTAT'), (1, 'PAPIORDER'),
            (2, 'OSTAT'), (2, 'PAPIORDER'),
        ):
            r=f'http://127.0.0.1:8080/SetOutput?region={region}&feedtype={feedtype}&output={PORT}&status=on'
            codes.append(f"r{region}/{feedtype}={requests.post(r, timeout=REQUEST_TIMEOUT).status_code}")
    except Exception as e:
        _log_once("feeds", f"EMS: feed registration failed: {e}", LOG)
        return None

    return codes


def check_connectivity():
    global CONNECTION
    global connection_polls
    try:
        url = 'http://127.0.0.1:8080/SetJSonOn?'
        r = requests.get(url,timeout=0.25)
        data = r.json()

        # Accessing misspelled key
        resp = data.get("Responce", {})
        success = resp.get("Success", "").lower() == "true"
        content = resp.get("Content", "")
        errors = resp.get("Errors", "")

        if success:
            # if DEBUGGING:
            #     print("Success:", content)

            # Feeds are bound per PPro session, so they must be re-registered on
            # every False->True edge -- not just the first one. This only fires
            # on a real transition, which means CONNECTION *must* be driven to
            # False on every disconnect path below, or the edge is lost and the
            # reconnect silently comes back with no OSTAT/PAPIORDER feed.
            if CONNECTION != success:

                CONNECTION=success

                codes = register_feeds()
                connection_polls = 0
                # Recovered: let the next outage log its first failure again.
                _reset_log_once("conn", "portbinding_ok", "getuser", "openorders", "userinfo", "feeds")
                if codes is not None:
                    message(f"EMS: PPro reconnected, OSTAT feeds re-registered on {PORT} -> {', '.join(codes)}", NOTIFICATION)

            else:
                # PPro can silently drop an output binding while its API stays
                # up -- we look connected but no OSTAT packets arrive. Re-sending
                # SetOutput is idempotent, so re-assert it periodically.
                # Counted off this poll (Manager hits /connection ~1/s) rather
                # than a separate timer thread, so ~300 polls is ~5 minutes.
                connection_polls += 1

                if connection_polls >= FEED_REFRESH_POLLS:
                    connection_polls = 0
                    codes = register_feeds()
                    if codes is not None:
                        message(f"EMS: periodic OSTAT feed refresh on {PORT} -> {', '.join(codes)}", LOG)

            return True
        else:
            if CONNECTION:
                message("EMS: PPro connection lost (reported not connected).", NOTIFICATION)
            else:
                _log_once("conn", f"EMS: connectivity check failed: {errors or content}", LOG)
            CONNECTION = False
            return False

    except requests.exceptions.RequestException:
        # If any request-related error occurs (like a timeout), just return False.
        # Only the falling edge is a NOTIFICATION -- this is polled every second,
        # so a sustained outage must not spam the UI or the log.
        if CONNECTION:
            message("EMS: PPro connection lost (request error) -- will re-register on reconnect.", NOTIFICATION)
        else:
            _log_once("conn", "EMS: connectivity check failed due to a request error.", LOG)
        CONNECTION = False
        return False
    except Exception as e:
        # Catch other unexpected errors
        if CONNECTION:
            message(f"EMS: PPro connection lost (unexpected error): {e} -- will re-register on reconnect.", NOTIFICATION)
        else:
            _log_once("conn", f"EMS: connectivity check error: {e},{traceback.format_exc()}", LOG)
        CONNECTION = False
        return False

def get_ordernumber(papi):

    try:
        r = f'http://127.0.0.1:8080/GetOrderNumber?requestid={papi}'

        r = requests.get(r,timeout=0.25)

        data = r.json()

        resp = data.get("Responce", {})
        success = resp.get("Success", "").lower() == "true"
        content = resp.get("Content", "")

        return content

    except Exception:
        return ''

def get_symbolvalidity(symbol):

    try:
        r = f'http://127.0.0.1:8080/ValidateSymbol?symbol={symbol}'

        r = requests.get(r,timeout=0.25)

        data = r.json()

        resp = data.get("Responce", {})
        success = resp.get("Success", "").lower() == "true"
        content = resp.get("Content", "")

        if 'is valid.' in content:
            return {'ret':True}

        else:
            return {'ret':False}
    except Exception:
        return {'ret':False}

def get_open_orders(user):
    url = f'http://127.0.0.1:8080/GetOpenOrders?user={user}'
    try:
        response = requests.get(url, timeout=REQUEST_TIMEOUT)
        data = response.json()
    except Exception:
        # PPro down/refused: report "no data" rather than letting the exception
        # escape into Flask as a 500.
        _log_once("openorders", "EMS: get_open_orders failed, PPro unreachable", LOG)
        return False

    resp = data.get("Responce", {})
    success = resp.get("Success", "").lower() == "true"

    if not success:
        return False

    content = resp.get("Content", "")

    orders = content.get("Orders", "")#root.find("Content").find("Orders")

    dic ={}

    for order in orders:
        order_id = order.get("id")
        # state = order.get("state")
        # description = order.get("description")
        open_shares = int(order.get("openSize"))
        side = order.get('side')


        symbol = order.get("symbol") if order.get("symbol") else "UNKNOWN"
        price = float(order.get("price") if order.get("price") else "0.0")


        if side!="B":
            price*=-1

        if abs(price)>=0.5:
            price = round(price,2)
        else:
            price = round(price,3)

        if symbol not in dic:
            dic[symbol] = {}

        dic[symbol][price] = order_id
    #print('return ' ,dic)
    return [dic,len(orders)]

def get_user_info(user):
    url = f'http://127.0.0.1:8080/GetTraderInfo?trader={user}&region=1&assetid=1'
    try:
        response = requests.get(url, timeout=REQUEST_TIMEOUT)
        data = response.json()
    except Exception:
        _log_once("userinfo", "EMS: get_user_info failed, PPro unreachable", LOG)
        return False

    resp = data.get("Responce", {})
    success = resp.get("Success", "").lower() == "true"

    if not success:
        return False

    content = resp.get("Content", "")

    return content

def run_flask(papi_lock,order_lock,symbol_lock,papi_book,order_book,position_book):

    #force_close_port(6666)
    global CONNECTION
    app = Flask(__name__)

    ### All flask function goes here. 
    @app.route("/papi")
    def papi():
        with papi_lock:
            return jsonify(papi_book)

    @app.route("/papi/<papi_number>")
    def papi_look_up(papi_number):
        r={'ret':False}
        if papi_number in papi_book:
            r['order'] = papi_book[papi_number]
            r['ret']=True
        else:   
            order = get_ordernumber(papi_number)

            r['order'] = order

            if order!='':
                r['ret'] = True 
        return jsonify(r)

    @app.route("/openorders/<user>")
    def open_orders(user):
        r={'ret':False}
        # get_open_orders returns [dic, count] on success but a bare False on
        # failure -- unpacking that into two names raises, so check first.
        result = get_open_orders(user)

        if not result:
            return jsonify(r)
        else:
            dic, ordercount = result
            r['ret']=True
            r['content']=dic
            r['order_count'] = ordercount
            return jsonify(r)

    @app.route("/papi_submit/<papi>")
    def papi_submit(papi_number):
        with papi_lock:
            if papi not in papi_book:
                papi_book[papi_number] = 0
    

    @app.route("/orders")
    def totalorder():

        result = order_book.copy()  # Make sure not to mutate the original
        return jsonify(result)


    @app.route("/order/<orderid>")
    def orderbook(orderid):
        if orderid in order_book:
            result = order_book[orderid].copy()  # Make sure not to mutate the original
            result["ret"] = True
            return jsonify(result)
        else:
            return {'ret':False} 


    @app.route("/connection")
    def connection_check():
        global CONNECTION
        global last_reset_date

        check_conn_result  = check_connectivity()

        current_date = date.today()
        if last_reset_date is None or current_date > last_reset_date:
            with papi_lock:
                papi_book.clear()
            
            # Note: order_locks and symbol_locks are defaultdicts, so we don't clear them directly.
            # We can just clear the corresponding books.
            # The locks will be recreated as needed.
            
              # Use a dummy lock to access the global scope if needed
            order_book.clear()

            
            last_reset_date = current_date

        # Report what the probe just observed, not the cached global -- they
        # diverge whenever check_connectivity() bails out early.
        return jsonify(ret=bool(check_conn_result))

    @app.route("/getuser")
    def getuser():


        ret = {'ret':False}
        if CONNECTION:
            user,enviroment = get_user()

            # get_user() returns the sentinel 'x','x' on any failure. Reporting
            # ret=True for that pushes USER='x'/ENV='x' downstream into the
            # Manager UI and its redis snapshot key, so treat it as a failure.
            if user and enviroment and user != 'x' and enviroment != 'x':
                ret['ret'] = True
                ret['user'] = user
                ret['environment'] = enviroment

                ret['info'] = get_user_info(user)

        return jsonify(ret)
    
    @app.route("/check/<symbol>")
    def checksymbol(symbol):

        r = get_symbolvalidity(symbol)

        return jsonify(r)


    @app.route("/register")
    def register():

        r = portbinding()

        ret = {'ret':r}

        return jsonify(ret)

    app.run(host="0.0.0.0", port=5000, use_reloader=False,debug=False)


global CONNECTION
CONNECTION = False
last_reset_date = None

# Successful /connection polls since the feeds were last registered.
connection_polls = 0

# Logging is unconditional -- volume is controlled by _log_once (edge-triggered)
# and by level (LOG vs NOTIFICATION), not by a verbosity flag. Kept defined only
# because commented-out blocks below still reference it.
DEBUGGING = True
PORT = 4399

# (connect, read) timeout for every call out to the PPro API on :8080. Without
# this a hung PPro blocks the Flask worker indefinitely instead of failing fast.
REQUEST_TIMEOUT = (0.25, 2.0)

# Re-assert the OSTAT/PAPIORDER bindings every N successful /connection polls.
# Manager polls once a second, so 300 is roughly 5 minutes -- but it tracks the
# poll rate, not the wall clock: if Manager's inspection_timer changes, so does
# this interval.
FEED_REFRESH_POLLS = 300

# if DEBUGGING:
#     print('check_connectivity:',check_connectivity())
#     print('get_user:',get_user())
# else:
#
def main():
    while True:
        try:
            ppro_in()
        except Exception as e:
            message(f"EMS: ppro_in crashed, restarting in 2s: {e},{traceback.format_exc()}", NOTIFICATION)
            time.sleep(2)  # pause before restart

if __name__ == "__main__":
    main()
# if __name__ == "__main__":

# 	Ppro_in()

# 	# Check all open orders
# 	orders = get_open_orders()
# 	print(f"Received {len(orders)} open orders:\n")
# 	for o in orders:
# 		print(o)
# 	# Or check a specific symbol
# 	orders = get_open_orders("SPY.AM")

# 	print(f"Received {len(orders)} open orders:\n")
# 	for o in orders:
# 		print(o)
# http://localhost:8080/GetTransactions?user=QIAOSUN

##http://localhost:8080/GetOrderState?ordernumber=QIAOSUN_00000242M17D33C100000