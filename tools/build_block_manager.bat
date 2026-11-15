@echo off
rem Builds dist\HeadRush_NAM_Block_Manager.exe (needs Python 3.10+ from python.org with "Add to PATH" and tcl/tk).
rem Works from any folder: it moves to the repository root first.
cd /d "%~dp0.."
set PY=python
python --version >nul 2>&1 || set PY=py
%PY% --version >nul 2>&1 || (echo No se encontro Python. Instalalo desde python.org marcando "Add Python to PATH". & goto :err)
%PY% -c "import tkinter" >nul 2>&1 || (echo A este Python le falta tkinter: reinstala Python con "tcl/tk and IDLE". & goto :err)
%PY% -m pip install --upgrade pyinstaller || goto :err
%PY% -m PyInstaller --noconfirm --onefile --windowed --name HeadRush_NAM_Block_Manager tools\headrush_block_manager_gui.py || goto :err
echo.
echo Listo: dist\HeadRush_NAM_Block_Manager.exe
pause
exit /b 0
:err
echo.
echo Fallo la compilacion.
pause
exit /b 1
