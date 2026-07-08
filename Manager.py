from datetime import datetime
import linecache
import sys
import os
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo
_NY = ZoneInfo("America/New_York")
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

import psutil

from logging_module import *

from flask import Flask, request

from Symbol import *
from TradingPlan import *
from ui_main import *

DEBUGGING = True 

DB_CONFIG = {
	"dbname": "railway",
	"user": "postgres",
	"password": "rpwhtKVvffybMqtZvszgOvNzeBSIcRva",  # Use the password YOU set, not the email one!
	"host": "mainline.proxy.rlwy.net",
	"port": "55828"
}

# CREATE TABLE IF NOT EXISTS ppro_audit_log (
#     id SERIAL PRIMARY KEY,
#     timestamp TIMESTAMPTZ NOT NULL DEFAULT NOW(),
#     username TEXT NOT NULL,
#     environment TEXT NOT NULL CHECK (environment IN ('TMS', 'LIVE')),
#     symbol TEXT,
#     intent TEXT,
#     action TEXT NOT NULL,
#     order_number TEXT,
#     reason JSONB,
#     full_url TEXT NOT NULL,
#     response_status INTEGER,
#     response_success BOOLEAN,
#     error_message TEXT
# );

try:
	import pymongo
except ImportError:
	import subprocess
	import sys
	
	subprocess.check_call([sys.executable, "-m", "pip", "install", "pymongo"])
	import pymongo


import queue
from functools import partial

try:
	import psycopg2
	import psycopg2.extras
except ImportError:
	import subprocess
	subprocess.check_call([sys.executable, "-m", "pip", "install", "psycopg2-binary"])
	import psycopg2
	import psycopg2.extras


