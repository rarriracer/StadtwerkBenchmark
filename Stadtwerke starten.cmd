@echo off
setlocal
cd /d "%~dp0"
if not exist ".venv\Scripts\python.exe" (
  echo Bitte zuerst Windows einrichten.cmd ausfuehren.
  pause
  exit /b 1
)
".venv\Scripts\python.exe" "scripts\start_app.py"
if errorlevel 1 (
  pause
  exit /b 1
)
