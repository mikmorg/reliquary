# B7-S2-SAC kit: for each file, record size, SHA-256, Authenticode status, signer,
# public-key algorithm (SAC accepts RSA only) and whether it carries Mark-of-the-Web
# (a Zone.Identifier stream). Works without admin.
#   powershell -ExecutionPolicy Bypass -File .\check-files.ps1 -Label v1-on-stick -Path E:\probe\*.exe
param(
    [Parameter(Mandatory = $true)][string]$Label,
    [Parameter(Mandatory = $true)][string[]]$Path
)
$out = Join-Path $PSScriptRoot "results\$Label"
New-Item -ItemType Directory -Force -Path $out | Out-Null
$rows = foreach ($p in (Get-Item -Path $Path)) {
    $sig = Get-AuthenticodeSignature -FilePath $p.FullName
    $zone = $null
    try { $zone = (Get-Content -LiteralPath $p.FullName -Stream Zone.Identifier -ErrorAction Stop) -join ' | ' } catch { $zone = '' }
    [pscustomobject]@{
        File          = $p.Name
        Bytes         = $p.Length
        SHA256        = (Get-FileHash -Algorithm SHA256 -LiteralPath $p.FullName).Hash
        SigStatus     = $sig.Status
        Signer        = if ($sig.SignerCertificate) { $sig.SignerCertificate.Subject } else { '' }
        Issuer        = if ($sig.SignerCertificate) { $sig.SignerCertificate.Issuer } else { '' }
        KeyAlgorithm  = if ($sig.SignerCertificate) { $sig.SignerCertificate.PublicKey.Oid.FriendlyName } else { '' }
        Timestamped   = [bool]$sig.TimeStamperCertificate
        ZoneIdentifier = $zone
    }
}
$rows | Export-Csv -NoTypeInformation -Encoding UTF8 (Join-Path $out 'files.csv')
$rows | Format-Table -AutoSize File, Bytes, SigStatus, KeyAlgorithm, ZoneIdentifier
