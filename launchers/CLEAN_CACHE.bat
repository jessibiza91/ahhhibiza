@echo off
TITLE AHHH IBIZA - CLEAN CACHE
color 0c
pushd %~dp0\..
call venv\Scripts\activate
echo [INFO] Limpiando solo caches seguros del proyecto...
python maintenance\clean_structure.py
if errorlevel 1 (
    echo [ERROR] La limpieza no pudo completarse.
) else (
    echo [DONE] Limpieza segura completada.
)
popd
pause
