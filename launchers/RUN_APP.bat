@echo off
TITLE AHHH IBIZA - SERVER
color 0a
pushd %~dp0\..
call venv\Scripts\activate
echo [SISTEMA] Iniciando motor Django...
python manage.py runserver
pause