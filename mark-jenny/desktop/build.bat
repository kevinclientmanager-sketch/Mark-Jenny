@echo off
echo ========================================
echo   Mark Imti Desktop - Build Script
echo ========================================
echo.

:: Check prerequisites
echo Checking prerequisites...

where node >nul 2>&1
if %errorlevel% neq 0 (
    echo ERROR: Node.js not found. Install from https://nodejs.org
    exit /b 1
)

where python >nul 2>&1
if %errorlevel% neq 0 (
    echo ERROR: Python not found. Install from https://python.org
    exit /b 1
)

where pyinstaller >nul 2>&1
if %errorlevel% neq 0 (
    echo Installing PyInstaller...
    pip install pyinstaller
)

echo.
echo [1/4] Installing Node.js dependencies...
cd desktop
call npm install

echo.
echo [2/4] Building Python backend executable...
cd ..\backend
pyinstaller ..\desktop\build-backend.spec --clean
if %errorlevel% neq 0 (
    echo ERROR: PyInstaller build failed
    exit /b 1
)

:: Copy backend executable to desktop/binaries
echo Copying backend to desktop...
mkdir ..\desktop\binaries 2>nul
copy dist\mark-jenny-server\mark-jenny-server.exe ..\desktop\binaries\

echo.
echo [3/4] Building frontend...
cd ..\frontend
call npx next build

:: Export static files for production
echo Exporting frontend...
call npx next export -o ..\desktop\frontend

echo.
echo [4/4] Building Electron installer...
cd ..\desktop
call npm run build

echo.
echo ========================================
echo   Build Complete!
echo ========================================
echo   Installer: desktop\dist\Mark Imti Setup.exe
echo   Portable:  desktop\dist\Mark Imti.exe
echo ========================================
pause
