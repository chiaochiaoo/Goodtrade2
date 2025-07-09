from psutil import process_iter
import psutil
import socket
import time
import json
import xmltodict
import threading
import queue
import requests
from flask import Flask, jsonify
from collections import defaultdict
import xml.etree.ElementTree as ET
import re

### vision for this ###
### return all kinds of json files once set up ###



# ACCEPTED  = 'Accepted'
# CANCELED = 'Canceled'
# REJECTED = 'Rejected'
# FILLED = 'Filled'
# PARTIALLY_FILLED = 'Partilly_Filled'

PORT = 4399

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




def Ppro_in():
	UDP_IP = "localhost"
	UDP_PORT = PORT

	force_close_port(PORT)


	#r=f'http://127.0.0.1:8080/SetOutput?region=1&feedtype=OSTAT&output={port}&status=on'
	#print(requests.post(r).status_code)

	# r=f'http://127.0.0.1:8080/SetOutput?region=1&feedtype=PAPIORDER&output={port}&status=on'
	# print(requests.post(r).status_code)

	#print('register complete',r)

	sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
	sock.setsockopt(socket.SOL_SOCKET, socket.SO_RCVBUF, 64 * 1024 * 1024)
	actual = sock.getsockopt(socket.SOL_SOCKET, socket.SO_RCVBUF)
	print("Actual RCVBUF size:", actual)
	sock.bind((UDP_IP, UDP_PORT))
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

	# 
	# Start Flask in a sub-thread inside processor
	threading.Thread(target=run_flask,args=(papi_lock,order_locks,symbol_locks,papi_book,order_book,symbol_book), daemon=True).start()

	#{"average_price":292.408,"fees":-0.08975,"fill":{"292.4":10,"292.41":40},"shares":50,"status":"Partially Filled","target_price":292.42,"target_share":100}
	#{"average_price":292.407,"fees":-0.1795,"fill":{"292.4":30,"292.41":70},"shares":100,"status":"Filled","target_price":292.42,"target_share":100}

	def order_processor(order_number,info):

		symbol = info['Symbol']
		price = float(info['Price'])
		shares = int(info['Shares'])
		side = info['Side']

		if side !='B':
			side =-1
		else:
			side =1
		shares = shares*side
		OrderState = info['OrderState']

		### Then fees related stuff. ###
		ChargeGway = float(info['ChargeGway'])
		ChargeSec  = float(info['ChargeSec'])
		ChargeAct  = float(info['ChargeAct'])
		ChargeClr  = float(info['ChargeClr'])
		ChargeExec = float(info['ChargeExec'])

		fees = ChargeGway+ChargeSec+ChargeAct+ChargeClr+ChargeExec
		###############################

		
		TRANSITION_STATES = {'Accepted','Accepted by GW','Partially Filled'}
		TERMINAL_STATES = {"Filled", "Multi Filled", "Canceled","Rejected"}

		INIT_STATES = {'Accepted','Accepted by GW'}
		FILL_STATES = {'Filled','Partially Filled','Multi Filled'}

		if OrderState in TRANSITION_STATES:
			open_orders.add(order_number)
		elif OrderState in TERMINAL_STATES:
			open_orders.discard(order_number)
		else:
			print("UNKOWN ORDER STATE:",OrderState)

		with order_locks[order_number]:
			order = order_book.setdefault(order_number, {'target_price':0,'target_share':0,'status':OrderState,'fill':{},'average_price':0,'shares':0,'fees':0})



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


def extract_order_number(xml_string):
	try:
		root = ET.fromstring(xml_string)

		success = root.findtext("Success")
		if success == "true":
			return root.findtext("Content") or ""
		else:
			return 0
	except ET.ParseError:
		return 0  # Return empty if XML is malformed or unreadable

def parse_environment_user(xml_string):
	"""
	Parses the XML and extracts Environment and User values from <Content>.
	
	Returns:
		dict: {'Environment': ..., 'User': ...}
	"""
#try:
	root = ET.fromstring(xml_string)
	content_text = root.find("Content").text.strip()

	
	user_match = re.search(r'User="([^"]+)"', content_text)
	env_match = re.search(r'Environment="([^"]+)"', content_text)


	return {
		"Environment": env_match.group(1) if env_match else None,
		"User": user_match.group(1) if user_match else None
	}
		

def run_flask(papi_lock,order_lock,symbol_lock,papi_book,order_book,position_book):

	#force_close_port(6666)
	global connection
	connection = False 

	app = Flask(__name__)

	### All flask function goes here. 
	@app.route("/papi")
	def papi():
		with papi_lock:
			return jsonify(papi_book)

	@app.route("/papi/<papi>")
	def papi_look_up(papi):
		if papi in papi_book:
			return papi_book[papi]
		else:
			r = f'http://127.0.0.1:8080/GetOrderNumber?requestid={papi}'

			response = requests.get(r)

			# Get the XML as a string
			xml_string = response.text

			num = extract_order_number(xml_string)

			with papi_lock:
				papi_book[papi] = num
			return jsonify(num)

	@app.route("/papi_submit/<papi>")
	def papi_submit(papi):
		with papi_lock:
			if papi not in papi_book:
				papi_book[papi] = 0


	@app.route("/orders")
	def totalorder():
		return jsonify(order_book)

	@app.route("/order/<orderid>")
	def orderbook(orderid):
		if orderid in order_book:
			return jsonify(order_book[orderid])
		else:
			return {} 


	@app.route("/getuser")
	def getuser():
		global connection
		p="http://127.0.0.1:8080/GetEnvironment?"
		try:
			r= requests.get(p,timeout=0.25)
			xml_string = r.text
		except:

			connection = False 
			return jsonify({})


		d=parse_environment_user(xml_string)

		if len(d)>0 and connection==False:
			connection=True 
			print('Now connected')

			r=f'http://127.0.0.1:8080/SetOutput?region=1&feedtype=OSTAT&output={PORT}&status=on'
			print(requests.post(r).status_code)

			r=f'http://127.0.0.1:8080/SetOutput?region=1&feedtype=PAPIORDER&output={PORT}&status=on'
			print(requests.post(r).status_code)

			print('register complete',r)



		return jsonify(d)
	app.run(port=5000)
	


if __name__ == "__main__":

	Ppro_in()

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

