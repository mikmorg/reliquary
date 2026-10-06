# B7-S2-SAC kit FALLBACK: reproduce what tauri-plugin-updater 2.13.0 does on Windows,
# for use only if the real in-app update (README Part 3) cannot be made to work.
# From the updater source (src/updater.rs, Windows install_inner / make_temp_dir / write_to_temp):
#   1. bytes are downloaded in-process (no browser), then written to
#      %TEMP%\<app>-<version>-updater-<random>\<app>-<version>-installer.exe
#   2. ShellExecuteW("open", installer, "/P /UPDATE ...") in the default passive mode
#   3. the app process exits.
# Here: step 1 with .NET HttpClient (in-process, like the updater), step 3 by stopping the
# probe, then step 2 with Start-Process (which also uses ShellExecute by default).
#   powershell -ExecutionPolicy Bypass -File .\simulate-update.ps1 -Url http://192.168.1.10:8000/reliquary-sac-probe_0.2.0_x64-setup.exe
param(
    [Parameter(Mandatory = $true)][string]$Url,
    [string]$AppName = 'reliquary-sac-probe',
    [string]$Version = '0.2.0'
)
Add-Type -AssemblyName System.Net.Http
$rand = [IO.Path]::GetRandomFileName().Replace('.', '')
$dir = Join-Path $env:TEMP "$AppName-$Version-updater-$rand"
New-Item -ItemType Directory -Force -Path $dir | Out-Null
$exe = Join-Path $dir "$AppName-$Version-installer.exe"
$client = New-Object System.Net.Http.HttpClient
$bytes = $client.GetByteArrayAsync($Url).GetAwaiter().GetResult()
[IO.File]::WriteAllBytes($exe, $bytes)
Write-Host "Wrote $exe ($($bytes.Length) bytes)"
try { Get-Content -LiteralPath $exe -Stream Zone.Identifier -ErrorAction Stop; Write-Host '(has Mark-of-the-Web)' }
catch { Write-Host 'No Zone.Identifier stream (no Mark-of-the-Web), as with the real updater.' }
Get-Process -Name $AppName -ErrorAction SilentlyContinue | Stop-Process
$start = Get-Date
Start-Process -FilePath $exe -ArgumentList '/P', '/UPDATE'
Write-Host "Installer started at $($start.ToString('o')). Use this time as -Since for export-ci-events.ps1."
