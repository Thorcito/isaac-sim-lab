@echo off
REM Publica en GitHub todos los cambios de esta carpeta (add + commit + push).
cd /d "%~dp0"
echo === Cambios a publicar ===
git status --short
git add -A
git diff --cached --quiet
if errorlevel 1 (
    git commit -m "Actualizacion %date% %time%"
) else (
    echo No hay cambios nuevos; se suben los commits pendientes si los hay.
)
git pull --rebase
git push
if errorlevel 1 (
    echo.
    echo ERROR al publicar. Copia este mensaje y mandalo al chat.
) else (
    echo.
    echo Listo: cambios publicados. En Isaac Sim corre actualizar^(^)
)
pause
