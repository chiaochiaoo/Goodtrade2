from datetime import datetime
import linecache
import sys
import os
from datetime import datetime, timedelta
import pandas as pd
import numpy as np
import tkinter as tk
import traceback
import socket
import time
import requests
import json
import threading

import xml.etree.ElementTree as ET

from psutil import process_iter
import psutil

from logging_module import *

from flask import Flask



class Manager:

	def __init__(self,ui_root,ems):

		self.root = ui_root 
		self.ems_enabled = ems

		# GLOBAL BOOLEAN #

		self.system_connected = False 

		self.SYSTEM_STATUS = tk.StringVar(value="")

		self.USER = tk.StringVar(value='')
		self.ENV = tk.StringVar(value='')

		self.POSITION_COUNT = tk.IntVar(value=0)
		self.ORDER_COUNT = tk.IntVar(value=0)
		self.TEST_MODE = tk.IntVar(value=0) 
		self.DISASTER_MODE = tk.IntVar(value=0)


		self.TOTAL_ALGO_COUNT = tk.IntVar(value=0)
		self.ACTIVE_ALGO_COUNT = tk.IntVar(value=0)
		self.PROACTIVE_ALGO_COUNT = tk.IntVar(value=0)
		self.DISPLAY_ALGO_COUNT = tk.IntVar(value=0)
		
		# CORE DATA # 

		self.symbols ={}


		self.user = ""
	
		self.positions ={}
		self.open_orders = {}


		self.lock = threading.Lock()

		### UI part ###

		self.ui = None


		### WAIT FOR UI TO FULLY INSTANTIATE ###
		while True:

			try:
				self.root.after(0, lambda: None)
				break
			except RuntimeError:
				time.sleep(3)


	### EMS PART ###

	def get_connectivity(self):
		env, user = self.get_env()

		connected = True
		if env==None:
			connected=False

		if connected != self.system_connected:
			if connected:
				self.USER.set(user)
				self.ENV.set(env)
			else:
				self.USER.set('DISCONNECTED')
				self.ENV.set('DISCONNECTED')
			self.system_connected = connected

		return self.system_connected

	def get_env(self):
		try:
			r = 'http://127.0.0.1:5000/getuser'
			response = requests.get(r, timeout=0.25)
			data = response.json()

			success = resp.get("ret", "").lower() == "true"

			if sucess:
				environment = data.get("Environment")
				user = data.get("User")
				return environment, user
		except:
			pass
		return None, None

	def inspection_loop(self):

		while True:
			try:

				if self.get_connectivity():


					keys =  list(self.symbols.keys())

					for symbol in keys:
						self.symbols[symbol].sysmbol_inspection()

						# if symbol in self.symbols:
						# 	self.symbols[symbol].update_data()

						# 	if symbol in self.open_orders:
						# 		self.symbols[symbol].update_orderbook(self.open_orders[symbol])
						# 	else:
						# 		self.symbols[symbol].update_orderbook({})

							
			except Exception as e:
				PrintException("Inspection error:")

			time.sleep(self.inspection_timer)
