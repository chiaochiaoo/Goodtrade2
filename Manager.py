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

from flask import Flask

from Symbol import *
from TradingPlan import *
from ui_main import *

DEBUGGING = True 

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


		# GLOBAL BOOLEAN #

		self.system_connected = False

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

		#if self.root !=None:
		self.ui = UI(self.root,self)
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



	### EMS PART ###

	def get_connectivity(self):

		try:
			r = f'http://{self.EMS_ADDRESS}:5000/connection'
			response = requests.get(r,timeout=0.25)
			data = response.json()

			success = data.get("ret", "")

		except Exception as e:
			#print(e)
			success = False

		if success != self.system_connected and len(self.USER.get())<=2:

			if success:
				env,user = self.get_env()

				print('ENV getting success',env,user)
				self.USER.set(user)
				self.ENV.set(env)
				self.SYSTEM_STATUS.set('CONNECTED')
			else:
				self.SYSTEM_STATUS.set('ERROR')
				self.USER.set('DISCONNECTED')
				self.ENV.set('DISCONNECTED')
			self.system_connected = success

		return self.system_connected

	def get_env(self):
		try:
			r = f'http://{self.EMS_ADDRESS}:5000/getuser'
			response = requests.get(r,timeout=0.25)
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

		# self.ui.active_algo_count_number.set(count)

		now = datetime.now()
		ts = now.hour*3600 + now.minute*60 + now.second

		print("Manager check pnl last period:",ts-self.last_pnl_check,"active algo:",count)

		self.last_pnl_check= ts 

	def inspection_loop(self):


		r = f'http://{self.EMS_ADDRESS}:5000/register'
		response = requests.get(r,timeout=0.25)
		data = response.json()

		success = data.get("ret", "")

		#print(data)

		if success:
			print('register succesful, inspection begins')

		while True:

			
			time.sleep(self.inspection_timer)
			try:

				if self.get_connectivity():



					keys =  list(self.symbols.keys())


					if DEBUGGING:
						print(self.source,"inspecting:",keys)
					for symbol in keys:
						self.symbols[symbol].sysmbol_inspection()

						# if symbol in self.symbols:
						# 	self.symbols[symbol].update_data()

						# 	if symbol in self.open_orders:
						# 		self.symbols[symbol].update_orderbook(self.open_orders[symbol])
						# 	else:
						# 		self.symbols[symbol].update_orderbook({})

					self.check_all_pnl()
			except Exception as e:
				print("Inspection error:",e,traceback.print_exc())

	def get_l1_regisration(self):


		self.symbols_registration = []
		r = 'http://127.0.0.1:8080/GetL1Registrations?'
		response = requests.get(r,timeout=0.25)
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
			response = requests.get(r,timeout=0.25)
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

	def apply_basket_cmd(self,algo_name,orders,info):

		if DEBUGGING:
			print(self.source,"receiving",algo_name,orders,info)
		if algo_name not in self.algos:

			# check 1 : make sure it's not empty init. 
			for j,i in orders.items():

				if i!=0:
					check = True 
					break

			# init the Trading plans 

			self.algos[algo_name] = TradingPlan(self,algo_name,info)

			if DEBUGGING:
				print(self.source,f'initializing {algo_name}')

			# init the UI needed 

			if self.ui!=None:
				pass

		if algo_name in self.algos:

			print(f'{self.source} checking {algo_name} and {self.algos[algo_name].shutdown}')

			if self.algos[algo_name].shutdown!=True:

				for symbol,value in orders.items():


					print(self.source,f'checking {symbol}')
					symbol_check = False 

					if symbol not in self.symbols:

						if self.check_symbol(symbol):
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
						else:
							share = value['share']
							if 'aggressive' in value:
								aggressive = True
							else:
								aggressive = False 
							self.algos[algo_name].submit_expected_shares(symbol,share,aggressive)






EMS_ADDRESS = "127.0.0.1"
#EMS_ADDRESS = "10.29.10.137"

root = tb.Window(themename="flatly") # Start with a light theme
root.title("GoodTrade AMS")

screen_width = root.winfo_screenwidth()
screen_height = root.winfo_screenheight()

root.geometry("1770x1280")

# app = UI(root)
# root.protocol("WM_DELETE_WINDOW", app._on_closing)



m = Manager(root,EMS_ADDRESS)
root.mainloop()


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

