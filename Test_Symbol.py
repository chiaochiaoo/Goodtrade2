from Symbol import *
from TradingPlan import *
from logging_module import *
import unittest
import unittest.mock as mock
from datetime import datetime, timedelta
import functools


def patch_both_datetimes(start_time: datetime):
    """
    Patch Symbol.datetime, TradingPlan.datetime, and logging_module.datetime
    to the SAME mutable clock. Also patches requests.get.

    Test signature stays the same:
        (self, mock_dt_symbol, mock_dt_tp, mock_get)

    Additional mock available as:
        self.mock_dt_logging
    """
    def decorator(test_func):
        @mock.patch('requests.post')
        @mock.patch('requests.get')
        @mock.patch('logging_module.datetime')
        @mock.patch('TradingPlan.datetime')
        @mock.patch('Symbol.datetime')
        @functools.wraps(test_func)
        def wrapper(self, mock_dt_symbol, mock_dt_tp, mock_dt_logging, mock_get, mock_post, *args, **kwargs):
            # shared mutable clock
            clock = {'t': start_time}

            def _now(tz=None):
                t = clock['t']
                return t if tz is None else t.replace(tzinfo=tz)

            for m in (mock_dt_symbol, mock_dt_tp, mock_dt_logging):
                m.now.side_effect = _now
                m.utcnow.side_effect = lambda: clock['t']

            # Link POST -> GET so tests only set mock_get.side_effect
            # (This lambda always uses the *current* mock_get.side_effect.)
            mock_post.side_effect = lambda *pa, **pkw: mock_get.side_effect(*pa, **pkw)

            # Expose helpers and the extra mock
            self._clock = clock
            self.advance_time = lambda **kw: clock.update(t=clock['t'] + timedelta(**kw))
            self.move_time = lambda new_t: clock.update(t=new_t)
            self.mock_dt_logging = mock_dt_logging

            # Optional convenience: set both GET/POST in one shot
            def _set_req_side_effect(fn):
                mock_get.side_effect = fn
                mock_post.side_effect = lambda *pa, **pkw: mock_get.side_effect(*pa, **pkw)
            self.set_requests_side_effect = _set_req_side_effect

            # Keep original test signature (do NOT pass mock_post)
            return test_func(self, mock_dt_symbol, mock_dt_tp, mock_get, *args, **kwargs)
        return wrapper
    return decorator

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
    if "GetLv1" in url:
        return MockResponse(json_data={"Responce": {"Success": "true", "Content": state.lv1_data}})
    elif "ExecuteOrder" in url:
        state.order_status = 'Accepted'
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
        print('TEST: state cancelled order received. Request granted.')
        return MockResponse(json_data={"Responce": {"Success": "true", "Content": ''}})
    else:
        return MockResponse(json_data={"error": "URL not recognized"}, status_code=404)


# ------------------------------
# Tests 
# ------------------------------

