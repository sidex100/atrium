# 2026-10-08 apollo-stop.ps1 - end the Apollo stream from the PC keyboard (monitors may be off).
# Apollo web API (local only): POST /api/login {username, password} -> "auth" cookie, then
# POST /api/apps/close -> the running app is closed, the stream ends, the virtual display goes away
# and Apollo runs its undo commands (apollo-wallpapers.ps1 restore - wallpapers back).
#   setup - once: asks for the Apollo web UI login (saved encrypted for this Windows user only - DPAPI,
#           apollo-cred.xml next to this script) and creates the Start menu shortcut with the hotkey
#           Ctrl+Alt+End
#   stop  - (default, what the hotkey runs) close the running app
# NB: logging in from here ends a login in the Apollo web UI in the browser (Apollo keeps one session).
param([ValidateSet('stop', 'setup')][string]$Mode = 'stop')

$ErrorActionPreference = 'Stop'
$Cred = Join-Path $PSScriptRoot 'apollo-cred.xml'
$Log = Join-Path $PSScriptRoot 'apollo-stop.log'
$Base = 'https://localhost:47990'
$Hotkey = 'Ctrl+Alt+End'

function Write-Log([string]$Text) {
    "$(Get-Date -Format 'yyyy-MM-dd HH:mm:ss') $Mode $Text" | Out-File -FilePath $Log -Append -Encoding utf8
}

if ($Mode -eq 'setup') {
    Get-Credential -Message 'Apollo web UI login' | Export-Clixml -Path $Cred
    $lnk = Join-Path ([Environment]::GetFolderPath('Programs')) 'Apollo - stop stream.lnk'
    $sh = (New-Object -ComObject WScript.Shell).CreateShortcut($lnk)
    $sh.TargetPath = Join-Path $env:SystemRoot 'System32\WindowsPowerShell\v1.0\powershell.exe'
    $sh.Arguments = "-NoProfile -ExecutionPolicy Bypass -WindowStyle Hidden -File `"$PSCommandPath`" stop"
    $sh.WindowStyle = 7          # minimized
    $sh.Hotkey = $Hotkey
    $sh.Description = 'End the Apollo stream (closes the running app)'
    $sh.Save()
    Write-Log "credentials saved, shortcut $lnk with $Hotkey"
    "saved. Hotkey: $Hotkey  (shortcut: $lnk)"
    return
}

try {
    # Apollo's web UI certificate is self-signed; trust it for this localhost call only
    [Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12
    [Net.ServicePointManager]::ServerCertificateValidationCallback = { $true }
    $c = Import-Clixml -Path $Cred
    $body = @{ username = $c.UserName; password = $c.GetNetworkCredential().Password } | ConvertTo-Json
    [void](Invoke-WebRequest -Uri "$Base/api/login" -Method Post -ContentType 'application/json' -Body $body `
        -SessionVariable web -UseBasicParsing)
    $r = Invoke-WebRequest -Uri "$Base/api/apps/close" -Method Post -ContentType 'application/json' -Body '{}' `
        -WebSession $web -UseBasicParsing
    Write-Log "apps/close -> $($r.StatusCode) $($r.Content)"
}
catch {
    Write-Log "failed: $($_.Exception.Message)"
}
