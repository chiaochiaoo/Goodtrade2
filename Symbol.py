import tkinter as tk
import requests
import threading
from datetime import datetime
from constants import *
import time
import traceback
from TradingPlan import *

DEBUGGING = True 


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


		self.tradingplans = {}
		self.central_dispatching_order_request = {}

		self.order_out = False
		self.order_pid = ""
		self.order_id = ""


		self.adjustment_holding = 0 
		##################
		self.rejections = []



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

	def register_tradingplan(self,algoname,tradingplan):

		self.tradingplans[algoname] = tradingplan

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

	def sysmbol_inspection(self):


		# step 0 update l1 infos.

		## if have more than 0. 

		if not self.inspection_lock.locked():

			now = datetime.now()

			ts = now.hour*3600 + now.minute*60 + now.second



			if DEBUGGING:
				print(self.symbol_name, 'inspection begins, tradable:',self.data['tradable'])
			if self.data['tradable'] == False:
				self.l1_update_module()
			if self.data['tradable'] == True:

				### Check if there exist a moudule				
				# if self.data['active_algo_count']>0:
				# 	self.l1_update_module()
				# else:
				# 	# nothing to inspect really. 
				# 	return 1

				# step 1 Order Checking (4) check the status of each order of tp..

				self.check_phase()

				if DEBUGGING:
					print(self.symbol_name,'complete inspection phase 1')


				# step 2 update the FSM of each TP. (move forward the TP plans) 

				# step 3 Distribution Phase of CD (5) 

				# step 4 Status check (6)

				# step 5 Aggragate Dispatching (1)



				self.aggragate_phase()




				# step 6 Ordering 

				if self.request!=0 and self.manager.open_order_check==True and ts<=57540 and self.datakey['tradable']:
					return self.ordering_phase()
			return 0
				#####   ORDERING PHASE   #####
		else:
			print(self.symbol_name,"Inspection LOCKED")
			return 0 
	### IDEALLY, move this to the ems. any symbol have a position on it should have update anyway. 

######################################## PHASE 1 check_phase  ###########################################

	def check_phase(self):

		### THERE IS REQUEST, order out.

		### THERE IS REQUEST, no order

		### THERE IS REQUEST, order fill

		### THERE IS REQUEST, order partially fill.

		### THERE IS NO REQUEST (anymore),order out.

		### THERE IS CHAGING REQUEST , order filled


		if self.order_out:
			if self.order_id=='':
				self.look_up_orderid()


			if self.order_id=='':
				print(WARNING,self.symbol_name,'Cannot locate order id.')




######################################## PHASE 5 aggragate_phase ########################################

	def aggragate_phase(self):

		#self.tp_current_shares,self.expired,self.tp_total_current_shares = self.get_all_current(tps)

		tps = list(self.tradingplans.keys())
		self.central_dispatching_order_request= {}

		self.tp_current_shares = self.get_all_current(tps)
		self.expected = self.get_all_expected(tps)
		
		self.request =  self.expected - self.tp_current_shares


		#if DEBUG_MODE:

		if DEBUGGING:
			print(self.source,self.symbol_name, "have",self.tp_current_shares," want",self.expected," request",self.request,self.central_dispatching_order_request)

	def get_all_expected(self,tps):

		"""
		Doesnt matter if the TP is running or not, having request or not. it runs through. 
		The less the parameter, the more generalizability 
		"""

		self.expected = 0
		
		for tp in tps:
			### ONLY IF TP is inspectable. 

			if DEBUGGING:
				print(self.tradingplans[tp].data)
			self.expected +=  self.tradingplans[tp].get_current_expected(self.symbol_name)

			self.central_dispatching_order_request[tp] = self.tradingplans[tp].get_current_request(self.symbol_name)
		return self.expected

	def get_all_current(self,tps):

		# note, can we skip checking epired stuff. move this process to ordering process.
		current_shares=0
		for tp in tps:
			current_shares +=  self.tradingplans[tp].get_current_share(self.symbol_name)
				
		return current_shares

		# current_shares = 0
		# total_current_shares = 0
		# expired =0
		# now = datetime.now()

		# ts = now.hour*3600 + now.minute*60 + now.second

		# # if within 5 cents. below 1 $. 

		# ### depending on the spread. 

		# if self.data['SPREAD']>0.1:
		#     self.fill_timer = 60 

		# if self.data['SPREAD']<0.05:
		#     self.fill_timer = 30 

		# if self.data['SPREAD']<0.03:
		#     self.fill_timer = 20

		# if now.hour*60+now.minute<575 or now.hour*60+now.minute>950:
		#     self.fill_timer = 10

		# cur_time = 0

		# for tp in tps:
		#     if self.tradingplans[tp].get_inspectable():
		#         current_shares +=  self.tradingplans[tp].get_current_share(self.symbol_name)
				
		#         if self.tradingplans[tp].get_request_time(self.symbol_name)>cur_time:
		#             cur_time = self.tradingplans[tp].get_request_time(self.symbol_name)

		#         if ts-self.tradingplans[tp].get_request_time(self.symbol_name)>self.fill_timer:
		#             expired+=self.tradingplans[tp].get_current_request(self.symbol_name)

		#     total_current_shares += self.tradingplans[tp].get_current_share(self.symbol_name)

		# self.fill_time_remianing = round((ts-cur_time)/self.fill_timer,2)

		# self.fill_time_remianing = min(self.fill_time_remianing,1)


		# return current_shares,expired,total_current_shares

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

		self.recent_rejection_check()

		if self.rejection_counts>=2:
			log_print(self.source,self.symbol_name," too much recent rejection detected. wait 1.")
			return 0

		# if self.market_out!=0:
		# 	self.market_out = 0
		# 	log_print(self.source,self.symbol_name, " just marked out. wait 1. skipping passive management")
		# 	return 0
		now = datetime.now()
		ts = now.hour*3600 + now.minute*60 + now.second

		self.l1_update_module()
		
		if self.request>0:
			self.action = BUY
		else:
			self.action = SELL


		# adjust the price. 
		
		offset=0.05

		################################

		## send orders. get id .##

		venue = self.get_venue()
		req = f'http://127.0.0.1:8080/ExecuteOrder?symbol={self.symbol_name}&limitprice=0.01&priceadjust={str(offset)}&ordername={venue}&shares={str(abs(self.request))}'

		
		r = requests.get(req,timeout=0.25)

		data = r.json()
		resp = data.get("Responce", {})
		success = resp.get("Success", "").lower() == "true"
		print('success?',success)
		if success:
			self.order_pid = resp.get("Content", "")
			self.order_id =''
			if len(self.order_pid)>0:
				self.order_out=True

			return 1 
		else:
			print(self.source,self.symbol_name,"Ordering sending failed.",req)
			return 0

		## look up and get the id now?



