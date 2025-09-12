git pull
start "Ppro EMS" cmd /k python ems.py
set PID1=%!
start "GoodTrade AMS" cmd /k python Manager.py
set PID2=%!
taskkill /F /PID %PID1%
taskkill /F /PID %PID2%