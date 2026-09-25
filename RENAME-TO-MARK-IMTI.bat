@echo off
title Rename mark-jenny to Mark-Imti
echo Renaming folder: mark-jenny -^> Mark-Imti
echo Make sure ALL terminals and editors are closed first.
echo.
cd /d "C:\Users\LAP TECH\Music\Mark"
ren "mark-jenny" "Mark-Imti"
if %errorlevel%==0 (
    echo SUCCESS: Folder renamed to Mark-Imti
) else (
    echo FAILED: Could not rename. Close all programs using the folder and try again.
)
pause
