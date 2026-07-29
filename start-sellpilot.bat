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
  pushd "%SELLPILOT_ROOT%backend"
  for /f "delims=" %%I in ('uv run sellpilot-start-api --print-proxy-target') do set "VITE_PROXY_TARGET=%%I"
  popd
  echo SellPilot launcher checks passed. Backend target: %VITE_PROXY_TARGET%
  exit /b 0
)

pushd "%SELLPILOT_ROOT%backend"
for /f "delims=" %%I in ('uv run sellpilot-start-api --print-proxy-target') do set "VITE_PROXY_TARGET=%%I"
popd
if not defined VITE_PROXY_TARGET (
  echo [ERROR] Could not resolve the configured SellPilot backend endpoint.
  exit /b 1
)

echo Starting or reusing SellPilot backend at %VITE_PROXY_TARGET% ...
start "SellPilot Backend" /D "%SELLPILOT_ROOT%backend" cmd /c "uv run sellpilot-start-api"
echo Starting SellPilot frontend at http://127.0.0.1:5173 ...
start "SellPilot Frontend" /D "%SELLPILOT_ROOT%frontend" cmd /k "set VITE_PROXY_TARGET=%VITE_PROXY_TARGET%&& npm run dev -- --host 127.0.0.1"

timeout /t 4 /nobreak >nul
start "" "http://127.0.0.1:5173/dashboard"

echo SellPilot startup commands were launched in two terminal windows.
echo Close those windows to stop the development servers.
endlocal
