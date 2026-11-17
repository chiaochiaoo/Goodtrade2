"""Local state persistence for algo attribution across app restarts.

WHAT THIS SAVES, AND WHY IT IS A SHORT LIST
-------------------------------------------
Positions do not live in this app -- they live in PPro, and the inspection
loop already re-fetches them every tick. Prices live in the L1 feed. Open
orders live in the EMS. All of that is re-fetched on startup and is *more*
correct than anything we could write to disk.

What is lost on restart, and exists nowhere else, is the ATTRIBUTION layer:
which algo owns which shares, at what cost basis, with how much realized
P&L and fees accrued. Without it PPro says "you are long 500 BAC" and no
TradingPlan claims those shares -- no P&L, no stop, no flatten target.

So this module persists attribution and configuration ONLY. Every field
persisted is a field that can be wrong after a restart, so the list is kept
deliberately small. Market data, in-flight order intent, and derived status
are all excluded -- see EXCLUDED below for the reasoning on each.

Symbols persist nothing at all. A Symbol is fully reconstructible from
Symbol(manager, name) + PPro + L1 + the algos that register into it, which
is the same path apply_basket_cmd already uses thousands of times a day.
The optional "symbols" block in the file is DIAGNOSTIC ONLY and is ignored
by the loader -- it exists so a post-mortem can see what the app believed
at the time, and must never become a restore source.

FILE LAYOUT
-----------
One file per (account, env):

    %LOCALAPPDATA%/GoodTrade/state/{account}_{env}.json

env is in the filename so SIM state can never be loaded into LIVE.

The trading date is stored INSIDE the file, not in the filename. A per-date
filename would mean a continuous account restarting the next morning finds
no file and silently comes up flat -- losing the position it exists to
carry. Day accounts compare the stored date against today and discard on
mismatch; continuous accounts ignore it entirely.
"""

import json
import os
import tempfile
import threading
from datetime import datetime, timedelta

from logging_module import *

# Schema version. Bump when the persisted shape changes incompatibly; the
# loader refuses anything it does not recognize rather than guessing.
SCHEMA_VERSION = 1

# Trading-date rollover. A session is stamped with the date it belongs to,
# not the wall-clock date: anything before this hour (America/New_York)
# counts as the previous trading day, so a 00:30 restart after a late
# session still resolves to that session rather than a fresh one.
_ROLLOVER_HOUR = 20
_MARKET_TZ = "America/New_York"


def _market_now():
	"""Current time in market tz, falling back to naive local time if the
	tzdata package is unavailable (frozen builds sometimes lack it)."""
	try:
		from zoneinfo import ZoneInfo
		return datetime.now(ZoneInfo(_MARKET_TZ))
	except Exception:
		return datetime.now()


def trading_date(now=None):
	"""The trading date this moment belongs to, as 'YYYY-MM-DD'.

	Rolls at _ROLLOVER_HOUR rather than midnight so an evening restart is
	treated as the same session, and an early-morning restart is not
	treated as yesterday's."""
	now = now or _market_now()
	if now.hour >= _ROLLOVER_HOUR:
		now = now + timedelta(days=1)
	return now.strftime("%Y-%m-%d")


def _sanitize(part):
	"""Make a string safe for use in a filename."""
	out = "".join(c if (c.isalnum() or c in "-_") else "_" for c in str(part))
	return out or "UNKNOWN"


def state_dir():
	base = os.environ.get("LOCALAPPDATA") or os.path.expanduser("~")
	return os.path.join(base, "GoodTrade", "state")


def state_path(account, env):
	return os.path.join(state_dir(), f"{_sanitize(account)}_{_sanitize(env)}.json")


def archive_dir():
	return os.path.join(state_dir(), "archive")


# ---------------------------------------------------------------------------
# Serialization
# ---------------------------------------------------------------------------

# Keys lifted straight out of tp.data. All plain dicts of primitives.
#
# PERSISTED -- irreplaceable attribution and accounting:
_DATA_KEYS = (
	"current_shares",      # which algo owns which shares -- the whole point
	"real_by_symbol",      # accumulated, unrecoverable
	"fees_by_symbol",      # accumulated, unrecoverable
	"unreal_by_symbol",    # written for diagnostics; recomputed on restore
	"moo_targets",         # standing intent that survives a restart
	"symbol_freeze",       # operator intent that must not be silently cleared
	"multiplier",
	"hedging_algo",
	"main_ticker",
	"heging_info",
)

