# 2026-10-08 apollo-wallpapers.ps1 - per-monitor wallpapers back after an Apollo stream.
# Apollo adds and removes its virtual display; on every such change Windows forgets the
# wallpaper picked for each monitor and puts one picture everywhere.
#   save     - remember the current wallpaper of every connected monitor (run once, while they are right)
#   restore  - for Apollo's "undo" command: starts itself hidden in the background and returns at once;
#              the background copy waits (up to 30 s) until the virtual display is gone - the set of
#              connected monitors is the saved one again - and puts every saved wallpaper back.
# Uses the Windows IDesktopWallpaper COM interface (the same one Settings uses). Data: wallpapers.json,
# log: wallpapers.log - next to this script.
param([ValidateSet('save', 'restore', 'restore-wait')][string]$Mode = 'save')

$ErrorActionPreference = 'Stop'
$Data = Join-Path $PSScriptRoot 'wallpapers.json'
$Log = Join-Path $PSScriptRoot 'wallpapers.log'

function Write-Log([string]$Text) {
    "$(Get-Date -Format 'yyyy-MM-dd HH:mm:ss') $Mode $Text" | Out-File -FilePath $Log -Append -Encoding utf8
}

Add-Type -TypeDefinition @'
using System;
using System.Runtime.InteropServices;

[StructLayout(LayoutKind.Sequential)]
public struct WpRect { public int Left, Top, Right, Bottom; }

[ComImport, Guid("B92B56A9-8B55-4E14-9A89-0199BBB6F93B"), InterfaceType(ComInterfaceType.InterfaceIsIUnknown)]
public interface IDesktopWallpaper {
    void SetWallpaper([MarshalAs(UnmanagedType.LPWStr)] string monitorID, [MarshalAs(UnmanagedType.LPWStr)] string wallpaper);
    [return: MarshalAs(UnmanagedType.LPWStr)] string GetWallpaper([MarshalAs(UnmanagedType.LPWStr)] string monitorID);
    [return: MarshalAs(UnmanagedType.LPWStr)] string GetMonitorDevicePathAt(uint monitorIndex);
    uint GetMonitorDevicePathCount();
    WpRect GetMonitorRECT([MarshalAs(UnmanagedType.LPWStr)] string monitorID);
}

[ComImport, Guid("C2CF3110-460E-4fc1-B9D0-8A1C0C9CC4BD")]
public class DesktopWallpaperClass { }

// all COM calls stay here: PowerShell does not see interface methods on the COM object
public static class Wallpapers {
    static IDesktopWallpaper Get() { return (IDesktopWallpaper)new DesktopWallpaperClass(); }

    // connected monitors only: for a remembered but detached one GetMonitorRECT throws
    public static string[] Monitors() {
        IDesktopWallpaper wp = Get();
        var list = new System.Collections.Generic.List<string>();
        uint n = wp.GetMonitorDevicePathCount();
        for (uint i = 0; i < n; i++) {
            string id = wp.GetMonitorDevicePathAt(i);
            try { wp.GetMonitorRECT(id); list.Add(id); } catch { }
        }
        return list.ToArray();
    }
    public static string GetWallpaper(string id) { return Get().GetWallpaper(id); }
    public static void SetWallpaper(string id, string path) { Get().SetWallpaper(id, path); }
}
'@

function Get-Monitors {
    foreach ($id in [Wallpapers]::Monitors()) {
        [pscustomobject]@{ Id = $id; Wallpaper = [Wallpapers]::GetWallpaper($id) }
    }
}

switch ($Mode) {
    'save' {
        $mons = @(Get-Monitors)
        $mons | ConvertTo-Json | Out-File -FilePath $Data -Encoding utf8
        Write-Log "saved $($mons.Count) monitors"
        $mons | Format-Table -AutoSize
    }
    'restore' {
        # do not keep Apollo waiting: the background copy does the job
        Start-Process -FilePath 'powershell.exe' -WindowStyle Hidden -ArgumentList @(
            '-NoProfile', '-ExecutionPolicy', 'Bypass', '-File', "`"$PSCommandPath`"", 'restore-wait')
    }
    'restore-wait' {
        # not "... | ConvertFrom-Json": in PowerShell 5.1 a JSON array then arrives as ONE object
        $saved = ConvertFrom-Json (Get-Content -Path $Data -Raw -Encoding utf8)
        $want = ($saved.Id | Sort-Object) -join '|'
        $deadline = (Get-Date).AddSeconds(30)
        do {
            Start-Sleep -Seconds 1
            $now = ((Get-Monitors).Id | Sort-Object) -join '|'
        } while ($now -ne $want -and (Get-Date) -lt $deadline)
        if ($now -ne $want) { Write-Log 'monitor set differs from the saved one after 30 s, restoring anyway' }
        Start-Sleep -Seconds 2   # let Windows finish its own reset first
        foreach ($m in $saved) {
            try { [Wallpapers]::SetWallpaper($m.Id, $m.Wallpaper); Write-Log "set $($m.Wallpaper)" }
            catch { Write-Log "failed $($m.Id): $($_.Exception.Message)" }
        }
    }
}
