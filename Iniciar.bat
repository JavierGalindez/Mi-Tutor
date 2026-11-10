@echo off
chcp 65001 >nul
title Mi Tutor
cd /d "%~dp0"
where py >nul 2>nul && (py iniciar.py) || (python iniciar.py)
echo.
pause
