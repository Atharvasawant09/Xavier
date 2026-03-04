@echo off
echo Starting Document Intelligence System...
cd /d %~dp0
uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers 1
pause
