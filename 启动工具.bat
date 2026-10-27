@echo off
cd /d "%~dp0"
if exist "dist\JianyingDraftTool.exe" (
    start "" "dist\JianyingDraftTool.exe"
    exit /b
)
python jianying_gui.py
if errorlevel 1 pause
