@echo off
REM Publica en GitHub todos los cambios de esta carpeta (add + commit + push).
cd /d "%~dp0"
echo === Cambios a publicar ===
git status --short
git add -A
git diff --cached --quiet
if %errorlevel%==0 (
    echo.
    echo No hay cambios para publicar.
    pause
    exit /b 0
)
git commit -m "Actualizacion %date% %time%"
git pull --rebase
git push
if %errorlevel%==0 (
    echo.
    echo Listo: cambios publicados. En Isaac Sim corre actualizar^(^)
) else (
    echo.
    echo ERROR al publicar. Copia este mensaje y mandalo al chat.
)
pause
