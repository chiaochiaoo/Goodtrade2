
from Symbol import *
from TradingPlan import *
import unittest
import unittest.mock as mock



class MockResponse:
	def __init__(self, json_data, status_code=200):
		self.json_data = json_data
		self.status_code = status_code
		self.ok = status_code == 200

	def json(self):
		return self.json_data

	def raise_for_status(self):
		if self.status_code >= 400:
			raise requests.exceptions.HTTPError(f"HTTP Error: {self.status_code}")

# The custom mock functions to handle each specific URL call
# def mock_get_lv1(symbol_name, bid_price, ask_price, market_state="Open"):
#     """Mocks a successful GetLv1 call with custom parameters."""
#     return MockResponse(json_data={
#         "Responce": {
#             "Success": "true",
#             "Content": {
#                 "BidPrice": bid_price,
#                 "AskPrice": ask_price,
#                 "MarketTime": "1672531200",
#                 "InstrumentState": market_state
#             }
#         }
#     })

# def mock_execute_order(pid="mock_pid_123"):
#     """Mocks a successful ExecuteOrder call."""
#     return MockResponse(json_data={
#         "Responce": {
#             "Success": "true",
#             "Content": pid
#         }
#     })

# def mock_lookup_orderid(pid, order_id="mock_id_456"):
#     """Mocks a successful /papi/ call."""
#     if pid:
#         return MockResponse(json_data={"ret": True, "order": order_id})
#     return MockResponse(json_data={"ret": False, "order": ""})

# def mock_lookup_order(order_id, status, fill_details=None, shares=0):
#     """Mocks a successful /order/ call with a specific status and fill."""
#     json_data = {
#         "ret": True,
#         "status": status,
#         "fill": fill_details or {},
#         "shares": shares,
#         "target_share": shares
#     }
#     return MockResponse(json_data=json_data)

class TestState:
	def __init__(self):
		self.lv1_data = {
			"BidPrice": "105.25",
			"AskPrice": "105.30",
			"MarketTime": "1672531200",
			"InstrumentState": "Open"
		}
		self.order_pid = "pid123"
		self.order_id = "id456"
		self.order_status = "Accepted"
		self.fill_details = {}
		self.shares = 0
		self.target_share = 0


def dynamic_mock_get(state, url, **kwargs): 
	"""A dynamic mock function that responds based on the test's state.Canceled """ 
	if "GetLv1" in url:
		return MockResponse(json_data={"Responce": {"Success": "true", "Content": state.lv1_data}})
	elif "ExecuteOrder" in url:
		return MockResponse(json_data={"Responce": {"Success": "true", "Content": state.order_pid}})
	elif "/papi/" in url:
		return MockResponse(json_data={"ret": True, "order": state.order_id})
	elif "/order/" in url:
		return MockResponse(json_data={
			"ret": True,
			"status": state.order_status,
			"fill": state.fill_details,
			"shares": state.shares,
			"target_share": state.target_share
		})
	elif 'CancelOrder' in url:
		state.order_status = 'Cancelled'
		return MockResponse(json_data={"Responce": {"Success": "true", "Content": ''}})
	else:
		return MockResponse(json_data={"error": "URL not recognized"}, status_code=404)
































