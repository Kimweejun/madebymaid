$ErrorActionPreference = 'Stop'
$komowPidFile = Join-Path $PSScriptRoot 'server.pid'
if (Test-Path -LiteralPath $komowPidFile) {
    $komowPid = [int](Get-Content -LiteralPath $komowPidFile)
    $komowProcess = Get-CimInstance Win32_Process -Filter "ProcessId=$komowPid"
    $komowScript = Join-Path $PSScriptRoot 'server.py'
    if ($komowProcess -and $komowProcess.Name -match '^python' -and $komowProcess.CommandLine.Contains($komowScript)) {
        Stop-Process -Id $komowPid
    }
}
