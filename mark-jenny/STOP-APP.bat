@echo off
title MARK IMTI - Launcher
REM MARK IMTI - STOP (hidden background)
REM Stops the backend + frontend processes started by START-APP.bat.

set "PIDFILE=%~dp0logs\app.pids"
if not exist "%PIDFILE%" (
    echo No running MARK IMTI instance found (pid file missing).
    pause
    exit /b 1
)

set /p PIDS=<"%PIDFILE%"
for %%P in (%PIDS%) do (
    taskkill /PID %%P /F >nul 2>&1
)

del "%PIDFILE%"
echo MARK IMTI stopped.
pause
