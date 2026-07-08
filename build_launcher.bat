@echo off
cd /d "%~dp0"

if exist "venv\Scripts\activate.bat" (
    call "venv\Scripts\activate.bat"
)

python -m pip install pyinstaller
python -m PyInstaller --noconfirm --onefile --windowed --name ControleDeAcesso launcher.py

if not exist "release" mkdir "release"
copy /Y "dist\ControleDeAcesso.exe" "release\ControleDeAcesso.exe"

echo.
echo Executavel criado em: release\ControleDeAcesso.exe
pause
