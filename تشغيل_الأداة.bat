@echo off
chcp 65001 >nul 2>&1
title Shopify Bulk Image Tool

echo.
echo  ====================================
echo   Shopify Bulk Image Tool
echo  ====================================
echo.
echo  Starting...
echo.

cd /d "%~dp0"

py shopify_gui.py 2>nul
if errorlevel 1 (
    python shopify_gui.py 2>nul
    if errorlevel 1 (
        python3 shopify_gui.py 2>nul
        if errorlevel 1 (
            echo.
            echo  ERROR: Python is not installed or not in PATH
            echo.
            echo  Download Python from: https://www.python.org/downloads/
            echo  IMPORTANT: Check "Add Python to PATH" during installation
            echo.
            echo  After installing, run: pip install requests Pillow tqdm
            echo.
            pause
        )
    )
)
