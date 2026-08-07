"""Rebuild the EMS order book from PPro's blotter.

WHY THIS REPLACES A LOCAL STATE FILE
------------------------------------
OSTAT is a live UDP push feed with no replay: when the EMS restarts, its
books come back empty and do not rebuild themselves. The obvious fix is to
persist the books to disk, but a file can only ever be as good as the
moment it was written -- anything that changed while the EMS was down is
missed, and that gap is unfixable from a local file.

The blotter closes it. GetBlotter returns PPro's own record of every order
status event for the session, so the books can be re-derived from the
broker's record rather than from our last guess. PPro becomes the source of
truth; a restart is just a rebuild.

IDEMPOTENCY IS THE WHOLE DESIGN CONSTRAINT
------------------------------------------
order_processor ACCUMULATES: order['fill'][price] += shares, and
order['fees'] += fees. That is correct for a live feed where each packet is
a new event, but the blotter is a CUMULATIVE LOG -- every poll returns the
same history again. Feeding blotter events through an accumulate path would
double-count on the second poll and triple on the third.

So rebuild_from_blotter() always builds into a FRESH dict and returns it.
It never accumulates into the live book. Same blotter in, same book out,
however often it is polled -- which is what makes periodic verification
safe rather than corrupting.

MERGE POLICY
------------
PPro is forced to refresh daily, so the blotter is inherently scoped to the
current session. The merge is additive, never subtractive:

  1. An order in the blotter that we do not have (or that we have in a
     staler state) -> take the blotter's version.
  2. An order we have that the blotter does not know about -> keep ours.
     This is normal: an order can be accepted locally via OSTAT before it
     shows up in the blotter, and a missing entry is never evidence that an
     order did not happen.

Live orders are treated more carefully than terminal ones -- see
merge_blotter() -- because OSTAT can be strictly fresher than the blotter
for an order that is still working, and silently overwriting a working
order's fill count would mean acting on a wrong position.
"""

import json
import threading
import time

import requests

from logging_module import *

# The blotter grows through the session and can reach ~8MB, taking 2-8s to
# transfer and parse. The read timeout must sit well above that or a slow
# fetch is killed mid-transfer and looks like an outage. Connect stays short
# -- PPro is on loopback, so a slow CONNECT means it is not listening.
REQUEST_TIMEOUT = (1.0, 30.0)

# Warn when a fetch+parse takes longer than this. Not a failure -- the call
# is off the hot path -- but worth surfacing, since it bounds how often the
# periodic verification can usefully run.
SLOW_FETCH_WARN_SEC = 10.0

# Mirrors the state sets in ems.order_processor. Duplicated rather than
# imported to avoid a circular import; keep in sync deliberately.
INIT_STATES = {"Accepted", "Accepted by GW"}
FILL_STATES = {"Filled", "Partially Filled", "Multi Filled"}
TRANSITION_STATES = {"Accepted", "Accepted by GW", "Partially Filled"}
TERMINAL_STATES = {
    "Filled", "Multi Filled", "Canceled", "Cancelled", "Cancel Request", "Rejected",
}


def fetch_blotter(user, host="127.0.0.1", port=8080, stats=None):
    """GET the session blotter for `user`. Returns the parsed payload or None.

    SLOW BY NATURE -- the blotter reaches ~8MB late in the session and takes
    2-8s to transfer and parse. Never call this from the OSTAT packet path
    or from Flask; it belongs on a background thread (see BlotterSyncer).

    Never raises -- PPro being unreachable must degrade to "no rebuild",
    not stop the EMS from starting."""
    url = f"http://{host}:{port}/GetBlotter?user={user}"

    t0 = time.monotonic()
    try:
        r = requests.get(url, timeout=REQUEST_TIMEOUT)
        raw = r.content
        t_fetch = time.monotonic() - t0

        payload = json.loads(raw.decode("utf-8", errors="ignore"))
        t_total = time.monotonic() - t0

        mb = len(raw) / (1024 * 1024)
        detail = (
            f"{mb:.2f}MB in {t_fetch:.2f}s "
            f"(+{t_total - t_fetch:.2f}s parse, {t_total:.2f}s total)"
        )
        if stats is not None:
            stats.update({"bytes": len(raw), "fetch_sec": t_fetch,
                          "total_sec": t_total, "mb": mb})

        if t_total >= SLOW_FETCH_WARN_SEC:
            message(f"EMS blotter: slow fetch -- {detail}", NOTIFICATION)
        else:
            message(f"EMS blotter: fetched {detail}", LOG)

        return payload

    except Exception as e:
        message(
            f"EMS blotter: fetch failed after {time.monotonic() - t0:.2f}s ({e})",
            LOG,
        )
        return None


