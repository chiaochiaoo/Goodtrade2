import psutil
import socket

import threading
import queue
import requests
from flask import Flask, jsonify
from collections import defaultdict


### vision for this ###
### return all kinds of json files once set up ###




def force_close_port(port, process_name=None):
    """Terminate a process that is bound to a port.
    
    The process name can be set (eg. python), which will
    ignore any other process that doesn't start with it.
    """
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

    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_RCVBUF, 64 * 1024 * 1024)
    actual = sock.getsockopt(socket.SOL_SOCKET, socket.SO_RCVBUF)
    print("Actual RCVBUF size:", actual)
    sock.bind(("localhost", PORT))
    flush_socket(sock)

    msg_queue = queue.Queue(maxsize=10000)

    # Start worker thread
    threading.Thread(target=processor, args=(msg_queue,), daemon=True).start()

    # Main loop — fast reading
    while True:
        try:
            data, addr = sock.recvfrom(2048)
            stream_data = data.decode().strip()
            print(stream_data)
            info = dict(item.split('=', 1) for item in stream_data.split(','))

            msg_queue.put_nowait(info)  # non-blocking
        except queue.Full:
            print("Warning: message queue full, dropping packet")
        except Exception as e:
            print("Socket read error:", e)


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

    def order_processor(order_num, info_dict):

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
        TERMINAL_STATES = {"Filled", "Multi Filled", "Canceled","Rejected"}

        INIT_STATES = {'Accepted','Accepted by GW'}
        FILL_STATES = {'Filled','Partially Filled','Multi Filled'}

        if OrderState in TRANSITION_STATES:
            open_orders.add(order_num)
        elif OrderState in TERMINAL_STATES:
            open_orders.discard(order_num)
        else:
            print("UNKOWN ORDER STATE:",OrderState)

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

    # Process queue messages
    while True:
        try:
            info = msg_queue.get()
            #with lock:
            #print(info)

            if 'Message' in info:
                if info['Message']=='OrderStatus':

                    order_number = info['OrderNumber']
                    order_processor(order_number,info)

                elif info['Message']=='PAPIORDER':
                    api_number = info['PProApiIndex']
                    order_number = info['OrderNumber']
                    with papi_lock:
                        papi_book[api_number] = order_number

                        # this is only for when main software looks it up. it knows it.

        except Exception as e:
            print("Processor error:", e)

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
        resp = data.get("Response", {})
        success = resp.get("Success", "").lower() == "true"
        content = resp.get("Content", {})
        user = content.get("User", "")
        environment = content.get("Environment", "")

        if success:
            if DEBUGGING:print("Success:", user,environment)
            return user,environment
        else:
            raise RuntimeError()

    except Exception:
        if DEBUGGING:print("get user Error occurred:")
        return 'x','x'

def check_connectivity():
    global CONNECTION
    try:
        url = 'http://127.0.0.1:8080/SetJSonOn?'
        r = requests.get(url,timeout=0.25)
        data = r.json()

        # Accessing misspelled key
        resp = data.get("Response", {})
        success = resp.get("Success", "").lower() == "true"
        content = resp.get("Content", "")
        errors = resp.get("Errors", "")

        if success:
            if DEBUGGING:print("Success:", content)

            if CONNECTION!=success:

                CONNECTION=success
                r=f'http://127.0.0.1:8080/SetOutput?region=1&feedtype=OSTAT&output={PORT}&status=on'
                print(requests.post(r).status_code)

                r=f'http://127.0.0.1:8080/SetOutput?region=1&feedtype=PAPIORDER&output={PORT}&status=on'
                print(requests.post(r).status_code)

                r=f'http://127.0.0.1:8080/SetOutput?region=1&feedtype=PAPIORDER&output={PORT}&status=on'
                print(requests.post(r).status_code)

                print('register complete')


            return True
        else:
            if DEBUGGING: print("Failed:", errors or content)
            return False

    except Exception as e:
        print("Error occurred:", e)
        return False

def get_ordernumber(papi):

    try:
        r = f'http://127.0.0.1:8080/GetOrderNumber?requestid={papi}'

        r = requests.get(r,timeout=0.25)

        data = r.json()

        resp = data.get("Response", {})
        success = resp.get("Success", "").lower() == "true"
        content = resp.get("Content", "")

        return content

    except Exception:
        return ''


def run_flask(papi_lock,order_lock,symbol_lock,papi_book,order_book,position_book):

    #force_close_port(6666)
    global CONNECTION
    app = Flask(__name__)

    ### All flask function goes here. 
    @app.route("/papi")
    def papi():
        with papi_lock:
            return jsonify(papi_book)

    @app.route("/papi/<papi>")
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

    @app.route("/papi_submit/<papi>")
    def papi_submit(papi):
        with papi_lock:
            if papi not in papi_book:
                papi_book[papi] = 0
    

    @app.route("/orders")
    def totalorder():

        result = order_book.copy()  # Make sure not to mutate the original
        result["r"] = True
        return jsonify(result)


    @app.route("/order/<orderid>")
    def orderbook(orderid):
        if orderid in order_book:
            result = order_book[orderid].copy()  # Make sure not to mutate the original
            result["r"] = True
            return jsonify(result)
        else:
            return {} 


    @app.route("/connection")
    def connection_check():

        check_connectivity()


        return jsonify(ret=CONNECTION)

    @app.route("/getuser")
    def getuser():


        ret = {'ret':False}
        if CONNECTION:
            user,enviroment = get_user()

            ret['ret'] = True
            ret['user'] = user 
            ret['environment'] = enviroment 
            
        return jsonify(ret)
    app.run(host="0.0.0.0",port=5000)
    

global CONNECTION
#CONNECTION = False

DEBUGGING = False
PORT = 4399

if DEBUGGING:
    print('check_connectivity:',check_connectivity())
    print('get_user:',get_user())
else:
    ppro_in()

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