class BasicTests(unittest.TestCase):

	@mock.patch('requests.get')
	def test_L1_Update_Module_Success(self, mock_get):
		"""Tests L1 update with minimal spread and changing bid/ask prices."""
		print("\n--- Running L1 Tests ---")

		state = TestState()
		mock_get.side_effect = lambda url, **kwargs: dynamic_mock_get(state, url, **kwargs)

		symbol = Symbol(manager=None, symbol="AMD.NQ")
		
		# --- Scenario 1: Initial update from mock data ---
		state.lv1_data['BidPrice'] = "105.25"
		state.lv1_data['AskPrice'] = "105.30"
		symbol.l1_update_module()
		self.assertEqual(symbol.data['bid'], 105.25)
		self.assertEqual(symbol.data['ask'], 105.30)
		self.assertTrue(symbol.bid_change)
		self.assertTrue(symbol.ask_change)
		#self.assertTrue(symbol.bid_ask_change)

		# --- Scenario 2: Bid changes, ask stays the same ---
		state.lv1_data['BidPrice'] = "105.26"
		symbol.l1_update_module()
		self.assertEqual(symbol.data['bid'], 105.26)
		self.assertEqual(symbol.data['ask'], 105.30)
		self.assertTrue(symbol.bid_change)
		self.assertFalse(symbol.ask_change)
		#self.assertTrue(symbol.bid_ask_change)

		# --- Scenario 3: Ask changes, bid stays the same ---
		state.lv1_data['AskPrice'] = "105.31"
		symbol.l1_update_module()
		self.assertEqual(symbol.data['bid'], 105.26)
		self.assertEqual(symbol.data['ask'], 105.31)
		self.assertFalse(symbol.bid_change)
		self.assertTrue(symbol.ask_change)
		#self.assertTrue(symbol.bid_ask_change)

		# --- Scenario 4: Both bid and ask change ---
		state.lv1_data['BidPrice'] = "105.27"
		state.lv1_data['AskPrice'] = "105.32"
		symbol.l1_update_module()
		self.assertEqual(symbol.data['bid'], 105.27)
		self.assertEqual(symbol.data['ask'], 105.32)
		self.assertTrue(symbol.bid_change)
		self.assertTrue(symbol.ask_change)
		#self.assertTrue(symbol.bid_ask_change)

		# --- Scenario 5: No price change (re-run of last state) ---
		symbol.l1_update_module()
		self.assertFalse(symbol.bid_change)
		self.assertFalse(symbol.ask_change)
		#self.assertFalse(symbol.bid_ask_change)

	### NO EXISTING ORDER TEST 1 ###

	@mock.patch('requests.get')
	@mock.patch('datetime.datetime')
	def test_No_Request (self, mock_datetime, mock_get):
		"""
		Tests the path: No Order Exists -> Is there a request? (N) -> Finish Inspection.
		"""
		print("\n--- Running test_path_no_request: Verifying no action is taken when no order exists and no request is present. ---")
		
		# --- SETUP ---
		mock_datetime.now.return_value = datetime(2025, 8, 5, 9, 30, 0)
		
		# Initialize a TestState object. The mock will use its default values.
		state = TestState()
		state.lv1_data['InstrumentState'] = "Open"
		mock_get.side_effect = lambda url, **kwargs: dynamic_mock_get(state, url, **kwargs)

		ticker = 'AMD.NQ'
		symbol = Symbol(manager=mock.MagicMock(open_order_check=True), symbol=ticker)
		
		# The symbol has no active trading plans, so symbol.request will be 0.
		tp1 = TradingPlan(self, "AMD_TEST", {})
		tp1.register_symbol(ticker, symbol)
		
		# --- ACTION ---
		symbol.sysmbol_inspection()
		
		# --- ASSERTIONS ---
		# The ordering_phase should not be triggered because symbol.request is 0.
		self.assertFalse(symbol.order_out)
		self.assertEqual(symbol.order_pid, "")
		self.assertEqual(symbol.request, 0)
		


	@mock.patch('requests.get')
	@mock.patch('datetime.datetime')
	def test_Init_Order_On_New_Request (self, mock_datetime, mock_get):
		"""
		Tests the path: No Order Exists -> Is there a request? (Y) -> Init the order.
		"""
		print("\n--- Running test_path_init_order_on_new_request: Verifying a new order is placed when a request is present. ---")

		# --- SETUP ---
		mock_datetime.now.return_value = datetime(2025, 8, 5, 9, 30, 0)
		
		# Initialize a TestState object. The dynamic mock will use its values.
		state = TestState()
		mock_get.side_effect = lambda url, **kwargs: dynamic_mock_get(state, url, **kwargs)

		ticker = 'AMD.NQ'
		symbol = Symbol(manager=mock.MagicMock(open_order_check=True), symbol=ticker)

		# Setup a trading plan to create a non-zero request.
		tp1 = TradingPlan(self, "AMD_TEST", {})
		tp1.register_symbol(ticker, symbol)
		tp1.submit_expected_shares(ticker, 10, False)
		
		
		# --- CONFIG STATE ---
		state.order_pid = "mock_pid_123"
		state.order_id = "mock_id_456"
		state.order_status = "Accepted"
		# self.fill_details = {"105.25": 10}
		# self.shares = 10
		# self.target_share = 10
		state.fill_details = {}
		state.shares = 0
		state.target_share = 0

		# --- ACTION ---
		symbol.sysmbol_inspection()


		# --- ASSERTIONS ---
		# The ordering_phase should have been triggered.
		self.assertTrue(symbol.order_out)
		self.assertEqual(symbol.order_pid, state.order_pid)
		self.assertEqual(symbol.request, 10)
		

		print('Checking---1',symbol.order_out,symbol.order_details,symbol.order_id)
		symbol.sysmbol_inspection()

		print('Checking---2',symbol.order_out,symbol.order_details,symbol.order_id)
		self.assertEqual(symbol.order_id,state.order_id)

		

		print("\n--- Running test_path_init_order_on_new_request: Complete ---")

		#
		# Verify both API calls were made in the correct order.
		# expected_calls = [
		#     mock.call("http://127.0.0.1:8080/GetLv1?symbol=AMD.NQ"),
		#     mock.call(f"http://127.0.0.1:8080/ExecuteOrder?symbol={ticker}&limitprice=0.01&priceadjust=0.05&ordername=ARCA SELL ARCX Limit Near DAY&shares=10", timeout=0.25),
		# ]
		# mock_get.assert_has_calls(expected_calls)

	@mock.patch('requests.get')
	@mock.patch('datetime.datetime')
	def test_Multiple_Partial_Fills_Long (self, mock_datetime, mock_get):
		# --- SETUP ---
		print("\n--- Running test_multiple_partial_fills_long:  ---")
		mock_datetime.now.return_value = datetime(2025, 8, 5, 9, 30, 0)
		
		# Instantiate a TestState object
		test_state = TestState()
		
		# Use a lambda to pass the state object to the mock function
		mock_get.side_effect = lambda url, **kwargs: dynamic_mock_get(test_state, url, **kwargs)

		ticker = 'AMD.NQ'
		symbol = Symbol(manager=mock.MagicMock(open_order_check=True), symbol=ticker)
		tp1 = TradingPlan(self, "AMD_TEST", {})
		tp1.register_symbol(ticker, symbol)
		tp1.submit_expected_shares(ticker, 10, False)

		# --- PHASE 1: Place the order with initial state ---
		symbol.sysmbol_inspection()
		self.assertTrue(symbol.order_out)
		self.assertEqual(symbol.order_pid, test_state.order_pid)


		# --- PHASE 2A: Simulate Accepted by changing the state ---
		test_state.order_status = "Accepted"
		test_state.fill_details = {}
		test_state.shares = 0

		# The next call to sysmbol_inspection() will get the new partial fill data.
		symbol.sysmbol_inspection()
		self.assertEqual(symbol.request, 10) # 10 shares requested, 5 filled

		# --- PHASE 2B: Simulate partial fill by changing the state ---
		test_state.order_status = "Partially Filled"
		test_state.fill_details = {"105.25": 5}
		test_state.shares = 5

		# The next call to sysmbol_inspection() will get the new partial fill data.
		symbol.sysmbol_inspection()
		self.assertEqual(symbol.request, 5) # 10 shares requested, 5 filled

		# --- PHASE 2C: Simulate full fill by changing the state ---
		test_state.order_status = "Filled"
		test_state.fill_details = {"105.25": 5,'105.26':5}
		test_state.shares = 10

		# The final inspection should mark the order as complete.
		symbol.sysmbol_inspection()
		self.assertEqual(symbol.request, 0)
		self.assertFalse(symbol.order_out)

	@mock.patch('requests.get')
	@mock.patch('datetime.datetime')
	def test_Multiple_Partial_Fills_Short (self, mock_datetime, mock_get):

		print("\n--- Running test_multiple_partial_fills_short:  ---")
		# --- SETUP ---
		mock_datetime.now.return_value = datetime(2025, 8, 5, 9, 30, 0)
		
		# Instantiate a TestState object
		test_state = TestState()
		
		# Use a lambda to pass the state object to the mock function
		mock_get.side_effect = lambda url, **kwargs: dynamic_mock_get(test_state, url, **kwargs)

		ticker = 'AMD.NQ'
		symbol = Symbol(manager=mock.MagicMock(open_order_check=True), symbol=ticker)
		tp1 = TradingPlan(self, "AMD_TEST", {})
		tp1.register_symbol(ticker, symbol)
		tp1.submit_expected_shares(ticker, -10, False)

		# --- PHASE 1: Place the order with initial state ---
		symbol.sysmbol_inspection()
		self.assertTrue(symbol.order_out)
		self.assertEqual(symbol.order_pid, test_state.order_pid)


		# --- PHASE 2A: Simulate Accepted by changing the state ---
		test_state.order_status = "Accepted"
		test_state.fill_details = {}
		test_state.shares = 0

		# The next call to sysmbol_inspection() will get the new partial fill data.
		symbol.sysmbol_inspection()
		self.assertEqual(symbol.request, -10) # 10 shares requested, 5 filled

		# --- PHASE 2B: Simulate partial fill by changing the state ---
		test_state.order_status = "Partially Filled"
		test_state.fill_details = {"105.25": -5}
		test_state.shares = -5

		# The next call to sysmbol_inspection() will get the new partial fill data.
		symbol.sysmbol_inspection()
		self.assertEqual(symbol.request, -5) # 10 shares requested, 5 filled

		# --- PHASE 2C: Simulate full fill by changing the state ---
		test_state.order_status = "Partially Filled"
		test_state.fill_details = {"105.25": -5,'105.26':-3}
		test_state.shares = -8

		symbol.sysmbol_inspection()
		self.assertEqual(symbol.request, -2)
		self.assertTrue(symbol.order_out)

		test_state.order_status = "Multi Filled"
		test_state.fill_details = {"105.25": -5,'105.26':-3,'106.2':-2}
		test_state.shares = -10

		# The final inspection should mark the order as complete.
		symbol.sysmbol_inspection()
		self.assertEqual(symbol.request, 0)
		self.assertFalse(symbol.order_out)

	@mock.patch('requests.get')
	@mock.patch('datetime.datetime')
	def test_Paritial_Fill_Cancel_Replace(self, mock_datetime, mock_get):

		# --- SETUP ---
		print("\n--- Running test_Paritial_Fill_Cancel_Replace:  ---")
		mock_datetime.now.return_value = datetime(2025, 8, 5, 9, 30, 0)
		
		# Instantiate a TestState object
		test_state = TestState()
		test_state.lv1_data = {
			"BidPrice": "105.25",
			"AskPrice": "105.30",
			"MarketTime": "1672531200",
			"InstrumentState": "Open"
		}
		# Use a lambda to pass the state object to the mock function
		mock_get.side_effect = lambda url, **kwargs: dynamic_mock_get(test_state, url, **kwargs)

		ticker = 'AMD.NQ'
		symbol = Symbol(manager=mock.MagicMock(open_order_check=True), symbol=ticker)
		tp1 = TradingPlan(self, "AMD_TEST", {})
		tp1.register_symbol(ticker, symbol)
		tp1.submit_expected_shares(ticker, 10, False)

		# --- PHASE 1: Place the order with initial state ---
		symbol.sysmbol_inspection()
		self.assertTrue(symbol.order_out)
		self.assertEqual(symbol.order_pid, test_state.order_pid)


		# --- PHASE 2A: Simulate Accepted by changing the state ---
		test_state.order_status = "Accepted"
		test_state.fill_details = {}
		test_state.shares = 0

		# The next call to sysmbol_inspection() will get the new partial fill data.
		symbol.sysmbol_inspection()
		self.assertEqual(symbol.request, 10) # 10 shares requested, 5 filled

		# --- PHASE 2B: Simulate partial fill by changing the state ---
		test_state.order_status = "Partially Filled"
		test_state.fill_details = {"105.25": 5}
		test_state.shares = 5

		# The next call to sysmbol_inspection() will get the new partial fill data.
		symbol.sysmbol_inspection()
		self.assertEqual(symbol.request, 5) # 10 shares requested, 5 filled

		# --- PHASE 2C: Simulate full fill by changing the state ---
		test_state.order_status = "Cancelled"
		test_state.fill_details = {"105.25": 5}
		test_state.shares = 5

		# The final inspection should mark the order as complete.
		symbol.sysmbol_inspection()
		self.assertEqual(symbol.request, 5)
		self.assertTrue(symbol.order_out)


	@mock.patch('requests.get')
	@mock.patch('datetime.datetime')
	def test_Over_Fills(self, mock_datetime, mock_get):

		# --- SETUP ---
		print("\n--- Running test_Over_Fills:  ---")
		mock_datetime.now.return_value = datetime(2025, 8, 5, 9, 30, 0)
		
		# Instantiate a TestState object
		test_state = TestState()
		test_state.lv1_data = {
			"BidPrice": "105.25",
			"AskPrice": "105.30",
			"MarketTime": "1672531200",
			"InstrumentState": "Open"
		}
		# Use a lambda to pass the state object to the mock function
		mock_get.side_effect = lambda url, **kwargs: dynamic_mock_get(test_state, url, **kwargs)

		ticker = 'AMD.NQ-overfill'
		symbol = Symbol(manager=mock.MagicMock(open_order_check=True), symbol=ticker)
		tp1 = TradingPlan(self, "AMD_TEST", {})
		tp1.register_symbol(ticker, symbol)
		tp1.submit_expected_shares(ticker, 10, False)

		# --- PHASE 1: Place the order with initial state ---
		symbol.sysmbol_inspection()
		self.assertTrue(symbol.order_out)
		self.assertEqual(symbol.order_pid, test_state.order_pid)


		# --- PHASE 2A: Simulate Accepted by changing the state ---
		test_state.order_status = "Accepted"
		test_state.fill_details = {}
		test_state.shares = 0

		# The next call to sysmbol_inspection() will get the new partial fill data.
		symbol.sysmbol_inspection()
		self.assertEqual(symbol.request, 10) # 10 shares requested, 5 filled

		# --- PHASE 2B: Simulate partial fill by changing the state ---
		test_state.order_status = "Filled"
		test_state.fill_details = {"105.25": 15}
		test_state.shares = 15

		# The next call to sysmbol_inspection() will get the new partial fill data.
		symbol.sysmbol_inspection()
		self.assertEqual(symbol.request, -5) # 10 shares requested, 5 filled

		# --- PHASE 2C: Simulate full fill by changing the state ---
		test_state.order_status = "Filled"
		test_state.fill_details = {"105.26": -5}
		test_state.shares = -5

		# The final inspection should mark the order as complete.
		symbol.sysmbol_inspection()
		self.assertEqual(symbol.request, 0)
		self.assertFalse(symbol.order_out)






















