[CmdletBinding()]
param([string]$TargetDirectory, [switch]$CheckOnly)
$ErrorActionPreference = 'Stop'
Set-StrictMode -Version Latest
$env:PSModulePath = Join-Path $PSHOME 'Modules'
if (-not $TargetDirectory) {
    foreach ($candidate in @($PSScriptRoot, 'D:\Apps\CodexEVA', 'H:\Apps\CodexEVA')) {
        if (Test-Path -LiteralPath (Join-Path $candidate 'installation.json') -PathType Leaf) { $TargetDirectory = $candidate; break }
    }
}
if (-not $TargetDirectory) { throw 'Installed EVA folder not found. Pass -TargetDirectory X:\Apps\CodexEVA.' }
$target = [IO.Path]::GetFullPath($TargetDirectory).TrimEnd('\')
if ($target -notmatch '^[A-Za-z]:\\[^\\]') { throw 'Choose an existing local EVA installation folder.' }
$cursor = Get-Item -LiteralPath $target -Force
while ($cursor) {
    if (($cursor.Attributes -band [IO.FileAttributes]::ReparsePoint) -ne 0) { throw 'Updates through junctions or symbolic links are not supported.' }
    $cursor = $cursor.Parent
}
$installationPath = Join-Path $target 'installation.json'
$installation = Get-Content -LiteralPath $installationPath -Raw -Encoding UTF8 | ConvertFrom-Json
$oldManifest = Get-Content -LiteralPath (Join-Path $target 'manifest.json') -Raw -Encoding UTF8 | ConvertFrom-Json
if ($oldManifest.version -notin @('R7-S4-installed-10.1', 'R7-S4-installed-10.2', 'R7-S4-installed-10.3', 'R7-S4-installed-10.4', 'R7-S4-installed-10.5', 'R7-S4-installed-10.6', 'R7-S4-installed-10.7', 'R7-S4-installed-10.8', 'R7-S4-installed-10.9', 'R7-S4-installed-10.10', 'R7-S4-installed-10.11')) { throw 'This update supports v10.1 through v10.11 installations. Use the complete v10.11 package for older versions.' }
$patch = Get-Content -LiteralPath (Join-Path $PSScriptRoot 'update-manifest.json') -Raw -Encoding UTF8 | ConvertFrom-Json
$allowed = @('CodexEVA.exe', 'loader.py', 'manifest.json', 'theme.bundle.js', 'Collect-Diagnostics.ps1', 'Collect-Diagnostics.cmd', 'startup.bundle.js', 'startup-native-video.mp4', 'startup-native.wav', 'startup-first-frame.jpg', 'startup-native.frames', '使用说明.txt')
if (@($patch.files.PSObject.Properties).Count -ne $allowed.Count) { throw 'Incomplete update manifest.' }
foreach ($item in $patch.files.PSObject.Properties) {
    if ($item.Name -notin $allowed) { throw 'Unexpected update file.' }
    $source = Join-Path (Join-Path $PSScriptRoot 'payload') $item.Name
    $info = Get-Item -LiteralPath $source
    if (($info.Attributes -band [IO.FileAttributes]::ReparsePoint) -ne 0 -or $info.Length -ne $item.Value.bytes -or (Get-FileHash -LiteralPath $source -Algorithm SHA256).Hash -ne $item.Value.sha256) { throw "Update checksum mismatch: $($item.Name)" }
}
# Verify unchanged assets against the new manifest and replaced assets against the installed manifest.
$newManifest = Get-Content -LiteralPath (Join-Path $PSScriptRoot 'payload\manifest.json') -Raw -Encoding UTF8 | ConvertFrom-Json
foreach ($item in $newManifest.files.PSObject.Properties) {
    if ($item.Name -notmatch '^[a-zA-Z0-9_.-]+$') { throw 'Unsafe asset name.' }
    $assetPath = Join-Path $target $item.Name
    if ($item.Name -in $allowed -and $oldManifest.files.PSObject.Properties.Name -notcontains $item.Name) {
        if (Test-Path -LiteralPath $assetPath) { throw "Unexpected existing file: $($item.Name). Move it aside before updating." }
        continue
    }
    $asset = Get-Item -LiteralPath $assetPath
    $expected = if ($item.Name -in $allowed) { $oldManifest.files.($item.Name) } else { $item.Value }
    if (($asset.Attributes -band [IO.FileAttributes]::ReparsePoint) -ne 0 -or $asset.Length -ne $expected.bytes -or (Get-FileHash -LiteralPath $asset.FullName -Algorithm SHA256).Hash -ne $expected.sha256) { throw "Installed asset mismatch: $($item.Name). Use the complete v10.11 package in an empty folder." }
}
$updateBytes = [long]0
foreach ($item in $patch.files.PSObject.Properties) { $updateBytes += [long]$item.Value.bytes }
$names = @($allowed) + @('installation.json')
$packagePath = Join-Path $target 'package-manifest.json'
if (Test-Path -LiteralPath $packagePath -PathType Leaf) { $names += 'package-manifest.json' }
$backupRoot = if (Test-Path -LiteralPath 'H:\') { 'H:\Archives\CodexEVA\updates' } else { Join-Path $target 'backups' }
$backupBytes = [long]0
foreach ($name in $names) {
    $path = Join-Path $target $name
    if (Test-Path -LiteralPath $path -PathType Leaf) { $backupBytes += (Get-Item -LiteralPath $path).Length }
}
$targetDrive = New-Object IO.DriveInfo ([IO.Path]::GetPathRoot($target))
$backupDrive = New-Object IO.DriveInfo ([IO.Path]::GetPathRoot($backupRoot))
$targetNeeded = $updateBytes + 64MB
if ($targetDrive.Name -eq $backupDrive.Name) { $targetNeeded += $backupBytes }
if ($targetDrive.AvailableFreeSpace -lt $targetNeeded -or $backupDrive.AvailableFreeSpace -lt ($backupBytes + 64MB)) { throw 'Insufficient free space for the new payload and verified rollback backup.' }
foreach ($name in $names) {
    $dest = Join-Path $target $name
    if (Test-Path -LiteralPath $dest) {
        if (((Get-Item -LiteralPath $dest -Force).Attributes -band [IO.FileAttributes]::ReparsePoint) -ne 0) { throw "Target link not supported: $name" }
        try { $handle = [IO.File]::Open($dest, 'Open', 'ReadWrite', 'None'); $handle.Dispose() }
        catch { throw "File in use or not writable: $name. Close the EVA animation, then run Update.cmd again." }
    }
}
if ($CheckOnly) { [ordered]@{ passed=$true; target=$target; version=$patch.version; checkOnly=$true } | ConvertTo-Json; exit 0 }
$backup = Join-Path $backupRoot ('before-v10.11-' + (Get-Date -Format 'yyyyMMdd-HHmmss') + '-' + [Guid]::NewGuid().ToString('N').Substring(0,6))
New-Item -ItemType Directory -Path $backup -Force | Out-Null
$present = @{}
foreach ($name in $names) {
    $path = Join-Path $target $name
    $present[$name] = Test-Path -LiteralPath $path -PathType Leaf
    if ($present[$name]) { Copy-Item -LiteralPath $path -Destination (Join-Path $backup $name) }
}
try {
    foreach ($name in $allowed) {
        Copy-Item -LiteralPath (Join-Path (Join-Path $PSScriptRoot 'payload') $name) -Destination (Join-Path $target $name) -Force
        if ((Get-FileHash -LiteralPath (Join-Path $target $name) -Algorithm SHA256).Hash -ne $patch.files.$name.sha256) { throw "Post-update checksum mismatch: $name" }
    }
    $installation | Add-Member -NotePropertyName version -NotePropertyValue $patch.version -Force
    $installation | Add-Member -NotePropertyName rendererVersion -NotePropertyValue $newManifest.version -Force
    $installation | Add-Member -NotePropertyName themeVersion -NotePropertyValue $newManifest.themeVersion -Force
    $installation | Add-Member -NotePropertyName updatedAt -NotePropertyValue (Get-Date).ToString('o') -Force
    $installation | Add-Member -NotePropertyName startupRecoveryBackup -NotePropertyValue $backup -Force
    $installation | ConvertTo-Json -Depth 12 | Set-Content -LiteralPath $installationPath -Encoding UTF8
    if ($present['package-manifest.json']) {
        $package = Get-Content -LiteralPath $packagePath -Raw -Encoding UTF8 | ConvertFrom-Json
        $package.version = $patch.version; $package.rendererVersion = $newManifest.version
        $package | Add-Member -NotePropertyName themeVersion -NotePropertyValue $newManifest.themeVersion -Force
        foreach ($item in $patch.files.PSObject.Properties) { $package.files | Add-Member -NotePropertyName ('payload/' + $item.Name) -NotePropertyValue $item.Value -Force }
        $package.installedBytes = [long]0
        foreach ($item in $package.files.PSObject.Properties) { if ($item.Name.StartsWith('payload/')) { $package.installedBytes += [long]$item.Value.bytes } }
        $package | ConvertTo-Json -Depth 12 | Set-Content -LiteralPath $packagePath -Encoding UTF8
    }
} catch {
    $failure = $_
    foreach ($name in $names) {
        $dest = Join-Path $target $name
        if ($present[$name]) { Copy-Item -LiteralPath (Join-Path $backup $name) -Destination $dest -Force }
        elseif (Test-Path -LiteralPath $dest -PathType Leaf) { Remove-Item -LiteralPath $dest -Force }
    }
    throw $failure
}
Write-Host "Updated: $target" -ForegroundColor Green
Write-Host "Backup: $backup"
Write-Host 'Close Codex normally, then start CodexEVA.exe. No app was closed or restarted by this update.'
[ordered]@{ updated=$true; version=$patch.version; target=$target; backup=$backup } | ConvertTo-Json
