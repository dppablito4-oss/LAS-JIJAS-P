$ErrorActionPreference = 'Stop'
Set-Location -LiteralPath (Split-Path -Parent $PSScriptRoot)
python -m uv sync --frozen
if ($LASTEXITCODE -ne 0) { throw 'Falló la instalación Python.' }
Push-Location frontend
try {
    npm ci
    if ($LASTEXITCODE -ne 0) { throw 'Falló npm ci.' }
    npm run build
    if ($LASTEXITCODE -ne 0) { throw 'Falló la compilación.' }
} finally { Pop-Location }
& .venv/Scripts/python -m uvicorn app.main:app --app-dir backend --host 127.0.0.1 --port 8000 --no-access-log