# EXCLUDED from tp.data, deliberately:
#
#   UNREAL              recomputed from restored average_price + live price.
#                       A stale unrealized number can trigger a phantom
#                       stop-out in the first minute after restore.
#   current_request     in-flight order intent. Stale means duplicate orders.
#   limit_request       same.
#   expected_shares     same -- re-derived when the algo next ticks.
#   status              restore to IDLE and let the loop re-derive.
#   cycle_active        same.
#   flatten_order       same.
#   rejected_stop       transient; a restart is a clean slate for rejections.
#   algo_total_shares   derived from current_shares.
#   algo_total_request  derived from in-flight requests we do not restore.
#   clone_dict          clones are re-created by the deployment path.


def tradingplan_to_dict(tp):
	"""Serialize a TradingPlan to a plain dict.

	Explicit whitelist rather than __dict__: tp holds manager, ui_component,
	tkvars and timers that are neither serializable nor meaningful across a
	restart, and the difference between "what is in memory" and "what is
	still true after a restart" is exactly what needs curating here."""
	data = getattr(tp, "data", {}) or {}

	payload = {
		"algo_name": tp.algo_name,
		# info carries Tag / Stop / Profit / Timer / Manual / hedge etc.
		# set_profit and set_stop write back into info, so live operator
		# adjustments to targets ride along here for free.
		"info": _jsonable(getattr(tp, "info", {}) or {}),
		"clone_number": getattr(tp, "clone_number", 0),
		"nbbo_only": bool(getattr(tp, "nbbo_only", False)),
		"tradable": bool(getattr(tp, "tradable", True)),
		"shutdown": bool(getattr(tp, "shutdown", False)),
		"banned": list(getattr(tp, "banned", []) or []),

		# Cost basis. Nothing in the world can reconstruct this.
		"average_price": _jsonable(getattr(tp, "average_price", {}) or {}),
		"current_exposure": _jsonable(getattr(tp, "current_exposure", {}) or {}),

		# Accumulated realized P&L. Persisted for BOTH account modes --
		# day accounts get a fresh file each session anyway, so scoping
		# handles the reset rather than special-casing the value here.
		"realized": _num(data.get("realized", 0)),

		# Trail state is NOT mirrored into info, unlike stop/profit. An
		# armed trailing stop that came back disarmed would silently widen
		# the operator's risk, so it is persisted explicitly.
		"profit_trail_activated": bool(getattr(tp, "profit_trail_activated", False)),
		"profit_trail": _num(getattr(tp, "profit_trail", 0)),
		"break_even": bool(getattr(tp, "break_even", False)),

		"data": {k: _jsonable(data.get(k)) for k in _DATA_KEYS if k in data},
	}
	return payload


