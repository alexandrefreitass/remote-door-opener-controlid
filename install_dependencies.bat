@echo off
cd /d "%~dp0"

where python >nul 2>nul
if errorlevel 1 (
    echo Python nao encontrado.
    echo Instale o Python 3.11 ou superior em https://www.python.org/downloads/
    pause
    exit /b 1
)

if not exist "venv" (
    python -m venv venv
)

"venv\Scripts\python.exe" -m pip install --upgrade pip
"venv\Scripts\python.exe" -m pip install -r requirements.txt

echo.
echo Dependencias instaladas. Agora abra ControleDeAcesso.exe.
pause