class BasicTests(unittest.TestCase):

    @patch_both_datetimes(datetime(2025, 8, 5, 9, 30, 0))
    def test_L1_Update_Module_Success(self, mock_dt_symbol, mock_dt_tp, mock_get):
        print("\n--- Running L1 Tests ---")
        state = TestState()
        mock_get.side_effect = lambda url, **kwargs: dynamic_mock_get(state, url, **kwargs)

        symbol = Symbol(manager=None, symbol="AMD.NQ")

        # Scenario 1
        state.lv1_data['BidPrice'] = "105.25"
        state.lv1_data['AskPrice'] = "105.30"
        symbol.l1_update_module()
        self.assertEqual(symbol.data['bid'], 105.25)
        self.assertEqual(symbol.data['ask'], 105.30)
        self.assertTrue(symbol.bid_change)
        self.assertTrue(symbol.ask_change)

        # Scenario 2
        state.lv1_data['BidPrice'] = "105.26"
        symbol.l1_update_module()
        self.assertEqual(symbol.data['bid'], 105.26)
        self.assertEqual(symbol.data['ask'], 105.30)
        self.assertTrue(symbol.bid_change)
        self.assertFalse(symbol.ask_change)

        # Scenario 3
        state.lv1_data['AskPrice'] = "105.31"
        symbol.l1_update_module()
        self.assertEqual(symbol.data['bid'], 105.26)
        self.assertEqual(symbol.data['ask'], 105.31)
        self.assertFalse(symbol.bid_change)
        self.assertTrue(symbol.ask_change)

        # Scenario 4
        state.lv1_data['BidPrice'] = "105.27"
        state.lv1_data['AskPrice'] = "105.32"
        symbol.l1_update_module()
        self.assertEqual(symbol.data['bid'], 105.27)
        self.assertEqual(symbol.data['ask'], 105.32)
        self.assertTrue(symbol.bid_change)
        self.assertTrue(symbol.ask_change)

        # Scenario 5
        symbol.l1_update_module()
        self.assertFalse(symbol.bid_change)
        self.assertFalse(symbol.ask_change)

    @patch_both_datetimes(datetime(2025, 8, 5, 9, 30, 0))
    def test_No_Request(self, mock_dt_symbol, mock_dt_tp, mock_get):
        print("\n--- Running test_path_no_request ---")
        state = TestState()
        state.lv1_data['InstrumentState'] = "Open"
        mock_get.side_effect = lambda url, **kwargs: dynamic_mock_get(state, url, **kwargs)

        ticker = 'AMD.NQ'
        symbol = Symbol(manager=mock.MagicMock(open_order_check=True), symbol=ticker)

        tp1 = TradingPlan(self, "AMD_TEST", {})
        tp1.register_symbol(ticker, symbol)

        symbol.symbol_inspection()

        self.assertFalse(symbol.order_out)
        self.assertEqual(symbol.order_pid, "")
        self.assertEqual(symbol.request, 0)

    @patch_both_datetimes(datetime(2025, 8, 5, 9, 30, 0))
    def test_Init_Order_On_New_Request(self, mock_dt_symbol, mock_dt_tp, mock_get):
        print("\n--- Running test_path_init_order_on_new_request ---")
        state = TestState()
        mock_get.side_effect = lambda url, **kwargs: dynamic_mock_get(state, url, **kwargs)

        ticker = 'AMD.NQ'
        symbol = Symbol(manager=mock.MagicMock(open_order_check=True), symbol=ticker)

        tp1 = TradingPlan(self, "AMD_TEST", {})
        tp1.register_symbol(ticker, symbol)
        tp1.submit_expected_shares(ticker, 10, False)

        state.order_pid = "mock_pid_123"
        state.order_id = "mock_id_456"
        state.order_status = "Accepted"
        state.fill_details = {}
        state.shares = 0
        state.target_share = 0

        symbol.symbol_inspection()

        self.assertTrue(symbol.order_out)
        self.assertEqual(symbol.order_pid, state.order_pid)
        self.assertEqual(symbol.request, 10)

        print('Checking---1', symbol.order_out, symbol.order_details, symbol.order_id)
        symbol.symbol_inspection()

        print('Checking---2', symbol.order_out, symbol.order_details, symbol.order_id)
        self.assertEqual(symbol.order_id, state.order_id)

    @patch_both_datetimes(datetime(2025, 8, 5, 9, 30, 0))
    def test_Multiple_Partial_Fills_Long(self, mock_dt_symbol, mock_dt_tp, mock_get):
        print("\n--- Running test_multiple_partial_fills_long:  ---")
        test_state = TestState()
        mock_get.side_effect = lambda url, **kwargs: dynamic_mock_get(test_state, url, **kwargs)

        ticker = 'AMD.NQ'
        symbol = Symbol(manager=mock.MagicMock(open_order_check=True), symbol=ticker)
        tp1 = TradingPlan(self, "AMD_TEST", {})
        tp1.register_symbol(ticker, symbol)
        tp1.submit_expected_shares(ticker, 10, False)

        symbol.symbol_inspection()
        self.assertTrue(symbol.order_out)
        self.assertEqual(symbol.order_pid, test_state.order_pid)

        test_state.order_status = "Accepted"
        test_state.fill_details = {}
        test_state.shares = 0

        symbol.symbol_inspection()
        self.assertEqual(symbol.request, 10)

        test_state.order_status = "Partially Filled"
        test_state.fill_details = {"105.25": 5}
        test_state.shares = 5
        symbol.symbol_inspection()
        self.assertEqual(symbol.request, 5)

        test_state.order_status = "Filled"
        test_state.fill_details = {"105.25": 5, '105.26': 5}
        test_state.shares = 10
        symbol.symbol_inspection()
        self.assertEqual(symbol.request, 0)
        self.assertFalse(symbol.order_out)

    @patch_both_datetimes(datetime(2025, 8, 5, 9, 30, 0))
    def test_Multiple_Partial_Fills_Short(self, mock_dt_symbol, mock_dt_tp, mock_get):
        print("\n--- Running test_multiple_partial_fills_short:  ---")
        test_state = TestState()
        mock_get.side_effect = lambda url, **kwargs: dynamic_mock_get(test_state, url, **kwargs)

        ticker = 'AMD.NQ'
        symbol = Symbol(manager=mock.MagicMock(open_order_check=True), symbol=ticker)
        tp1 = TradingPlan(self, "AMD_TEST", {})
        tp1.register_symbol(ticker, symbol)
        tp1.submit_expected_shares(ticker, -10, False)

        symbol.symbol_inspection()
        self.assertTrue(symbol.order_out)
        self.assertEqual(symbol.order_pid, test_state.order_pid)

        test_state.order_status = "Accepted"
        test_state.fill_details = {}
        test_state.shares = 0
        symbol.symbol_inspection()
        self.assertEqual(symbol.request, -10)

        test_state.order_status = "Partially Filled"
        test_state.fill_details = {"105.25": -5}
        test_state.shares = -5
        symbol.symbol_inspection()
        self.assertEqual(symbol.request, -5)

        test_state.order_status = "Partially Filled"
        test_state.fill_details = {"105.25": -5, '105.26': -3}
        test_state.shares = -8
        symbol.symbol_inspection()
        self.assertEqual(symbol.request, -2)
        self.assertTrue(symbol.order_out)

        test_state.order_status = "Multi Filled"
        test_state.fill_details = {"105.25": -5, '105.26': -3, '106.2': -2}
        test_state.shares = -10
        symbol.symbol_inspection()
        self.assertEqual(symbol.request, 0)
        self.assertFalse(symbol.order_out)

    @patch_both_datetimes(datetime(2025, 8, 5, 9, 30, 0))
    def test_Paritial_Fill_Cancel_Replace(self, mock_dt_symbol, mock_dt_tp, mock_get):
        print("\n--- Running test_Paritial_Fill_Cancel_Replace:  ---")
        test_state = TestState()
        test_state.lv1_data = {
            "BidPrice": "105.25",
            "AskPrice": "105.30",
            "MarketTime": "1672531200",
            "InstrumentState": "Open"
        }
        mock_get.side_effect = lambda url, **kwargs: dynamic_mock_get(test_state, url, **kwargs)

        ticker = 'AMD.NQ'
        symbol = Symbol(manager=mock.MagicMock(open_order_check=True), symbol=ticker)
        tp1 = TradingPlan(self, "AMD_TEST", {})
        tp1.register_symbol(ticker, symbol)
        tp1.submit_expected_shares(ticker, 10, False)

        symbol.symbol_inspection()
        self.assertTrue(symbol.order_out)
        self.assertEqual(symbol.order_pid, test_state.order_pid)

        test_state.order_status = "Accepted"
        test_state.fill_details = {}
        test_state.shares = 0
        symbol.symbol_inspection()
        self.assertEqual(symbol.request, 10)

        test_state.order_status = "Partially Filled"
        test_state.fill_details = {"105.25": 5}
        test_state.shares = 5
        symbol.symbol_inspection()
        self.assertEqual(symbol.request, 5)

        test_state.order_status = "Cancelled"
        test_state.fill_details = {"105.25": 5}
        test_state.shares = 5
        symbol.symbol_inspection()
        self.assertEqual(symbol.request, 5)
        self.assertTrue(symbol.order_out)

    @patch_both_datetimes(datetime(2025, 8, 5, 9, 30, 0))
    def test_Over_Fills(self, mock_dt_symbol, mock_dt_tp, mock_get):
        print("\n--- Running test_Over_Fills:  ---")
        test_state = TestState()
        test_state.lv1_data = {
            "BidPrice": "105.25",
            "AskPrice": "105.30",
            "MarketTime": "1672531200",
            "InstrumentState": "Open"
        }
        mock_get.side_effect = lambda url, **kwargs: dynamic_mock_get(test_state, url, **kwargs)

        ticker = 'AMD.NQ-overfill'
        symbol = Symbol(manager=mock.MagicMock(open_order_check=True), symbol=ticker)
        tp1 = TradingPlan(self, "AMD_TEST", {})
        tp1.register_symbol(ticker, symbol)
        tp1.submit_expected_shares(ticker, 10, False)

        symbol.symbol_inspection()
        self.assertTrue(symbol.order_out)
        self.assertEqual(symbol.order_pid, test_state.order_pid)

        test_state.order_status = "Accepted"
        test_state.fill_details = {}
        test_state.shares = 0
        symbol.symbol_inspection()
        self.assertEqual(symbol.request, 10)

        test_state.order_status = "Filled"
        test_state.fill_details = {"105.25": 15}
        test_state.shares = 15
        symbol.symbol_inspection()
        self.assertEqual(symbol.request, -5)

        test_state.order_status = "Filled"
        test_state.fill_details = {"105.26": -5}
        test_state.shares = -5
        symbol.symbol_inspection()
        self.assertEqual(symbol.request, 0)
        self.assertFalse(symbol.order_out)

    @patch_both_datetimes(datetime(2025, 8, 5, 9, 36, 0))
    def test_passive_to_aggressive_over_time(self, mock_dt_symbol, mock_dt_tp, mock_get):
        """As time passes with no fill, order is cancelled and re-placed more aggressively."""
        print("--- Running test_passive_to_aggressive_over_time ---")
        test_state = TestState()
        test_state.lv1_data = {
            "BidPrice": "105.25",
            "AskPrice": "105.30",
            "MarketTime": "1672531200",
            "InstrumentState": "Open"
        }
        mock_get.side_effect = lambda url, **kwargs: dynamic_mock_get(test_state, url, **kwargs)

        ticker = 'AMD.NQ-p2a'
        symbol = Symbol(manager=mock.MagicMock(open_order_check=True), symbol=ticker)
        tp1 = TradingPlan(self, "AMD_TEST", {})
        tp1.register_symbol(ticker, symbol)
        tp1.submit_expected_shares(ticker, 10, False)

        symbol.symbol_inspection()
        

        self.assertEqual(symbol.order_price, 105.25)
        self.assertTrue(symbol.order_out)

        self.advance_time(seconds=2)
        symbol.symbol_inspection()

        self.advance_time(seconds=2)
        symbol.symbol_inspection()

        #canceled
        self.advance_time(seconds=2)
        symbol.symbol_inspection()
        

        #replace
        self.advance_time(seconds=2)
        symbol.symbol_inspection()
        self.assertEqual(symbol.order_price, 105.26)

        self.advance_time(seconds=2)
        symbol.symbol_inspection()

        self.advance_time(seconds=2)
        symbol.symbol_inspection()

        
        self.advance_time(seconds=2)
        symbol.symbol_inspection()

         #canceled
        self.advance_time(seconds=2)
        symbol.symbol_inspection()

        self.advance_time(seconds=2)
        symbol.symbol_inspection()
        self.assertEqual(symbol.order_price, 105.28)

        self.advance_time(seconds=2)   
        symbol.symbol_inspection()

        self.advance_time(seconds=2)
        symbol.symbol_inspection()

        self.advance_time(seconds=2)
        symbol.symbol_inspection()

        self.advance_time(seconds=2) 
        symbol.symbol_inspection()

        self.advance_time(seconds=2)
        symbol.symbol_inspection()

        self.advance_time(seconds=2)
        symbol.symbol_inspection()
        self.assertEqual(symbol.order_price, 105.32)
        self.assertTrue(symbol.aggresive_ordering)
