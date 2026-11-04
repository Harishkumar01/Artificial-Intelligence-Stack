$ErrorActionPreference = 'Stop'
$pythonPath = Join-Path $PSScriptRoot '.venv\Scripts\python.exe'
if (-not (Test-Path -LiteralPath $pythonPath)) { throw 'Run Setup.ps1 first.' }
& $pythonPath -m remote_logs.configure --config (Join-Path $PSScriptRoot 'config.json')
if ($LASTEXITCODE -ne 0) { throw 'Configuration failed.' }
