#!/usr/bin/env bash
cd "$(dirname "$0")"
echo "===== Shefa AI - installing requirements ====="
python3 -m pip install -r requirements.txt
echo "===== Starting Shefa AI... ====="
python3 -m streamlit run app.py