def restore_tradingplan_fields(tp, tpp):
	"""Overwrite a freshly-built TradingPlan with its persisted attribution.

	Counterpart of tradingplan_to_dict. The caller (Manager) has already
	constructed the TP from the saved info and called register_symbol for
	every symbol, so all per-symbol dicts exist and are zeroed; this fills
	them back in. Symbol objects and UI wiring stay the caller's job.

	Two deliberate deviations from "restore exactly what was saved":

	  * expected_shares is set EQUAL to current_shares rather than restored.
	    expected is the target the central dispatcher converges toward -- a
	    restored target above the position would fire orders the moment the
	    hold lifts. Equal means: hold the position, request nothing.
	    Resuming a chase is an operator action, not a restore side effect.

	  * moo_targets restore DISARMED (moo_armed stays False). An armed MOO
	    fires at the open; re-arming silently on import would be an order
	    the operator never re-confirmed.
	"""
	data = tpp.get("data", {}) or {}

	# --- attribution: the reason the file exists -----------------------
	for sym, sh in (data.get("current_shares") or {}).items():
		sh = int(sh)
		tp.data["current_shares"][sym] = sh
		tp.data["expected_shares"][sym] = sh
	for sym, exp in (tpp.get("current_exposure") or {}).items():
		tp.current_exposure[sym] = list(exp)
	for sym, ap in (tpp.get("average_price") or {}).items():
		tp.average_price[sym] = ap

	tp.data["realized"] = tpp.get("realized", 0)
	for key in ("real_by_symbol", "fees_by_symbol"):
		for sym, v in (data.get(key) or {}).items():
			tp.data[key][sym] = v

	# --- configuration --------------------------------------------------
	tp.data["multiplier"] = data.get("multiplier", 1)
	tp.banned = list(tpp.get("banned") or [])
	tp.tradable = bool(tpp.get("tradable", True))
	tp.nbbo_only = bool(tpp.get("nbbo_only", False))
	tp.clone_number = tpp.get("clone_number", 0)
	tp.profit_trail_activated = bool(tpp.get("profit_trail_activated", False))
	tp.profit_trail = tpp.get("profit_trail", 0)
	tp.break_even = bool(tpp.get("break_even", False))

	for sym, tgt in (data.get("moo_targets") or {}).items():
		tp.data["moo_targets"][sym] = int(tgt)
		if int(tgt):
			message(
				f"restore: {tp.algo_name} {sym} MOO target {tgt} restored "
				f"DISARMED -- re-arm to use", NOTIFICATION)
	for sym, fz in (data.get("symbol_freeze") or {}).items():
		tp.data["symbol_freeze"][sym] = fz

	# --- hedge structure ------------------------------------------------
	# The data fields restore here; register_hedge() on the Symbol objects
	# is the caller's job (the symbols live Manager-side).
	if data.get("hedging_algo"):
		tp.data["hedging_algo"] = True
		tp.data["main_ticker"] = data.get("main_ticker", "")
		tp.data["heging_info"] = dict(data.get("heging_info") or {})

	tp.tradingplan_classification()
	return tp


def symbol_diagnostic(sym):
	"""Non-authoritative snapshot of a Symbol, for post-mortems only.

	NEVER read back on restore. Symbols rebuild from PPro + L1 + algo
	re-registration; restoring a stale bid/ask would mean trading on prices
	from before the restart."""
	return {
		"symbol": getattr(sym, "symbol_name", None),
		"ppro_position": _num(getattr(sym, "ppro_position", 0)),
		"discrepancy": _num(getattr(sym, "discrepancy", 0)),
		"is_hedge": bool(getattr(sym, "is_hedge", False)),
		"order_out": bool(getattr(sym, "order_out", False)),
		"order_id": str(getattr(sym, "order_id", "") or ""),
		"open_order_count": _num(getattr(sym, "open_order_count", 0)),
	}


def _num(v):
	"""Coerce to a JSON-safe number, tolerating Decimal and junk."""
	try:
		f = float(v)
	except (TypeError, ValueError):
		return 0
	if f != f or f in (float("inf"), float("-inf")):
		return 0
	return int(f) if f.is_integer() else f


def _jsonable(v):
	"""Best-effort conversion to JSON-safe primitives."""
	if v is None or isinstance(v, (bool, int, str)):
		return v
	if isinstance(v, float):
		return _num(v)
	if isinstance(v, dict):
		return {str(k): _jsonable(x) for k, x in v.items()}
	if isinstance(v, (list, tuple, set)):
		return [_jsonable(x) for x in v]
	try:
		return _num(v)  # Decimal and friends
	except Exception:
		return str(v)


def build_state(account, env, trading_mode, algos, symbols=None):
	"""Assemble the full on-disk payload."""
	plans = {}
	for name, tp in list((algos or {}).items()):
		try:
			plans[name] = tradingplan_to_dict(tp)
		except Exception as e:
			# One bad algo must not cost us the whole backup.
			message(f"state_store: skipped {name} during save: {e}", NOTIFICATION)

	payload = {
		"schema": SCHEMA_VERSION,
		"account": account,
		"env": env,
		"trading_mode": trading_mode,
		"trading_date": trading_date(),
		"saved_at": _market_now().isoformat(),
		"host": os.environ.get("COMPUTERNAME", ""),
		"tradingplans": plans,
	}

	if symbols:
		diag = {}
		for name, sym in list(symbols.items()):
			try:
				diag[name] = symbol_diagnostic(sym)
			except Exception:
				pass
		# Named to make it obvious at a glance that this is not restored.
		payload["symbols_diagnostic_ignored_on_load"] = diag

	return payload


