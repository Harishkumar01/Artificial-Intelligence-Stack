$ErrorActionPreference = 'Stop'
$pythonPath = Join-Path $PSScriptRoot '.venv\Scripts\python.exe'
if (-not (Test-Path -LiteralPath $pythonPath)) {
    & py -3 -m venv (Join-Path $PSScriptRoot '.venv')
    if ($LASTEXITCODE -ne 0) { throw 'Install Python 3.11 or newer with the Windows py launcher, then retry.' }
}
& $pythonPath -m pip install -r (Join-Path $PSScriptRoot 'requirements.lock.txt')
if ($LASTEXITCODE -ne 0) { throw 'Dependency installation failed.' }
& $pythonPath -m pip install --no-deps -e $PSScriptRoot
if ($LASTEXITCODE -ne 0) { throw 'Package installation failed.' }
Write-Host 'Installed. Run Configure.ps1 to enter environment details and password locally.'
