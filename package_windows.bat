@echo off
setlocal EnableExtensions
cd /d "%~dp0"

set "VERSION=1.0.0"
set "PRODUCT=ClipForge-AI-v%VERSION%"
set "STAGE=%TEMP%\%PRODUCT%"
set "ZIP=%CD%\%PRODUCT%.zip"

if exist "%STAGE%" rmdir /s /q "%STAGE%"
if exist "%ZIP%" del /q "%ZIP%"
mkdir "%STAGE%"

 echo ========================================
echo       ClipForge AI Package Builder
echo ========================================
echo.

echo Copying product files...
robocopy "%CD%" "%STAGE%" /E /XD ".git" "node_modules" "dist" "uploads" "outputs" "__pycache__" ".venv" "venv" /XF "*.log" "*.pyc" "%PRODUCT%.zip" >nul
if errorlevel 8 (
  echo ERROR: File copy failed.
  rmdir /s /q "%STAGE%"
  exit /b 1
)

if not exist "%STAGE%\uploads" mkdir "%STAGE%\uploads"
if not exist "%STAGE%\outputs" mkdir "%STAGE%\outputs"

> "%STAGE%\uploads\.gitkeep" echo.
> "%STAGE%\outputs\.gitkeep" echo.

if exist "%STAGE%\frontend\.env" del /q "%STAGE%\frontend\.env"

 echo Creating ZIP package...
powershell -NoProfile -ExecutionPolicy Bypass -Command "Compress-Archive -Path '%STAGE%\*' -DestinationPath '%ZIP%' -CompressionLevel Optimal"
if errorlevel 1 (
  echo ERROR: ZIP creation failed.
  rmdir /s /q "%STAGE%"
  exit /b 1
)

rmdir /s /q "%STAGE%"

echo.
echo ========================================
echo Package created successfully:
echo %ZIP%
echo ========================================
echo.
echo Upload this ZIP to your Gumroad product Content section when
 echo your payout method is available and the product can be published.
echo.
pause
