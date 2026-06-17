@echo off
echo ========================================
echo  TradeWin Standalone — Build Script
echo ========================================
python --version >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Python not found in PATH
    exit /b 1
)
echo [1/3] Installing dependencies...
pip install -r requirements.txt
pip install -e ..
echo [2/3] Cleaning old builds...
if exist build rmdir /s /q build
if exist dist rmdir /s /q dist
echo [3/3] Building single .exe...
pyinstaller --clean --noconfirm tradewin.spec
echo.
echo ========================================
echo  Build complete!
echo  Executable: dist\TradeWin.exe
echo ========================================
pause
