# B7-S2-SAC census: one line describing this PC's Smart App Control state.
# Read-only. Needs no admin rights (if the registry value cannot be read without admin,
# the line says "unreadable"; that is itself a result). Sends nothing anywhere.
# Data class FAM -> AGG: the person sees the line first and decides whether to share it.
# It contains no user name, no computer name and no file names.
#
# Run: right-click > Run with PowerShell, or in PowerShell:
#   powershell -ExecutionPolicy Bypass -File .\census.ps1
# (Unsigned scripts may themselves be blocked on a PC with SAC On. If so, record
#  "script blocked" and use the Settings route in the README instead.)

$ErrorActionPreference = 'Stop'

$cv = Get-ItemProperty 'HKLM:\SOFTWARE\Microsoft\Windows NT\CurrentVersion'
$buildNum = [int]$cv.CurrentBuild
$os = if ($buildNum -ge 22000) { 'Windows 11' } else { 'Windows 10' }
$build = "$($cv.CurrentBuild).$($cv.UBR)"

# SAC mode, as documented in Microsoft's SAC testing guide:
# ...\Control\CI\Policy\VerifiedAndReputablePolicyState  0 = Off, 1 = On, 2 = Evaluation
$sac = 'unreadable'
try {
    $v = (Get-ItemProperty -Path 'HKLM:\SYSTEM\CurrentControlSet\Control\CI\Policy' `
          -Name 'VerifiedAndReputablePolicyState').VerifiedAndReputablePolicyState
    $sac = switch ($v) { 0 { 'Off' } 1 { 'On' } 2 { 'Evaluation' } default { "Other($v)" } }
} catch [System.Management.Automation.PSArgumentException] {
    $sac = 'value-absent'
} catch {
    $sac = 'unreadable'
}

# Optional second opinion from the documented WinRT API (IsEnabled). It may not load
# in every PowerShell version; "n/a" is fine.
$api = 'n/a'
try {
    $null = [Windows.System.Profile.SmartAppControlPolicy, Windows.System.Profile, ContentType = WindowsRuntime]
    $api = [string][Windows.System.Profile.SmartAppControlPolicy]::IsEnabled
} catch { $api = 'n/a' }

$line = "SAC=$sac; OS=$os; build=$build; edition=$($cv.EditionID); arch=$env:PROCESSOR_ARCHITECTURE; api_IsEnabled=$api"
Write-Host ''
Write-Host 'This is everything this script found (nothing has been sent):' -ForegroundColor Cyan
Write-Host ''
Write-Host $line
Write-Host ''
Write-Host 'If you are happy to share it, copy the line above and send it to the person who asked.'
Read-Host 'Press Enter to close'
