@echo off
chcp 65001 >nul
cd /d "%~dp0"
echo ===== Shefa AI - installing requirements =====
python -m pip install -r requirements.txt
echo ===== Starting Shefa AI... the browser will open automatically =====
python -m streamlit run app.py
pause