class Rejection_Tests(unittest.TestCase):

    @patch_both_datetimes(datetime(2025, 8, 5, 9, 30, 0))
    def test_on_long_rejected(self, mock_dt_symbol, mock_dt_tp, mock_get):
        print("\n--- Running test_on_long_rejected ---")
        state = TestState()
        state.lv1_data['BidPrice'] = "105.25"
        state.lv1_data['AskPrice'] = "105.26"
        state.order_pid = "mock_pid_123"
        state.order_id = "mock_id_456"
        state.order_status = ""
        mock_get.side_effect = lambda url, **kwargs: dynamic_mock_get(state, url, **kwargs)

        ticker = 'AMD.NQ-long-rejected'
        symbol = Symbol(manager=mock.MagicMock(open_order_check=True), symbol=ticker)

        tp1 = TradingPlan(self, "AMD_TEST", {})
        tp1.register_symbol(ticker, symbol)
        tp1.submit_expected_shares(ticker, 10, False)

        symbol.symbol_inspection()
        state.order_status = "Rejected"
        symbol.symbol_inspection()
        self.assertEqual(symbol.request, 0)
        self.assertFalse(symbol.order_out)

    @patch_both_datetimes(datetime(2025, 8, 5, 9, 30, 0))
    def test_on_short_rejected(self, mock_dt_symbol, mock_dt_tp, mock_get):
        print("\n--- Running test_on_short_rejected ---")
        state = TestState()
        state.lv1_data['BidPrice'] = "105.25"
        state.lv1_data['AskPrice'] = "105.26"
        state.order_pid = "mock_pid_123"
        state.order_id = "mock_id_456"
        state.order_status = ""
        mock_get.side_effect = lambda url, **kwargs: dynamic_mock_get(state, url, **kwargs)

        ticker = 'AMD.NQ-long-rejected'
        symbol = Symbol(manager=mock.MagicMock(open_order_check=True), symbol=ticker)

        tp1 = TradingPlan(self, "AMD_TEST", {})
        tp1.register_symbol(ticker, symbol)
        tp1.submit_expected_shares(ticker, -10, False)

        symbol.symbol_inspection()
        state.order_status = "Rejected"
        symbol.symbol_inspection()
        self.assertEqual(symbol.request, 0)
        self.assertFalse(symbol.order_out)

    @patch_both_datetimes(datetime(2025, 8, 5, 9, 30, 0))
    def test_on_long_out_short_rejected(self, mock_dt_symbol, mock_dt_tp, mock_get):
        print("\n--- Running test_on_long_out_short_rejected ---")
        state = TestState()
        state.lv1_data['BidPrice'] = "105.25"
        state.lv1_data['AskPrice'] = "105.26"
        state.order_pid = "mock_pid_123"
        state.order_id = "mock_id_456"
        state.order_status = ""
        mock_get.side_effect = lambda url, **kwargs: dynamic_mock_get(state, url, **kwargs)

        ticker = 'AMD.NQ-long-out-short-rejected'
        symbol = Symbol(manager=mock.MagicMock(open_order_check=True), symbol=ticker)

        tp1 = TradingPlan(self, "AMD_TEST", {})
        tp1.register_symbol(ticker, symbol)
        tp1.submit_expected_shares(ticker, 10, False)

        tp2 = TradingPlan(self, "AMD_TEST2", {})
        tp2.register_symbol(ticker, symbol)
        tp2.submit_expected_shares(ticker, -5, False)

        state.order_status = "Accepted"
        state.fill_details = {}
        state.shares = 0
        state.target_share = 0

        symbol.symbol_inspection()
        self.assertEqual(symbol.order_price, 105.25)
        self.assertEqual(symbol.request, 5)

        state.lv1_data['BidPrice'] = "105.26"
        state.lv1_data['AskPrice'] = "105.27"

        print('\n', 1)
        symbol.symbol_inspection()

        state.order_id = 'Order1'
        state.fill_details = {105.26: 5}
        state.shares = 5
        state.target_share = 5
        state.order_status = 'Filled'

        print('\n', 2)
        symbol.symbol_inspection()

        self.assertEqual(symbol.request, 0)
        self.assertFalse(symbol.order_out)

        print('\n', 3)
        tp1.submit_expected_shares(ticker, 0, False)
        symbol.symbol_inspection()
        self.assertEqual(symbol.request, -10)

        state.order_id = 'Order2'
        state.fill_details = {105.26: -5}
        state.shares = -5
        state.target_share = -5
        state.order_status = 'Filled'

        print('\n', 4)
        symbol.symbol_inspection()
        self.assertEqual(symbol.request, -5)
        self.assertTrue(symbol.order_out)

        state.order_id = 'Order2'
        state.fill_details = {}
        state.shares = 0
        state.target_share = 0
        state.order_status = 'Rejected'

        print('\n', 5)
        symbol.symbol_inspection()
        self.assertEqual(symbol.request, 0)
        self.assertFalse(symbol.order_out)

        print('\n', 6)
        symbol.symbol_inspection()
        self.assertEqual(symbol.request, 0)
        self.assertFalse(symbol.order_out)

        symbol.symbol_inspection()

