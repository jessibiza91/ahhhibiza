@echo off
TITLE AHHH IBIZA - SMART MIGRATE
color 0e
pushd %~dp0\..
call venv\Scripts\activate

echo [1/3] Backing up DB...
if not exist "backups" mkdir "backups"
if exist "db_ahhh.sqlite3" copy "db_ahhh.sqlite3" "backups\db_ahhh_before_migrate_%RANDOM%.sqlite3" >nul

echo [2/3] Making Migrations...
python manage.py makemigrations

echo [3/3] Migrating...
python manage.py migrate

echo.
echo [DONE] Migration Complete.
popd
pause
