@echo off
REM ============================================================
REM Goodtrade AMS - Performance Optimized Launcher
REM Allocates more CPU and memory resources for better performance
REM ============================================================

echo Starting Goodtrade AMS with performance optimizations...
echo.

REM Pull latest changes
git fetch origin
git reset --hard origin/main

echo.
echo Applying resource optimizations...
echo.

REM Start Ppro EMS with HIGH priority and optimized Python
REM /HIGH sets the process priority to HIGH
REM -O enables Python optimizations (faster execution)
start "Ppro EMS" /HIGH cmd.exe /k "python -O ems.py || pause"

REM Wait 2 seconds before starting the Manager
timeout /t 2 /nobreak >nul

REM Start GoodTrade AMS (Manager) with HIGH priority and optimizations
start "GoodTrade AMS" /HIGH cmd.exe /k "python -O Main.py || pause"

echo.
echo ============================================================
echo Both processes started with HIGH priority
echo - Ppro EMS: High CPU priority, Python optimizations enabled
echo - GoodTrade AMS: High CPU priority, Python optimizations enabled
echo ============================================================
echo.
echo TIP: To monitor performance, open Task Manager (Ctrl+Shift+Esc)
echo      and check the "Priority" column for python.exe processes
echo.