class Multi_Tp_Tests(unittest.TestCase):

    @patch_both_datetimes(datetime(2025, 8, 5, 9, 30, 0))
    def test_2_tp_same_side_long(self, mock_dt_symbol, mock_dt_tp, mock_get):
        print("\n--- Running test_2_tp_same_side_long ---")
        state = TestState()
        state.lv1_data['BidPrice'] = "105.25"
        state.lv1_data['AskPrice'] = "105.26"
        state.order_pid = "mock_pid_123"
        state.order_id = "mock_id_456"
        state.order_status = ""
        mock_get.side_effect = lambda url, **kwargs: dynamic_mock_get(state, url, **kwargs)

        ticker = 'AMD.NQ-same-long'
        symbol = Symbol(manager=mock.MagicMock(open_order_check=True), symbol=ticker)

        tp1 = TradingPlan(self, "AMD_TEST", {})
        tp1.register_symbol(ticker, symbol)
        tp1.submit_expected_shares(ticker, 10, False)

        tp2 = TradingPlan(self, "AMD_TEST2", {})
        tp2.register_symbol(ticker, symbol)
        tp2.submit_expected_shares(ticker, 5, False)

        state.order_status = "Accepted"
        state.fill_details = {}
        state.shares = 0
        state.target_share = 0

        symbol.symbol_inspection()
        self.assertEqual(symbol.order_price, 105.25)
        self.assertEqual(symbol.request, 15)

        state.lv1_data['BidPrice'] = "105.26"
        state.lv1_data['AskPrice'] = "105.27"
        symbol.symbol_inspection()  # cancel
        symbol.symbol_inspection()  # replace

        state.order_pid = "mock_pid_123"
        state.order_id = "mock_id_456"
        state.order_status = "Accepted"
        symbol.symbol_inspection()

        state.fill_details = {105.26: 10}
        state.shares = 10
        state.target_share = 10
        state.order_status = 'Partially Filled'
        symbol.symbol_inspection()
        self.assertEqual(symbol.request, 5)

        state.fill_details = {105.26: 15}
        state.shares = 15
        state.target_share = 15
        state.order_status = 'Multi Filled'
        symbol.symbol_inspection()
        self.assertEqual(symbol.request, 0)
        self.assertFalse(symbol.order_out)

    @patch_both_datetimes(datetime(2025, 8, 5, 9, 30, 0))
    def test_2_tp_same_side_short(self, mock_dt_symbol, mock_dt_tp, mock_get):
        print("\n--- Running test_2_tp_same_side_short ---")
        state = TestState()
        state.lv1_data['BidPrice'] = "105.25"
        state.lv1_data['AskPrice'] = "105.26"
        state.order_pid = "mock_pid_123"
        state.order_id = "mock_id_456"
        state.order_status = ""
        mock_get.side_effect = lambda url, **kwargs: dynamic_mock_get(state, url, **kwargs)

        ticker = 'AMD.NQ-same-short'
        symbol = Symbol(manager=mock.MagicMock(open_order_check=True), symbol=ticker)

        tp1 = TradingPlan(self, "AMD_TEST", {})
        tp1.register_symbol(ticker, symbol)
        tp1.submit_expected_shares(ticker, -10, False)

        tp2 = TradingPlan(self, "AMD_TEST2", {})
        tp2.register_symbol(ticker, symbol)
        tp2.submit_expected_shares(ticker, -5, False)

        state.order_status = "Accepted"
        state.fill_details = {}
        state.shares = 0
        state.target_share = 0

        symbol.symbol_inspection()
        self.assertEqual(symbol.order_price, 105.26)
        self.assertEqual(symbol.request, -15)

        state.lv1_data['BidPrice'] = "105.26"
        state.lv1_data['AskPrice'] = "105.27"
        symbol.symbol_inspection()  # cancel
        symbol.symbol_inspection()  # replace

        state.order_pid = "mock_pid_123"
        state.order_id = "mock_id_456"
        state.order_status = "Accepted"
        symbol.symbol_inspection()

        state.fill_details = {105.26: -10}
        state.shares = -10
        state.target_share = -10
        state.order_status = 'Partially Filled'
        symbol.symbol_inspection()
        self.assertEqual(symbol.request, -5)

        state.fill_details = {105.26: -15}
        state.shares = -15
        state.target_share = -15
        state.order_status = 'Multi Filled'
        symbol.symbol_inspection()
        self.assertEqual(symbol.request, 0)
        self.assertFalse(symbol.order_out)

    @patch_both_datetimes(datetime(2025, 8, 5, 9, 30, 0))
    def test_2_tp_pairing(self, mock_dt_symbol, mock_dt_tp, mock_get):
        print("\n--- Running test_2_tp_diverging ---")
        state = TestState()
        state.lv1_data['BidPrice'] = "105.25"
        state.lv1_data['AskPrice'] = "105.26"
        state.order_pid = "mock_pid_123"
        state.order_id = "mock_id_456"
        state.order_status = ""
        mock_get.side_effect = lambda url, **kwargs: dynamic_mock_get(state, url, **kwargs)

        ticker = 'AMD.NQ-pairing test'
        symbol = Symbol(manager=mock.MagicMock(open_order_check=True), symbol=ticker)
        symbol.symbol_inspection()

        tp1 = TradingPlan(self, "AMD_LONG", {})
        tp1.register_symbol(ticker, symbol)
        tp1.submit_expected_shares(ticker, 10, False)

        tp2 = TradingPlan(self, "AMD_SHORT", {})
        tp2.register_symbol(ticker, symbol)
        tp2.submit_expected_shares(ticker, -5, False)

        state.fill_details = {}
        state.shares = 0
        state.target_share = 0

        print('\n', 1)
        symbol.symbol_inspection()
        self.assertEqual(symbol.order_price, 105.25)
        self.assertEqual(symbol.request, 5)

        state.lv1_data['BidPrice'] = "105.26"
        state.lv1_data['AskPrice'] = "105.27"
        state.order_pid = "mock_pid_123"
        state.order_id = "mock_id_456"
        state.order_status = "Accepted"
        print(f'\n 2 ')
        symbol.symbol_inspection()

        state.fill_details = {105.26: 10}
        state.shares = 10
        state.target_share = 10
        state.order_status = 'Multi Filled'
        print(f'\n 3 ')
        symbol.symbol_inspection()
        self.assertEqual(symbol.request, -5)

        state.fill_details = {105.27: 15}
        state.shares = 15
        state.target_share = 15
        state.order_status = 'Filled'
        print(f'\n 4 ')
        symbol.symbol_inspection()
        self.assertEqual(symbol.request, -20)
        self.assertTrue(symbol.order_out)

        print(f'\n 5 ')
        symbol.symbol_inspection()

    @patch_both_datetimes(datetime(2025, 8, 5, 9, 30, 0))
    def test_2_tp_same_side_1_out(self, mock_dt_symbol, mock_dt_tp, mock_get):
        print("\n--- Running test_2_tp_same_side_1_out ---")
        state = TestState()
        state.lv1_data['BidPrice'] = "105.25"
        state.lv1_data['AskPrice'] = "105.26"
        state.order_pid = "mock_pid_123"
        state.order_id = "mock_id_456"
        state.order_status = ""
        mock_get.side_effect = lambda url, **kwargs: dynamic_mock_get(state, url, **kwargs)

        ticker = 'AMD.NQ-1-out'
        symbol = Symbol(manager=mock.MagicMock(open_order_check=True), symbol=ticker)

        tp1 = TradingPlan(self, "AMD_TEST", {})
        tp1.register_symbol(ticker, symbol)
        tp1.submit_expected_shares(ticker, 10, False)

        tp2 = TradingPlan(self, "AMD_TEST2", {})
        tp2.register_symbol(ticker, symbol)
        tp2.submit_expected_shares(ticker, 5, False)

        state.order_status = "Accepted"
        state.fill_details = {}
        state.shares = 0
        state.target_share = 0

        symbol.symbol_inspection()
        self.assertEqual(symbol.order_price, 105.25)
        self.assertEqual(symbol.request, 15)

        state.lv1_data['BidPrice'] = "105.26"
        state.lv1_data['AskPrice'] = "105.27"
        print('\n', 1)
        symbol.symbol_inspection()

        state.order_id = 'Order1'
        state.fill_details = {105.26: 15}
        state.shares = 15
        state.target_share = 15
        state.order_status = 'Filled'
        print('\n', 2)
        symbol.symbol_inspection()

        print('\n', 3)
        tp2.submit_expected_shares(ticker, 0, False)
        symbol.symbol_inspection()
        self.assertEqual(symbol.request, -5)

        state.order_id = 'Order2'
        state.fill_details = {105.26: -5}
        state.shares = -5
        state.target_share = -5
        state.order_status = 'Filled'

        tp1.submit_expected_shares(ticker, 0, False)
        symbol.symbol_inspection()

        state.order_id = 'Order3'
        state.fill_details = {105.27: -10}
        state.shares = -10
        state.target_share = -10
        state.order_status = 'Filled'
        symbol.symbol_inspection()
        self.assertEqual(symbol.request, 0)
        self.assertFalse(symbol.order_out)

    @patch_both_datetimes(datetime(2025, 8, 5, 9, 30, 0))
    def test_2_tp_diverging_side_short_out(self, mock_dt_symbol, mock_dt_tp, mock_get):
        print("\n--- Running test_2_tp_diverging_side_short_out ---")
        state = TestState()
        state.lv1_data['BidPrice'] = "105.25"
        state.lv1_data['AskPrice'] = "105.26"
        state.order_pid = "mock_pid_123"
        state.order_id = "mock_id_456"
        state.order_status = ""
        mock_get.side_effect = lambda url, **kwargs: dynamic_mock_get(state, url, **kwargs)

        ticker = 'AMD.NQ-div-short-out'
        symbol = Symbol(manager=mock.MagicMock(open_order_check=True), symbol=ticker)

        tp1 = TradingPlan(self, "AMD_TEST", {})
        tp1.register_symbol(ticker, symbol)
        tp1.submit_expected_shares(ticker, 10, False)

        tp2 = TradingPlan(self, "AMD_TEST2", {})
        tp2.register_symbol(ticker, symbol)
        tp2.submit_expected_shares(ticker, -5, False)

        state.order_status = "Accepted"
        state.fill_details = {}
        state.shares = 0
        state.target_share = 0

        symbol.symbol_inspection()
        self.assertEqual(symbol.order_price, 105.25)
        self.assertEqual(symbol.request, 5)

        state.lv1_data['BidPrice'] = "105.26"
        state.lv1_data['AskPrice'] = "105.27"
        print('\n', 1)
        symbol.symbol_inspection()

        state.order_id = 'Order1'
        state.fill_details = {105.26: 5}
        state.shares = 5
        state.target_share = 5
        state.order_status = 'Filled'
        print('\n', 2)
        symbol.symbol_inspection()
        self.assertEqual(symbol.request, 0)
        self.assertFalse(symbol.order_out)

        print('\n', 3)
        tp2.submit_expected_shares(ticker, 0, False)
        symbol.symbol_inspection()
        self.assertEqual(symbol.request, 5)

        state.order_id = 'Order2'
        state.fill_details = {105.26: 5}
        state.shares = 5
        state.target_share = 5
        state.order_status = 'Filled'
        symbol.symbol_inspection()
        self.assertEqual(symbol.request, 0)
        self.assertFalse(symbol.order_out)

    @patch_both_datetimes(datetime(2025, 8, 5, 9, 30, 0))
    def test_2_tp_diverging_side_long_out(self, mock_dt_symbol, mock_dt_tp, mock_get):
        print("\n--- Running test_2_tp_diverging_side_long_out ---")
        state = TestState()
        state.lv1_data['BidPrice'] = "105.25"
        state.lv1_data['AskPrice'] = "105.26"
        state.order_pid = "mock_pid_123"
        state.order_id = "mock_id_456"
        state.order_status = ""
        mock_get.side_effect = lambda url, **kwargs: dynamic_mock_get(state, url, **kwargs)

        ticker = 'AMD.NQ-div-short-out'
        symbol = Symbol(manager=mock.MagicMock(open_order_check=True), symbol=ticker)

        tp1 = TradingPlan(self, "AMD_TEST", {})
        tp1.register_symbol(ticker, symbol)
        tp1.submit_expected_shares(ticker, 10, False)

        tp2 = TradingPlan(self, "AMD_TEST2", {})
        tp2.register_symbol(ticker, symbol)
        tp2.submit_expected_shares(ticker, -5, False)

        state.order_status = "Accepted"
        state.fill_details = {}
        state.shares = 0
        state.target_share = 0

        symbol.symbol_inspection()
        self.assertEqual(symbol.order_price, 105.25)
        self.assertEqual(symbol.request, 5)

        state.lv1_data['BidPrice'] = "105.26"
        state.lv1_data['AskPrice'] = "105.27"
        print('\n', 1)
        symbol.symbol_inspection()

        state.order_id = 'Order1'
        state.fill_details = {105.26: 5}
        state.shares = 5
        state.target_share = 5
        state.order_status = 'Filled'
        print('\n', 2)
        symbol.symbol_inspection()
        self.assertEqual(symbol.request, 0)
        self.assertFalse(symbol.order_out)

        print('\n', 3)
        tp1.submit_expected_shares(ticker, 0, False)
        symbol.symbol_inspection()
        self.assertEqual(symbol.request, -10)

        state.order_id = 'Order2'
        state.fill_details = {105.26: -10}
        state.shares = -10
        state.target_share = -10
        state.order_status = 'Filled'
        symbol.symbol_inspection()
        self.assertEqual(symbol.request, 0)
        self.assertFalse(symbol.order_out)
        self.assertEqual(symbol.tp_current_shares, -5)


