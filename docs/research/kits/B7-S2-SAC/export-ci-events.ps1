# B7-S2-SAC kit (lab PC): export CodeIntegrity/Operational events since a start time.
# Microsoft's SAC testing guide: SAC logs blocked (or would-be-blocked) files there,
# event 3076 in evaluation/audit mode and 3077 in enforcement mode, one event per file.
# Run from an ADMIN PowerShell (reading this log may need it).
#   powershell -ExecutionPolicy Bypass -File .\export-ci-events.ps1 -Label W11-sac-on_first-launch -Since '2026-10-01 14:05'
param(
    [Parameter(Mandatory = $true)][string]$Label,
    [Parameter(Mandatory = $true)][datetime]$Since
)
$out = Join-Path $PSScriptRoot "results\$Label"
New-Item -ItemType Directory -Force -Path $out | Out-Null

$events = @()
try {
    $events = Get-WinEvent -FilterHashtable @{
        LogName   = 'Microsoft-Windows-CodeIntegrity/Operational'
        StartTime = $Since
    } -ErrorAction Stop
} catch {
    if ($_.Exception.Message -match 'No events were found') { $events = @() }
    else { "ERROR: $($_.Exception.Message)" | Out-File (Join-Path $out 'ci-events-error.txt'); throw }
}

# Everything in the window (all IDs), so nothing is filtered away by assumption.
$events | Select-Object TimeCreated, Id, LevelDisplayName,
    @{ n = 'Message'; e = { ($_.Message -replace '\s+', ' ') } } |
    Export-Csv -NoTypeInformation -Encoding UTF8 (Join-Path $out 'ci-events-all.csv')

# The SAC block/audit events the guide names.
$sac = $events | Where-Object { $_.Id -in 3076, 3077 }
$sac | Select-Object TimeCreated, Id,
    @{ n = 'Message'; e = { ($_.Message -replace '\s+', ' ') } } |
    Export-Csv -NoTypeInformation -Encoding UTF8 (Join-Path $out 'ci-events-3076-3077.csv')

"{0} events in window; {1} with ID 3076; {2} with ID 3077" -f $events.Count,
    ($sac | Where-Object Id -eq 3076).Count, ($sac | Where-Object Id -eq 3077).Count |
    Tee-Object -FilePath (Join-Path $out 'ci-events-summary.txt')
Write-Host 'Check the CSVs: the file paths name the test user folder; use a test account (sactest).'
