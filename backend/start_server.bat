@echo off
echo ========================================
echo Starting Print X Django Server
echo ========================================
echo.

REM Set email environment variables
set EMAIL_HOST_USER=3dprintxcontact@gmail.com
set EMAIL_HOST_PASSWORD=mugptymalyopurwb

echo [EMAIL] SMTP Enabled
echo [USER] %EMAIL_HOST_USER%
echo.

echo Starting Django development server...
echo Press CTRL+C to stop the server
echo.

python manage.py runserver
