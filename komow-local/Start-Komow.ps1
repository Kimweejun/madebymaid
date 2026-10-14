$ErrorActionPreference = 'Stop'
$komowUrl = 'http://127.0.0.1:8788'
$komowReady = $false
try {
    $komowHealth = Invoke-RestMethod -Uri ($komowUrl + '/api/health') -TimeoutSec 2
    if ($komowHealth.service -eq 'Komow Local') { $komowReady = $true }
    else { throw 'Port 8788 is used by another application.' }
} catch { }
if (-not $komowReady) {
    # LAN mode (phone on the same Wi-Fi): set "lan_password" (12+ chars) in data\secrets.json
    $komowSecrets = Join-Path $PSScriptRoot 'data\secrets.json'
    $komowLan = $null
    if (Test-Path $komowSecrets) { $komowLan = (Get-Content $komowSecrets -Raw -Encoding UTF8 | ConvertFrom-Json).lan_password }
    if ($komowLan -and $komowLan.Length -ge 12) {
        $komowIps = @(Get-NetIPAddress -AddressFamily IPv4 | Where-Object { $_.IPAddress -notlike '127.*' -and $_.IPAddress -notlike '169.254.*' } | ForEach-Object { $_.IPAddress })
        $env:KOMOW_HOST = '0.0.0.0'; $env:KOMOW_PASSWORD = $komowLan; $env:KOMOW_ALLOWED_HOSTS = ($komowIps -join ',')
        $komowIps | ForEach-Object { "http://$($_):8788" } | Set-Content (Join-Path $PSScriptRoot 'phone-address.txt') -Encoding UTF8
    }
    $komowPython = (Get-Command python -ErrorAction Stop).Source
    $komowScript = Join-Path $PSScriptRoot 'server.py'
    $komowProcess = Start-Process -FilePath $komowPython -ArgumentList ('"' + $komowScript + '" --port 8788') -WorkingDirectory $PSScriptRoot -WindowStyle Hidden -PassThru -RedirectStandardOutput (Join-Path $PSScriptRoot 'server.log') -RedirectStandardError (Join-Path $PSScriptRoot 'server-error.log')
    $komowProcess.Id | Set-Content (Join-Path $PSScriptRoot 'server.pid')
    for ($komowAttempt=0; $komowAttempt -lt 40; $komowAttempt++) {
        Start-Sleep -Milliseconds 250
        if ($komowProcess.HasExited) { throw 'Komow server failed. See server-error.log.' }
        try {
            $komowHealth = Invoke-RestMethod -Uri ($komowUrl + '/api/health') -TimeoutSec 1
            if ($komowHealth.service -eq 'Komow Local') { $komowReady = $true; break }
        } catch { }
    }
    if (-not $komowReady) { throw 'Komow server did not start.' }
}
# no browser window on start (open http://127.0.0.1:8788 yourself; phone address is in phone-address.txt)
