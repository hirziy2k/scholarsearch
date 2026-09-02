@echo off
REM Build Mendeley Patcher into standalone .exe using PyInstaller
REM Run this from the mendeley-patcher directory

echo.
echo +============================================================+
echo |         Building Mendeley Patcher Executable               |
echo +============================================================+
echo.

REM Check if Python is available
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo [ERROR] Python not found. Please install Python 3.10+
    pause
    exit /b 1
)

REM Install build dependencies
echo [1/4] Installing build dependencies...
pip install pyinstaller requests

echo.
echo [2/4] Building executable...
pyinstaller ^
    --name mendeley-patcher ^
    --onefile ^
    --console ^
    --icon=NONE ^
    --add-data "references.bib;." ^
    --add-data "templates;templates" ^
    --hidden-import requests ^
    --hidden-import json ^
    --hidden-import sqlite3 ^
    --hidden-import hashlib ^
    --hidden-import base64 ^
    --hidden-import secrets ^
    --hidden-import webbrowser ^
    --hidden-import http.server ^
    --hidden-import urllib.parse ^
    --hidden-import ctypes ^
    --hidden-import ctypes.wintypes ^
    --clean ^
    orchestrator.py

if %errorlevel% neq 0 (
    echo.
    echo [ERROR] Build failed. Check the output above for errors.
    pause
    exit /b 1
)

echo.
echo [3/4] Copying reference files...
if not exist "dist\output" mkdir "dist\output"
copy references.bib dist\ 2>nul

echo.
echo [4/4] Build complete!
echo.
echo +============================================================+
echo | Build Output:                                               |
echo +============================================================+
echo.
echo   Executable: dist\mendeley-patcher.exe
echo   Size: 
echo.
echo To deploy:
echo   1. Copy dist\mendeley-patcher.exe to target laptop
echo   2. Run: mendeley-patcher.exe setup
echo   3. Run: mendeley-patcher.exe full thesis.docx references.bib
echo.
pause
