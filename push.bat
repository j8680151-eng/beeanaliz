@echo off
chcp 65001 >nul
title BeeAnaliz - GitHub va Render Yangilash
echo ==============================================
echo    BeeAnaliz - Render / GitHub Yangilash
echo ==============================================
echo.
set /p msg="O'zgarishlar haqida qisqacha yozing (yoki shunchaki Enter bosing): "
if "%msg%"=="" set msg=Yangilanishlar yuklandi

echo.
echo 1. O'zgarishlar tanlanmoqda...
git add .

echo 2. Saqlanmoqda (commit)...
git commit -m "%msg%"

echo 3. GitHub-ga jo'natilmoqda...
git push origin main

echo.
echo ==============================================
echo   Muvaffaqiyatli yuklandi!
echo   Render.com 1-2 daqiqada avtomatik yangilanadi.
echo ==============================================
pause
