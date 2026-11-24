@echo off
cd /d "%~dp0backend"
if exist venv312\Scripts\activate.bat (
    call venv312\Scripts\activate.bat
) else (
    call venv\Scripts\activate.bat
)
python run.py
pause
