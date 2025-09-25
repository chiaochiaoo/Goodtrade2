from datetime import datetime
import linecache
import sys
import os
from datetime import datetime, timedelta
# import pandas as pd
# import numpy as np
# import matplotlib.pyplot as plt
# from matplotlib import ticker
# import matplotlib.pyplot as plt
import traceback
import time
import json
import requests 

import getpass


try:
	import smtplib
except ImportError:
	import pip
	pip.main(['install', 'smtplib'])
	import smtplib

try:
	from email.mime.text import MIMEText
	from email.mime.multipart import MIMEMultipart
	from email.mime.application import MIMEApplication
except ImportError:
	import pip
	pip.main(['install', 'email'])
	
	from email.mime.text import MIMEText
	from email.mime.multipart import MIMEMultipart
	from email.mime.application import MIMEApplication

def find_between(data, first, last):
	try:
		start = data.index(first) + len(first)
		end = data.index(last, start)
		return data[start:end]
	except ValueError:
		return data


# try:
#     from twilio.rest import Client
# except ImportError:
#     import pip
#     pip.main(['install','twilio'])
#     from twilio.rest import Client
# Dispatch routing based on message type


INFO     = "info"
LOG  = "log"
NOTIFICATION  = "notification"
CLIKABLE = "clikable"
ERROR    = "error"
CRITICAL = "critical"
DEBUG    = "debug"
REPORT   = "report"

DISPATCH_RULES = {
    INFO:     ["print"],
    LOG:  ["print", "file"],
    NOTIFICATION:  ["print", "file", "ui"],
    CLIKABLE: ['print','clickable'],
    REPORT:   ["email"],
    ERROR:    ["print", "file", "email","ui"],
    CRITICAL: ["print", "file", "email", "sms","ui"],
    DEBUG:    ["print"]
}
# print(DISPATCH_RULES.get(SUCCESS))
# Email Configuration



EMAIL_SENDER = "algomanagertnv@gmail.com"
EMAIL_PASSWORD = "myvjbplswvsvktau"
EMAIL_RECEIVER =  ['algomanagertnv@gmail.com']
SMTP_SERVER = "smtp.gmail.com"
SMTP_PORT = 465



LOG_FOLDER = "logs/"

PUSHKEY = 'u7gqg258165ns35y5gwo8rjq7cw8ti'

# global ui
ui = None

def set_ui(uix):
    global ui
    ui = uix



class message:
    def __init__(self, content, mtype="info"):

        self.timestamp = datetime.now()
        self.content = content
        self.type = mtype
        self.status = "unread"

        self.auto_dispatch()

    def to_dict(self):
        return {

            "timestamp": self.timestamp.isoformat(),
            "content": self.content,
            "type": self.type,
            "sender": self.sender,
            "recipient": self.recipient,
            "status": self.status
        }

    def dispatch(self, actions=("print",), log_folder=LOG_FOLDER):

        if "print" in actions:
            self._handle_print()
        if "file" in actions:
            self._handle_save_to_daily_file(log_folder)
        if "ui" in actions:
            self._handle_ui()
        if "email" in actions:
            self._handle_email()
        if "sms" in actions:
            self._handle_sms()
        if "clickable" in actions:
            self._handle_ui_clickable()

    def auto_dispatch(self, rules=DISPATCH_RULES, log_folder=LOG_FOLDER):
        actions = rules.get(self.type)
        
        self.dispatch(actions=actions, log_folder=log_folder)

    # Individual Handlers
    def _handle_print(self):
        print(f"[{self.type.upper()}] [{self.timestamp.strftime('%H:%M:%S')}]: {self.content}")

    def _handle_save_to_daily_file(self, folder):
        try:
            os.makedirs(folder, exist_ok=True)
            date_str = self.timestamp.strftime("%Y-%m-%d")
            time_str = self.timestamp.strftime("%H:%M:%S")
            filepath = os.path.join(folder, f"{date_str}.txt")
            #print(" saving to ",filepath)
            with open(filepath, "a+", encoding="utf-8") as f:
                f.write(f"{time_str} [{self.type.upper()}] {self.content}\n")
        except Exception as e:
            print("[FILE LOGGING FAILED]", e)

    def _handle_ui_clickable(self):

        if ui!=None and len(self.content)==2:
            ui.clickable_notification(message=f"[{self.timestamp.strftime('%H:%M:%S')}]: {self.content[0]}",cmd=self.content[1],remove_on_click=True,right_click_runs_cmd=True)
        if ui!=None and len(self.content)==3:
            ui.clickable_notification(message=f"[{self.timestamp.strftime('%H:%M:%S')}]: {self.content[0]}",cmd=self.content[1],remove_on_click=True,right_click_runs_cmd=False)

    def _handle_ui(self):
        #print(f"[UI] → {self.content}")

        #global ui 
        if ui!=None:
            ui.show_notification(f"[{self.timestamp.strftime('%H:%M:%S')}]: {self.content}")

    def _handle_email(self):
        try:
            msg = MIMEText(self.content)
            msg["Subject"] = f"[{self.type.upper()}] message from {EMAIL_SENDER}"
            msg["From"] = EMAIL_SENDER
            msg["To"] = ', '.join(EMAIL_RECEIVER) 

            with smtplib.SMTP_SSL('smtp.gmail.com', 465) as smtp_server:
               smtp_server.login(EMAIL_SENDER, EMAIL_PASSWORD)
               smtp_server.sendmail(EMAIL_SENDER, EMAIL_RECEIVER, msg.as_string())


            print("[EMAIL SENT]")

        except Exception as e:
            print("[EMAIL FAILED]", e)

    def _handle_sms(self):


        try:
            client = Client(TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN)
            sms = client.messages.create(
                body=f"[{self.type.upper()}] {self.content}",
                from_=TWILIO_FROM,
                to=TWILIO_TO
            )
            print(f"[SMS SENT] SID: {sms.sid}")
        except Exception as e:
            print("[SMS FAILED]", e)


def PrintException(info_msg="ERROR", level=ERROR):
    exc_type, exc_obj, exc_tb = sys.exc_info()
    if exc_tb is None:
        location = "Unknown"
    else:
        fname = os.path.split(exc_tb.tb_frame.f_code.co_filename)[1]
        location = f"{fname}, line {exc_tb.tb_lineno}"

    trace = traceback.format_exc()
    full_msg = f"{info_msg} | {exc_type.__name__} @ {location}\n{trace}"

    msg = message(full_msg, mtype=level)
    msg.auto_dispatch()




## TEST
pushover_url = "https://api.pushover.net/1/messages.json"


# payload = {"user": pushover_user, "token": pushover_token, "message": message}
# requests.post(pushover_url, data=payload)

# message("Info level only", INFO)
# message("Success log test", SUCCESS)
# message("Warning alert", WARNING)
# message("Error handling test", ERROR)
# message("Critical shutdown alert", CRITICAL)
# message("REPROT: EMAIL CHECK",REPORT)

# message("Debug trace", DEBUG)

# try:
#     1 / 0
# except:
#     PrintException("Crash in calculation", level="critical")