class TestOrderPlacingAndCancel(unittest.TestCase):

    @patch_both_datetimes(datetime(2025, 8, 5, 15, 49, 50))
    def test_order_place_and_cancel(self, mock_dt_symbol, mock_dt_tp, mock_get):
        print("\n--- Running test_l1_update_module_successx Test ---")
        state = TestState()
        mock_get.side_effect = lambda url, **kw: dynamic_mock_get(state, url, **kw)

        ticker = "AMD-replace"
        symbol = Symbol(manager=mock.MagicMock(open_order_check=True), symbol=ticker)
        symbol.symbol_inspection()

        tp1 = TradingPlan(self, "AMD_TEST", {})
        tp1.register_symbol(ticker, symbol)
        tp1.submit_expected_shares(ticker, 10, False)

        state.lv1_data['BidPrice'] = "105.25"
        state.lv1_data['AskPrice'] = "105.26"
        state.order_pid = "mock_pid_123"
        state.order_id = "mock_id_456"
        state.order_status = "Accepted"
        state.fill_details = {}
        state.shares = 0
        state.target_share = 0

        symbol.symbol_inspection()
        self.assertEqual(symbol.order_price, 105.25)
        self.assertEqual(symbol.request, 10)

        state.lv1_data['BidPrice'] = "105.26"
        state.lv1_data['AskPrice'] = "105.27"
        symbol.symbol_inspection()  # cancel
        symbol.symbol_inspection()  # replace

        state.order_pid = "mock_pid_123"
        state.order_id = "mock_id_456"
        state.order_status = "Accepted"
        symbol.symbol_inspection()


