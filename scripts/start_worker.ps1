# Arranque local del worker para Windows PowerShell.
# No modifica config.yaml ni imprime credenciales.

$ErrorActionPreference = "Stop"

$ProjectRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
$VenvPath = Join-Path $ProjectRoot ".venv"
$ActivateScript = Join-Path $VenvPath "Scripts\Activate.ps1"
$EnvPath = Join-Path $ProjectRoot ".env"

Set-Location $ProjectRoot

Write-Host "Iniciando worker de job-watcher..."

if (-not (Test-Path $VenvPath)) {
    Write-Host "No se encontro la carpeta .venv."
    Write-Host "Crea el entorno con: python -m venv .venv"
    exit 1
}

if (-not (Test-Path $ActivateScript)) {
    Write-Host "No se encontro el activador de PowerShell en .venv\Scripts\Activate.ps1."
    Write-Host "Revisa que el entorno virtual se haya creado correctamente."
    exit 1
}

if (-not (Test-Path $EnvPath)) {
    Write-Host "No se encontro el archivo .env local."
    Write-Host "Crea .env usando .env.example como plantilla, sin subirlo a Git."
    exit 1
}

Write-Host "Activando entorno virtual..."
. $ActivateScript

Write-Host "Para detener el worker usa Ctrl + C."
python scripts/run_job_watcher.py

$ExitCode = $LASTEXITCODE

if ($ExitCode -ne 0) {
    Write-Host "El worker finalizo con codigo de salida $ExitCode."
    exit $ExitCode
}

Write-Host "Worker finalizado."
