from datetime import datetime
import linecache
import sys
import os
from datetime import datetime, timedelta
import tkinter as tk
import traceback
import socket
import time
import requests
import json
import threading
import tkinter as tk
from tkinter import ttk
import ttkbootstrap as tb

from psutil import process_iter
import psutil

from logging_module import *

from flask import Flask, request

from Symbol import *
from TradingPlan import *
from ui_main import *

DEBUGGING = True 


def _sec(h, m, s): return h*3600 + m*60 + s




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



class Manager:

	def __init__(self,ui_root,ems):

		self.root = ui_root 
		self.EMS_ADDRESS = ems
		self.source = "Manager"

		self.SYSTEM_STATUS = tk.StringVar()
		self.USER = tk.StringVar()
		self.ENV = tk.StringVar()


		self.DISASTER_MODE = tk.IntVar(value=0)
		self.POSITION_COUNT = tk.IntVar(value=0)
		self.OPEN_ORDER_COUNT = tk.IntVar(value=0)
		self.TOTAL_ALGO_COUNT = tk.IntVar(value=0)
		self.ACTIVE_ALGO_COUNT = tk.IntVar(value=0)
		self.PROACTIVE_ALGO_COUNT = tk.IntVar(value=0)
		self.HALT_NOTIFICATION = tk.IntVar(value=0)
		self.NO_MORE_ALGOS = tk.IntVar(value=0)

		# GLOBAL BOOLEAN #
		self.system_connected = False
		self.registration_required = True


		self.inspection_timer = 2
		# CORE DATA # 
		self.symbols ={}
		self.algos = {}

		self.positions ={}
		self.open_orders = {}



		self.symbols_registration = []
		self.symbols_registration_count = 0
		#self.lock = threading.Lock()

		self.open_order_check = True 
		### UI part ###



		self.MKT_TIMINGS = {
			".NQ": {
				"MOO": {"send": _sec(9,29,45), "cut": _sec(9,30,0),
						"venue": "NSDQ ACTION NSDQ MOO DAY", "trigger": False, "mode": "order"},
				"MOC": {"send": _sec(15,54,30), "cut": _sec(15,55,0),
						"venue": "NSDQ ACTION NSDQ MOC DAY", "trigger": False, "mode": "order"},
			},
			".NY": {
				"MOO": {"send": _sec(9,29,45), "cut": _sec(9,30,0),
						"venue": "NYSE ACTION NYSE Market OPG DAY", "trigger": False, "mode": "order"},
				"MOC": {"send": _sec(15,58,45), "cut": _sec(15,59,0),
						"venue": "ROSN ACTION RosenblattDQuoteClose MOC DAY", "trigger": False, "mode": "order"},
			},
			".AM": {
				"MOO": {"send": _sec(9,29,45), "cut": _sec(9,30,0),
						"venue": "AMEX ACTION AMEX Market OPG DAY", "trigger": False, "mode": "order"},
				"MOC": {"send": _sec(15,58,45), "cut": _sec(15,59,0),
						"venue": "ARCA ACTION ARCX MOC DAY", "trigger": False, "mode": "order"},
			},

			# Example: European venue that should FLATTEN instead of sending MOO/MOC
			".EU": {
				# Flatten at what would be the “open” moment
				"MOO": {"send": _sec(3,59,45), "cut": _sec(4, 0, 0),  # 09:00 CET ~= 03:00/04:00 ET depending DST; adjust as needed
						"trigger": False, "mode": "flatten"},
				# Flatten at “close”
				"MOC": {"send": _sec(11,29,45), "cut": _sec(11,30,0),
						"trigger": False, "mode": "flatten"},
			},
		}
		### TEST FILE ###
		self.RISK_CFG = {
			"global": {
				"max_gross_pos": 20000,       # sum of abs(all shares)
				"max_symbols": 60,            # distinct live symbols with non-zero pos
				"max_open_orders": 200,
				"daily_unreal_stop": -5000.0, # soft stop: reduce aggressiveness
				"daily_hard_stop":  -10000.0, # hard stop: halt & flatten
			},
			"per_suffix": {
				".NQ": {"max_gross_pos": 10000, "max_symbol_pos": 2000},
				".NY": {"max_gross_pos": 8000,  "max_symbol_pos": 1500},
				".AM": {"max_gross_pos": 4000,  "max_symbol_pos": 1000},
				".EU": {"max_gross_pos": 2000,  "max_symbol_pos":  800},
			},
			"per_symbol": {
				# "TSLA.NQ": {"max_long": 500, "max_short": 500, "max_gross": 700}
			}
		}
		self.RISK_STATE = {
			"gross_pos": 0,          # live snapshot of gross shares
			"distinct_symbols": 0,
			"open_orders": 0,        # if you track from EMS, wire it here
			"daily_unreal": 0.0,     # updated from sum_unreal_real()
			"hard_tripped": False,
			"soft_tripped": False,
		}

		self.test_files = {}

		self.test_files['sim1'] = self.sim1
		self.test_files['sim2'] = self.sim2

		self.test_files['sim3'] = self.sim3
		self.test_files['sim4'] = self.sim4
		self.test_files['sim5'] = self.sim5
		self.test_files['sim6'] = self.sim6

		self.test_files['MOO ALL'] = self.moo_all
		self.test_files['MOC ALL'] = self.moc_all

		self.test_files['QQQ_LIMIT_TEST'] = self.QQQ_LIMIT_TEST
		self.test_files['QQQ_LIMIT_TEST_PRICE_CHANGE'] = self.QQQ_LIMIT_TEST_PRICE_CHANGE
		self.test_files['QQQ_LIMIT_REJ_TEST'] = self.QQQ_LIMIT_REJ_TEST
		self.test_files['QQQ_LIMIT_TEST_BLUK'] = self.QQQ_LIMIT_TEST_BLUK

		#if self.root !=None:
		self.ui = UI(self.root,self)
		set_ui(self.ui)


		self.last_pnl_check = 0

		### WAIT FOR UI TO FULLY INSTANTIATE ###
		# while True:
		
		# 	try:
		# 		self.root.after(0, lambda: None)
		# 		break
		# 	except RuntimeError:
		# 		time.sleep(3)

		good = threading.Thread(target=self.inspection_loop, daemon=True)
		good.start()


		scheduler = threading.Thread(target=self.scheduler, daemon=True)
		scheduler.start()

		self.app = Flask('GoodTrade AMS REST API')
		self._register_routes()

		flask_thread = threading.Thread(
			target=lambda: self.app.run(host="0.0.0.0", port=4440, debug=False, use_reloader=False),
			daemon=True
		)
		flask_thread.start()


	def hello(self):

		print("HI!")
	### EMS PART ###
	def _register_routes(self):
		@self.app.route("/command", methods=["POST"])
		def receive_command():
			try:
				data = request.get_json()
				if data:
					algo_name = data.get("name")
					orders = data.get("orders")
					info = data.get("infos")
					if algo_name and orders is not None and info is not None:
						# Call your Manager method on the Tkinter main thread

						confirmation,orders,aggresive,multiplier,tag = self.ui.algo_authorization.order_confirmation(algo_name,orders)

						if confirmation:
							for key in info.keys():
								if type(info[key])==int  or type(info[key])==float:
									if key!="TA":
										info[key] =info[key]*multiplier
							info['Tag'] = tag
							if aggresive:
								info['aggressive'] = True
							self.root.after(0, self.apply_basket_cmd, algo_name, orders, info)
						return {"status": "success", "message": f"Command for {algo_name} received."}, 200
					else:
						return {"status": "error", "message": "Invalid JSON format"}, 400
				return {"status": "error", "message": "No JSON data provided"}, 400
			except Exception as e:
				print(traceback.print_exc())
				return {"status": "error", "message": str(e)}, 500
				


	def get_env(self):
		try:
			r = f'http://{self.EMS_ADDRESS}:5000/getuser'
			response = requests.get(r)
			data = response.json()

			success = data.get("ret", "")

			#print(data)

			if success:
				environment = data.get("environment")
				user = data.get("user")
				return environment, user
		except Exception as e:
			pass
			#print(e)
		return None, None


	def check_all_pnl(self):
		tps = list(self.algos.keys())
		count = 0
		for tp in tps:
			# if it is still running.
			if self.algos[tp].get_algo_status()!=True:
				count+=1
				
			self.algos[tp].check_pnl()

			self.algos[tp].refresh_ui_component()

		#### 
		# demo_rows = [
		#     {"Symbol": "AAPL", "Net Pos": 120, "#Algos": 3, "Unreal": 235.42, "Real": 1020.00, "Risk": 1500.00},
		#     {"Symbol": "MSFT", "Net Pos": -60, "#Algos": 2, "Unreal": -88.10, "Real": 250.00, "Risk": 900.00},
		#     {"Symbol": "NVDA", "Net Pos": 0, "#Algos": 1, "Unreal": 0.00, "Real": 75.00, "Risk": 700.00},
		#     {"Symbol": "TSLA", "Net Pos": 25, "#Algos": 1, "Unreal": 12.55, "Real": -40.00, "Risk": 500.00},
		#     {"Symbol": "AMZN", "Net Pos": -10, "#Algos": 1, "Unreal": -5.25, "Real": 130.00, "Risk": 400.00},
		# ]
		####

		# self.ui.active_algo_count_number.set(count)

		now = datetime.now()
		ts = now.hour*3600 + now.minute*60 + now.second


		self.ACTIVE_ALGO_COUNT.set(count)

		print("Manager check pnl last period:",ts-self.last_pnl_check,"active algo:",count)

		self.last_pnl_check= ts 


		# 2) Build symbol-level dashboard rows (one row per symbol)
		symbols = list(self.symbols.keys())
		dash = []
		for symbol in symbols:
			# Symbol.update_dashboard_data() returns:
			# {"Symbol": "...", "Tradable": ..., "Net Pos": ..., "#Algos": ..., "Unreal": ..., "Real": ..., "Risk": ...}
			drow = self.symbols[symbol].update_dashboard_data()
			dash.append(drow)

		# 3) Compute totals to display in the Symbol dashboard headers
		#    (You already have a helper that sums totals from all TradingPlans)
		tu, tr = self.get_all_unreal_real()   # total unreal, total real across all algos

		# 4) Push rows + header totals into the Symbol dashboard
		try:
			if getattr(self.ui, "dashboard", None) and getattr(self.ui.dashboard, "symbol_panel", None):
				self.ui.dashboard.symbol_panel.set_data(
					dash,
					header_unreal=tu,
					header_real=tr,
				)
		except Exception:
			# keep Manager resilient even if UI is not yet constructed
			pass

		# 5) Push rows + header totals into the *Algo (by tag)* dashboard
		#    (requires the two helpers below to exist on Manager)
		try:
			self.update_algo_dashboard()   # <— NEW line (calls build_algo_dashboard_rows() internally)
		except Exception:
			pass

		# 6) If you show totals elsewhere (e.g., headers on another panel), keep it updated
		try:
			if getattr(self.ui, "algo_deployment", None):
				self.ui.algo_deployment.update_unreal_real_headers(tu, tr)
		except Exception:
			pass

	def build_algo_dashboard_rows(self):
		"""
		Aggregate per TradingPlan.tag:
		  - 'Algos'   -> tag name
		  - '#Algos'  -> count of TPs with that tag
		  - 'Unreal'  -> sum of TP.get_total_unreal()
		  - 'Real'    -> sum of TP.get_total_real()
		"""
		by_tag = {}
		for tp in list(self.algos.values()):
			tag = getattr(tp, "tag", "SYS")
			row = by_tag.setdefault(tag, {"Algos": tag, "#Algos": 0, "Unreal": 0.0, "Real": 0.0})
			row["#Algos"] += 1
			try:
				row["Unreal"] += float(tp.get_total_unreal())
			except Exception:
				pass
			try:
				row["Real"]   += float(tp.get_total_real())
			except Exception:
				pass
		return list(by_tag.values())

	def update_algo_dashboard(self):
		"""Push rows into ui.dashboard.algo_panel if it exists."""
		rows = self.build_algo_dashboard_rows()
		total_unreal = sum(r.get("Unreal", 0.0) for r in rows)
		total_real   = sum(r.get("Real", 0.0) for r in rows)
		try:
			panel = getattr(self.ui.dashboard, "algo_panel", None)
			if panel is not None:
				panel.set_data(rows, header_unreal=total_unreal, header_real=total_real)
		except Exception:
			# keep Manager resilient even if UI structure changes
			pass


	def get_all_unreal_real(self):


		unreal = 0 
		real = 0

		tps = list(self.algos.keys())

		for tp in tps:

			unreal += self.algos[tp].get_total_unreal()
			real += self.algos[tp].get_total_real()

		return unreal,real

	def sum_unreal_real(self,rows, unreal_key="Unreal", real_key="Real"):
		"""
		Returns (total_unreal, total_real) as floats rounded to 2 decimals.
		rows can be:
		  - list[dict]
		  - dict[str, dict]  (symbol -> row dict)
		"""
		def _to_float(v):
			try:
				return float(str(v).replace(",", ""))
			except Exception:
				return 0.0

		if isinstance(rows, dict):
			iterable = rows.values()
		else:
			iterable = rows or []

		total_unreal = 0.0
		total_real = 0.0
		for d in iterable:
			if not isinstance(d, dict):
				continue
			total_unreal += _to_float(d.get(unreal_key, 0))
			total_real  += _to_float(d.get(real_key, 0))

		return round(total_unreal, 2), round(total_real, 2)

	def moo_all(self):
		"""Within the MOO window, arm all symbols to run their MOO lifecycle."""
		now = datetime.now()
		ts = now.hour*3600 + now.minute*60 + now.second
		for sym in self.symbols.values():
			suffix = sym._market_suffix()
			cfg = self.MKT_TIMINGS.get(suffix, {}).get("MOO", None)
			if not cfg: 
				continue
			send = int(cfg.get("send", 0)); cut = int(cfg.get("cut", 0))
			if send <= ts < cut and not cfg.get("trigger", False):
				sym.time_to_moo(cfg["venue"])

		# mark as fired once per day (be sure you already have your daily reset)
		for suffix, group in self.MKT_TIMINGS.items():
			if "MOO" in group:
				group["MOO"]["trigger"] = True

	# def moo_all(self):
	# 	print('MOO')
	def moc_all(self):
		now = datetime.now()
		ts = now.hour*3600 + now.minute*60 + now.second
		for sym in self.symbols.values():
			suffix = sym._market_suffix()
			cfg = self.MKT_TIMINGS.get(suffix, {}).get("MOC", None)
			if not cfg: 
				continue
			send = int(cfg.get("send", 0)); cut = int(cfg.get("cut", 0))
			if send <= ts < cut and not cfg.get("trigger", False):
				sym.time_to_moc(cfg["venue"])
				
		# mark as fired once per day (be sure you already have your daily reset)
		for suffix, group in self.MKT_TIMINGS.items():
			if "MOC" in group:
				group["MOC"]["trigger"] = True


	def scheduler(self):

		"""
		Once per second, for each suffix+{MOO,MOC}:
		  - if send <= now < cut and trigger==False:
			  if mode=='order': send MOO/MOC orders for symbols with that suffix
			  if mode=='flatten': flatten those symbols (set expected=0) across algos
			then mark trigger=True so it won't fire again today.
		"""
		def _suffix_of(sym_name: str) -> str:
			parts = sym_name.rsplit('.', 1)
			return f".{parts[1]}" if len(parts) == 2 else ""

		while True:
			try:
				now = datetime.now()
				ts = now.hour * 3600 + now.minute * 60 + now.second

				for suffix, cfg in self.MKT_TIMINGS.items():
					for kind in ("MOO", "MOC"):
						entry = cfg.get(kind)
						if not entry:
							continue

						send_sec = entry["send"]
						cut_sec  = entry["cut"]
						triggered = entry.get("trigger", False)
						mode = entry.get("mode", "order")  # default to old behavior
						venue = entry.get("venue", "")

						if not triggered and send_sec <= ts < cut_sec:
							# Gather all symbols with this suffix

							message(f'{suffix} {kind} triggered.',NOTIFICATION)
							for sym_name, symbol in list(self.symbols.items()):
								if _suffix_of(sym_name) != suffix:
									continue

								if mode == "order":

									if kind =="MOO":
										symbol.time_to_moo(venue)
									elif kind =="MOC":
										symbol.time_to_moc(venue)

								elif mode == "flatten":
									# Set expected shares to 0 for this symbol across all algos that hold it
									try:
										for tp_name, tp in list(self.algos.items()):
											if sym_name in tp.symbols:
												tp.submit_expected_shares(sym_name, 0, aggresive=False)
									except Exception as e:
										print(f"scheduler flatten error {sym_name} {kind}: {e}", traceback.print_exc())

							# Mark event triggered after processing the suffix/kind window
							entry["trigger"] = True

			except Exception as e:
				print("scheduler loop error:", e, traceback.print_exc())

			time.sleep(1.0)

	def registration(self):

		### couple things req re-reg. Disconneced. even once. will req. 
		#print('trying to reg')
		if self.registration_required:
			try:
				r = f'http://{self.EMS_ADDRESS}:5000/register'
				response = requests.get(r)
				data = response.json()

				success = data.get("ret", "")

				#print(data)
				
				if success:
					self.registration_required = False
					message('Register successful, inspection begins',NOTIFICATION)
					return True
			except:
				return False
		else:
			return True

	def check_open_orders(self):
		try:
			r = f"""http://{self.EMS_ADDRESS}:5000/openorders/{self.USER.get()}"""

			#http://localhost:5000/openorders/QIAOSUN
			response = requests.get(r)
			data = response.json()

			success = data.get("ret", "")

			if success:
				order_count = data.get("order_count")
				dic = data.get("content")

				self.OPEN_ORDER_COUNT.set(order_count)

				for sym in list(self.symbols.keys()):
					if sym in dic:
						self.symbols[sym].set_openorders(dic[symbol])
					else:
						self.symbols[sym].set_openorders({})


		except Exception as e:

			success = False
	def get_connectivity(self):

		success = False
		try:
			r = f'http://{self.EMS_ADDRESS}:5000/connection'
			response = requests.get(r)
			data = response.json()

			success = data.get("ret", "")

		except Exception as e:

			success = False

		#print('get connectivity:',success)
		if success != self.system_connected or success==False: #and len(self.USER.get())<=2

			if success:
				env,user = self.get_env()

				message(f'ENV getting success,{env},{user}',NOTIFICATION)

				self.USER.set(user)
				self.ENV.set(env)
				self.SYSTEM_STATUS.set('CONNECTED')
				self.ui.DISCONNECTED.set(0)
			else:
				self.SYSTEM_STATUS.set('ERROR')
				self.USER.set('DISCONNECTED')
				self.ENV.set('DISCONNECTED')

				self.ui.DISCONNECTED.set(1)
				self.ui.flashing_red()

				self.registration_required = True 

			self.system_connected = success

		return self.system_connected
	def inspection_loop(self):
		consecutive_errors = 0
		while True:
			
			time.sleep(self.inspection_timer)
			try:

				if  self.get_connectivity() and self.registration() and self.DISASTER_MODE.get()!=True:

					self.check_open_orders()
					for sym in list(self.symbols.values()):
						sym.symbol_inspection()  # uses real acquire/finally release

						# if symbol in self.symbols:
						# 	self.symbols[symbol].update_data()

						# 	if symbol in self.open_orders:
						# 		self.symbols[symbol].update_orderbook(self.open_orders[symbol])
						# 	else:
						# 		self.symbols[symbol].update_orderbook({})

					self.check_all_pnl()

					  # success path resets error counter
				else:
					message(f'System Disconnected. Please Check',NOTIFICATION)
			except Exception as e:
				consecutive_errors += 1

				time.sleep(min(0.25, 0.01 * (2 ** min(consecutive_errors, 5))))
				print("Inspection error:",e,traceback.print_exc())

	def get_l1_regisration(self):


		self.symbols_registration = []
		r = 'http://127.0.0.1:8080/GetL1Registrations?'
		response = requests.get(r)
		data = response.json()

		x=data['Responce']['Content']['Regions']
		#symbols =[]
		for y in x:
			for l in y['l1 registrations']:
				self.symbols_registration.append(l['symbol'])

		self.symbols_registration_count = len(self.symbols_registration)

	def deregister_symbol(self):

		###http://localhost:8080/Deregister?symbol=OKTA.NQ&feedtype=L1
		pass

	def check_symbol(self,symbol):

		####
		try:
			r = f'http://{self.EMS_ADDRESS}:5000/check/{symbol}'
			response = requests.get(r)
			data = response.json()

			#success = data.get("ret", "")
			#print(data)
			if data['ret']==True:
				return True 
			else:
				return False
		except Exception as e:
			#print(e)

			return False

	def aflatten_all(self):
		for sym_name, symbol in list(self.algos.items()):
			symbol.a_flatten_cmd()
			
	def flatten_all(self):
		for sym_name, symbol in list(self.algos.items()):
			symbol.flatten_cmd()
		#####
	def apply_basket_cmd(self,algo_name,orders,info):

		if DEBUGGING:
			print(self.source,"receiving",algo_name,orders,info)

		new_algo = False
		if algo_name not in self.algos and self.NO_MORE_ALGOS.get()==False and self.system_connected!=False:

			# check 1 : make sure it's not empty init. 


			total = sum(abs(v['share']) for v in orders.values())

			if total ==0:
				return

			# init the Trading plans 

			self.algos[algo_name] = TradingPlan(self,algo_name,info)
			new_algo =True 

			self.TOTAL_ALGO_COUNT.set(self.TOTAL_ALGO_COUNT.get()+1)

			if DEBUGGING:
				print(self.source,f'initializing {algo_name}')

			# init the UI needed 

			if self.ui!=None:
				
				ui_element = {}
				ui_element['algo'] = algo_name
				ui_element['position'] =self.algos[algo_name].data['current_shares']
				ui_element['status'] =self.algos[algo_name].data['status']
				ui_element['unreal'] =self.algos[algo_name].data[UNREAL]
				ui_element['real'] = self.algos[algo_name].data[REALIZED]
				ui_element['multiplier'] = self.algos[algo_name].data['multiplier']
				
				ui_element['tp'] = self.algos[algo_name]
				self.ui.algo_deployment.add_algo(self.algos[algo_name])

				self.algos[algo_name].set_ui(self.ui)

		if algo_name in self.algos:

			print(f'{self.source} checking {algo_name} and {self.algos[algo_name].shutdown},{orders},{info}')

			if self.algos[algo_name].shutdown!=True:

				for symbol,value in orders.items():


					print(self.source,f'checking {symbol}')
					symbol_check = False 

					if symbol not in self.symbols:

						#if self.check_symbol(symbol):
						symbol_check = True
						self.symbols[symbol] = Symbol(self,symbol)

						if DEBUGGING:
							print(self.source,f'initializing {symbol}')

					else:
						symbol_check=True

			
					### NOW THERE ARE SOME CHANGES.  X: {'share':x,'limit:'y,'hedge?':k,'aggressive':y}

					if symbol_check:

						self.algos[algo_name].register_symbol(symbol,self.symbols[symbol])

						if 'limit' in value:
							pass

							limit_price = value['limit']
							share = value['share']

							self.algos[algo_name].submit_limit_request(symbol,share,limit_price)

						else:
							share = value['share']
							if 'aggressive' in info:
								aggressive = True
							else:
								aggressive = False 
							self.algos[algo_name].submit_expected_shares(symbol,share,aggressive)


				self.algos[algo_name].tradingplan_classification()

	def sim1(self):

		name = 'SIM1'
	
		orders = {'QQQ.NQ':{'share':10}}
		risk = 0 
		aggresive = False 
		info = {}
		self.apply_basket_cmd(name,orders,info)

	def sim2(self):

		name1 = 'SIM2-1'
		orders1 ={'QQQ.NQ':{'share':10}}
		risk = 0 
		aggresive = False 
		info = {}
		self.apply_basket_cmd(name1,orders1,info)

		name1 = 'SIM2-2'
		orders1 = {'SPY.AM':{'share':10}}
		risk = 0 
		aggresive = False 
		info = {}
		self.apply_basket_cmd(name1,orders1,info)
 
	def sim3(self):

		name1 = 'SIM3-1'
		orders1 = {'IWM.AM':{'share':10}}
		risk = 0 
		aggresive = False 
		info = {}
		self.apply_basket_cmd(name1,orders1,info)

		name1 = 'SIM3-2'
		orders1 = {'VOO.AM':{'share':-10}}
		risk = 0 
		aggresive = False 
		info = {}
		self.apply_basket_cmd(name1,orders1,info)

		name1 = 'SIM3-3'
		orders1 = {'IWM.AM':{'share':-5}}
		risk = 0 
		aggresive = False 
		info = {}
		self.apply_basket_cmd(name1,orders1,info)

		name1 = 'SIM3-4'
		orders1 = {'VOO.AM':{'share':5}}
		risk = 0 
		aggresive = False 
		info = {}
		self.apply_basket_cmd(name1,orders1,info)

	def sim4(self):

		name1 = 'SIM4-'
		orders1 ={'TQQQ.NQ':{'share':1}}
		risk = 0 
		aggresive = False 
		info = {}

		for i in range(100):
			name = name1+str(i)

			self.root.after(0, self.apply_basket_cmd, name, orders1, info)
			#self.apply_basket_cmd(name,orders1,info)

	def sim5(self):

		name1 = 'SIM5-'
		orders1 ={'SQQQ.NQ':{'share':1}}
		risk = 0 
		aggresive = False 
		info = {}

		for i in range(100):
			name = name1+str(i)

			self.root.after(0, self.apply_basket_cmd, name, orders1, info)

			#self.apply_basket_cmd(name,orders1,info)

	def sim6(self):

		name1 = 'SIM6-1'
		orders1 ={'QQQ.NQ':{'share':1}}
		risk = 0 
		aggresive = False 
		info = {}
		self.apply_basket_cmd(name1,orders1,info)

		name1 = 'SIM6-2'
		orders1 = {'SPY.AM':{'share':-1}}
		risk = 0 
		aggresive = False 
		info = {}
		self.apply_basket_cmd(name1,orders1,info)

		name1 = 'SIM6-3'
		orders1 = {'BABA.NY':{'share':1}}
		risk = 0 
		aggresive = False 
		info = {}
		self.apply_basket_cmd(name1,orders1,info)

	def QQQ_LIMIT_REJ_TEST(self):

		name1 = 'SIMQQQ-LIMIT-PRICE'
		orders1 ={'QQQ.NQ':{'share':10,'limit':0}}
		risk = 0 
		aggresive = False 
		info = {}
		self.apply_basket_cmd(name1,orders1,info)

	def QQQ_LIMIT_TEST_BLUK(self):

		for i in range(100):
			name1 = 'SIMQQQ-LIMIT-PRICE'+str(i)
			orders1 ={'QQQ.NQ':{'share':10,'limit':566-i}}
			risk = 0 
			aggresive = False 
			info = {}
			self.apply_basket_cmd(name1,orders1,info)

	def QQQ_LIMIT_TEST(self):

		name1 = 'SIMQQQ-LIMIT-PRICE'
		orders1 ={'QQQ.NQ':{'share':10,'limit':566}}
		risk = 0 
		aggresive = False 
		info = {}
		self.apply_basket_cmd(name1,orders1,info)

		name1 = 'SIMQQQ-LIMIT-PRICE2'
		orders1 ={'QQQ.NQ':{'share':10,'limit':567}}
		risk = 0 
		aggresive = False 
		info = {}
		self.apply_basket_cmd(name1,orders1,info)

		name1 = 'SIMQQQ-LIMIT-PRICE3'
		orders1 ={'QQQ.NQ':{'share':10,'limit':568}}
		risk = 0 
		aggresive = False 
		info = {}
		self.apply_basket_cmd(name1,orders1,info)

		name1 = 'SIMQQQ-LIMIT-PRICE-'
		orders1 ={'QQQ.NQ':{'share':-10,'limit':570}}
		risk = 0 
		aggresive = False 
		info = {}
		self.apply_basket_cmd(name1,orders1,info)

		name1 = 'SIMQQQ-LIMIT-PRICE2-'
		orders1 ={'QQQ.NQ':{'share':-10,'limit':571}}
		risk = 0 
		aggresive = False 
		info = {}
		self.apply_basket_cmd(name1,orders1,info)

		name1 = 'SIMQQQ-LIMIT-PRICE3-'
		orders1 ={'QQQ.NQ':{'share':-10,'limit':572}}
		risk = 0 
		aggresive = False 
		info = {}
		self.apply_basket_cmd(name1,orders1,info)

	def QQQ_LIMIT_TEST_PRICE_CHANGE(self):

		name1 = 'SIMQQQ-LIMIT-PRICE'
		orders1 ={'QQQ.NQ':{'share':10,'limit':566.5}}
		risk = 0 
		aggresive = False 
		info = {}
		self.apply_basket_cmd(name1,orders1,info)

		name1 = 'SIMQQQ-LIMIT-PRICE2'
		orders1 ={'QQQ.NQ':{'share':10,'limit':567.5}}
		risk = 0 
		aggresive = False 
		info = {}
		self.apply_basket_cmd(name1,orders1,info)

		name1 = 'SIMQQQ-LIMIT-PRICE3'
		orders1 ={'QQQ.NQ':{'share':10,'limit':568.5}}
		risk = 0 
		aggresive = False 
		info = {}
		self.apply_basket_cmd(name1,orders1,info)

		name1 = 'SIMQQQ-LIMIT-PRICE-'
		orders1 ={'QQQ.NQ':{'share':-10,'limit':570.5}}
		risk = 0 
		aggresive = False 
		info = {}
		self.apply_basket_cmd(name1,orders1,info)

		name1 = 'SIMQQQ-LIMIT-PRICE2-'
		orders1 ={'QQQ.NQ':{'share':-10,'limit':571.5}}
		risk = 0 
		aggresive = False 
		info = {}
		self.apply_basket_cmd(name1,orders1,info)

		name1 = 'SIMQQQ-LIMIT-PRICE3-'
		orders1 ={'QQQ.NQ':{'share':-10,'limit':572.5}}
		risk = 0 
		aggresive = False 
		info = {}
		self.apply_basket_cmd(name1,orders1,info)

force_close_port(4440)
# force_close_port(5000)

EMS_ADDRESS = "127.0.0.1"
#EMS_ADDRESS = "10.29.10.137"

root = tb.Window(themename="flatly") # Start with a light theme
root.title("GoodTrade AMS 09-18")

screen_width = root.winfo_screenwidth()
screen_height = root.winfo_screenheight()

root.geometry("1870x1280")

# app = UI(root)
# root.protocol("WM_DELETE_WINDOW", app._on_closing)



m = Manager(root,EMS_ADDRESS)

message("System Initialized",NOTIFICATION)
root.mainloop()

message('System Terminated',LOG)
# force_close_port(4440)
current_system_pid = os.getpid()

ThisSystem = psutil.Process(current_system_pid)
ThisSystem.terminate()
os._exit(1)

print('HI')


# if m.get_connectivity():
# 	print(m.USER.get(),m.ENV.get())


# c=1
# time.sleep(3)
# while 1:

# 	if c%3==0:

# 		m.apply_basket_cmd('TEST'+str(1),{
# 			'NFLX.NQ':{'share':1}
# 			},{})

# 	c+=1

# 	if c==60:
# 		break
# 	time.sleep(1)

