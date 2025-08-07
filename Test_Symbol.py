
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
		self.order_pid = "mock_pid_123"
		self.order_id = "mock_id_456"
		self.order_status = "Filled"
		self.fill_details = {"105.25": 10}
		self.shares = 10
		self.target_share = 10


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
		

		print('Checking---',symbol.order_out,symbol.order_details,symbol.order_id)
		symbol.sysmbol_inspection()

		print('Checking---',symbol.order_out,symbol.order_details,symbol.order_id)
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

class TestOrderPlacingAndCancel(unittest.TestCase):

	
	
	@mock.patch('datetime.datetime')
	@mock.patch('requests.get')
	def test_l1_update_module_success(self, mock_datetime,mock_get):
		"""Tests L1 update with minimal spread and changing bid/ask prices."""

		print("\n--- Running Bid Change Test ---")
		mock_datetime.now.return_value = datetime(2025, 8, 5, 9, 30, 0)
		state = TestState()
		mock_get.side_effect = lambda url, **kwargs: dynamic_mock_get(state, url, **kwargs)

		symbol = Symbol(manager=None, symbol="AMD.NQ")
		

		# --- Set up


		ticker = 'AMD.NQ'
		symbol = Symbol(manager=mock.MagicMock(open_order_check=True), symbol=ticker)

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
if __name__ == "__main__":
	root = tk.Tk()

	#unittest.main()

	suite = unittest.TestSuite()
	
	# Load only the tests from TestOrderPlacingAndCancel

	suite.addTest(unittest.makeSuite(BasicTests))

	#suite.addTest(unittest.makeSuite(TestOrderPlacingAndCancel))
	
	# Run the specific suite
	runner = unittest.TextTestRunner()
	runner.run(suite)