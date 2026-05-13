"""
Device-code sign-in for the Tk desktop app.

The desktop never talks to Clerk directly. Instead it goes through the
goodtradeadmin website (which is already Clerk-authenticated):

  1. POST {WEBSITE}/api/public/device/start         -> { device_code, user_code,
                                                          verification_url_complete }
  2. Open verification_url_complete in the user's browser.
  3. User signs in via Clerk on the website (if not already), then approves the
     code on /link-device.
  4. Poll POST {WEBSITE}/api/public/device/token { device_code }
       202 -> still pending; keep polling
       200 -> { user: { display_name, email, ppro_username, ... } }
       401/410 -> denied / expired; stop

The caller (Manager.clerk_login) must marshal the result back onto Tk via
ui_bus.post since this runs on a worker thread.
"""

import os
import socket
import threading
import time
import webbrowser

import requests

# Where goodtradeadmin is hosted. Override with env var GOODTRADE_WEB_URL.
GOODTRADE_WEB_URL = os.environ.get(
    "GOODTRADE_WEB_URL",
    "https://goodtrade-terminal.up.railway.app",
)

POLL_TIMEOUT_SEC = 600   # give up after 10 min total
POLL_INTERVAL_SEC = 2    # server tells us 2s, hard-coded fallback


def _get_local_ipv4():
    """Best-effort: the LAN IP this machine would use to reach the internet.

    Doesn't actually send anything; the UDP socket trick just makes the OS pick
    a routing interface. Falls back to 127.0.0.1 if everything fails (e.g. no
    network)."""
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        s.connect(("8.8.8.8", 80))
        return s.getsockname()[0]
    except Exception:
        return "127.0.0.1"
    finally:
        s.close()


def start_login(on_success, on_error, on_status=None):
    """Run the device-code flow on a worker thread.

    Callbacks (all invoked on the worker thread — caller marshals to Tk):
      on_status(message: str)         — optional, lifecycle updates
      on_success(user: dict, name: str) — happy path
      on_error(exc: Exception)        — denied / expired / network
    """
    def _run():
        try:
            local_ip = _get_local_ipv4()
            hostname = socket.gethostname()

            if on_status:
                on_status("Requesting code…")

            r = requests.post(
                f"{GOODTRADE_WEB_URL}/api/public/device/start",
                json={"client_ip": local_ip, "hostname": hostname},
                timeout=10,
            )
            r.raise_for_status()
            data = r.json()

            device_code = data["device_code"]
            user_code = data["user_code"]
            verify_url = data.get("verification_url_complete") or (
                data["verification_url"] + "?code=" + user_code
            )
            interval = int(data.get("interval", POLL_INTERVAL_SEC)) or POLL_INTERVAL_SEC

            webbrowser.open(verify_url, new=2)
            if on_status:
                on_status(f"Code {user_code} — approve in browser")

            deadline = time.time() + POLL_TIMEOUT_SEC
            while time.time() < deadline:
                time.sleep(interval)
                p = requests.post(
                    f"{GOODTRADE_WEB_URL}/api/public/device/token",
                    json={"device_code": device_code},
                    timeout=10,
                )
                if p.status_code == 200:
                    payload = p.json()
                    user = payload.get("user") or {}
                    display = (
                        user.get("display_name")
                        or user.get("ppro_username")
                        or user.get("email")
                        or "Signed in"
                    )
                    on_success(user, display)
                    return
                if p.status_code == 202:
                    continue  # pending
                if p.status_code in (401, 410):
                    try:
                        reason = p.json().get("error", "denied")
                    except Exception:
                        reason = str(p.status_code)
                    raise RuntimeError(f"Sign-in {reason}")
                p.raise_for_status()

            raise TimeoutError("Sign-in timed out — no approval after 10 min.")
        except Exception as e:
            on_error(e)

    t = threading.Thread(target=_run, daemon=True)
    t.start()
    return t
