@echo off
echo ========================================
echo  TradeWin Standalone — Build Script
echo ========================================
python --version >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Python not found in PATH
    echo Please install Python 3.11+ from https://python.org
    pause
    exit /b 1
)

echo [1/4] Installing build dependencies...
pip install -r requirements.txt
if errorlevel 1 (
    echo [ERROR] Failed to install PySide6 / pyinstaller
    pause
    exit /b 1
)

echo [2/4] Installing Trade + Hermes Agent...
pip install -e ..
if errorlevel 1 (
    echo [ERROR] Failed to install Trade
    pause
    exit /b 1
)

pip install hermes-agent
if errorlevel 1 (
    echo [WARNING] hermes-agent install failed — AI features won't work
)

echo [3/4] Cleaning old builds...
if exist build rmdir /s /q build
if exist dist rmdir /s /q dist

echo [4/4] Building single .exe (this may take 5-10 minutes)...
pyinstaller --clean --noconfirm tradewin.spec
if errorlevel 1 (
    echo [ERROR] PyInstaller build failed
    pause
    exit /b 1
)

echo.
echo ========================================
echo  Build complete!
echo  Executable: dist\TradeWin.exe
echo.
echo  Copy TradeWin.exe to any Windows computer.
echo  First run will auto-install everything needed.
echo ========================================
pause
