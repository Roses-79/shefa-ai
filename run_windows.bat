@echo off
chcp 65001 >nul
cd /d "%~dp0"
title Shefa AI

rem ---- find Python (py launcher first, then python) ----
set PY=
py -3 --version >nul 2>nul && set PY=py -3
if not defined PY (python --version >nul 2>nul && set PY=python)
if not defined PY (
    echo.
    echo  Python is not installed.
    echo  Install it from the page that will open now, and TICK "Add Python to PATH".
    echo  Then double-click this file again.
    start https://www.python.org/downloads/
    pause
    exit /b
)

echo.
echo  ===== Shefa AI: installing requirements (first time only, needs internet) =====
%PY% -m pip install --disable-pip-version-check -q -r requirements.txt
if errorlevel 1 (
    echo  Installing failed. Check your internet connection and try again.
    pause
    exit /b
)

echo.
echo  ===== Starting Shefa AI... the browser will open in a few seconds =====
echo  ===== Keep this black window OPEN while you use the app =====
start "" cmd /c "timeout /t 6 >nul & start http://localhost:8501"
%PY% -m streamlit run app.py --server.headless true
pause
