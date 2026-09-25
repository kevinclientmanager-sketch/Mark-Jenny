@echo off
title Mark-Imti - Launcher
REM Mark-Imti - ONE-CLICK START (hidden background)
REM Launches backend + frontend with no visible terminal windows.

cd /d "%~dp0"

REM Launch everything hidden via PowerShell
powershell.exe -NoProfile -NonInteractive -ExecutionPolicy Bypass -WindowStyle Hidden -Command "& '%~dp0START-APP.ps1'"

REM Give the servers a moment, then open the app
timeout /t 6 /nobreak >nul
start "" "http://localhost:3000"

exit
