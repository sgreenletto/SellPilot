@echo off
setlocal

set "SELLPILOT_ROOT=%~dp0"
set "CHECK_ONLY="
if /I "%~1"=="--check" set "CHECK_ONLY=1"

where uv >nul 2>&1
if errorlevel 1 (
  echo [ERROR] uv was not found. Install uv and make sure it is available on PATH.
  if not defined CHECK_ONLY pause
  exit /b 1
)

where npm >nul 2>&1
if errorlevel 1 (
  echo [ERROR] npm was not found. Install Node.js and make sure npm is available on PATH.
  if not defined CHECK_ONLY pause
  exit /b 1
)

if not exist "%SELLPILOT_ROOT%backend\pyproject.toml" (
  echo [ERROR] backend\pyproject.toml is missing.
  if not defined CHECK_ONLY pause
  exit /b 1
)

if not exist "%SELLPILOT_ROOT%frontend\package.json" (
  echo [ERROR] frontend\package.json is missing.
  if not defined CHECK_ONLY pause
  exit /b 1
)

if not exist "%SELLPILOT_ROOT%frontend\node_modules" (
  echo [ERROR] Frontend dependencies are missing.
  echo Run "cd frontend" followed by "npm install", then open this file again.
  if not defined CHECK_ONLY pause
  exit /b 1
)

if defined CHECK_ONLY (
  echo SellPilot launcher checks passed.
  exit /b 0
)

echo Starting SellPilot backend at http://127.0.0.1:8000 ...
start "SellPilot Backend" /D "%SELLPILOT_ROOT%backend" cmd /k "uv run uvicorn sellpilot.main:app --host 127.0.0.1 --port 8000"

echo Starting SellPilot frontend at http://127.0.0.1:5173 ...
start "SellPilot Frontend" /D "%SELLPILOT_ROOT%frontend" cmd /k "npm run dev -- --host 127.0.0.1"

timeout /t 4 /nobreak >nul
start "" "http://127.0.0.1:5173/dashboard"

echo SellPilot startup commands were launched in two terminal windows.
echo Close those windows to stop the development servers.
endlocal
