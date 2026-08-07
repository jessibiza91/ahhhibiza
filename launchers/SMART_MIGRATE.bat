@echo off
TITLE AHHH IBIZA - SMART MIGRATE
color 0e
pushd %~dp0\..
call venv\Scripts\activate

echo [1/3] Backing up DB...
if not exist "backups" mkdir "backups"
docker compose exec -T db pg_dump -U ahhh_user -d ahhh_db > "backups\ahhh_backup_%RANDOM%.sql"

echo [2/3] Making Migrations...
python manage.py makemigrations

echo [3/3] Migrating...
python manage.py migrate

echo.
echo [DONE] Migration Complete.
popd
pause