class Rejection_Tests(unittest.TestCase):


	@mock.patch('requests.get')
	@mock.patch('datetime.datetime')
	def test_on_long_rejected(self, mock_datetime,mock_get):
		"""Tests L1 update with minimal spread and changing bid/ask prices."""

		print("\n--- Running test_2_tp_same_side_long ---")
		mock_datetime.now.return_value = datetime(2025, 8, 5, 9, 30, 0)
		state = TestState()
		state.lv1_data['BidPrice'] = "105.25"
		state.lv1_data['AskPrice'] = "105.26"
		state.order_pid = "mock_pid_123"
		state.order_id = "mock_id_456"
		state.order_status = ""  # Initial status
		mock_get.side_effect = lambda url, **kwargs: dynamic_mock_get(state, url, **kwargs)
		
		# --- Set up
		ticker = 'AMD.NQ-long-rejected'
		symbol = Symbol(manager=mock.MagicMock(open_order_check=True), symbol=ticker)

		# Setup a trading plan to create a non-zero request.
		tp1 = TradingPlan(self, "AMD_TEST", {})
		tp1.register_symbol(ticker, symbol)
		tp1.submit_expected_shares(ticker, 10, False)
		
		# --- CONFIG STATE ---

		symbol.sysmbol_inspection()

		state.order_status = "Rejected"


		symbol.sysmbol_inspection()
		self.assertEqual(symbol.request, 0)
		self.assertFalse(symbol.order_out)


	@mock.patch('requests.get')
	@mock.patch('datetime.datetime')
	def test_on_short_rejected(self, mock_datetime,mock_get):
		"""Tests L1 update with minimal spread and changing bid/ask prices."""

		print("\n--- Running test_2_tp_same_side_long ---")
		mock_datetime.now.return_value = datetime(2025, 8, 5, 9, 30, 0)
		state = TestState()
		state.lv1_data['BidPrice'] = "105.25"
		state.lv1_data['AskPrice'] = "105.26"
		state.order_pid = "mock_pid_123"
		state.order_id = "mock_id_456"
		state.order_status = ""  # Initial status
		mock_get.side_effect = lambda url, **kwargs: dynamic_mock_get(state, url, **kwargs)
		
		# --- Set up
		ticker = 'AMD.NQ-long-rejected'
		symbol = Symbol(manager=mock.MagicMock(open_order_check=True), symbol=ticker)

		# Setup a trading plan to create a non-zero request.
		tp1 = TradingPlan(self, "AMD_TEST", {})
		tp1.register_symbol(ticker, symbol)
		tp1.submit_expected_shares(ticker, -10, False)
		
		# --- CONFIG STATE ---

		symbol.sysmbol_inspection()

		state.order_status = "Rejected"


		symbol.sysmbol_inspection()
		self.assertEqual(symbol.request, 0)
		self.assertFalse(symbol.order_out)


	@mock.patch('requests.get')
	@mock.patch('datetime.datetime')
	def test_on_long_out_short_rejected(self, mock_datetime,mock_get):
		"""Tests L1 update with minimal spread and changing bid/ask prices."""
		print("\n--- Running test_on_long_out_short_rejected ---")
		mock_datetime.now.return_value = datetime(2025, 8, 5, 9, 30, 0)
		state = TestState()
		state.lv1_data['BidPrice'] = "105.25"
		state.lv1_data['AskPrice'] = "105.26"
		state.order_pid = "mock_pid_123"
		state.order_id = "mock_id_456"
		state.order_status = ""  # Initial status
		mock_get.side_effect = lambda url, **kwargs: dynamic_mock_get(state, url, **kwargs)
		
		# --- Set up

		ticker = 'AMD.NQ-long-out-short-rejected'
		symbol = Symbol(manager=mock.MagicMock(open_order_check=True), symbol=ticker)

		# Setup a trading plan to create a non-zero request.
		tp1 = TradingPlan(self, "AMD_TEST", {})
		tp1.register_symbol(ticker, symbol)
		tp1.submit_expected_shares(ticker, 10, False)
		
		tp2 = TradingPlan(self, "AMD_TEST2", {})
		tp2.register_symbol(ticker, symbol)
		tp2.submit_expected_shares(ticker, -5, False)
		# --- CONFIG STATE ---

		state.lv1_data['BidPrice'] = "105.25"
		state.lv1_data['AskPrice'] = "105.26"

		state.order_pid = "mock_pid_123"
		state.order_id = "mock_id_456"
		state.order_status = "Accepted"
		state.fill_details = {}
		state.shares = 0
		state.target_share = 0

		symbol.sysmbol_inspection()
		self.assertEqual(symbol.order_price, 105.25)
		self.assertEqual(symbol.request, 5)

		state.lv1_data['BidPrice'] = "105.26"
		state.lv1_data['AskPrice'] = "105.27"

		## needs to be canceled now

		stage = 1
		print('\n',stage)
		symbol.sysmbol_inspection()

		state.order_id = 'Order1'
		state.fill_details = {105.26:5}
		state.shares = 5
		state.target_share = 5
		state.order_status = 'Filled'

		### NEED STAGE 2 TO BE , No action and complete. 
		stage = 2
		print('\n',stage)
		symbol.sysmbol_inspection()


		self.assertEqual(symbol.request, 0)
		self.assertFalse(symbol.order_out)


		# STAGE 3, submit long out. should be minus -10 shares.
		stage = 3
		print('\n',stage)

		tp1.submit_expected_shares(ticker, 0, False)
		symbol.sysmbol_inspection()

		self.assertEqual(symbol.request, -10)


		state.order_id = 'Order2'
		state.fill_details = {105.26:-5}
		state.shares = -5
		state.target_share = -5
		state.order_status = 'Filled'


		# stage 4, now overall it has 0 shares. another -5 shares out.
		stage = 4
		print('\n',stage)

		symbol.sysmbol_inspection()


		self.assertEqual(symbol.request, -5)
		self.assertTrue(symbol.order_out)



		### This is a problem because it impacts 2 TPs. ###
		state.order_id = 'Order2'
		state.fill_details = {}
		state.shares = 0
		state.target_share = 0
		state.order_status = 'Rejected'

		stage = 5
		print('\n',stage)

		symbol.sysmbol_inspection()

		self.assertEqual(symbol.request, 0)
		self.assertFalse(symbol.order_out)

		stage = 6
		print('\n',stage)

		symbol.sysmbol_inspection()
		self.assertEqual(symbol.request, 0)
		self.assertFalse(symbol.order_out)
