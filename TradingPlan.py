import tkinter as tk
from datetime import datetime, timedelta
from logging_module import *

REALIZED = 'realized'
UNREAL = 'unreal'

DEBUGGING = False 


IDLE = 'IDLE'
ORDERING = 'ORDERING'
RUNNING = 'RUNNING'
FLATTENING = 'FLATTENING'
DONE = 'DONE'
REJECTED = 'REJECTED'


MOC ='MOC'
MOO ='MOO'


REG = 'REG' # no limit.
LMT = 'LMT' # have only limit orders in.
MOO = 'MOO' # have moo in
HDG = 'R-HDG' # have limit and mix. Mutiplierable. AUTO NBBO ONLY.
LHDG = 'L-HDG' # Limit -> Trigger. Not multiplierable.

class TradingPlan:
	def __init__(self,manager,algo_name,info={}):

		self.manager = manager
		self.source = "TP"
		self.source2 = 'Algo'
		self.algo_name = algo_name
		self.algo_type = ""

		self.nbbo_only = False 



		self.tradable = True

		self.shutdown = False 
		## INTERNAL DATA ##

		## UI RELATED DATA ##

		self.symbols ={}

		self.tkvars = {}
		self.data = {}

		### PART FOR CENTRAL DISPACH ###
		# self.expected_shares = {}
		# self.current_shares = {}
		# self.current_request = {}

		self.current_request_timer = {}
		# self.original_positions = {}

		self.current_exposure = {}
		self.average_price = {}
		#################################

		self.banned = []


		self.data[REALIZED] = 0
		self.data[UNREAL] = 0 

		self.data['limit_request'] = {}
		self.data['moo_request'] = {}
		self.data['hedge_request'] = {}
		

		self.data['expected_shares'] = {}  
		self.data['current_shares'] = {} 
		self.data['current_request'] = {}  


		self.data['moo_targets'] = {}
		self.data['symbol_freeze'] = {}

		self.data['unreal_by_symbol'] = {}  
		self.data['real_by_symbol'] = {}  


		self.data['algo_total_shares'] = 0
		self.data['algo_total_request'] =0

		self.data['multiplier'] = 1
		self.data['status'] = IDLE

		self.data['flatten_order'] = False
		self.data['rejected_stop'] = False


		#self.data['nbbo_only'] = False
		self.data['clone_dict'] = {}
		self.ui_component = None

		self.info = info


		if 'Timer' not in self.info:
			self.info['timer'] = 999

		if 'clone' not in info:
			self.clone_number = 0
		else:
			self.clone_number = info['clone']


		if 'Stop' in self.info:
			self.stop = int(self.info['Stop'])
		else:
			self.stop = 0

		if 'Profit' in self.info:
			self.profit = int(self.info['Profit'])
		else:
			self.profit = 0

		self.profit_trail_activated = False
		self.profit_trail = 0

		self.break_even= False
		self.break_even_amount = 100000000

		if "Breakeven" in info:
			self.break_even_amount = int(abs(info["Breakeven"]))

		if "Tag" in info:
			self.tag = info['Tag']
		else:
			self.tag = "SYS"


	def tradingplan_classification(self):

		## This is called once. and that's it .
		# REG = 'REG' # no limit.
		# LMT = 'LMT' # have only limit orders in.
		# MOO = 'MOO' # have moo in
		# HDG = 'HDG' # have limit and mix.


		lr = self.data.get('limit_request', {}) or {}
		mr = self.data.get('moo_request', {}) or {}
		hr = self.data.get('hedge_request', {}) or {}

		# --- helpers to decide "has stuff" ---
		def _limit_has_stuff() -> bool:
			for sym, node in lr.items():
				if not isinstance(node, dict):
					continue
				if node.get('shares') or node.get('status') or node.get('oid') or node.get('target_price'):
					return True
			return False

		def _dict_has_stuff(d: dict) -> bool:
			# consider non-zero numeric or any truthy value as "stuff"
			for _k, v in d.items():
				if isinstance(v, (int, float)):
					if v != 0:
						return True
				elif v:  # any truthy structure/value
					return True
			return False

		has_limit = _limit_has_stuff()
		has_moo   = _dict_has_stuff(mr)
		has_hedge = _dict_has_stuff(hr)

		# ---- apply your simple precedence rules ----
		# 4) limit + hedge => HDG
		if has_limit and has_hedge:
			self.algo_type = HDG
			return self.algo_type

		# 3) any MOO => MOO
		if has_moo and not has_hedge:
			self.algo_type = MOO
			return self.algo_type

		# 2) limit only => LMT
		if has_limit and not has_moo and not has_hedge:
			# (Optional) your rule about expected_shares being only that symbol and == 0 is ambiguous;
			# keeping it minimal as requested: if limit present (and no moo/hedge), call it LMT.
			self.algo_type = LMT
			return self.algo_type

		# 1) nothing => REG
		self.algo_type = REG


		return self.algo_type


	def register_symbol(self,symbol_name,symbol):

		if symbol_name not in self.symbols:

			self.symbols[symbol_name] = symbol
			self.symbols[symbol_name].register_tradingplan(self.algo_name,self)

			self.data['expected_shares'][symbol_name] = 0
			self.data['current_shares'][symbol_name] = 0
			self.data['current_request'][symbol_name] = 0
			self.data['moo_targets'][symbol_name] = 0
			self.data['unreal_by_symbol'][symbol_name] = 0
			self.data['real_by_symbol'][symbol_name] = 0 

			self.data['symbol_freeze'][symbol_name] = 0


			self.init_limit_request(symbol_name)
			#self.data['limit_request'][symbol_name] = {'order_out':False,'status':'','pid':'','oid':'','tgt_price':'','order_price':''}

			self.current_request_timer[symbol_name] = 0
			self.current_exposure[symbol_name] = []
			self.average_price[symbol_name] = 0

	def set_moo_target(self, symbol: str, shares: int):
		"""Declare where this TP wants the symbol to be *after* the open."""
		self.data['moo_targets'][symbol] = int(shares)

	def get_moo_target(self, symbol: str) -> int:
		"""Return this TP's MOO target for the symbol (0 if none)."""
		return int(self.data['moo_targets'].get(symbol, 0))

	def freeze_symbol(self,symbol:str):
		self.data['symbol_freeze'][symbol] = True

	def unfreeze_symbol(self,symbol:str):
		self.data['symbol_freeze'][symbol] = False
		
	def get_nbbo_only(self):

		return self.nbbo_only
	def status_check(self):

		# ###
		# IDLE = 'IDLE'
		# ODERING = 'ORDERING'
		# RUNNING = 'RUNNING'
		# FLATTENING = ' FLATTENING'
		# DONE = 'DONE'
		# REJECTED = 'REJECTED'
		# ###

		shares   = self.data['algo_total_shares']
		request  = self.data['algo_total_request']
		flatten  = bool(self.data.get("flatten_order"))
		rejected = bool(self.data.get("rejected_stop"))

		if rejected:
			self.data["status"] = REJECTED
		elif flatten:
			if shares == 0:
				self.data["status"] = DONE
			else:
				self.data["status"] = FLATTENING
		else:
			if shares == 0 and request == 0:
				self.data["status"] = IDLE
			elif abs(request) > 0:                 # covers shares==0 or shares>0 while new orders pending
				self.data["status"] = ORDERING
			else:                              # shares != 0 and no new requests
				self.data["status"] = RUNNING

		# debugging_line = f'{self.source},{symbol} :{self.source2} :{self.algo_name}, status_check()'
		# if DEBUGGING:

		# 	print(debugging_line,f'{shares},{request},{flatten},{rejected}')
				
		# if self.data['flatten_order']==True:

		#     if self.algo_total_shares == 0:
		#         self.data['status'] = DONE

		#     if self.data['rejected_stop']:
		#         self.data['status'] = REJECTED


		#     if self.algo_total_shares!= 0 :
		#         self.data['status'] = FLATTENING


		# else:

		#     if self.algo_total_shares==0:
		#         self.data['status'] = IDLE
		#     if self.algo_total_request !=0:
		#         self.data['status'] = ORDERING

		#     if self.algo_total_shares!=0 and self.algo_total_request==0:
		#         self.data['status'] = RUNNING


	def set_ui(self,ui):

		self.ui_component = ui


	def get_algo_status(self):

		self.status_check()

		return self.data['status'] in [REJECTED,DONE,IDLE]

	def a_flatten_cmd(self):

		self.flatten_cmd(1)

	def flatten_cmd(self,aggresive=0):

		for symbol,item in self.symbols.items():
			self.submit_expected_shares(symbol,0,aggresive)
			self.recalculate_current_request(symbol)
			self.data['multiplier'] = 0

		self.clear_all_limit()

		self.data['flatten_order']=True
		self.data['status'] = FLATTENING

	def get_unreal(self,symbol):
		return self.data['unreal_by_symbol'][symbol]
	def get_real(self,symbol):
		return self.data['real_by_symbol'][symbol]

	def get_total_unreal(self):
		return self.data[UNREAL]

	def get_total_real(self):
		return self.data[REALIZED]
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

		self.data['status'] = REJECTED
		self.data['rejected_stop'] = True


		message([f'{self.algo_name} rejected. click to retry',self.create_clone],CLIKABLE)

	def calculate_avg_price(self,symbol):

		if self.data['current_shares'][symbol]!=0:
			self.average_price[symbol] = sum(self.current_exposure[symbol])/self.data['current_shares'][symbol]

	def holding_update(self,symbol,share_added,price):

		"""
		update PNL structures.
		"""

		if share_added<0:
			price=price*-1


		symbol_realize =0 

		for i in range(abs(share_added)):

			if len(self.current_exposure[symbol])==0:
				self.current_exposure[symbol].append(price)

			elif self.current_exposure[symbol][-1]*price >0: #same side.
				self.current_exposure[symbol].append(price)

			elif self.current_exposure[symbol][-1]*price <0:

				symbol_realize+= -1*price - self.current_exposure[symbol].pop()
				
				#self.manager.new_record(self)
			else:
				#this is the senario where price is 0.
				print("HOLDING UPDATE ERROR",symbol,share_added,price)

		self.data[REALIZED] += symbol_realize
		self.data['real_by_symbol'][symbol] += round(symbol_realize,2)

		message(f"""Tp: {self.algo_name} realized {symbol} {self.data['real_by_symbol'][symbol]}""",LOG)
		self.data[REALIZED] = round(self.data[REALIZED],2)
		#self.sync_all()



	def request_fufill(self,symbol,share,price):

		preq = self.data['current_request'][symbol]
		debugging_line = f'{self.source},{symbol} :{self.source2} :{self.algo_name}, request_fulfill()'
		self.data['current_shares'][symbol] = self.data['current_shares'].get(symbol, 0) + share


		self.data['algo_total_shares'] = sum(self.data['current_shares'].values())
		
		self.holding_update(symbol,share,price)
		self.calculate_avg_price(symbol)
		self.recalculate_current_request(symbol)

		req = self.data['current_request'][symbol]
		if DEBUGGING:
			print(debugging_line,f'incoming shares {share} @ {price}. now request {req} prev {preq}')


		self.status_check()

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
					u = ((bid - self.average_price[symbol])) * abs(self.data['current_shares'][symbol])  
					total_unreal +=  u
					check[symbol] = [bid,self.average_price[symbol],self.data['current_shares'][symbol],((bid - self.average_price[symbol])) * abs(self.data['current_shares'][symbol])]

					# if ".TO" in symbol:
					#   log_print(self.algo_name,symbol,"avg price",self.average_price[symbol],"cur price",cur_stock_price,"share",val,"result", (cur_stock_price - self.average_price[symbol]) * abs(self.current_shares[symbol]))
				else:
					cur_stock_price = self.symbols[symbol].get_price()
					u =  ((self.average_price[symbol] - ask)) * abs(self.data['current_shares'][symbol])
					total_unreal += u
					check[symbol] = [ask,self.average_price[symbol],self.data['current_shares'][symbol],((self.average_price[symbol] - ask)) * abs(self.data['current_shares'][symbol])]
					
					# if ".TO" in symbol

				self.data['unreal_by_symbol'][symbol] = u


		self.data[UNREAL] = round(total_unreal,2)

		self.status_check()
		#self.refresh_ui_component()


		if self.stop!=0 and self.data['flatten_order']!=True and ts<=950:
			if total_unreal*-1 >= self.stop:
				message(f"""{self.source}:{self.algo_name}, " MEET STOP ",{self.stop} {self.break_even}""",LOG)
				self.a_flatten_cmd()

		if self.profit!=0 and self.data['flatten_order']!=True and ts<=950:

			if self.data[UNREAL]+self.data[REALIZED] >=  self.profit and self.profit_trail_activated==False:
				message(f"""{self.source}:{self.algo_name}, " MEET PROFIT ",{self.profit}""",LOG)

				self.profit_trail_activated = True
				# self.break_even = True

				# ## init. 

				# self.break_even = 0
				self.profit_trail = self.data[UNREAL]+self.data[REALIZED] - self.profit*0.5

				#self.flatten_cmd()

				self.break_even_function()

				self.change_percentage(-0.5)

				##upgrade the trail, hit the trail, upgrade the breakeven, hit the breakeven.
			elif self.profit_trail_activated==True:


				if self.data[UNREAL]+self.data[REALIZED] - self.profit*0.5>self.profit_trail:
					self.profit_trail =  self.data[UNREAL]+self.data[REALIZED] - self.profit*0.5

				elif self.data[UNREAL]+self.data[REALIZED]<self.profit_trail:

					self.flatten_cmd()
					message(f"""{self.source}:{self.algo_name}, " MEET TRAILING STOP ",{self.profit_trail}""",LOG)



	def refresh_ui_component(self):


		if self.ui_component!=None:

			#algo_name, new_status=None, new_unreal=None, new_real=None,multiplier
			algo_name = self.algo_name
			new_status = self.data['status']
			unreal = self.data[UNREAL]
			real = self.data[REALIZED]
			mult = self.data['multiplier']

			profit = self.profit
			stop = self.stop

			pr = self.profit_trail

			#position = str(self.data['current_shares'])
			info = {}
			for symbol in self.data['current_shares'].keys():
				info[symbol] = str(self.data['current_shares'][symbol])+"->"

			for symbol in self.data['current_shares'].keys():
				info[symbol] += str(self.data['expected_shares'][symbol])+" | "

			for symbol in self.data['current_shares'].keys():
				info[symbol] += str(self.data['clone_dict'][symbol]['share'])

			position = str(info).replace("'", "")
			if profit!=0:
				position += f' P:{profit}'
			if stop!=0:
				position += f' S:{stop}'

			if pr!=0:
				position += f' T:{pr}'
			self.ui_component.algo_deployment.modify_algo_values(self.algo_name,self.algo_type,new_status,unreal,real,mult,position)
