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
set PYINSTALLER_CMD=
where pyinstaller >nul 2>&1 && set PYINSTALLER_CMD=pyinstaller || python -m PyInstaller --version >nul 2>&1 && set PYINSTALLER_CMD=python -m PyInstaller
if "%PYINSTALLER_CMD%"=="" (
    echo [ERROR] PyInstaller not found. Run: pip install pyinstaller
    pause
    exit /b 1
)
if exist app.ico (
    %PYINSTALLER_CMD% --onefile --noconsole --name StartupLauncher --icon=app.ico main.py
) else (
    echo [INFO] app.ico not found, building without custom icon.
    %PYINSTALLER_CMD% --onefile --noconsole --name StartupLauncher main.py
)

if errorlevel 1 (
    echo.
    echo [WARN] Build completed with warnings.
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