#!/usr/bin/env bash
cd "$(dirname "$0")"
echo "===== Shefa AI: installing requirements (first time only) ====="
python3 -m pip install --disable-pip-version-check -q -r requirements.txt || { echo "Install failed"; exit 1; }
echo "===== Starting Shefa AI... keep this window open ====="
( sleep 6; (open http://localhost:8501 || xdg-open http://localhost:8501) >/dev/null 2>&1 ) &
python3 -m streamlit run app.py --server.headless true
