@echo off
title BeeAnaliz Server
echo ===================================================
echo   BeeAnaliz - 100%% Python POS va Do'kon Tizimi
echo ===================================================
echo Server ishga tushmoqda...
echo Brauzerda oching: http://localhost:5000
echo.
python -m uvicorn app:app --host 0.0.0.0 --port 5000 --reload
pause
