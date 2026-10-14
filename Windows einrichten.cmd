@echo off
setlocal
cd /d "%~dp0"
where uv >nul 2>nul
if errorlevel 1 (
  echo uv fehlt. In PowerShell einmal ausfuehren:
  echo winget install --id astral-sh.uv -e
  echo Danach dieses Fenster schliessen und die Einrichtung erneut starten.
  pause
  exit /b 1
)
if exist ".venv\bin\python" (
  echo Dieser Ordner enthaelt eine Mac- oder Linux-Umgebung.
  echo Bitte das Windows-Paket in einen frischen Ordner entpacken.
  pause
  exit /b 1
)
uv sync --frozen --python 3.12
if errorlevel 1 goto failed
".venv\Scripts\python.exe" "scripts\start_app.py" --setup
if errorlevel 1 goto failed
pause
exit /b 0
:failed
echo Einrichtung fehlgeschlagen. Bitte die Meldung oben beachten.
pause
exit /b 1