######################################################################################################

	def print_info(self,val=''):

		print("=== Data & Tk Variables ===",val,self.algo_name,self.algo_type)
		for key in self.data:
			primitive = self.data[key]
			print(f"{key:<12} | data: {primitive!r:<10} ")

		print("===========================")

	def print_all_data(self):
		print("=== Data & Tk Variables ===")
		for key in self.data:
			primitive = self.data[key]
			tkvar = self.tkvars.get(key)
			tk_type = type(tkvar).__name__ if tkvar else "None"
			tk_value = tkvar.get() if tkvar else "N/A"
			print(f"{key:<12} | data: {primitive!r:<10} | tkvar: {tk_type:<12} = {tk_value!r}")
		print("===========================")

	def recalculate_current_request(self,symbol,agg=False):
		diff = self.data['expected_shares'][symbol] - self.data['current_shares'][symbol]
		if self.data['current_request'][symbol]!=diff:
			now = datetime.now()
			ts = now.hour*3600 + now.minute*60+ now.second
			self.data['current_request'][symbol] = diff

			if agg:
				self.current_request_timer[symbol] = 0
			else:
				self.current_request_timer[symbol] = ts

			self.data['algo_total_request'] = sum(self.data['current_request'].values())

			message(f"""TP:{self.algo_name} new request: {symbol} {self.data['current_shares'][symbol]}->{self.data['expected_shares'][symbol]}:{diff} @ {ts} """,LOG)

	def get_request_time(self,symbol):

		return self.current_request_timer[symbol] 


	def break_even_function(self):


		if self.data[UNREAL]>3:
			self.break_even = True 
			self.stop = 0.1

	def change_percentage(self,p):

		if self.data['flatten_order']!=True:
			if p<0 and self.data['multiplier']<=abs(p):
				self.data['multiplier'] =0
				self.flatten_cmd()
			else:
				self.data['multiplier'] += p
				self.data['multiplier'] = round(self.data['multiplier'],2)


				self.break_even_function()

				for symbol,item in self.symbols.items():
					if symbol in self.data['clone_dict']:

						mult = self.data['multiplier']

						shares = int(self.data['clone_dict'][symbol]['share']*mult)

						self.submit_expected_shares(symbol,shares,0)
						# if self.expected_shares[symbol]!=0:
						# 	if abs(self.expected_shares[symbol])<=abs(self.original_positions[symbol]//coefficient): # set to 0
						# 		self.submit_expected_shares(symbol,0,1)
						# 	else:
						# 		self.submit_expected_shares(symbol,self.expected_shares[symbol]-self.original_positions[symbol]//coefficient,1)


				message(f"""TP:{self.algo_name} adjust multiplier {mult} new expect {self.data['expected_shares']}""",LOG)


		self.refresh_ui_component()

	def create_clone(self):

		#algo_name,orders,info


		infos = self.info.copy()

		self.clone_number+=1
		infos['clone'] = self.clone_number

		if "CLONE:" not in self.algo_name:
			algo_name = self.algo_name+'-CLONE:'+str(infos['clone'])
		else:
			base_name = self.algo_name.split("-CLONE:")[0]
			algo_name = f"{base_name}-CLONE:{infos['clone']}"
		self.manager.apply_basket_cmd(algo_name,self.data['clone_dict'] ,infos)


	def algo_as_is(self,tag=""):

		# if tag!=""
		# 	self.data['status'] = tag

		# if tag=="MOC":
		# 	self.data['flatten_order'] = True 

		for symbol in self.symbols.keys():
			self.data['expected_shares'][symbol] = self.data['current_shares'][symbol]
			self.data['current_request'][symbol] = 0

	def init_limit_request(self, symbol: str):
		self.data['limit_request'][symbol] = {
			'status': '',
			'pid': '',
			'oid': '',
		
			'target_price': '',   # use target_price consistently
			'order_price': '',
			'shares': 0,
			'ts': 0,              # when the live order was sent (epoch-sec)
			'fills': {}           # cumulative fills by price for THIS oid
		}


	def clear_limit_request(self, symbol: str):
		# Reset the LR node for this symbol
		self.data['limit_request'][symbol].update({
			'target_price': '',   # use target_price consistently
			'order_price': '',
			'shares': 0,
			'ts': 0,              # when the live order was sent (epoch-sec)
			'fills': {},           # cumulative fills by price for THIS oid
			'status': '',
		})

			# 'status': '',
			# 'pid': '',
			# 'oid': '',
	def submit_moo_request(self,symbol,shares):


		self.data['moo_request'][symbol] = shares

	def submit_limit_request(self,symbol,shares,limit_price):

		self.data['limit_request'][symbol]['shares'] = shares
		self.data['limit_request'][symbol]['target_price'] = limit_price

		#{'status':'','pid':'','oid':'','target_price':'','order_price':'','shares'}


	def clear_all_limit(self):
		for symbol in list(self.data['limit_request'].keys()):
			self.data['limit_request'][symbol]['shares'] = 0

	def clear_all_moo(self):

		pass
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

		#print(self.source,self.algo_name,symbol,shares,aggresive)


		if symbol not in self.data['clone_dict'] :
			self.data['clone_dict'][symbol] = {'share':shares}

		if shares==0:
			self.data['expected_shares'][symbol] = shares
			self.recalculate_current_request(symbol,aggresive)

		if symbol not in self.banned and self.data['flatten_order']!=True:

			# now = datetime.now()
			# ts = now.hour*3600 + now.minute*60 + now.second


			self.data['expected_shares'][symbol] = shares
			self.recalculate_current_request(symbol,aggresive)
			
			
			# if aggresive:
			# 	pass
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
	s = TradingPlan(None,"AMD.NQ")
	s.print_all_data()


	s.submit_expected_shares("AMD.NQ",5)
