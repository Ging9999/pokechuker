@echo off
echo Installing BGS Scraper dependencies...
pip install -r requirements.txt
echo Installing Playwright Chromium browser...
python -m playwright install chromium
echo.
echo Setup complete. Run with:
echo   python main.py --help
