@echo off
setlocal
cd /d "%~dp0"

echo ========================================
echo       ClipForge AI - Windows Setup
echo ========================================
echo.

where python >nul 2>nul
if errorlevel 1 (
  echo ERROR: Python was not found on PATH.
  echo Install Python 3.10 or newer, then run this file again.
  pause
  exit /b 1
)

where node >nul 2>nul
if errorlevel 1 (
  echo ERROR: Node.js was not found on PATH.
  echo Install Node.js 18 or newer, then run this file again.
  pause
  exit /b 1
)

echo [1/3] Installing backend dependencies...
python -m pip install -r backend\requirements.txt
if errorlevel 1 (
  echo ERROR: Backend dependency installation failed.
  pause
  exit /b 1
)

echo.
echo [2/3] Installing frontend dependencies...
cd frontend
call npm install
if errorlevel 1 (
  echo ERROR: Frontend dependency installation failed.
  cd ..
  pause
  exit /b 1
)
cd ..

echo.
echo [3/3] Preparing runtime folders...
if not exist uploads mkdir uploads
if not exist outputs mkdir outputs
if not exist .bin mkdir .bin

where deno >nul 2>nul
if errorlevel 1 (
  echo WARNING: Deno was not found. YouTube extraction may be less reliable.
  echo Deno is optional and can be installed from https://deno.com/
) else (
  echo Deno detected.
)

echo.
echo ========================================
echo Setup complete.
echo Run start_windows.bat to launch ClipForge AI.
echo ========================================
pause
