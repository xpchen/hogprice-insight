@echo off
chcp 65001 >nul
cd /d %~dp0
cd ..
python scripts\extract_region_spread.py
pause