def iter_transactions(payload):
    """Yield every transaction row across all regions, de-duplicated.

    Two shapes have to be tolerated here:

    * The same order appears under several regions (NCSA/EMEA/APAC/AUNZ all
      carry the same QIAOSUN_* orders), so rows must be de-duplicated or
      every fill would be counted once per region.
    * Some region objects contain the key "Transactions" more than once.
      Duplicate JSON keys are legal to parse and Python keeps the LAST one,
      which is often the empty string "" -- silently discarding the
      populated list. Anything that is not a list is skipped rather than
      trusted.
    """
    if not payload:
        return

    try:
        regions = payload["Responce"]["Content"]["Regions"]
    except (KeyError, TypeError):
        return

    seen = set()
    for region in regions or []:
        if not isinstance(region, dict):
            continue
        rows = region.get("Transactions")
        if not isinstance(rows, list):
            # "" (empty region) or a clobbered duplicate key.
            continue

        for row in rows:
            if not isinstance(row, dict):
                continue
            # Identity of an event: same order, same state, same timestamp,
            # same price/shares. Region is deliberately excluded so the
            # cross-region duplicates collapse.
            key = (
                row.get("OrderNumber"),
                row.get("OrderState"),
                row.get("MarketDateTime"),
                row.get("Price"),
                row.get("Shares"),
                row.get("InfoText"),
            )
            if key in seen:
                continue
            seen.add(key)
            yield row


def _fees_of(row):
    total = 0.0
    for k in ("ChargeGway", "ChargeSec", "ChargeAct", "ChargeClr", "ChargeExec"):
        try:
            total += float(row.get(k) or 0)
        except (TypeError, ValueError):
            pass
    return total


def rebuild_from_blotter(payload):
    """Rebuild an order_book from a blotter payload. Always a FRESH dict.

    Mirrors order_processor's arithmetic exactly so a rebuilt order is
    indistinguishable from one accumulated live off OSTAT."""
    book = {}

    for row in iter_transactions(payload):
        num = row.get("OrderNumber")
        if not num:
            continue

        state = row.get("OrderState") or ""
        symbol = row.get("Symbol") or ""

        try:
            price = float(row.get("Price") or 0)
            shares = int(row.get("Shares") or 0)
        except (TypeError, ValueError):
            continue

        # Shares is unsigned; Side carries the direction. Without this a
        # sell fill would be counted as a buy.
        shares = shares if row.get("Side") == "B" else -shares

        order = book.setdefault(num, {
            "symbol": symbol, "target_price": 0, "target_share": 0,
            "status": state, "fill": {}, "average_price": 0,
            "shares": 0, "fees": 0,
        })

        order["status"] = state

        # 'Cancel Request' rows are stubs: empty Symbol, zeroed Price and
        # Shares, Side '-'. Assigning unconditionally would blank a real
        # symbol, so only overwrite when the row actually carries one.
        if symbol:
            order["symbol"] = symbol

        if state in INIT_STATES:
            order["target_price"] = price
            order["target_share"] = shares

        if state in FILL_STATES:
            order["fill"][price] = order["fill"].get(price, 0) + shares
            total = sum(order["fill"].values())
            order["average_price"] = (
                sum(p * s for p, s in order["fill"].items()) / total if total else 0
            )
            order["shares"] = total
            order["fees"] += _fees_of(row)

    return book


def merge_blotter(order_book, rebuilt, open_orders=None, trust_live=True):
    """Merge a rebuilt book into the live one. Returns a summary dict.

    Additive, never subtractive: an order we hold that the blotter does not
    mention is kept untouched. An order can legitimately be known to OSTAT
    before it reaches the blotter, so absence is not evidence of anything.

    trust_live guards orders that are still working. For those, OSTAT can be
    strictly fresher than the blotter, and overwriting a working order's
    fill count would mean acting on a wrong position -- so a disagreement is
    logged and the live version kept. Terminal orders take the blotter's
    version, since PPro's record of a completed order is authoritative.
    """
    added, updated, conflicts, unchanged = [], [], [], 0

    for num, new in rebuilt.items():
        cur = order_book.get(num)

        if cur is None:
            order_book[num] = new
            added.append(num)
            if open_orders is not None and new.get("status") in TRANSITION_STATES:
                open_orders.add(num)
            continue

        if cur == new:
            unchanged += 1
            continue

        cur_terminal = cur.get("status") in TERMINAL_STATES

        if trust_live and not cur_terminal:
            # Live order: the local book has seen packets the blotter may
            # not carry yet. Surface the disagreement, do not overwrite.
            if (cur.get("shares") != new.get("shares")
                    or cur.get("status") != new.get("status")):
                conflicts.append({
                    "order": num,
                    "local": {"status": cur.get("status"), "shares": cur.get("shares")},
                    "blotter": {"status": new.get("status"), "shares": new.get("shares")},
                })
            continue

        order_book[num] = new
        updated.append(num)
        if open_orders is not None:
            if new.get("status") in TRANSITION_STATES:
                open_orders.add(num)
            else:
                open_orders.discard(num)

    summary = {
        "added": added,
        "updated": updated,
        "conflicts": conflicts,
        "unchanged": unchanged,
        "blotter_orders": len(rebuilt),
        "book_orders": len(order_book),
    }

    if added or updated:
        message(
            f"EMS blotter: merged {len(added)} new, {len(updated)} updated "
            f"({unchanged} already matched, {len(rebuilt)} in blotter)",
            NOTIFICATION if added else LOG,
        )
    if conflicts:
        message(
            f"EMS blotter: {len(conflicts)} live order(s) disagree with the "
            f"blotter; keeping local (OSTAT is fresher for working orders). "
            f"{conflicts[:3]}",
            NOTIFICATION,
        )

    return summary


