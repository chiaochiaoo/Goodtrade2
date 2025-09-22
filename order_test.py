#!/usr/bin/env python3
import requests
from datetime import datetime
from urllib.parse import quote
import time
LV1_URL = "http://127.0.0.1:8080/GetLv1?symbol=TQQQ.NQ"
ORDER_BASE = "https://tnv.ngrok.io"  # trailing slash not required

def get_lv1(url: str):
    """Return (bid, ask) as floats from the local L1 service."""
    r = requests.get(url, timeout=3)
    r.raise_for_status()
    data = r.json()

    # The payload (per your screenshot) uses 'Responce' -> 'Content'
    content = data["Responce"]["Content"]
    bid = float(content["BidPrice"])
    ask = float(content["AskPrice"])
    return bid, ask, content

def build_order_url(num:int,bid: float, offset:float,share:int,now: datetime):
    """Compose the order URL:
       /Basket=BB_EX_TEST_{HHMMSS},Order=*TQQQ.NQ:10*,Limit=*TQQQ.NQ:{bid+0.05}*,Info={Timer={timer_plus_30}s}
    """
    HH = now.hour
    MM = now.minute
    SS = now.second
    Time = f"{HH:02d}{MM:02d}{SS:02d}"
    timer = HH * 3600 + MM * 60 + SS
    timer_plus_30 = timer + 30

    basket = f"BB_EX_TEST_{num}{int((bid +offset)*100)}"
    order  = f"*TQQQ.NQ:{share}*"
    limit  = f"*TQQQ.NQ:{bid +offset:.2f}*"
    info   = f"Timer={timer_plus_30},Stop=5,Profit=5"

    # Assemble the path exactly like your format, then URL-encode the part after the slash.
    path = f"Basket={basket},Order={order},Limit={limit},Infos=({info})"
    safe_path = quote(path, safe="=,*{}:,()")  # keep your special chars as-is

    return f"{ORDER_BASE}/{safe_path}"

def main():
    try:

        c=0
        while True:
            bid, ask, raw = get_lv1(LV1_URL)
            print(f"[L1] Bid: {bid:.4f}  Ask: {ask:.4f}")

            now = datetime.now()
            order_url = build_order_url(c,bid,-0.04,10,now)
            c+=1

            print(f"[ORDER] GET {order_url}")
            resp = requests.get(order_url, timeout=2)
            print(f"[ORDER] Status: {resp.status_code}")
            print(f"[ORDER] Body  : {resp.text[:500]}")

            order_url = build_order_url(c,ask,0.04,-10,now)
            c+=1
            print(f"[ORDER] GET {order_url}")
            resp = requests.get(order_url, timeout=2)
            print(f"[ORDER] Status: {resp.status_code}")
            print(f"[ORDER] Body  : {resp.text[:500]}")

            time.sleep(3)
    except Exception as e:
        print(f"[ERROR] {e}")

if __name__ == "__main__":
    main()
