# Start the local TrendForge API with the inventory-app collector flags.
# Refresh then POSTs http://127.0.0.1:8000/api/market-data/refresh
# and runs the 123 registry jobs (aliases share a parent job).

$ErrorActionPreference = "Continue"

$env:MARKET_DATA_69_ENABLED = "1"
$env:MARKET_DATA_69_PROVISIONAL_OVERRIDE = "1"
$env:MARKET_DATA_69_AUTOSTART = "1"
$env:PYTHONUNBUFFERED = "1"
$env:PYTHONPATH = "D:\TrendForge\backend"

$projectRoot = "D:\TrendForge"
$backendRoot = Join-Path $projectRoot "backend"
$pythonPath = Join-Path $projectRoot ".venv\Scripts\python.exe"
if (-not (Test-Path -LiteralPath $pythonPath)) {
    $pythonPath = "python"
}

Set-Location -LiteralPath $backendRoot
& $pythonPath (Join-Path $backendRoot "run_server.py")