def sync(user, order_book, open_orders=None, trust_live=True,
         host="127.0.0.1", port=8080, stats=None):
    """Fetch, rebuild and merge in one call. Returns a summary dict.

    Blocks for as long as the fetch takes (seconds) -- call from a worker
    thread, never from the packet path. Safe to call repeatedly:
    rebuild_from_blotter is idempotent, so polling cannot double-count."""
    payload = fetch_blotter(user, host=host, port=port, stats=stats)
    if payload is None:
        return {"ok": False, "reason": "fetch failed"}

    t0 = time.monotonic()
    try:
        rebuilt = rebuild_from_blotter(payload)
    except Exception as e:
        message(f"EMS blotter: rebuild failed: {e}", NOTIFICATION)
        return {"ok": False, "reason": f"rebuild failed: {e}"}

    # Merge is in-memory and fast, but it mutates the book the processor
    # thread also writes, so it stays short and is done in one pass.
    summary = merge_blotter(order_book, rebuilt, open_orders, trust_live=trust_live)
    summary["ok"] = True
    summary["rebuild_sec"] = time.monotonic() - t0
    return summary


class BlotterSyncer:
    """Background blotter sync. Keeps the slow fetch off every hot path.

    A blotter fetch is 2-8s of blocking network and parse work on a payload
    that reaches ~8MB. That must never run on:

      * the OSTAT socket loop  -- packets queue and drop (lost fills)
      * the processor thread   -- same, one queue back
      * a Flask request        -- the Manager polls those ~1/s

    so it runs here, on its own daemon thread. The initial sync is fired on
    start() rather than awaited, so EMS startup is not blocked for seconds
    waiting on PPro; the books fill in shortly after Flask comes up.
    """

    def __init__(self, order_book, open_orders=None, interval=300.0,
                 host="127.0.0.1", port=8080):
        self.order_book = order_book
        self.open_orders = open_orders
        self.interval = interval
        self.host = host
        self.port = port

        self._user = None
        self._thread = None
        self._wake = threading.Event()
        self._stop = threading.Event()

        # Last-run diagnostics, readable from Flask for a status endpoint.
        self.last_summary = None
        self.last_stats = {}
        self.last_run_ts = 0.0
        self.running = False

    def set_identity(self, user):
        """Set the PPro user. Nothing syncs before this resolves.

        Triggers a sync whenever the identity actually changes -- including
        the first time it resolves after PPro was unreachable at startup,
        and after a reconnect under a different user. get_user() returns
        'x' as its failure sentinel, which must never be treated as real."""
        if not user or user in ("", "x", "X"):
            return False
        if user != self._user:
            self._user = user
            message(f"EMS blotter: identity -> {user}, sync requested", LOG)
            self.request_sync()
        return True

    def request_sync(self):
        """Ask for a sync as soon as the worker is free. Returns immediately."""
        self._wake.set()

    def _run_once(self):
        if not self._user:
            return
        self.running = True
        stats = {}
        try:
            summary = sync(
                self._user, self.order_book, self.open_orders,
                host=self.host, port=self.port, stats=stats,
            )
            self.last_summary = summary
            self.last_stats = stats
            self.last_run_ts = time.time()
        except Exception as e:
            message(f"EMS blotter: sync error: {e}", NOTIFICATION)
        finally:
            self.running = False

    def _loop(self):
        # Sync once as soon as we have an identity -- this is the important
        # one: it rebuilds the book after a restart and recovers whatever
        # changed while the EMS was down.
        #
        # After that, wait to be asked. With interval=0 (the default) the
        # only further syncs are on-demand ones: a reconnect, or an explicit
        # request. A positive interval also re-syncs on that cadence, which
        # only serves to pick up orders lost mid-session.
        while not self._stop.is_set():
            self._run_once()
            timeout = self.interval if self.interval and self.interval > 0 else None
            self._wake.wait(timeout=timeout)
            self._wake.clear()

    def start(self):
        if self._thread is None:
            self._thread = threading.Thread(target=self._loop, daemon=True)
            self._thread.start()
        return self._thread

    def stop(self):
        self._stop.set()
        self._wake.set()