class Multi_Tp_Tests(unittest.TestCase):

	@mock.patch('requests.get')
	@mock.patch('datetime.datetime')
	def test_2_tp_same_side_long(self, mock_datetime,mock_get):
		"""Tests L1 update with minimal spread and changing bid/ask prices."""

		print("\n--- Running test_2_tp_same_side_long ---")
		mock_datetime.now.return_value = datetime(2025, 8, 5, 9, 30, 0)
		state = TestState()
		state.lv1_data['BidPrice'] = "105.25"
		state.lv1_data['AskPrice'] = "105.26"
		state.order_pid = "mock_pid_123"
		state.order_id = "mock_id_456"
		state.order_status = ""  # Initial status
		mock_get.side_effect = lambda url, **kwargs: dynamic_mock_get(state, url, **kwargs)
		
		# --- Set up
		ticker = 'AMD.NQ-same-long'
		symbol = Symbol(manager=mock.MagicMock(open_order_check=True), symbol=ticker)

		# Setup a trading plan to create a non-zero request.
		tp1 = TradingPlan(self, "AMD_TEST", {})
		tp1.register_symbol(ticker, symbol)
		tp1.submit_expected_shares(ticker, 10, False)
		
		tp2 = TradingPlan(self, "AMD_TEST2", {})
		tp2.register_symbol(ticker, symbol)
		tp2.submit_expected_shares(ticker, 5, False)
		# --- CONFIG STATE ---

		state.lv1_data['BidPrice'] = "105.25"
		state.lv1_data['AskPrice'] = "105.26"

		state.order_pid = "mock_pid_123"
		state.order_id = "mock_id_456"
		state.order_status = "Accepted"
		state.fill_details = {}
		state.shares = 0
		state.target_share = 0

		symbol.sysmbol_inspection()
		self.assertEqual(symbol.order_price, 105.25)

		self.assertEqual(symbol.request, 15)

		state.lv1_data['BidPrice'] = "105.26"
		state.lv1_data['AskPrice'] = "105.27"

		## needs to be canceled now
		symbol.sysmbol_inspection()

		symbol.sysmbol_inspection() #replace.

		#self.assertEqual(symbol.request, 0)

		state.order_pid = "mock_pid_123"
		state.order_id = "mock_id_456"
		state.order_status = "Accepted"


		symbol.sysmbol_inspection()



		state.fill_details = {105.26:10}
		state.shares = 10
		state.target_share = 10
		state.order_status = 'Partially Filled'

		symbol.sysmbol_inspection()

		self.assertEqual(symbol.request, 5)

		state.fill_details = {105.26:15}
		state.shares = 15
		state.target_share = 15
		state.order_status = 'Multi Filled'

		symbol.sysmbol_inspection()


		self.assertEqual(symbol.request, 0)
		self.assertFalse(symbol.order_out)


	@mock.patch('requests.get')
	@mock.patch('datetime.datetime')
	def test_2_tp_same_side_short(self, mock_datetime,mock_get):
		"""Tests L1 update with minimal spread and changing bid/ask prices."""

		print("\n--- Running test_2_tp_same_side_short ---")
		mock_datetime.now.return_value = datetime(2025, 8, 5, 9, 30, 0)
		state = TestState()
		state.lv1_data['BidPrice'] = "105.25"
		state.lv1_data['AskPrice'] = "105.26"
		state.order_pid = "mock_pid_123"
		state.order_id = "mock_id_456"
		state.order_status = ""  # Initial status
		mock_get.side_effect = lambda url, **kwargs: dynamic_mock_get(state, url, **kwargs)
		
		# --- Set up
		ticker = 'AMD.NQ-same-short'
		symbol = Symbol(manager=mock.MagicMock(open_order_check=True), symbol=ticker)

		# Setup a trading plan to create a non-zero request.
		tp1 = TradingPlan(self, "AMD_TEST", {})
		tp1.register_symbol(ticker, symbol)
		tp1.submit_expected_shares(ticker, -10, False)
		
		tp2 = TradingPlan(self, "AMD_TEST2", {})
		tp2.register_symbol(ticker, symbol)
		tp2.submit_expected_shares(ticker, -5, False)
		# --- CONFIG STATE ---

		state.lv1_data['BidPrice'] = "105.25"
		state.lv1_data['AskPrice'] = "105.26"

		state.order_pid = "mock_pid_123"
		state.order_id = "mock_id_456"
		state.order_status = "Accepted"
		state.fill_details = {}
		state.shares = 0
		state.target_share = 0

		symbol.sysmbol_inspection()
		self.assertEqual(symbol.order_price, 105.26)

		self.assertEqual(symbol.request, -15)

		state.lv1_data['BidPrice'] = "105.26"
		state.lv1_data['AskPrice'] = "105.27"

		## needs to be canceled now
		symbol.sysmbol_inspection()

		symbol.sysmbol_inspection() #replace.

		#self.assertEqual(symbol.request, 0)

		state.order_pid = "mock_pid_123"
		state.order_id = "mock_id_456"
		state.order_status = "Accepted"


		symbol.sysmbol_inspection()



		state.fill_details = {105.26:-10}
		state.shares = -10
		state.target_share = -10
		state.order_status = 'Partially Filled'

		symbol.sysmbol_inspection()

		self.assertEqual(symbol.request, -5)

		state.fill_details = {105.26:-15}
		state.shares = -15
		state.target_share = -15
		state.order_status = 'Multi Filled'

		symbol.sysmbol_inspection()


		self.assertEqual(symbol.request, 0)
		self.assertFalse(symbol.order_out)

	@mock.patch('requests.get')
	@mock.patch('datetime.datetime')
	def test_2_tp_pairing(self, mock_datetime,mock_get):
		"""Tests L1 update with minimal spread and changing bid/ask prices."""

		print("\n--- Running test_2_tp_diverging ---")
		mock_datetime.now.return_value = datetime(2025, 8, 5, 9, 30, 0)
		state = TestState()
		state.lv1_data['BidPrice'] = "105.25"
		state.lv1_data['AskPrice'] = "105.26"
		state.order_pid = "mock_pid_123"
		state.order_id = "mock_id_456"
		state.order_status = ""  # Initial status
		mock_get.side_effect = lambda url, **kwargs: dynamic_mock_get(state, url, **kwargs)
		
		# --- Set up
		ticker = 'AMD.NQ-pairing test'
		symbol = Symbol(manager=mock.MagicMock(open_order_check=True), symbol=ticker)

		symbol.sysmbol_inspection()


		# Setup a trading plan to create a non-zero request.
		tp1 = TradingPlan(self, "AMD_LONG", {})
		tp1.register_symbol(ticker, symbol)
		tp1.submit_expected_shares(ticker, 10, False)
		
		tp2 = TradingPlan(self, "AMD_SHORT", {})
		tp2.register_symbol(ticker, symbol)
		tp2.submit_expected_shares(ticker, -5, False)
		# --- CONFIG STATE ---

		state.lv1_data['BidPrice'] = "105.25"
		state.lv1_data['AskPrice'] = "105.26"

		state.order_pid = "mock_pid_123"
		state.order_id = "mock_id_456"

		state.fill_details = {}
		state.shares = 0
		state.target_share = 0


		stage = 1
		print('\n',stage)
		symbol.sysmbol_inspection()
		self.assertEqual(symbol.order_price, 105.25)
		self.assertEqual(symbol.request, 5)


		# Accepted -
		state.lv1_data['BidPrice'] = "105.26"
		state.lv1_data['AskPrice'] = "105.27"

		state.order_pid = "mock_pid_123"
		state.order_id = "mock_id_456"
		state.order_status = "Accepted"


		stage = 2
		print(f'\n {stage} ')
		symbol.sysmbol_inspection()


		# Filled -

		state.fill_details = {105.26:10}
		state.shares = 10
		state.target_share = 10
		state.order_status = 'Multi Filled'


		stage = 3
		print(f'\n {stage} ')
		symbol.sysmbol_inspection()

		self.assertEqual(symbol.request, -5)


		state.fill_details = {105.27:15}
		state.shares = 15
		state.target_share = 15
		state.order_status = 'Filled'

		stage = 4
		print(f'\n {stage} ')
		symbol.sysmbol_inspection()


		self.assertEqual(symbol.request, -20)
		self.assertTrue(symbol.order_out)

		stage = 5
		print(f'\n {stage} ')
		symbol.sysmbol_inspection()

		# state.fill_details = {105.27:-20}
		# state.shares = -20
		# state.order_status = 'Filled'

		# symbol.sysmbol_inspection()


		# self.assertEqual(symbol.request, 0)
		# self.assertFalse(symbol.order_out)


	@mock.patch('requests.get')
	@mock.patch('datetime.datetime')
	def test_2_tp_same_side_1_out(self, mock_datetime,mock_get):
		"""Tests L1 update with minimal spread and changing bid/ask prices."""

		print("\n--- Running test_2_tp_same_side_long ---")
		mock_datetime.now.return_value = datetime(2025, 8, 5, 9, 30, 0)
		state = TestState()
		state.lv1_data['BidPrice'] = "105.25"
		state.lv1_data['AskPrice'] = "105.26"
		state.order_pid = "mock_pid_123"
		state.order_id = "mock_id_456"
		state.order_status = ""  # Initial status
		mock_get.side_effect = lambda url, **kwargs: dynamic_mock_get(state, url, **kwargs)
		
		# --- Set up
		ticker = 'AMD.NQ-1-out'
		symbol = Symbol(manager=mock.MagicMock(open_order_check=True), symbol=ticker)

		# Setup a trading plan to create a non-zero request.
		tp1 = TradingPlan(self, "AMD_TEST", {})
		tp1.register_symbol(ticker, symbol)
		tp1.submit_expected_shares(ticker, 10, False)
		
		tp2 = TradingPlan(self, "AMD_TEST2", {})
		tp2.register_symbol(ticker, symbol)
		tp2.submit_expected_shares(ticker, 5, False)
		# --- CONFIG STATE ---

		state.lv1_data['BidPrice'] = "105.25"
		state.lv1_data['AskPrice'] = "105.26"

		state.order_pid = "mock_pid_123"
		state.order_id = "mock_id_456"
		state.order_status = "Accepted"
		state.fill_details = {}
		state.shares = 0
		state.target_share = 0

		symbol.sysmbol_inspection()
		self.assertEqual(symbol.order_price, 105.25)

		self.assertEqual(symbol.request, 15)

		state.lv1_data['BidPrice'] = "105.26"
		state.lv1_data['AskPrice'] = "105.27"

		## needs to be canceled now

		stage = 1
		print('\n',stage)
		symbol.sysmbol_inspection()

		state.order_id = 'Order1'
		state.fill_details = {105.26:15}
		state.shares = 15
		state.target_share = 15
		state.order_status = 'Filled'

		stage = 2
		print('\n',stage)
		symbol.sysmbol_inspection()


		stage = 3
		print('\n',stage)

		tp2.submit_expected_shares(ticker, 0, False)
		symbol.sysmbol_inspection()

		self.assertEqual(symbol.request, -5)


		state.order_id = 'Order2'
		state.fill_details = {105.26:-5}
		state.shares = -5
		state.target_share = -5
		state.order_status = 'Filled'


		tp1.submit_expected_shares(ticker, 0, False)
		symbol.sysmbol_inspection()

		state.order_id = 'Order3'
		state.fill_details = {105.27:-10}
		state.shares = -10
		state.target_share = -10
		state.order_status = 'Filled'

		symbol.sysmbol_inspection()
		self.assertEqual(symbol.request, 0)
		self.assertFalse(symbol.order_out)

	@mock.patch('requests.get')
	@mock.patch('datetime.datetime')
	def test_2_tp_diverging_side_short_out(self, mock_datetime,mock_get):
		"""Tests L1 update with minimal spread and changing bid/ask prices."""

		print("\n--- Running test_2_tp_same_side_long ---")
		mock_datetime.now.return_value = datetime(2025, 8, 5, 9, 30, 0)
		state = TestState()
		state.lv1_data['BidPrice'] = "105.25"
		state.lv1_data['AskPrice'] = "105.26"
		state.order_pid = "mock_pid_123"
		state.order_id = "mock_id_456"
		state.order_status = ""  # Initial status
		mock_get.side_effect = lambda url, **kwargs: dynamic_mock_get(state, url, **kwargs)
		
		# --- Set up
		ticker = 'AMD.NQ-div-short-out'
		symbol = Symbol(manager=mock.MagicMock(open_order_check=True), symbol=ticker)

		# Setup a trading plan to create a non-zero request.
		tp1 = TradingPlan(self, "AMD_TEST", {})
		tp1.register_symbol(ticker, symbol)
		tp1.submit_expected_shares(ticker, 10, False)
		
		tp2 = TradingPlan(self, "AMD_TEST2", {})
		tp2.register_symbol(ticker, symbol)
		tp2.submit_expected_shares(ticker, -5, False)
		# --- CONFIG STATE ---

		state.lv1_data['BidPrice'] = "105.25"
		state.lv1_data['AskPrice'] = "105.26"

		state.order_pid = "mock_pid_123"
		state.order_id = "mock_id_456"
		state.order_status = "Accepted"
		state.fill_details = {}
		state.shares = 0
		state.target_share = 0

		symbol.sysmbol_inspection()
		self.assertEqual(symbol.order_price, 105.25)
		self.assertEqual(symbol.request, 5)

		state.lv1_data['BidPrice'] = "105.26"
		state.lv1_data['AskPrice'] = "105.27"

		## needs to be canceled now

		stage = 1
		print('\n',stage)
		symbol.sysmbol_inspection()

		state.order_id = 'Order1'
		state.fill_details = {105.26:5}
		state.shares = 5
		state.target_share = 5
		state.order_status = 'Filled'

		stage = 2
		print('\n',stage)
		symbol.sysmbol_inspection()
		self.assertEqual(symbol.request, 0)
		self.assertFalse(symbol.order_out)


		stage = 3
		print('\n',stage)

		tp2.submit_expected_shares(ticker, 0, False)
		symbol.sysmbol_inspection()

		self.assertEqual(symbol.request, 5)


		state.order_id = 'Order2'
		state.fill_details = {105.26:5}
		state.shares = 5
		state.target_share = 5
		state.order_status = 'Filled'



		symbol.sysmbol_inspection()


		self.assertEqual(symbol.request, 0)
		self.assertFalse(symbol.order_out)


	@mock.patch('requests.get')
	@mock.patch('datetime.datetime')
	def test_2_tp_diverging_side_long_out(self, mock_datetime,mock_get):
		"""Tests L1 update with minimal spread and changing bid/ask prices."""

		print("\n--- Running test_2_tp_same_side_long ---")
		mock_datetime.now.return_value = datetime(2025, 8, 5, 9, 30, 0)
		state = TestState()
		state.lv1_data['BidPrice'] = "105.25"
		state.lv1_data['AskPrice'] = "105.26"
		state.order_pid = "mock_pid_123"
		state.order_id = "mock_id_456"
		state.order_status = ""  # Initial status
		mock_get.side_effect = lambda url, **kwargs: dynamic_mock_get(state, url, **kwargs)
		
		# --- Set up
		ticker = 'AMD.NQ-div-short-out'
		symbol = Symbol(manager=mock.MagicMock(open_order_check=True), symbol=ticker)

		# Setup a trading plan to create a non-zero request.
		tp1 = TradingPlan(self, "AMD_TEST", {})
		tp1.register_symbol(ticker, symbol)
		tp1.submit_expected_shares(ticker, 10, False)
		
		tp2 = TradingPlan(self, "AMD_TEST2", {})
		tp2.register_symbol(ticker, symbol)
		tp2.submit_expected_shares(ticker, -5, False)
		# --- CONFIG STATE ---

		state.lv1_data['BidPrice'] = "105.25"
		state.lv1_data['AskPrice'] = "105.26"

		state.order_pid = "mock_pid_123"
		state.order_id = "mock_id_456"
		state.order_status = "Accepted"
		state.fill_details = {}
		state.shares = 0
		state.target_share = 0

		symbol.sysmbol_inspection()
		self.assertEqual(symbol.order_price, 105.25)
		self.assertEqual(symbol.request, 5)

		state.lv1_data['BidPrice'] = "105.26"
		state.lv1_data['AskPrice'] = "105.27"

		## needs to be canceled now

		stage = 1
		print('\n',stage)
		symbol.sysmbol_inspection()

		state.order_id = 'Order1'
		state.fill_details = {105.26:5}
		state.shares = 5
		state.target_share = 5
		state.order_status = 'Filled'

		stage = 2
		print('\n',stage)
		symbol.sysmbol_inspection()
		self.assertEqual(symbol.request, 0)
		self.assertFalse(symbol.order_out)


		stage = 3
		print('\n',stage)

		tp1.submit_expected_shares(ticker, 0, False)
		symbol.sysmbol_inspection()

		self.assertEqual(symbol.request, -10)


		state.order_id = 'Order2'
		state.fill_details = {105.26:-10}
		state.shares = -10
		state.target_share = -10
		state.order_status = 'Filled'

		symbol.sysmbol_inspection()

		self.assertEqual(symbol.request, 0)
		self.assertFalse(symbol.order_out)
		self.assertEqual(symbol.tp_current_shares,-5)