class Test_MOC_Basics(unittest.TestCase):

    @patch_both_datetimes(datetime(2025, 8, 5, 15, 49, 50))
    def test_moc_long_no_orders(self, mock_dt_symbol, mock_dt_tp, mock_get):
        state = TestState()
        mock_get.side_effect = lambda url, **kw: dynamic_mock_get(state, url, **kw)

        ticker = "AMD.NQ"
        symbol = Symbol(manager=mock.MagicMock(open_order_check=True), symbol="AMD.NQ")
        symbol.symbol_inspection()

        tp1 = TradingPlan(self, "TP1", {})
        tp1.register_symbol("AMD.NQ", symbol)
        tp1.submit_expected_shares(ticker, 10, False)
        symbol.symbol_inspection()

        state.lv1_data['BidPrice'] = "105.25"
        state.lv1_data['AskPrice'] = "105.26"
        state.order_id = 'Order2'
        state.fill_details = {105.26: 10}
        state.shares = 10
        state.target_share = 10
        state.order_status = 'Filled'

        symbol.symbol_inspection()
        symbol.symbol_inspection()

        symbol.time_to_moc("ARCA ACTION ARCX Market MOC DAY")
        symbol.symbol_inspection()

        self.assertTrue(symbol.moc_order_out)
        self.assertTrue(symbol.order_out)

        state.order_status = "Filled"
        state.order_id = "moc123"
        state.fill_details = {105.25: -10}
        state.shares = -10
        state.target_share = -10

        symbol.symbol_inspection()
        self.assertEqual(symbol.tp_current_shares, 10)
        self.assertEqual(symbol.request, -10)
        self.assertFalse(symbol.order_out)
        self.assertTrue(symbol.moc_order_out)


