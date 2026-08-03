@echo off
TITLE AHHH IBIZA - VERIFY PROJECT
color 0a
pushd %~dp0\..
call venv\Scripts\activate

echo [1/3] Comprobando configuracion Django...
python manage.py check
if errorlevel 1 goto :error

echo [2/3] Comprobando migraciones pendientes...
python manage.py makemigrations --check --dry-run
if errorlevel 1 goto :error

echo [3/3] Ejecutando pruebas de flujos criticos...
python manage.py test
if errorlevel 1 goto :error

echo.
echo [OK] Proyecto estable: checks, migraciones y pruebas correctos.
popd
pause
exit /b 0

:error
echo.
echo [ERROR] La verificacion ha detectado un problema. Revisa el mensaje anterior.
popd
pause
exit /b 1