class TestOrderPlacingAndCancel(unittest.TestCase):

	@mock.patch('requests.get')
	@mock.patch('datetime.datetime')
	def test_order_place_and_cancel(self, mock_dt,mock_get):
		"""Tests L1 update with minimal spread and changing bid/ask prices."""

		print("\n--- Running test_l1_update_module_successx Test ---")



		state = TestState()
		# set prices, ids, etc.
		mock_dt.now.return_value = datetime(2025, 8, 5, 15, 49, 50)  # inside window
		mock_get.side_effect = lambda url, **kw: dynamic_mock_get(state, url, **kw)

		ticker = "AMD-replace"
		symbol = Symbol(manager=mock.MagicMock(open_order_check=True), symbol=ticker)
		
		symbol.sysmbol_inspection()
		

		# Setup a trading plan to create a non-zero request.
		tp1 = TradingPlan(self, "AMD_TEST", {})
		tp1.register_symbol(ticker, symbol)
		tp1.submit_expected_shares(ticker, 10, False)
		
		
		# --- CONFIG STATE ---

		state.lv1_data['BidPrice'] = "105.25"
		state.lv1_data['AskPrice'] = "105.26"

		state.order_pid = "mock_pid_123"
		state.order_id = "mock_id_456"
		state.order_status = "Accepted"
		state.fill_details = {}
		state.shares = 0
		state.target_share = 0

		symbol.sysmbol_inspection()
		self.assertEqual(symbol.order_price, 105.25)

		self.assertEqual(symbol.request, 10)

		state.lv1_data['BidPrice'] = "105.26"
		state.lv1_data['AskPrice'] = "105.27"

		## needs to be canceled now
		symbol.sysmbol_inspection()

		symbol.sysmbol_inspection() #replace.

		#self.assertEqual(symbol.request, 0)

		state.order_pid = "mock_pid_123"
		state.order_id = "mock_id_456"
		state.order_status = "Accepted"

		symbol.sysmbol_inspection()


		#self.assertEqual(symbol.order_price, 105.26)