# ---------------------------------------------------------------------------
# Writing
# ---------------------------------------------------------------------------

_write_lock = threading.Lock()


def write_state(payload, path=None):
	"""Atomically write state to disk, keeping one .bak generation.

	Atomic because a torn write during a crash would lose exactly the state
	we are crashing to protect -- write to a temp file in the same
	directory, fsync, then os.replace (atomic on Windows and POSIX)."""
	path = path or state_path(payload.get("account"), payload.get("env"))
	d = os.path.dirname(path)

	with _write_lock:
		os.makedirs(d, exist_ok=True)
		body = json.dumps(payload, indent=1, sort_keys=True, default=str)

		fd, tmp = tempfile.mkstemp(dir=d, prefix=".state-", suffix=".tmp")
		try:
			with os.fdopen(fd, "w", encoding="utf-8") as f:
				f.write(body)
				f.flush()
				os.fsync(f.fileno())

			# Roll the previous good copy aside before replacing it.
			if os.path.exists(path):
				bak = path + ".bak"
				try:
					if os.path.exists(bak):
						os.remove(bak)
					os.replace(path, bak)
				except OSError:
					pass  # a missing .bak is survivable; a failed write is not

			os.replace(tmp, path)
			tmp = None
		finally:
			if tmp and os.path.exists(tmp):
				try:
					os.remove(tmp)
				except OSError:
					pass

	return path


def state_fingerprint(payload):
	"""Stable hash of the meaningful contents, ignoring timestamps.

	Used to skip writes when nothing changed -- saved_at alone must not
	count as a change or every tick would rewrite the file."""
	trimmed = {
		"tradingplans": payload.get("tradingplans", {}),
		"trading_date": payload.get("trading_date"),
	}
	return hash(json.dumps(trimmed, sort_keys=True, default=str))


# ---------------------------------------------------------------------------
# Reading
# ---------------------------------------------------------------------------

def read_state(account, env, path=None):
	"""Load state from disk, falling back to .bak if the primary is corrupt.

	Returns None when there is nothing usable. Never raises -- a failed
	restore must degrade to "start fresh", not to a crash on launch."""
	path = path or state_path(account, env)

	for candidate in (path, path + ".bak"):
		if not os.path.exists(candidate):
			continue
		try:
			with open(candidate, "r", encoding="utf-8") as f:
				payload = json.load(f)
		except Exception as e:
			message(f"state_store: {candidate} unreadable ({e})", NOTIFICATION)
			continue

		schema = payload.get("schema")
		if schema != SCHEMA_VERSION:
			message(
				f"state_store: {candidate} schema {schema!r} != {SCHEMA_VERSION}, ignoring",
				NOTIFICATION,
			)
			continue

		# env is already in the filename, but an operator could copy a file
		# by hand. Refuse a mismatch rather than load SIM state into LIVE.
		if payload.get("env") != env or payload.get("account") != account:
			message(
				f"state_store: {candidate} belongs to "
				f"{payload.get('account')!r}/{payload.get('env')!r}, refusing",
				NOTIFICATION,
			)
			continue

		if candidate.endswith(".bak"):
			message("state_store: primary state unusable, recovered from .bak", NOTIFICATION)

		return payload

	return None


def is_stale_for_day_mode(payload, now=None):
	"""True when a day account's saved state belongs to a previous session.

	Day accounts start fresh every session regardless of what they held;
	continuous accounts never consult this."""
	return payload.get("trading_date") != trading_date(now)


def archive_state(account, env, reason="", path=None):
	"""Move state aside instead of deleting it.

	Discarded state is exactly what you want to read during a post-mortem,
	so 'start fresh' and the day-mode wipe both archive rather than unlink."""
	path = path or state_path(account, env)
	if not os.path.exists(path):
		return None


	adir = archive_dir()
	os.makedirs(adir, exist_ok=True)
	stamp = _market_now().strftime("%Y%m%d-%H%M%S")
	tag = _sanitize(reason) if reason else "archived"
	dest = os.path.join(adir, f"{os.path.basename(path)}.{stamp}.{tag}")

	try:
		os.replace(path, dest)
		message(f"state_store: archived state -> {dest}", LOG)
		return dest
	except OSError as e:
		message(f"state_store: archive failed: {e}", NOTIFICATION)
		return None
