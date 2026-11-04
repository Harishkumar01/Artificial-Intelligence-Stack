$ErrorActionPreference = 'Stop'
$pythonPath = Join-Path $PSScriptRoot '.venv\Scripts\python.exe'
if (-not (Test-Path -LiteralPath $pythonPath)) { throw 'Run Setup.ps1 first.' }
& $pythonPath -m remote_logs.server --config (Join-Path $PSScriptRoot 'config.json')
exit $LASTEXITCODE
