param([string]$PythonExe = '')
$ErrorActionPreference = 'Stop'
Set-Location -LiteralPath $PSScriptRoot
if (-not $PythonExe) {
    $pythonRoot = Join-Path $env:LOCALAPPDATA 'Programs\Python'
    $candidate = Get-ChildItem -LiteralPath $pythonRoot -Directory -ErrorAction SilentlyContinue |
        Where-Object Name -Match '^Python\d+$' | Sort-Object Name -Descending |
        ForEach-Object { Join-Path $_.FullName 'python.exe' } |
        Where-Object { Test-Path -LiteralPath $_ } | Select-Object -First 1
    if ($candidate) { $PythonExe = $candidate }
    else {
        $launcher = Get-Command py -ErrorAction SilentlyContinue
        if ($launcher) { $PythonExe = (& $launcher.Source -3 -c 'import sys; print(sys.executable)') }
    }
}
if (-not $PythonExe -or -not (Test-Path -LiteralPath $PythonExe)) {
    throw 'Python 3 was not found. Install Python 3 or run setup.ps1 -PythonExe <python.exe path>.'
}
$venvPython = Join-Path $PSScriptRoot '.venv\Scripts\python.exe'
if (-not (Test-Path -LiteralPath $venvPython)) {
    & $PythonExe -m venv (Join-Path $PSScriptRoot '.venv')
    if ($LASTEXITCODE -ne 0) { throw 'Could not create .venv.' }
}
& $venvPython -m pip install --disable-pip-version-check -r (Join-Path $PSScriptRoot 'requirements.txt')
if ($LASTEXITCODE -ne 0) { throw 'Dependency installation failed.' }
Write-Host 'Ready. Run run_game.cmd or open the folder in VS Code and press F5.'
