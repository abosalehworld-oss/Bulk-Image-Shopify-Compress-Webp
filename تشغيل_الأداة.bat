@echo off
chcp 65001 >nul 2>&1
title Bulk Image SEO Tool — Shopify & WordPress
color 0B

echo.
echo  ╔══════════════════════════════════════════════════════╗
echo  ║     Bulk Image SEO Tool — Shopify ^& WordPress      ║
echo  ║     أداة تحسين صور المنتجات — شوبيفاي وووردبريس    ║
echo  ╚══════════════════════════════════════════════════════╝
echo.

cd /d "%~dp0"

:: ══════════════════════════════════════════════════════════
:: Step 1: Check if Python is installed
:: ══════════════════════════════════════════════════════════
set PYTHON_CMD=
where py >nul 2>&1
if %errorlevel%==0 (
    set PYTHON_CMD=py
    goto :found_python
)
where python >nul 2>&1
if %errorlevel%==0 (
    set PYTHON_CMD=python
    goto :found_python
)
where python3 >nul 2>&1
if %errorlevel%==0 (
    set PYTHON_CMD=python3
    goto :found_python
)

:: Python not found — guide user
color 0C
echo.
echo  ╔══════════════════════════════════════════════════════╗
echo  ║  ⚠  Python is not installed on your computer       ║
echo  ║  ⚠  البايثون غير مثبت على جهازك                    ║
echo  ╚══════════════════════════════════════════════════════╝
echo.
echo  Opening Python download page...
echo  جارى فتح صفحة تحميل البايثون...
echo.
echo  ┌─────────────────────────────────────────────────────┐
echo  │  1. Download and install Python                     │
echo  │  2. CHECK "Add Python to PATH" ✅                   │
echo  │  3. After install, run this file again              │
echo  │                                                     │
echo  │  1. حمّل وثبّت البايثون                              │
echo  │  2. ✅ ضع علامة على Add Python to PATH              │
echo  │  3. بعد التثبيت شغّل هذا الملف مرة أخرى            │
echo  └─────────────────────────────────────────────────────┘
echo.
start https://www.python.org/downloads/
pause
exit /b

:found_python
echo  ✅ Python found: %PYTHON_CMD%
echo.

:: ══════════════════════════════════════════════════════════
:: Step 2: Check & install required packages automatically
:: ══════════════════════════════════════════════════════════
echo  Checking required packages...
echo  جارى فحص المكتبات المطلوبة...
echo.

set NEED_INSTALL=0

%PYTHON_CMD% -c "import PIL" >nul 2>&1
if %errorlevel% neq 0 set NEED_INSTALL=1

%PYTHON_CMD% -c "import requests" >nul 2>&1
if %errorlevel% neq 0 set NEED_INSTALL=1

%PYTHON_CMD% -c "import tqdm" >nul 2>&1
if %errorlevel% neq 0 set NEED_INSTALL=1

%PYTHON_CMD% -c "import rarfile" >nul 2>&1
if %errorlevel% neq 0 set NEED_INSTALL=1

if %NEED_INSTALL%==1 (
    echo  ┌─────────────────────────────────────────────────────┐
    echo  │  Installing required packages — first time only...  │
    echo  │  جارى تثبيت المكتبات — مرة واحدة فقط...             │
    echo  └─────────────────────────────────────────────────────┘
    echo.
    %PYTHON_CMD% -m pip install --upgrade pip >nul 2>&1
    %PYTHON_CMD% -m pip install requests Pillow tqdm rarfile
    if %errorlevel% neq 0 (
        color 0C
        echo.
        echo  ╔══════════════════════════════════════════════════════╗
        echo  ║  ❌ Error installing packages                       ║
        echo  ║  ❌ خطأ في تثبيت المكتبات                          ║
        echo  ╚══════════════════════════════════════════════════════╝
        echo.
        echo  Try running this as Administrator
        echo  جرّب تشغيل الملف كمسؤول ^(Run as Administrator^)
        echo.
        pause
        exit /b
    )
    echo.
    echo  ✅ All packages installed successfully!
    echo  ✅ تم تثبيت جميع المكتبات بنجاح!
    echo.
) else (
    echo  ✅ All packages already installed
    echo  ✅ جميع المكتبات مثبتة بالفعل
    echo.
)

:: ══════════════════════════════════════════════════════════
:: Step 3: Launch the GUI
:: ══════════════════════════════════════════════════════════
echo  ┌─────────────────────────────────────────────────────┐
echo  │  🚀 Launching the tool...                           │
echo  │  🚀 جارى تشغيل الأداة...                            │
echo  └─────────────────────────────────────────────────────┘
echo.

%PYTHON_CMD% shopify_gui.py

if %errorlevel% neq 0 (
    color 0C
    echo.
    echo  ╔══════════════════════════════════════════════════════╗
    echo  ║  ❌ The tool exited with an error                   ║
    echo  ║  ❌ الأداة أُغلقت بسبب خطأ                         ║
    echo  ╚══════════════════════════════════════════════════════╝
    echo.
    echo  If the error persists, contact support.
    echo  إذا استمر الخطأ، تواصل مع الدعم الفني.
    echo.
    pause
)
