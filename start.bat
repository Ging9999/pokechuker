@echo off
echo Starting PokeChuker...
echo.
echo [1/2] Starting FastAPI backend on http://localhost:8001
start "PokeChuker Backend" cmd /k "cd /d %~dp0backend && python -m uvicorn main:app --reload --port 8001"

timeout /t 2 /nobreak > nul

echo [2/2] Starting React frontend on http://localhost:5173
start "PokeChuker Frontend" cmd /k "cd /d %~dp0frontend && npm run dev"

echo.
echo Both servers starting. Open http://localhost:5173 in your browser.
