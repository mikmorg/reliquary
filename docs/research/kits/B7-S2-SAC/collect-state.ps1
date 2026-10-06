# B7-S2-SAC kit (lab PC): record the SAC state and Defender versions into results\<label>\state.txt.
# Run from an ADMIN PowerShell if possible; without admin, parts may say "access denied",
# which is recorded as-is.
#   powershell -ExecutionPolicy Bypass -File .\collect-state.ps1 -Label W11-sac-on_before-install
param([Parameter(Mandatory = $true)][string]$Label)

$out = Join-Path $PSScriptRoot "results\$Label"
New-Item -ItemType Directory -Force -Path $out | Out-Null
$f = Join-Path $out 'state.txt'

function Section($name, [scriptblock]$body) {
    "== $name" | Out-File -Append -Encoding utf8 $f
    try { & $body 2>&1 | Out-String -Width 200 | Out-File -Append -Encoding utf8 $f }
    catch { "ERROR: $($_.Exception.Message)" | Out-File -Append -Encoding utf8 $f }
}

"B7-S2-SAC state, label $Label, $(Get-Date -Format o)" | Out-File -Encoding utf8 $f
Section 'Windows version' {
    $cv = Get-ItemProperty 'HKLM:\SOFTWARE\Microsoft\Windows NT\CurrentVersion'
    "ProductName=$($cv.ProductName) DisplayVersion=$($cv.DisplayVersion) Build=$($cv.CurrentBuild).$($cv.UBR) Edition=$($cv.EditionID) Arch=$env:PROCESSOR_ARCHITECTURE"
}
Section 'Is this session elevated' {
    ([Security.Principal.WindowsPrincipal][Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)
}
Section 'SAC registry (Policy\VerifiedAndReputablePolicyState: 0 Off, 1 On, 2 Evaluation)' {
    Get-ItemProperty 'HKLM:\SYSTEM\CurrentControlSet\Control\CI\Policy' |
        Select-Object VerifiedAndReputablePolicyState
}
Section 'SAC registry (Protected\VerifiedAndReputablePolicyStateMinValueSeen)' {
    Get-ItemProperty 'HKLM:\SYSTEM\CurrentControlSet\Control\CI\Protected' |
        Select-Object VerifiedAndReputablePolicyStateMinValueSeen
}
Section 'Defender SacLearningModeSwitch' {
    Get-ItemProperty 'HKLM:\SOFTWARE\Microsoft\Windows Defender' | Select-Object SacLearningModeSwitch
}
Section 'citool -lp (VerifiedAndReputable* policies; full output in citool.txt)' {
    $all = & citool.exe -lp 2>&1
    $all | Out-File -Encoding utf8 (Join-Path $out 'citool.txt')
    $all | Select-String -Pattern 'VerifiedAndReputable' -Context 3, 6
}
Section 'Defender versions' {
    Get-MpComputerStatus | Select-Object AMProductVersion, AMEngineVersion, AntivirusSignatureVersion, RealTimeProtectionEnabled
}
Write-Host "Wrote $f"
