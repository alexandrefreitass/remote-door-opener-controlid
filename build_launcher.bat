@echo off
cd /d "%~dp0"

set "PYTHON=python"
if exist "venv\Scripts\python.exe" set "PYTHON=venv\Scripts\python.exe"

"%PYTHON%" -m pip install pyinstaller==6.21.0
if errorlevel 1 exit /b 1

"%PYTHON%" -m PyInstaller --clean --noconfirm --onedir --windowed --name ControleDeAcesso --version-file version_info.txt launcher.py
if errorlevel 1 exit /b 1

if exist "release\ControleDeAcesso" rmdir /S /Q "release\ControleDeAcesso"
if exist "release\ControleDeAcesso" (
    echo.
    echo Nao foi possivel atualizar o launcher. Feche ControleDeAcesso.exe e tente novamente.
    exit /b 1
)
if not exist "release" mkdir "release"
xcopy /E /I /Y "dist\ControleDeAcesso" "release\ControleDeAcesso" >nul
if errorlevel 1 exit /b 1

echo.
echo Launcher criado em: release\ControleDeAcesso\ControleDeAcesso.exe
if not defined CI pause
