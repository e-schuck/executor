@echo off
echo ========================================
echo   Startup Launcher - Build Script
echo ========================================
echo.

REM Check Python
python --version >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Python not found. Install Python 3.10+ and add to PATH.
    pause
    exit /b 1
)

REM Install dependencies
echo Installing dependencies...
pip install -r requirements.txt
if errorlevel 1 (
    echo [ERROR] Failed to install dependencies.
    pause
    exit /b 1
)

REM Build executable
echo.
echo Building StartupLauncher.exe...
pyinstaller --onefile --noconsole --name StartupLauncher --icon=app.ico main.py

if errorlevel 1 (
    echo.
    echo [WARN] Build completed with warnings or icon not found.
    echo        Try without --icon if app.ico is missing.
)

echo.
if exist dist\StartupLauncher.exe (
    echo [OK] Build successful: dist\StartupLauncher.exe
    echo      Copy config.json next to the exe before running.
) else (
    echo [ERROR] Build failed. Check output above.
)

echo.
pause