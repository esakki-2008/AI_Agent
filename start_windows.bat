@echo off
setlocal
cd /d "%~dp0"

echo Starting ClipForge AI...
echo.

echo Backend: http://127.0.0.1:8000
start "ClipForge AI - Backend" cmd /k "cd /d ""%~dp0backend"" && python -m uvicorn main:app --host 127.0.0.1 --port 8000"

timeout /t 2 /nobreak >nul

echo Frontend: http://localhost:5173
start "ClipForge AI - Frontend" cmd /k "cd /d ""%~dp0frontend"" && npm run dev -- --host localhost"

timeout /t 4 /nobreak >nul
start "" http://localhost:5173

echo.
echo ClipForge AI is starting in separate terminal windows.
echo Close those windows when you want to stop the application.
