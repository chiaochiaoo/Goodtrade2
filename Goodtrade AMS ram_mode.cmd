@echo off
REM ============================================================
REM Goodtrade AMS - ADVANCED Performance Launcher
REM Maximum resource allocation with pre-optimization
REM ============================================================

echo ============================================================
echo Goodtrade AMS - ADVANCED Performance Mode
echo ============================================================
echo.

REM Pull latest changes
echo [1/4] Pulling latest updates...
git pull
echo.

REM Apply Windows-level resource optimizations first
echo [2/4] Applying Windows resource optimizations...
echo This will set process priority and reserve memory...
python windows_resource_optimizer.py
echo.

REM Wait for optimizations to settle
timeout /t 1 /nobreak >nul

echo [3/4] Starting Ppro EMS with maximum performance...
REM Start with:
REM - /HIGH priority (more CPU time)
REM - /AFFINITY sets which CPU cores to use (optional)
REM - -O enables Python optimizations
REM - Sets working set size via environment variable
start "Ppro EMS" /HIGH /B cmd.exe /c "python -O ems.py"

echo [3/4] Waiting 3 seconds before starting Manager...
timeout /t 3 /nobreak >nul

echo [4/4] Starting GoodTrade AMS Manager with maximum performance...
start "GoodTrade AMS" /HIGH /B cmd.exe /c "python -O Main.py"

echo.
echo ============================================================
echo PERFORMANCE MODE ACTIVE
echo ============================================================
echo.
echo Both processes started with:
echo   ✓ HIGH CPU Priority
echo   ✓ Python Optimizations (-O flag)
echo   ✓ Reserved Memory Allocation
echo   ✓ Enhanced Process Priority
echo.
echo Monitoring Tips:
echo   • Open Task Manager (Ctrl+Shift+Esc)
echo   • Go to Details tab
echo   • Find python.exe processes
echo   • Check "Priority" column should show "High"
echo   • Monitor "Memory" and "CPU" columns
echo.
echo Performance Recommendations:
echo   • Close unnecessary programs
echo   • Don't resize windows frequently
echo   • Monitor system resources
echo   • Keep total RAM usage below 80%%
echo.
echo Press any key to exit this window...
pause >nul
