@echo off
REM Arranque local del worker para Windows con doble clic.
REM No modifica config.yaml ni imprime credenciales.

setlocal
set "PROJECT_ROOT=%~dp0.."

pushd "%PROJECT_ROOT%" >nul
if errorlevel 1 (
    echo No se pudo ubicar la raiz del proyecto.
    pause
    exit /b 1
)

echo Iniciando worker de job-watcher...

if not exist ".venv\" (
    echo No se encontro la carpeta .venv.
    echo Crea el entorno con: python -m venv .venv
    pause
    popd >nul
    exit /b 1
)

if not exist ".venv\Scripts\activate.bat" (
    echo No se encontro .venv\Scripts\activate.bat.
    echo Revisa que el entorno virtual se haya creado correctamente.
    pause
    popd >nul
    exit /b 1
)

if not exist ".env" (
    echo No se encontro el archivo .env local.
    echo Crea .env usando .env.example como plantilla, sin subirlo a Git.
    pause
    popd >nul
    exit /b 1
)

echo Activando entorno virtual...
call ".venv\Scripts\activate.bat"

echo Para detener el worker usa Ctrl + C.
python scripts\run_job_watcher.py

set "EXIT_CODE=%ERRORLEVEL%"

if not "%EXIT_CODE%"=="0" (
    echo El worker finalizo con codigo de salida %EXIT_CODE%.
) else (
    echo Worker finalizado.
)

pause
popd >nul
exit /b %EXIT_CODE%