### EMS API PART ####

	def look_up_orderid(self):


		if self.order_pid!="":

			req = f'http://127.0.0.1:5000/papi/{self.order_pid}'
			r = requests.get(req,timeout=0.25)

			data=r.json()
			if data['ret']=='true':
				self.order_id = data['order']

			else:
				self.order_id = ''


	def look_up_order(self):

		if self.order_id!="":
			req = f'http://127.0.0.1:5000/order/{self.order_id}'
			r = requests.get(req,timeout=0.25)

			data=r.json()
			if data['ret']=='true':
				self.order_id = data['order']

			else:
				self.order_id = ''

### REJECTION HANDLING MOUDULE ####

	def recent_rejection_check(self):
		now = datetime.now()
		timestamp = now.hour*60 + now.minute 
		
		self.rejection_counts =  sum(1 for num in self.rejections if num > timestamp-2)

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

	def l1_update_module(self):

		### tell the system if there is any bid ask changes since last time.

		try:
			postbody = "http://127.0.0.1:8080/GetLv1?symbol=" + self.symbol_name 

			r= requests.get(postbody)
			data = r.json()
			resp = data.get("Responce", {})
			success = resp.get("Success", "").lower() == "true"
			
			if success:
				stream_data = resp.get("Content", "")

				bid = float(stream_data['BidPrice']) #float(find_between(stream_data, "BidPrice=\"", "\""))
				ask = float(stream_data['AskPrice']) #float(find_between(stream_data, "AskPrice=\"", "\""))
				ts = stream_data['MarketTime'] # find_between(stream_data, "MarketTime=\"", "\"")
				state = stream_data['InstrumentState'] # find_between(stream_data,"InstrumentState=\"", "\"") 

				if state =="Open":
					self.data['tradable']=True
				else:
					self.data['tradable']=False 
					print(self.symbol_name,"State:",state,self.data['tradable'])

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
				self.data['timestamp'] = ts

				if DEBUGGING:
					print(self.symbol_name,"SPREAD:",self.data['spread'],self.data['bid'],self.bid_change,self.data['ask'],self.ask_change)
			else:
				raise RuntimeError()
			return 
		except Exception as e:

			print(self.symbol_name,"Init L1 Update",e,traceback.print_exc())

			self.ask_change = True 
			self.bid_change = True 

if __name__ == "__main__":
	root = tk.Tk()

	#parakeys = {'1':'a','b':1,}

	#print({*parakeys})
	s = Symbol(None,"AMD.NQ")
	s.print_all_data()

	s.request=10

	c=0
	while True:

		s.sysmbol_inspection()

		c+=1
		time.sleep(3)
	#s.ordering_phase()