class Test_MOC_Basics(unittest.TestCase):


	@mock.patch('requests.get')
	@mock.patch('datetime.datetime')
	def test_moc_long_no_orders(self, mock_dt, mock_get):
		state = TestState()
		# set prices, ids, etc.
		mock_dt.now.return_value = datetime(2025, 8, 5, 15, 49, 50)  # inside window
		mock_get.side_effect = lambda url, **kw: dynamic_mock_get(state, url, **kw)


		ticker = "AMD.NQ"
		symbol = Symbol(manager=mock.MagicMock(open_order_check=True), symbol="AMD.NQ")

		symbol.sysmbol_inspection()


		tp1 = TradingPlan(self, "TP1", {})
		tp1.register_symbol("AMD.NQ", symbol)
		tp1.submit_expected_shares(ticker, 10, False)
		#tp.request_fufill("AMD.NQ", 10, 105.26)  # start +10
		symbol.sysmbol_inspection()

		state.lv1_data['BidPrice'] = "105.25"
		state.lv1_data['AskPrice'] = "105.26"

		state.order_id = 'Order2'
		state.fill_details = {105.26:10}
		state.shares = 10
		state.target_share = 10
		state.order_status = 'Filled'

		symbol.sysmbol_inspection()
		symbol.sysmbol_inspection()
		
		symbol.time_to_moc("ARCA ACTION ARCX Market MOC DAY")

		symbol.sysmbol_inspection()

		self.assertTrue(symbol.moc_order_out)
		self.assertTrue(symbol.order_out)

		# complete fill
		state.order_status = "Filled"
		state.order_id = "moc123"
		state.fill_details = {105.25: -10}
		state.shares = -10
		state.target_share = -10

		symbol.sysmbol_inspection()

		self.assertEqual(symbol.tp_current_shares, 10)
		self.assertEqual(symbol.request, -10)
		self.assertFalse(symbol.order_out)
		self.assertTrue(symbol.moc_order_out)


if __name__ == "__main__":
	root = tk.Tk()

	#unittest.main()

	suite = unittest.TestSuite()
	
	# Load only the tests from TestOrderPlacingAndCancel

	# suite.addTest(unittest.makeSuite(BasicTests))

	# suite.addTest(unittest.makeSuite(Multi_Tp_Tests))


	# suite.addTest(unittest.makeSuite(Rejection_Tests))

	suite.addTest(unittest.makeSuite(Test_MOC_Basics))
	


	#suite.addTest(unittest.makeSuite(TestOrderPlacingAndCancel))
	
	# Run the specific suite
	runner = unittest.TextTestRunner()
	runner.run(suite)