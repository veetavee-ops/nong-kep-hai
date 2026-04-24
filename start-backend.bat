@echo off
chcp 65001 >nul
cd /d C:\typhoon-asr\nong-kep-hai
call venv\Scripts\activate

echo ========================================
echo   น้องเก็บให้ Backend Server
echo   Port: 8080
echo ========================================
echo.

python backend.py
pause
