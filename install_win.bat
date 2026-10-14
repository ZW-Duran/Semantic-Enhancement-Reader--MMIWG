@echo off
CHCP 65001 >nul
echo ========================================================
echo   News Coding Tool - Windows Environment Installer
echo ========================================================
echo.

REM Check if Python is installed
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo [!] ERROR: Python is not detected on your system.
    echo.
    echo Please follow these quick steps to install Python:
    echo 1. Visit the official Python downloads page: https://www.python.org/downloads/
    echo 2. Download and run the latest Python 3.13 installer.
    echo 3. [CRITICAL] At the bottom of the installer window, make sure to check:
    echo    [√] Add python.exe to PATH
    echo 4. Click "Install Now" to complete the setup.
    echo.
    echo After installation, please re-double-click [install_windows.bat].
    echo ========================================================
    pause
    exit /b
)

echo [√] Python detected. Checking version...
python --version

echo.
echo [1/3] Creating an isolated local virtual environment (.venv)...
python -m venv .venv

echo [2/3] Activating sandbox and upgrading pip...
call .venv\Scripts\activate
python -m pip install --upgrade pip

echo [3/3] Installing required packages (Streamlit, Google GenAI, etc.)...
pip install -r requirements.txt

echo.
echo ========================================================
echo   [SUCCESS] Environment setup complete!
echo   You can now close this window and double-click any 
echo   run_appX_win.bat file to launch the tools.
echo ========================================================
pause