class Test_Limit_Orders(unittest.TestCase):
    """
    Flow under test (per TP, per symbol):

      Order Exists?
        N -> Send Order
        Y -> Is it terminated?
              Y -> Is it filled?
                    Y -> Add to TP, Tag Finish
                    N -> (cancelled/rejected) -> Finish (clear LR)
              N -> Has the timer expired?
                    Y -> Cancel
                    N -> Has the price changed?
                          Y -> Cancel
                          N -> Do nothing
    """

    def _mk_symbol_and_tp(self, ticker="AMD.NQ"):
        sym = Symbol(manager=mock.MagicMock(open_order_check=True), symbol=ticker)
        tp = TradingPlan(self, "TP_LIMIT_TEST", {})
        tp.register_symbol(ticker, sym)
        return sym, tp

    # @patch_both_datetimes(datetime(2025, 8, 5, 9, 30, 0))
    # def test_send_order_when_no_existing_order(self, mock_dt_symbol, mock_dt_tp, mock_get):
    #     state = TestState()
    #     state.order_pid = "mock_pid_123"
    #     state.order_id = "mock_id_456"
    #     mock_get.side_effect = lambda url, **kw: dynamic_mock_get(state, url, **kw)

    #     sym, tp = self._mk_symbol_and_tp("AMD.NQ-LR-send")
    #     tp.submit_limit_request(sym.symbol_name, 10, 105.26)
    #     sym.symbol_inspection()

    #     lr = tp.data['limit_request'][sym.symbol_name]
    #     self.assertEqual(lr.get('pid'), state.order_pid)
    #     self.assertEqual(lr.get('status'), '')
    #     self.assertEqual(lr.get('order_price'), 105.26)
    #     self.assertTrue(lr.get('ts', 0) > 0)

    #     state.order_status = "Accepted"
    #     state.fill_details = {}
    #     state.shares = 0
    #     state.target_share = 0
    #     sym.symbol_inspection()
    #     lr = tp.data['limit_request'][sym.symbol_name]
    #     sym.symbol_inspection()

    # @patch_both_datetimes(datetime(2025, 8, 5, 10, 30, 0))
    # def test_timer_expired_triggers_cancel(self, mock_dt_symbol, mock_dt_tp, mock_get):
    #     state = TestState()
    #     state.order_pid = "mock_pid_123"
    #     state.order_id = "mock_id_456"
    #     mock_get.side_effect = lambda url, **kw: dynamic_mock_get(state, url, **kw)

    #     sym, tp = self._mk_symbol_and_tp("AMD.NQ-LR-send")
    #     tp.submit_limit_request(sym.symbol_name, 10, 105.26)
    #     tp.info['timer'] = 900
    #     sym.symbol_inspection()

    #     lr = tp.data['limit_request'][sym.symbol_name]
    #     self.assertEqual(lr.get('pid'), state.order_pid)
    #     self.assertEqual(lr.get('status'), '')
    #     self.assertEqual(lr.get('order_price'), 105.26)
    #     self.assertTrue(lr.get('ts', 0) > 0)

    #     state.order_status = "Accepted"
    #     state.fill_details = {}
    #     state.shares = 0
    #     state.target_share = 0
    #     sym.symbol_inspection()
    #     lr = tp.data['limit_request'][sym.symbol_name]
    #     self.assertEqual(lr.get('status'), 'Accepted')
    #     sym.symbol_inspection()

    #     tp.info['timer'] = 600
    #     sym.symbol_inspection()   # start cancel
    #     sym.symbol_inspection()
    #     lr = tp.data['limit_request'][sym.symbol_name]
    #     self.assertEqual(lr.get('status'), 'Cancelled')
    #     sym.symbol_inspection()

    @patch_both_datetimes(datetime(2025, 8, 5, 10, 30, 0))
    def test_price_change_triggers_cancel(self, mock_dt_symbol, mock_dt_tp, mock_get):
        state = TestState()
        state.order_pid = "mock_pid_123"
        state.order_id = "mock_id_456"
        mock_get.side_effect = lambda url, **kw: dynamic_mock_get(state, url, **kw)

        sym, tp = self._mk_symbol_and_tp("AMD.NQ-PRICE")
        tp.submit_limit_request(sym.symbol_name, 10, 105.26)
        tp.info['timer'] = 900
        sym.symbol_inspection()

        lr = tp.data['limit_request'][sym.symbol_name]
        self.assertEqual(lr.get('pid'), state.order_pid)
        self.assertEqual(lr.get('status'), '')
        self.assertEqual(lr.get('order_price'), 105.26)
        self.assertTrue(lr.get('ts', 0) > 0)

        state.order_status = "Accepted"
        state.fill_details = {}
        state.shares = 0
        state.target_share = 0
        sym.symbol_inspection()
        lr = tp.data['limit_request'][sym.symbol_name]
        self.assertEqual(lr.get('status'), 'Accepted')

        tp.submit_limit_request(sym.symbol_name, 10, 105.2)
        ### PRICE SHOULD BE CHANGED.

        sym.symbol_inspection()   # cancel
        sym.symbol_inspection()   # replace
        self.assertEqual(lr.get('status'), 'Cancelled')
        sym.symbol_inspection()   # new send
        sym.symbol_inspection()
        self.assertEqual(lr.get('status'), 'Accepted')

    @patch_both_datetimes(datetime(2025, 8, 5, 10, 30, 0))
    def test_terminated_filled_allocates_and_clears(self, mock_dt_symbol, mock_dt_tp, mock_get):
        state = TestState()
        state.order_pid = "mock_pid_123"
        state.order_id = "mock_id_456"
        mock_get.side_effect = lambda url, **kw: dynamic_mock_get(state, url, **kw)

        sym, tp = self._mk_symbol_and_tp("AMD.NQ-PRICE")
        tp.submit_limit_request(sym.symbol_name, 10, 105.26)
        tp.info['timer'] = 900
        sym.symbol_inspection()

        lr = tp.data['limit_request'][sym.symbol_name]
        self.assertEqual(lr.get('pid'), state.order_pid)
        self.assertEqual(lr.get('status'), '')
        self.assertEqual(lr.get('order_price'), 105.26)
        self.assertTrue(lr.get('ts', 0) > 0)

        state.order_status = "Accepted"
        state.fill_details = {}
        state.shares = 0
        state.target_share = 0
        sym.symbol_inspection()
        lr = tp.data['limit_request'][sym.symbol_name]
        self.assertEqual(lr.get('status'), 'Accepted')
        sym.symbol_inspection()
        sym.symbol_inspection()

        state.fill_details = {105.26: 10}
        state.shares = 10
        state.target_share = 10
        state.order_status = "Filled"
        sym.symbol_inspection()

        self.assertEqual(tp.data['current_shares'][sym.symbol_name], 10)
        lr = tp.data['limit_request'][sym.symbol_name]
        self.assertEqual(lr.get('status', ''), 'Filled')
        self.assertEqual(lr.get('pid', ''), '')
        self.assertEqual(lr.get('oid', ''), '')
        sym.symbol_inspection()

    @patch_both_datetimes(datetime(2025, 8, 5, 9, 30, 0))
    def test_terminated_cancelled_clears(self, mock_dt_symbol, mock_dt_tp, mock_get):
        state = TestState()
        mock_get.side_effect = lambda url, **kw: dynamic_mock_get(state, url, **kw)

        sym, tp = self._mk_symbol_and_tp("AMD.NQ-LR-cancelled")
        tp.submit_limit_request(sym.symbol_name, 10, 105.26)
        sym.symbol_inspection()

        state.order_status = "Cancelled"
        sym.symbol_inspection()

        lr = tp.data['limit_request'][sym.symbol_name]
        self.assertEqual(lr.get('status', ''), 'Cancelled')
        self.assertEqual(lr.get('pid', ''), '')
        self.assertEqual(lr.get('oid', ''), '')

    @patch_both_datetimes(datetime(2025, 8, 5, 9, 30, 0))
    def test_terminated_rejected_clears(self, mock_dt_symbol, mock_dt_tp, mock_get):
        state = TestState()
        mock_get.side_effect = lambda url, **kw: dynamic_mock_get(state, url, **kw)

        sym, tp = self._mk_symbol_and_tp("AMD.NQ-LR-rejected")
        tp.submit_limit_request(sym.symbol_name, 10, 105.26)
        sym.symbol_inspection()

        state.order_status = "Rejected"
        sym.symbol_inspection()

        lr = tp.data['limit_request'][sym.symbol_name]
        self.assertEqual(lr.get('status', ''), '')
        self.assertEqual(lr.get('pid', ''), '')
        self.assertEqual(lr.get('oid', ''), '')


class AlgoManagement:
    def __init__(self):
        self.tradingplans = {}

    def register_tradingplan(self, name: str, tp: TradingPlan):
        """Attach a TradingPlan under management."""
        self.tradingplans[name] = tp

    def get_total_unreal(self) -> float:
        return sum(tp.data['unreal'] for tp in self.tradingplans.values())

    def get_total_realized(self) -> float:
        return sum(tp.data['realized'] for tp in self.tradingplans.values())

    def check_all_pnls(self):
        """Run PnL checks on all trading plans (triggering stop/profit logic)."""
        for tp in self.tradingplans.values():
            tp.check_pnl()

            print('Check PNL:',tp.algo_name,tp.data[UNREAL])

    def summary(self):
        out = {}
        for name, tp in self.tradingplans.items():
            out[name] = {
                "unreal": tp.data['unreal'],
                "real": tp.data['realized'],
                "profit_threshold": tp.profit,
                "stop_threshold": tp.stop,
                "status": tp.data['status'],
            }
        return out

