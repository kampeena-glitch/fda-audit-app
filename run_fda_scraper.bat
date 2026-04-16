@echo off
cd /d "D:\app-fda-audit"
".venv\Scripts\python.exe" "fda_scraper_agent_v2.py" fda >> "fda_scraper_log.txt" 2>&1
