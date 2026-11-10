@echo off
chcp 65001 >nul
cd /d "%~dp0"
echo Creando acceso directo "Mi Tutor" en el escritorio...
powershell -NoProfile -ExecutionPolicy Bypass -Command "$s=(New-Object -ComObject WScript.Shell).CreateShortcut([Environment]::GetFolderPath('Desktop')+'\Mi Tutor.lnk'); $s.TargetPath='%~dp0Iniciar.bat'; $s.WorkingDirectory='%~dp0'; $s.Save()"
echo Listo. Use el acceso del escritorio para abrir Mi Tutor.
echo Esta accion no borra ni reinicia la base de datos.
pause