class Test_AlgoManagement(unittest.TestCase):

    @patch_both_datetimes(datetime(2025, 8, 5, 10, 0, 0))
    def test_profit(self, mock_dt_symbol, mock_dt_tp, mock_get):
        state = TestState()
        mock_get.side_effect = lambda url, **kw: dynamic_mock_get(state, url, **kw)

        # Setup symbol + TP

        ticker = "AMD-Profit-Test"
        symbol = Symbol(manager=mock.MagicMock(open_order_check=True), symbol=ticker)
        tp = TradingPlan(self, "TP1", {"Profit": 5, "Stop": 5})
        tp.register_symbol(ticker, symbol)

        # Attach to AlgoManagement
        manager = AlgoManagement()
        manager.register_tradingplan("TP1", tp)

        # Fake some fills -> long 10 @ 105.0
        tp.submit_expected_shares(ticker, 100, False)

        # Update L1 price higher (simulate profit)

        symbol.symbol_inspection()

        state.order_status = "Filled"
        state.fill_details = {"105.25": 100}
        state.shares = 100
        state.order_id = 'Order2'
        state.target_share = 100


        
        state.lv1_data['BidPrice'] = "105.25"
        state.lv1_data['AskPrice'] = "105.26"
        symbol.symbol_inspection()

        manager.check_all_pnls()

        state.lv1_data['BidPrice'] = "105.26"
        state.lv1_data['AskPrice'] = "105.27"
        symbol.symbol_inspection()
        
        manager.check_all_pnls()
        self.assertEqual(tp.data['unreal'], 1.)


        state.lv1_data['BidPrice'] = "105.29"
        state.lv1_data['AskPrice'] = "105.30"
        symbol.symbol_inspection()
        
        manager.check_all_pnls()
        self.assertEqual(tp.data['unreal'], 4.)

        #summary = manager.summary()
        #self.assertGreater(summary['TP1']['unreal'], 0)
        #self.assertEqual(tp.data['status'], 'FLATTENING')  # because profit hit
        state.lv1_data['BidPrice'] = "105.30"
        state.lv1_data['AskPrice'] = "105.31"

        self.advance_time(seconds=60)
        symbol.symbol_inspection()
        manager.check_all_pnls()
        symbol.symbol_inspection()
        self.assertEqual(tp.data['unreal'], 5.)

        self.assertEqual(tp.data['expected_shares']['AMD-Profit-Test'], 50)
        self.assertEqual(tp.data['current_request']['AMD-Profit-Test'], -50)
        self.assertEqual(tp.data['unreal'], 5.)
        self.assertEqual(tp.data['status'], 'RUNNING')
        self.assertEqual(symbol.aggresive_ordering, False)
        symbol.symbol_inspection()
        # trigger out.
        state.order_pid = "mock_pid_123s"
        state.order_id = "mock_id_456s"
        state.order_status = "Accepted"
        state.fill_details = {}
        # state.shares = -100
        # state.order_id = 'Order2'
        # state.target_share = -100

        symbol.symbol_inspection()
        symbol.symbol_inspection()

        state.order_pid = "mock_pid_123s"
        state.order_id = "mock_id_456s"
        state.order_status = "Filled"
        state.fill_details = {"105.25": -100}
        state.shares = -100
        state.order_id = 'Order2'
        state.target_share = -100

        symbol.symbol_inspection()
        symbol.symbol_inspection()
        #print(tp.data)


    @patch_both_datetimes(datetime(2025, 8, 5, 10, 0, 0))
    def test_stop(self, mock_dt_symbol, mock_dt_tp, mock_get):
        state = TestState()
        mock_get.side_effect = lambda url, **kw: dynamic_mock_get(state, url, **kw)

        # Setup symbol + TP

        ticker = "AMD-Stop-Test"
        symbol = Symbol(manager=mock.MagicMock(open_order_check=True), symbol=ticker)
        tp = TradingPlan(self, "TP1", {"Profit": 5, "Stop": 5})
        tp.register_symbol(ticker, symbol)

        # Attach to AlgoManagement
        manager = AlgoManagement()
        manager.register_tradingplan("TP1", tp)

        # Fake some fills -> long 10 @ 105.0
        tp.submit_expected_shares(ticker, 100, False)

        # Update L1 price higher (simulate profit)

        symbol.symbol_inspection()

        state.order_status = "Filled"
        state.fill_details = {"105.25": 100}
        state.shares = 100
        state.order_id = 'Order2'
        state.target_share = 100


        
        state.lv1_data['BidPrice'] = "105.25"
        state.lv1_data['AskPrice'] = "105.26"
        symbol.symbol_inspection()

        manager.check_all_pnls()

        state.lv1_data['BidPrice'] = "105.26"
        state.lv1_data['AskPrice'] = "105.27"
        symbol.symbol_inspection()
        
        manager.check_all_pnls()
        self.assertEqual(tp.data['unreal'], 1.)


        state.lv1_data['BidPrice'] = "105.29"
        state.lv1_data['AskPrice'] = "105.30"
        symbol.symbol_inspection()
        
        manager.check_all_pnls()
        self.assertEqual(tp.data['unreal'], 4.)

        #summary = manager.summary()
        #self.assertGreater(summary['TP1']['unreal'], 0)
        #self.assertEqual(tp.data['status'], 'FLATTENING')  # because profit hit
        state.lv1_data['BidPrice'] = "105.19"
        state.lv1_data['AskPrice'] = "105.20"

        self.advance_time(seconds=60)
        symbol.symbol_inspection()
        manager.check_all_pnls()
        symbol.symbol_inspection()
        print(tp.data)
        self.assertEqual(tp.data['unreal'], -6.)
        self.assertEqual(tp.data['expected_shares']['AMD-Stop-Test'], 0)
        self.assertEqual(tp.data['current_request']['AMD-Stop-Test'], -100)
        self.assertEqual(tp.data['unreal'], -6.)
        self.assertEqual(tp.data['status'], 'FLATTENING')
        self.assertEqual(symbol.aggresive_ordering, True)
        symbol.symbol_inspection()
        # trigger out.
        state.order_pid = "mock_pid_123s"
        state.order_id = "mock_id_456s"
        state.order_status = "Accepted"
        state.fill_details = {}
        # state.shares = -100
        # state.order_id = 'Order2'
        # state.target_share = -100

        symbol.symbol_inspection()
        symbol.symbol_inspection()

        state.order_pid = "mock_pid_123s"
        state.order_id = "mock_id_456s"
        state.order_status = "Filled"
        state.fill_details = {"105.25": -100}
        state.shares = -100
        state.order_id = 'Order2'
        state.target_share = -100

        symbol.symbol_inspection()
        symbol.symbol_inspection()
        #print(tp.data)
if __name__ == "__main__":
    root = tk.Tk()

    #unittest.main()

    suite = unittest.TestSuite()
    
    # Load only the tests from TestOrderPlacingAndCancel

    suite.addTest(unittest.makeSuite(BasicTests))
    suite.addTest(unittest.makeSuite(Multi_Tp_Tests))
    suite.addTest(unittest.makeSuite(Rejection_Tests))
    suite.addTest(unittest.makeSuite(Test_MOC_Basics))
    suite.addTest(unittest.makeSuite(TestOrderPlacingAndCancel))

    suite.addTest(unittest.makeSuite(Test_Limit_Orders))

    suite.addTest(unittest.makeSuite(Test_AlgoManagement))
    
    suite.addTest(Rejection_Tests("test_on_long_out_short_rejected"))
    # Run the specific suite
    runner = unittest.TextTestRunner()
    runner.run(suite)