class UiBus:
	"""Thread-safe dispatcher to ensure Tk is only touched from the main thread."""
	def __init__(self, root):
		self.root = root
		self.q = queue.Queue()
		# Drain ~60fps without starving the event loop
		self.root.after(16, self._drain)

	def post(self, fn, *args, **kwargs):
		self.q.put((fn, args, kwargs))

	def _drain(self):
		drain_cap = 250  # prevent long frames if flooded
		try:
			for _ in range(drain_cap):
				fn, args, kwargs = self.q.get_nowait()
				try:
					fn(*args, **kwargs)
				except Exception:
					# swallow UI paint errors so the loop never dies
					pass
		except queue.Empty:
			pass
		self.root.after(16, self._drain)

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

		self.CLERK_USER = tk.StringVar(value="Not signed in")
		self.clerk_user_info = None

		self.env = ''

		self.info = {}
		self.DISASTER_MODE = tk.IntVar(value=1)
		self.POSITION_COUNT = tk.IntVar(value=0)
		self.OPEN_ORDER_COUNT = tk.IntVar(value=0)
		self.TOTAL_ALGO_COUNT = tk.IntVar(value=0)
		self.ACTIVE_ALGO_COUNT = tk.IntVar(value=0)
		self.PROACTIVE_ALGO_COUNT = tk.IntVar(value=0)
		self.HALT_NOTIFICATION = tk.IntVar(value=0)

		self.DEBUG_mode = tk.IntVar(value=0)
		self.DEBUG_ORDER_mode = tk.IntVar(value=0)
		self.NO_MORE_ALGOS = tk.IntVar(value=0)

		self.SMARTGATE = tk.IntVar(value=0)
		self.LIMIT_EXIT_mode = tk.IntVar(value=0)

		self.STOPLITMIT = tk.IntVar(value=0)

		# GLOBAL BOOLEAN #
		self.system_connected = False
		self.registration_required = True


		self.inspection_timer = 1
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


		euro_moc_time =  _sec(11,30,1)
		#euro_moc_time =  _sec(10,55,45)
		euro_moc_time_cut =_sec(11,32,0)

		with open("fx_pairs.json", "r", encoding="utf-8") as f:
			self.FX_rules = json.load(f)

		self.MKT_TIMINGS = {
			".NQ": {			
				"MOO": {"send": _sec(9,27,52), "cut": _sec(9,30,0),
						"venue": "NSDQ ACTION NSDQ MOO Regular OnOpen", "trigger": False, "mode": "order"},
				"MOC": {"send": _sec(15,54,52), "cut": _sec(15,55,0),
						"tms_venue":"ARCA ACTION ARCX Market DAY",
						"venue": "NSDQ ACTION NSDQ MOC DAY", "trigger": False, "mode": "order"},
			},
			".NY": {
				"MOO": {"send": _sec(9,29,40), "cut": _sec(9,30,0),
						"venue": "NYSE ACTION NYSE MOO OnOpen", "trigger": False, "mode": "order"},
				"MOC": {"send": _sec(15,58,52), "cut": _sec(15,59,0),
						"tms_venue":"ARCA ACTION ARCX Market DAY",
						"venue": "ROSN ACTION RosenblattDQuoteClose MOC DAY", "trigger": False, "mode": "order"},
			},
			".AM": {
				"MOO": {"send": _sec(9,29,40), "cut": _sec(9,30,0),
						"venue": "ARCA ACTION ARCX MOO OnOpen", "trigger": False, "mode": "order"},
				"MOC": {"send": _sec(15,58,52), "cut": _sec(15,59,0),
						"tms_venue":"ARCA ACTION ARCX Market DAY",
						"venue": "ARCA ACTION ARCX MOC DAY", "trigger": False, "mode": "order"},
			},








			".PA": {
				"MOO": {"send": _sec(9,29,40), "cut": _sec(9,30,0),
						"venue": "ARCA ACTION ARCX MOO OnOpen", "trigger": False, "mode": "order"},
				"MOC": {"send": euro_moc_time, "cut": euro_moc_time_cut,
						"tms_venue":"ERNX ACTION PARIS Market DAY",
						"venue": "ERNX ACTION PARIS Market DAY", "trigger": False, "mode": "order"},
			},


			".AS": {
				"MOO": {"send": _sec(9,29,40), "cut": _sec(9,30,0),
						"venue": "ARCA ACTION ARCX MOO OnOpen", "trigger": False, "mode": "order"},
				"MOC": {"send": euro_moc_time, "cut": euro_moc_time_cut,
						"tms_venue":"ERNX ACTION AMSTERDAM Market DAY",
						"venue": "ERNX ACTION AMSTERDAM Market DAY", "trigger": False, "mode": "order"},
			},

			".BR": {
				"MOO": {"send": _sec(9,29,40), "cut": _sec(9,30,0),
						"venue": "ARCA ACTION ARCX MOO OnOpen", "trigger": False, "mode": "order"},
				"MOC": {"send": euro_moc_time, "cut": euro_moc_time_cut,
						"tms_venue":"ERNX ACTION BRUSSELS Market DAY",
						"venue": "ERNX ACTION BRUSSELS Market DAY", "trigger": False, "mode": "order"},
			},


			".LS": {
				"MOO": {"send": _sec(9,29,40), "cut": _sec(9,30,0),
						"venue": "ARCA ACTION ARCX MOO OnOpen", "trigger": False, "mode": "order"},
				"MOC": {"send": euro_moc_time, "cut": euro_moc_time_cut,
						"tms_venue":"ERNX ACTION LISBON Market DAY",
						"venue":"ERNX ACTION LISBON Market DAY", "trigger": False, "mode": "order"},
			},




			".CO": {
				"MOO": {"send": _sec(9,29,40), "cut": _sec(9,30,0),
						"venue": "ARCA ACTION ARCX MOO OnOpen", "trigger": False, "mode": "order"},
				"MOC": {"send": _sec(10,55,5), "cut": euro_moc_time_cut,
						"tms_venue":"NORX ACTION COPENHAGEN Market DAY",
						"venue": "NORX ACTION COPENHAGEN Market DAY", "trigger": False, "mode": "order"},
			},


			".MI": {
				"MOO": {"send": _sec(9,29,40), "cut": _sec(9,30,0),
						"venue": "ARCA ACTION ARCX MOO OnOpen", "trigger": False, "mode": "order"},
				"MOC": {"send": euro_moc_time, "cut": euro_moc_time_cut,
						"tms_venue":"MILA ACTION MILAN Market DAY",
						"venue": "MILA ACTION MILAN Market DAY", "trigger": False, "mode": "order"},
			},

			".DE": {
				"MOO": {"send": _sec(9,29,40), "cut": _sec(9,30,0),
						"venue": "ARCA ACTION ARCX MOO OnOpen", "trigger": False, "mode": "order"},
				"MOC": {"send": euro_moc_time, "cut": euro_moc_time_cut,
						"tms_venue":"XETR ACTION XETRA Market DAY",
						"venue": "XETR ACTION XETRA Market DAY", "trigger": False, "mode": "order"},
			},


			".CH": {
				"MOO": {"send": _sec(9,20,5), "cut": _sec(9,30,0),
						"venue": "ARCA ACTION ARCX MOO OnOpen", "trigger": False, "mode": "order"},
				"MOC": {"send": _sec(11,20,5), "cut": _sec(11,25,5),
						"tms_venue": "SWX ACTION Swiss Market DAY",
						"venue": "SWX ACTION Swiss Market DAY", "trigger": False, "mode": "order"},
			},

			

			".MA": {
				"MOO": {"send": _sec(9,29,40), "cut": _sec(9,30,0),
						"venue": "ARCA ACTION ARCX MOO OnOpen", "trigger": False, "mode": "order"},
				"MOC": {"send": euro_moc_time, "cut": euro_moc_time_cut,
						"tms_venue": "CBOX ACTION DXEMADRID Market DAY",
						"venue": "CBOX ACTION DXEMADRID Market DAY", "trigger": False, "mode": "order"},
			},



			".ST": {
				"MOO": {"send": _sec(9,29,40), "cut": _sec(9,30,0),
						"venue": "ARCA ACTION ARCX MOO OnOpen", "trigger": False, "mode": "order"},
				"MOC": {"send": _sec(11,25,5), "cut": _sec(11,29,5),
						"tms_venue": "NORX ACTION STOCKHOLM Market DAY",
						"venue": "NORX ACTION STOCKHOLM Market DAY", "trigger": False, "mode": "order"},
			},


			".HE": {
				"MOO": {"send": _sec(9,29,40), "cut": _sec(9,30,0),
						"venue": "ARCA ACTION ARCX MOO OnOpen", "trigger": False, "mode": "order"},
				"MOC": {"send": _sec(11,25,5), "cut": _sec(11,29,5),
						"tms_venue": "NORX ACTION HELSINKI Market DAY",
						"venue": "NORX ACTION HELSINKI Market DAY", "trigger": False, "mode": "order"},
			},


			".NO": {
				"MOO": {"send": _sec(9,29,40), "cut": _sec(9,30,0),
						"venue": "ARCA ACTION ARCX MOO OnOpen", "trigger": False, "mode": "order"},
				"MOC": {"send": _sec(10,20,5), "cut": _sec(10,25,5),
						"tms_venue": "NORX ACTION OSLO Market DAY",
						"venue": "NORX ACTION OSLO Market DAY", "trigger": False, "mode": "order"},
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


		self.gateway_order_control = self.ui.dashboard.market_panel

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



		try:
			CONNECTION_STRING = "mongodb://mongo:ZqBgzncvgHgbHapAdslyYogiUhxgYWKs@shuttle.proxy.rlwy.net:24709"

			self.db =  pymongo.MongoClient(CONNECTION_STRING)
			self.db = self.db['algorecords']

			#firestore.client(database_id="algorecords")
			message('Record Database Connected.',NOTIFICATION)
		except:
			self.db = None
			message('Record Database Unable to Connect.',NOTIFICATION)

		# --- Postgres audit log ---
		self._audit_queue = queue.Queue()
		self._audit_conn  = None
		self._connect_audit_db()

		audit_thread = threading.Thread(target=self._audit_writer_loop, daemon=True)
		audit_thread.start()




		self.ui_bus = UiBus(self.root)

		# Reuse one TCP pool; set short timeouts so workers never hang
		self.http = requests.Session()
		self.http.headers.update({"User-Agent": "GoodTrade-AMS"})
		self._READ_TIMEOUT = 0.75    # seconds
		self._CONNECT_TIMEOUT = 0.25 # seconds

		# throttle for UI pushes (avoid >10fps table redraws)
		self._last_ui_push_ts = 0.0
		self._ui_push_interval = 0.10  # seconds


	def get_fx_rule(self, key):
		return self.FX_rules.get(key)

	def submit_record(self, algo_data):
		algo_data['account'] = self.USER.get()
		algo_data['time'] = datetime.utcnow()
		env = self.ENV.get()

		try:
			# MongoDB insert (existing)
			if env != "" and len(env) > 1 and env != "DISCONNECTED":
				algo_data['env'] = env
				result = self.db[env].insert_one(algo_data)
		except Exception as e:
			message(f"Record: An error occurred while writing to MongoDB: {e}", NOTIFICATION)

		try:
			# Postgres insert (new)
			if env != "" and len(env) > 1 and env != "DISCONNECTED":
				insert_sql = """
					INSERT INTO algo_record 
						(time, account, env, algo, checkbox, symbol, share, price, realize, fees)
					VALUES 
						(%(time)s, %(account)s, %(env)s, %(algo)s, %(checkbox)s, %(symbol)s, %(share)s, %(price)s, %(realize)s, %(fees)s)
				"""

				
				#cur.execute(INSERT_SQL, record)
				# with psycopg2.connect(**DB_CONFIG) as conn:
				# 	with conn.cursor() as cur:
				with self._audit_conn.cursor() as cur:
					cur.execute(insert_sql, {
							'time': algo_data['time'],
							'account': algo_data['account'],
							'env': env,
							'algo': algo_data.get('algo'),
							'checkbox': algo_data.get('checkbox'),
							'symbol': algo_data.get('symbol'),
							'share': algo_data.get('share'),
							'price': algo_data.get('price'),
							'realize': algo_data.get('realize'),
							'fees': algo_data.get('fees', 0)
						})
					conn.commit()
		except Exception as e:
			message(f"Record: An error occurred while writing to Postgres: {e}", NOTIFICATION)

	def hello(self):

		print("HI!")

	def clerk_login(self):
		"""Kick off device-code sign-in via the goodtradeadmin website. Runs on
		a worker thread; result is marshalled back to Tk via ui_bus."""
		try:
			from clerk_auth import start_login
		except Exception as e:
			message(f"Sign-in unavailable: {e}", NOTIFICATION)
			return

		def _ok(user, display_name):
			def _apply():
				self.clerk_user_info = user
				self.CLERK_USER.set(display_name)
				message(f"Signed in as {display_name}", NOTIFICATION)
				try:
					self.ui.algo_authorization.on_signed_in()
				except Exception as e:
					message(f"Checkbox fetch hook failed: {e}", NOTIFICATION)
			self.ui_bus.post(_apply)

		def _err(exc):
			def _apply():
				self.CLERK_USER.set("Not signed in")
				message(f"Sign-in failed: {exc}", NOTIFICATION)
			self.ui_bus.post(_apply)

		def _status(text):
			self.ui_bus.post(lambda: self.CLERK_USER.set(text))

		self.CLERK_USER.set("Signing in…")
		start_login(_ok, _err, on_status=_status)

	def clerk_sign_out(self):
		"""Clear the local Clerk session. (No server-side revoke — the desktop
		never held a long-lived token.)"""
		who = self.CLERK_USER.get()
		self.clerk_user_info = None
		self.CLERK_USER.set("Not signed in")
		message(f"Signed out of {who}", NOTIFICATION)
		try:
			self.ui.algo_authorization.refresh()
		except Exception:
			pass

	# ------------------------------------------------------------------ #
	#  Postgres audit log                                                  #
	# ------------------------------------------------------------------ #

	def _connect_audit_db(self):
		"""Try to open a Postgres connection. Returns True on success."""
		try:
			self._audit_conn = psycopg2.connect(**DB_CONFIG)
			self._audit_conn.autocommit = True
			message('Audit Database Connected.', NOTIFICATION)
			return True
		except Exception as e:
			self._audit_conn = None
			message(f'Audit Database connection failed: {e}', NOTIFICATION)
			return False

	def _audit_writer_loop(self):
		"""
		Background thread: drains _audit_queue and writes rows to Postgres.
		On write failure, reconnects up to 5 times before dropping the record.
		"""
		INSERT_SQL = """
			INSERT INTO ppro_audit_log
				(timestamp, username, environment, action, intent, order_number, full_url,
				 symbol, reason, response_status, response_success, error_message)
			VALUES
				(%(timestamp)s, %(username)s, %(environment)s, %(action)s, %(intent)s, %(order_number)s, %(full_url)s,
				 %(symbol)s, %(reason)s, %(response_status)s, %(response_success)s, %(error_message)s)
		"""
		while True:
			record = self._audit_queue.get()   # blocks until something arrives
			for attempt in range(1, 6):
				try:
					if self._audit_conn is None or self._audit_conn.closed:
						if not self._connect_audit_db():
							raise ConnectionError("no connection")
					with self._audit_conn.cursor() as cur:
						cur.execute(INSERT_SQL, record)
					break  # success
				except Exception as e:
					message(f'Audit write failed (attempt {attempt}/5): {e}', NOTIFICATION)
					self._audit_conn = None
					if attempt < 5:
						time.sleep(1)
					else:
						message(f'Audit record dropped after 5 retries: {record}', NOTIFICATION)

	def submit_audit(self, action: str, full_url: str, symbol: str = None,
					 reason: dict = None, order_number: str = None, intent: str = None,
					 response_status: int = None, response_success: bool = None,
					 error_message: str = None):
		"""
		Non-blocking. Call from Symbol or anywhere — just enqueues the record.
		The writer thread handles the actual DB insert.
		"""
		record = {
			"timestamp":        datetime.now(tz=_NY),
			"username":         self.USER.get(),
			"environment":      self.ENV.get().upper(),
			"action":           action,
			"intent":           intent or "",
			"order_number":     order_number,
			"full_url":         full_url,
			"symbol":           symbol,
			"reason":           json.dumps(reason) if reason else None,
			"response_status":  response_status,
			"response_success": response_success,
			"error_message":    error_message,
		}
		self._audit_queue.put(record)

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

						user = self.USER.get()
						env = self.env
						if user+"_"+env+"_TFM" in algo_name:
							confirmation = True
							multiplier=1
							aggresive = False
							if 'aggresive' in info:
								aggresive=True
							tag = 'TFM'
						elif user+"_"+env+"_PP" in algo_name:
							confirmation = True
							multiplier=1
							aggresive = False
							if 'aggresive' in info:
								aggresive=True
							tag = 'PP'

						else: 
							confirmation,orders,aggresive,multiplier,tag = self.ui.algo_authorization.order_confirmation(algo_name,orders)

						if confirmation:
							for key in info.keys():
								if type(info[key])==int  or type(info[key])==float:
									if key!="TA":
										info[key] =info[key]*multiplier
							info['Tag'] = tag
							if aggresive:
								info['aggressive'] = True


							if self.SMARTGATE.get()!=0:
								self.root.after(0, self.gate_mode, algo_name, orders, info)
							else:
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
				info = data.get("info")
				return environment, user,info
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

		#print("Manager check pnl last period:",ts-self.last_pnl_check,"active algo:",count)

		self.last_pnl_check= ts 

		symbols = list(self.symbols.keys())
		dash_symbols = []
		for symbol in symbols:
			try:
				drow = self.symbols[symbol].update_dashboard_data()
				dash_symbols.append(drow)
			except Exception:
				pass

		tu, tr = self.get_all_unreal_real()   # totals

		# Build algo-tag view once
		dash_algos = self.build_algo_dashboard_rows()

		# throttle UI pushes
		now = time.time()
		if now - self._last_ui_push_ts >= self._ui_push_interval:
			# Paint on the Tk thread
			def _paint():
				try:
					if getattr(self.ui, "dashboard", None) and getattr(self.ui.dashboard, "symbol_panel", None):
						self.ui.dashboard.symbol_panel.set_data(
							dash_symbols,
							header_unreal=tu,
							header_real=tr,
						)
				except Exception:
					pass
				try:
					if getattr(self.ui, "dashboard", None) and getattr(self.ui.dashboard, "algo_pannel", None):
						self.ui.dashboard.algo_pannel.set_data(
							dash_algos,
							header_unreal=tu,
							header_real=tr,
						)
				except Exception:
					pass

			self.ui_bus.post(_paint)
			self._last_ui_push_ts = now
		# 2) Build symbol-level dashboard rows (one row per symbol)
		# symbols = list(self.symbols.keys())
		# dash = []
		# for symbol in symbols:
		# 	# Symbol.update_dashboard_data() returns:
		# 	# {"Symbol": "...", "Tradable": ..., "Net Pos": ..., "#Algos": ..., "Unreal": ..., "Real": ..., "Risk": ...}
		# 	drow = self.symbols[symbol].update_dashboard_data()
		# 	dash.append(drow)

		# tu, tr = self.get_all_unreal_real()   # total unreal, total real across all algos

		# # 4) Push rows + header totals into the Symbol dashboard
		# try:
		# 	if getattr(self.ui, "dashboard", None) and getattr(self.ui.dashboard, "symbol_panel", None):
		# 		self.ui.dashboard.symbol_panel.set_data(
		# 			dash,
		# 			header_unreal=tu,
		# 			header_real=tr,
		# 		)
		# except Exception:
		# 	# keep Manager resilient even if UI is not yet constructed
		# 	pass


		# dash = self.build_algo_dashboard_rows()

		# self.ui.dashboard.algo_pannel.set_data(
		# 	dash,
		# 	header_unreal=tu,
		# 	header_real=tr,
		# )
		# try:
		# 	if getattr(self.ui, "dashboard", None) and getattr(self.ui.dashboard, "algo_pannel", None):
		# 		self.ui.dashboard.algo_pannel.set_data(
		# 			dash,
		# 			header_unreal=tu,
		# 			header_real=tr,
		# 		)
		# except Exception:
		# 	# keep Manager resilient even if UI is not yet constructed
		# 	pass	

	def build_manager_snapshot_json(self):
		"""
		Return a JSON string with the 3 primary sections:
		1) aggregate symbol level
		2) aggregate algo level
		3) individual algo level
		4) KPI level 
		"""

		total_unreal = 0.0
		total_real = 0.0
		try:
			total_unreal, total_real = self.get_all_unreal_real()
			total_unreal = float(total_unreal)
			total_real = float(total_real)
		except Exception:
			pass

		algo_total = len(self.algos)
		algo_running = 0
		algo_status_breakdown = {}
		for tp in list(self.algos.values()):
			try:
				raw_status = str(tp.data.get("status", "")).strip()
			except Exception:
				raw_status = ""
			status_key = raw_status.lower() if raw_status else "unknown"
			algo_status_breakdown[status_key] = algo_status_breakdown.get(status_key, 0) + 1
			if status_key not in ("done", "rejected"):
				algo_running += 1

		kpi_level = {
			"total_unreal": total_unreal,
			"total_real": total_real,
			"algo_running": algo_running,
			"algo_total": algo_total,
			"algo_running_over_total": f"{algo_running}/{algo_total}",
			"algo_status_breakdown": algo_status_breakdown,
		}

		
		aggregate_symbol_level = []
		for symbol in list(self.symbols.keys()):
			try:
				aggregate_symbol_level.append(dict(self.symbols[symbol].update_dashboard_data()))
			except Exception:
				pass

		aggregate_algo_level = []
		try:
			aggregate_algo_level = [dict(row) for row in self.build_algo_dashboard_rows()]
		except Exception:
			aggregate_algo_level = []

		individual_algo_level = []
		for algo_name, tp in list(self.algos.items()):
			try:
				row = {
					"Algo": algo_name,
					"Tag": getattr(tp, "tag", "SYS"),
					"Type": getattr(tp, "algo_type", ""),
					"Status": tp.data.get("status", ""),
					"Unreal": float(tp.get_total_unreal()),
					"Real": float(tp.get_total_real()),
					"CurrentShares": dict(tp.data.get("current_shares", {})),
					"ExpectedShares": dict(tp.data.get("expected_shares", {})),
					"CurrentRequest": dict(tp.data.get("current_request", {})),
				}
			except Exception as e:
				row = {"Algo": algo_name, "error": str(e)}
			individual_algo_level.append(row)


			

		payload = {
			"timestamp_ny": datetime.now(tz=_NY).isoformat(),
			"environment": self.ENV.get(),
			"user": self.USER.get(),
			"info": self.info,
			"kpi_level": kpi_level,
			"aggregate_symbol_level": aggregate_symbol_level,
			"aggregate_algo_level": aggregate_algo_level,
			"individual_algo_level": individual_algo_level,
		}

		return json.dumps(payload, ensure_ascii=True)

	def send_manager_snapshot_json_to_redis(self):
		"""
		Send self.last_manager_snapshot_json to Redis.
		All Redis credentials/config are defined inside this function.
		"""
		# Embed everything in one URL, e.g.:
		# rediss://default:password@your-host:6380/0
		redis_public_url = "redis://default:GYIYIwJcOTSwOxmxUpxPziZhKHgRHjTW@nozomi.proxy.rlwy.net:15055"

		redis_channel = "goodtrade:manager_snapshot"
		user_key = str(self.USER.get() or "UNKNOWN_USER").strip()
		env_key = str(self.ENV.get() or "UNKNOWN_ENV").strip()
		redis_key = f"{user_key}_{env_key}"
		ttl_seconds = 10

		snapshot = getattr(self, "last_manager_snapshot_json", "")
		if not snapshot:
			snapshot = self.build_manager_snapshot_json()

		try:
			try:
				import redis
			except ImportError:
				import subprocess
				subprocess.check_call([sys.executable, "-m", "pip", "install", "redis"])
				import redis

			client = redis.Redis.from_url(
				redis_public_url,
				decode_responses=True,
				socket_connect_timeout=0.5,
				socket_timeout=0.5,
			)
			client.set(redis_key, snapshot, ex=ttl_seconds)
			client.publish(redis_channel, snapshot)
			return True
		except Exception as e:
			message(f"send_manager_snapshot_json_to_redis error: {e}", LOG)
			return False





	def build_algo_dashboard_rows(self):
		"""
		Aggregate per TradingPlan.tag:
		  - 'Algos'   -> tag name
		  - '#Algos'  -> count of TPs with that tag
		  - 'Unreal'  -> sum of TP.get_total_unreal()
		  - 'Real'    -> sum of TP.get_total_real()
		"""
		by_tag = {}
		for tp in list(self.algos.keys()):
			tag = getattr(self.algos[tp], "tag", "SYS")
			row = by_tag.setdefault(tag, {"Algo": tag, "#Algos": 0, "Pos":{},"Unreal": 0.0, "Real": 0.0,"Flatten":'Flat!'})
			row["#Algos"] += 1
			try:
				row["Unreal"] += float(self.algos[tp].get_total_unreal())
			except Exception:
				pass
			try:
				row["Real"]   += float(self.algos[tp].get_total_real())
			except Exception:
				pass

			try:
				## get all symbol shares.
				share = self.algos[tp].data['current_shares'].copy()
				for sym,s in share.items():
					if s!=0:
						if sym in row["Pos"]:
							row["Pos"][sym]+=s
						else:
							row["Pos"][sym]=s

				
			except Exception:
				pass

		for k in by_tag.keys():
			by_tag[k]['Pos'] = str(by_tag[k]['Pos']).replace("'","")

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

			if self.ENV.get()=="TMS":
				sym.time_to_moo('ARCA ACTION ARCX Market DAY')
			else:
				sym.time_to_moo(cfg["venue"])


			if not cfg: 
				continue
			send = int(cfg.get("send", 0)); cut = int(cfg.get("cut", 0))
			if send <= ts < cut and not cfg.get("trigger", False):
				sym.time_to_moo(cfg["venue"])

		# mark as fired once per day (be sure you already have your daily reset)
		for suffix, group in self.MKT_TIMINGS.items():
			if "MOO" in group:
				group["MOO"]["trigger"] = True

	def moc_all(self):


		now = datetime.now()
		ts = now.hour*3600 + now.minute*60 + now.second
		for sym in self.symbols.values():
			print('moc moc moc ',sym)
			suffix = sym._market_suffix()
			cfg = self.MKT_TIMINGS.get(suffix, {}).get("MOC", None)

			if self.ENV.get()=="TMS":
				sym.time_to_moc('ARCA ACTION ARCX Market DAY')
			else:
				sym.time_to_moc(cfg["venue"])


			#######
			if not cfg: 
				continue
			send = int(cfg.get("send", 0)); cut = int(cfg.get("cut", 0))
			if send <= ts < cut and not cfg.get("trigger", False):
				sym.time_to_moc(cfg["venue"])
				print('moc moc moc !',sym)
				
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
						tms_venue = entry.get("tms_venue","")
						if not triggered and send_sec <= ts < cut_sec:
							# Gather all symbols with this suffix

							message(f'{suffix} {kind} triggered.',NOTIFICATION)
							for sym_name, symbol in list(self.symbols.items()):
								if _suffix_of(sym_name) != suffix:
									continue

								if mode == "order":


									if kind =="MOO":
										if self.ENV.get()=="TMS":
											symbol.time_to_moo(tms_venue)
										else:
											symbol.time_to_moo(venue)

									elif kind =="MOC":
										if self.ENV.get()=="TMS":
											symbol.time_to_moc(tms_venue)
										else:
											symbol.time_to_moc(venue)

								# elif mode == "flatten":
								# 	# Set expected shares to 0 for this symbol across all algos that hold it
								# 	try:
								# 		for tp_name, tp in list(self.algos.items()):
								# 			if sym_name in tp.symbols:
								# 				tp.submit_expected_shares(sym_name, 0, aggresive=False)
								# 		#send flatten order for that.
								# 	except Exception as e:
								# 		print(f"scheduler flatten error {sym_name} {kind}: {e}", traceback.print_exc())

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


				
				if success:
					self.registration_required = False
					message('Register successful, inspection begins',NOTIFICATION)
					return True
				else:
					return False
			except:
				return False
		else:
			return True



	def get_current_positions(self):

		try:
			d = {}
			#p="http://127.0.0.1:8080/GetOpenPositions?user="+user
			p = "http://127.0.0.1:8080/GetOpenPositions?user="+self.USER.get()
			r= requests.get(p).json()

			try:
				regions = r["Responce"]["Content"]["Trader"]["Regions"]
			except KeyError as e:
				#print(f"Error navigating JSON structure: Missing key {e}")
				regions = []

			# 3. Iterate through each region
			for region in regions:
				# 4. Access the Positions value
				positions = region.get("Positions")

				# 5. Check if Positions is a list (not an empty string or None)
				if isinstance(positions, list):
					# 6. Iterate through each position dictionary
					for position in positions:
						symbol = position.get("Symbol")
						volume = int(position.get("Volume"))

						d[symbol] = volume #(price,share) 
			#log_print("Ppro_in:, get positions:",d)
			
			#print(d)
			for sym in list(self.symbols.keys()):
				if sym in d:
					self.symbols[sym].set_ppro_position(d[sym])
				else:
					self.symbols[sym].set_ppro_position(0)

			self.POSITION_COUNT.set(len(d))

		except Exception as e:
			pass


	def check_open_orders(self):
		try:
			r = f"""http://{self.EMS_ADDRESS}:5000/openorders/{self.USER.get()}"""

			#http://localhost:5000/openorders/QIAOSUN
			response = requests.get(r)
			data = response.json()

			success = data.get("ret", "")

			if success:
				order_count = data.get("order_count")
				dic = data.get("content") or {}

				self.OPEN_ORDER_COUNT.set(order_count)

				for sym in list(self.symbols.keys()):
					if sym in dic:
						self.symbols[sym].set_openorders(dic.get(sym, {}))
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
		if success != self.system_connected or success == False:
			if success:
				env, user,info = self.get_env()
				message(f'ENV getting success,{env},{user}', NOTIFICATION)

				def _apply_connected():
					self.USER.set(user)
					self.ENV.set(env)
					self.env = env
					self.SYSTEM_STATUS.set('CONNECTED')
					self.ui.DISCONNECTED.set(0)

				self.ui_bus.post(_apply_connected)
				self.info = info
			else:
				def _apply_disconnected():
					self.SYSTEM_STATUS.set('ERROR')
					self.USER.set('DISCONNECTED')
					self.ENV.set('DISCONNECTED')
					self.ui.DISCONNECTED.set(1)
					self.ui.flashing_red()
					self.registration_required = True

				self.ui_bus.post(_apply_disconnected)

			self.system_connected = success
		return self.system_connected
	

	def inspection_loop(self):
		consecutive_errors = 0
		while True:
			
			time.sleep(self.inspection_timer)
			try:

				if  self.get_connectivity() and self.registration() and self.DISASTER_MODE.get()!=True:

					self.check_open_orders()
					self.get_current_positions()
					for sym in list(self.symbols.values()):
						sym.symbol_inspection()  # uses real acquire/finally release


					self.check_all_pnl()
					# Keep latest snapshot JSON available for inspection/debug.
					self.last_manager_snapshot_json = self.build_manager_snapshot_json()
					self.send_manager_snapshot_json_to_redis()
					#print(f'inspection loop success, next in {self.last_manager_snapshot_json} seconds')
					#message(f'management loop',LOG)
					  # success path resets error counter
				else:
					message(f'System Disconnected. Please Check {self.get_connectivity()} {self.registration()}',NOTIFICATION)
			except Exception as e:
				consecutive_errors += 1

				time.sleep(min(0.25, 0.01 * (2 ** min(consecutive_errors, 5))))
				message(f"""Inspection error:,{e},{traceback.print_exc()}""",LOG)

				

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

		self.NO_MORE_ALGOS.set(1)
		for sym_name, symbol in list(self.algos.items()):
			symbol.a_flatten_cmd()
			
	def flatten_all(self):
		#self.NO_MORE_ALGOS.set(1)
		for sym_name, symbol in list(self.algos.items()):
			symbol.flatten_cmd()
		#####

	def flatten_algo(self,algo):

		message(f'Flattening all algos on {algo}',NOTIFICATION)
		tps = list(self.algos.keys())

		for tp in tps:
			if self.algos[tp].tag==algo:
				message(f'Flattening {tp}',NOTIFICATION)
				self.algos[tp].flatten_cmd()

	def flatten_symbol(self,symbol):


		if symbol in self.symbols:

			self.symbols[symbol].flatten_all()

			message(f'Flattening all algos on {symbol}',NOTIFICATION)

	def aflatten_symbol(self,symbol):

		if symbol in self.symbols:

			self.symbols[symbol].aflatten_all()

			message(f'A-Flattening all algos on {symbol}',NOTIFICATION)		

	def gate_mode(self,algo_name,orders,info):


		# precondition.
		# exactly 1 symbol.

		print('\n',algo_name,orders,info)

		# algo_name='BC_LCREV_BITO'
		# orders= {'BITO.AM': {'share': 0}}
		# info= {'Tag': 'BC_LCREV'}
		# algo_name='BC_RV_ORB_BAC'
		# orders= {'BAC.NY': {'share': -37}}
		# info= {'Tag': 'BC_RV_ORB'}

		if len(orders)==1 and algo_name not in self.algos:
			### SUBMIT TO IT ###
			self.ui.dashboard.smartgate.submit_and_go(algo_name,orders,info)
		else:
			self.apply_basket_cmd(algo_name,orders,info)



	def apply_basket_cmd(self,algo_name,orders,info):

		if DEBUGGING:
			print(self.source,"receiving",algo_name,orders,info)


		new_algo = False
		if algo_name not in self.algos and self.NO_MORE_ALGOS.get()==False and self.DISASTER_MODE.get()==False and self.system_connected!=False and 'MOD' not in info:

			# check 1 : make sure it's not empty init. 
			total = sum(abs(v['share']) for v in orders.values())

			if total == 0:
				# Check if 'MOO' exists in any value v
				if any('MOO' in str(v) for v in orders.values()):
					# If 'MOO' exists, we DO NOT return (we continue execution)
					pass # Or you can just leave this block empty, execution continues
				else:
					# If 'MOO' does NOT exist, and total is 0, then we return
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

		if self.DEBUG_mode.get()==1:

			for symbol,value in orders.items():
				if value['share'] >0:
					value['share'] = 1
				else:
					value['share'] = -1
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

						if 'MOO' in value:

							mooshare = value['MOO']

							self.algos[algo_name].set_moo_target(symbol,mooshare)

						if 'limit' in value:
							pass

							limit_price = value['limit']
							share = value['share']

							fx_rule = self.get_fx_rule(symbol) if symbol[-2:] == "FX" else None
							if fx_rule is not None:
								max_share_size = fx_rule["max_order_size"]
							else:
								max_share_size = self.ui.dashboard.risk_panel.effective_global("max_algo_size")
							try:
								max_share_size = int(max_share_size)
							except Exception:
								max_share_size = 0
							if max_share_size > 0:
								share_abs = min(abs(int(share)), max_share_size)
								share = share_abs if share >= 0 else -share_abs
								message(f"Applying max_algo_size limit: {share} shares for {symbol} (requested {value['share']})", NOTIFICATION)
							self.algos[algo_name].submit_limit_request(symbol,share,limit_price)

						else:
							share = value['share']
							fx_rule = self.get_fx_rule(symbol) if symbol[-2:] == "FX" else None
							if fx_rule is not None:
								max_share_size = fx_rule["max_order_size"]
							else:
								max_share_size = self.ui.dashboard.risk_panel.effective_global("max_algo_size")
							try:
								max_share_size = int(max_share_size)
							except Exception:
								max_share_size = 0
							if max_share_size > 0:
								share_abs = min(abs(int(share)), max_share_size)
								share = share_abs if share >= 0 else -share_abs
								message(f"Applying max_algo_size limit: {share} shares for {symbol} (requested {value['share']})", NOTIFICATION)
							if 'aggressive' in info:
								aggressive = True
							else:
								aggressive = False 
							self.algos[algo_name].submit_expected_shares(symbol,share,aggressive)

				#### ALSO REIGSITER HEDGE

					if 'hedge' in info:
						for symbol in info['hedge'].keys():

							if symbol not in orders:

								if symbol not in self.symbols:
									self.symbols[symbol] = Symbol(self,symbol)
								self.algos[algo_name].register_symbol(symbol,self.symbols[symbol])

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

# force_close_port(4440)
# # force_close_port(5000)

# EMS_ADDRESS = "127.0.0.1"
# #EMS_ADDRESS = "10.29.10.137"

# root = tb.Window(themename="flatly") # Start with a light theme
# root.title("GoodTrade AMS 02-09")

# screen_width = root.winfo_screenwidth()
# screen_height = root.winfo_screenheight()
	
# root.geometry("1870x1280")



# m = Manager(root,EMS_ADDRESS)

# message("System Initialized",NOTIFICATION)
# root.mainloop()

# message('System Terminated',LOG)

# current_system_pid = os.getpid()

# ThisSystem = psutil.Process(current_system_pid)
# ThisSystem.terminate()
# os._exit(1)

# print('HI')




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

