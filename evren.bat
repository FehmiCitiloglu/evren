@echo off
REM evren masaüstü uygulaması başlatıcısı (Windows)
cd /d "%~dp0"
if exist ".venv\Scripts\evren.exe" (
    start "" ".venv\Scripts\evren.exe" gui
) else (
    start "" python -m evren_agent.ui
)
