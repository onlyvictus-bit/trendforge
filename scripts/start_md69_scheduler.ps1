# Native collector warnings are written to stderr. Keep them in the log without
# letting PowerShell convert a recoverable per-source warning into task failure.
$ErrorActionPreference = "Continue"

$env:MARKET_DATA_69_ENABLED = "1"
$env:MARKET_DATA_69_PROVISIONAL_OVERRIDE = "1"
$env:PYTHONUNBUFFERED = "1"

$projectRoot = "D:\TrendForge"
$backendRoot = Join-Path $projectRoot "backend"
$pythonPath = Join-Path $projectRoot ".venv\Scripts\python.exe"
$databasePath = Join-Path $projectRoot "data\trendforge_research.db"
$marketDataRoot = Join-Path $projectRoot "data\market_data"
$logRoot = Join-Path $marketDataRoot "logs"
$logPath = Join-Path $logRoot "scheduler.log"

New-Item -ItemType Directory -Path $logRoot -Force | Out-Null
Set-Location -LiteralPath $backendRoot

& $pythonPath -m trendforge_api.cli start-scheduler `
    --db-path $databasePath `
    --data-root $marketDataRoot `
    --poll-seconds 15 *>> $logPath

exit $LASTEXITCODE
