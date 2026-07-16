@echo off
title Bulk Image SEO Tool
cd /d "%~dp0"
cls
echo.
echo  ================================================
echo   Bulk Image SEO Tool - Shopify and WordPress
echo  ================================================
echo.
echo  [1/3] Checking Python...
py --version >nul 2>&1
if %errorlevel% neq 0 goto nopython
echo  OK - Python found.
echo.
echo  [2/3] Checking packages...
py -c "import PIL, requests, tqdm, rarfile" >nul 2>&1
if %errorlevel% neq 0 goto install
echo  OK - All packages ready.
goto launch

:install
echo  Installing packages - first time only, please wait...
py -m pip install requests Pillow tqdm rarfile -q --disable-pip-version-check
if %errorlevel% neq 0 goto installerror
echo  OK - Packages installed!
goto launch

:launch
echo.
echo  [3/3] Launching tool...
echo  ================================================
echo.
py shopify_gui.py
if %errorlevel% neq 0 (
echo.
echo  ERROR: Tool crashed. Contact support.
pause
)
goto done

:nopython
echo.
echo  ERROR: Python is not installed!
echo.
echo  Steps:
echo  1. Download page will open now
echo  2. Install Python
echo  3. Check ADD PYTHON TO PATH
echo  4. Run this file again
echo.
start https://www.python.org/downloads/
pause
goto done

:installerror
echo.
echo  ERROR: Install failed!
echo  Right-click this file - Run as Administrator
echo.
pause

:done