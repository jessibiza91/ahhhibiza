@echo off
TITLE AHHH IBIZA - SETUP INICIAL
color 0a
pushd %~dp0\..

echo [INFO] Preparando el entorno del proyecto...

if exist "venv\Scripts\activate.bat" (
    echo [OK] Venv ya existe, se reutiliza.
) else (
    echo [1/3] Creando entorno virtual (venv)...
    python -m venv venv
    if errorlevel 1 goto :error
)

call venv\Scripts\activate
if errorlevel 1 goto :error

echo [2/3] Instalando dependencias desde requirements.txt...
python -m pip install -r requirements.txt
if errorlevel 1 goto :error

if exist ".env" (
    echo [OK] .env ya existe, no se sobrescribe.
) else (
    echo [3/3] Creando .env desde .env.example...
    copy ".env.example" ".env" >nul
    if errorlevel 1 goto :error
)

echo.
echo [OK] Entorno listo. Ejecuta SMART_MIGRATE.bat para crear/aplicar la DB y luego RUN_APP.bat para arrancar.
popd
pause
exit /b 0

:error
echo.
echo [ERROR] El setup no pudo completarse. Revisa el mensaje anterior.
popd
pause
exit /b 1
