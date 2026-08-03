@echo off
TITLE AHHH IBIZA - SNAPSHOT
color 0b
pushd %~dp0\..
call venv\Scripts\activate
python maintenance/snapshot/take_snapshot.py
echo.
echo Presione cualquier tecla para cerrar...
pause >nul
