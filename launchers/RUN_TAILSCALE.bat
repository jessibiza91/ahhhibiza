@echo off
TITLE AHHH IBIZA - TAILSCALE SERVER
color 0b
pushd %~dp0\..
call venv\Scripts\activate
echo [SISTEMA] Iniciando Django para acceso LAN/Tailscale...
echo [INFO] URL Tailscale habitual: http://100.95.61.46:8000/
echo [INFO] Si Windows Firewall pregunta, permite redes privadas.
python manage.py runserver 0.0.0.0:8000
