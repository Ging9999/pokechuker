@echo off
echo === PokeChuker Setup ===
echo.

echo [1/4] Installing Python dependencies...
cd /d %~dp0backend
pip install -r requirements.txt
if errorlevel 1 (
    echo ERROR: pip install failed. Make sure Python 3.11+ is installed.
    pause
    exit /b 1
)

echo.
echo [2/4] Installing Playwright browser (Chromium - needed to scrape eBay)...
python -m playwright install chromium
if errorlevel 1 (
    echo ERROR: Playwright browser install failed.
    pause
    exit /b 1
)

echo.
echo [3/4] Installing Node.js dependencies...
cd /d %~dp0frontend
npm install
if errorlevel 1 (
    echo ERROR: npm install failed. Make sure Node.js 18+ is installed.
    pause
    exit /b 1
)

echo.
echo [4/4] Setup complete!
echo Run start.bat to launch the app.
pause
