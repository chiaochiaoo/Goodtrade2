@echo off
REM Goodtrade UI Performance Launcher
REM Applies optimizations before starting the UI

echo ============================================================
echo Goodtrade UI - Performance Optimized Launch
echo ============================================================
echo.

REM Check if Python is available
python --version >nul 2>&1
if errorlevel 1 (
    echo ERROR: Python not found in PATH
    echo Please install Python or add it to your PATH
    pause
    exit /b 1
)

echo Step 1: Checking optimizations...
python check_performance_optimizations.py
if errorlevel 1 (
    echo.
    echo WARNING: Some optimizations are missing
    echo The application will still run, but performance may be reduced
    echo.
    pause
)

echo.
echo ============================================================
echo Step 2: Launching Goodtrade UI...
echo ============================================================
echo.

REM Run with optimization flags
REM -O enables Python optimizations (removes assert statements, __debug__)
REM -OO also removes docstrings for slightly faster loading
python -O ui_main.py

echo.
echo Application closed.
pause
