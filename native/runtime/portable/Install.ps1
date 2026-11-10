[CmdletBinding()]
param(
    [string]$TargetDirectory,
    [switch]$CheckOnly,
    [switch]$NoShortcut
)
$ErrorActionPreference = 'Stop'
Set-StrictMode -Version Latest
# Scope module discovery to this Windows PowerShell process, not an inherited SDK.
$env:PSModulePath = Join-Path $PSHOME 'Modules'
Import-Module (Join-Path $PSHOME 'Modules\Microsoft.PowerShell.Utility\Microsoft.PowerShell.Utility.psd1') -Force

function Get-SafePath([string]$Root, [string]$Relative) {
    $base = [IO.Path]::GetFullPath($Root).TrimEnd('\') + '\'
    $path = [IO.Path]::GetFullPath((Join-Path $base $Relative))
    if (-not $path.StartsWith($base, [StringComparison]::OrdinalIgnoreCase)) { throw "Unsafe package path: $Relative" }
    return $path
}

function Test-Package {
    $manifest = Get-Content -LiteralPath (Join-Path $PSScriptRoot 'package-manifest.json') -Raw -Encoding UTF8 | ConvertFrom-Json
    foreach ($item in $manifest.files.PSObject.Properties) {
        $path = Get-SafePath $PSScriptRoot $item.Name
        if (-not (Test-Path -LiteralPath $path -PathType Leaf)) { throw "Package file missing: $($item.Name)" }
        $file = Get-Item -LiteralPath $path
        if (($file.Attributes -band [IO.FileAttributes]::ReparsePoint) -ne 0) { throw 'Package links are not supported.' }
        if ($file.Length -ne $item.Value.bytes -or (Get-FileHash -LiteralPath $path -Algorithm SHA256).Hash -ne $item.Value.sha256) {
            throw "Package checksum mismatch: $($item.Name). Extract the ZIP again."
        }
    }
    return $manifest
}

function Test-Runtime([string]$Root) {
    $python = Join-Path $Root 'runtime\python\python.exe'
    $output = & $python -B (Join-Path $Root 'runtime_check.py') 2>&1
    if ($LASTEXITCODE -ne 0) { throw "Bundled runtime check failed: $output" }
    $result = ($output -join "`n") | ConvertFrom-Json
    if (-not $result.passed) { throw 'Bundled runtime check failed.' }
    return $result
}

function Get-Codex {
    $package = Get-AppxPackage -Name 'OpenAI.Codex' | Sort-Object Version -Descending | Select-Object -First 1
    if (-not $package) { throw 'Install the official Codex Windows desktop app for this user first, then run Install.cmd again.' }
    $xml = Get-AppxPackageManifest -Package $package.PackageFullName
    $app = @($xml.Package.Applications.Application) | Where-Object { $_.Executable -match '(?i)ChatGPT\.exe$' } | Select-Object -First 1
    if (-not $app) { throw 'Unsupported Codex package: native desktop executable not found.' }
    $exe = Get-SafePath $package.InstallLocation ([string]$app.Executable)
    if (-not (Test-Path -LiteralPath $exe)) { throw 'The native Codex installation is incomplete.' }
    return @{ package = $package; aumid = "$($package.PackageFamilyName)!$($app.Id)"; executable = $exe }
}

if (-not [Environment]::Is64BitOperatingSystem -or $env:PROCESSOR_ARCHITECTURE -eq 'ARM64' -or $env:PROCESSOR_ARCHITEW6432 -eq 'ARM64') {
    throw 'This package supports x64 Windows only. ARM64 needs a separate build.'
}
if ([Environment]::OSVersion.Version.Build -lt 19041) { throw 'Windows 10 build 19041 or newer is required.' }
Add-Type -AssemblyName System.Windows.Forms
Add-Type -AssemblyName System.Web.Extensions

Write-Host 'Checking package integrity and bundled runtime...'
$manifest = Test-Package
$runtime = Test-Runtime (Join-Path $PSScriptRoot 'payload')
$codex = Get-Codex
# Portable installs need space for the payload and headroom, not this build PC's reserve policy.
$requiredFreeBytes = 3 * [long]$manifest.installedBytes
if (-not $TargetDirectory) {
    foreach ($driveName in @('D', 'H')) {
        $drive = Get-PSDrive -Name $driveName -PSProvider FileSystem -ErrorAction SilentlyContinue
        if ($drive -and $drive.Free -ge $requiredFreeBytes) {
            $TargetDirectory = Join-Path $drive.Root 'Apps\CodexEVA'
            break
        }
    }
    if (-not $TargetDirectory) { throw ('No default D: or H: drive has the required {0:N2} GiB free. Run Install.ps1 -TargetDirectory X:\Apps\CodexEVA with an explicit local target.' -f ($requiredFreeBytes / 1GB)) }
}
$target = [IO.Path]::GetFullPath($TargetDirectory).TrimEnd('\')
if ($target -notmatch '^[A-Za-z]:\\[^\\]') { throw 'Choose a local installation folder below a drive root.' }
$sourceRoot = [IO.Path]::GetFullPath($PSScriptRoot).TrimEnd('\')
if ($target.Equals($sourceRoot, [StringComparison]::OrdinalIgnoreCase) -or $target.StartsWith($sourceRoot + '\', [StringComparison]::OrdinalIgnoreCase) -or $sourceRoot.StartsWith($target + '\', [StringComparison]::OrdinalIgnoreCase)) {
    throw 'The installation folder must be separate from the extracted package folder.'
}
$driveInfo = New-Object IO.DriveInfo ([IO.Path]::GetPathRoot($target))
if ($driveInfo.AvailableFreeSpace -lt $requiredFreeBytes) { throw ('Insufficient space on {0}: {1:N2} GiB available; {2:N2} GiB required.' -f $driveInfo.Name, ($driveInfo.AvailableFreeSpace / 1GB), ($requiredFreeBytes / 1GB)) }
if ($CheckOnly) {
    [ordered]@{ passed = $true; checkOnly = $true; version = $manifest.version; codexVersion = $codex.package.Version.ToString(); aumid = $codex.aumid; target = $target; requiredFreeBytes = $requiredFreeBytes; availableFreeBytes = $driveInfo.AvailableFreeSpace; runtime = $runtime } | ConvertTo-Json -Depth 6
    exit 0
}
# Existing installations remain untouched: use an empty folder for a separate install.
if ((Test-Path -LiteralPath $target) -and ((Get-Item -LiteralPath $target -Force).Attributes -band [IO.FileAttributes]::ReparsePoint) -ne 0) {
    throw 'The installation folder cannot be a junction or symbolic link.'
}
if ((Test-Path -LiteralPath $target) -and @(Get-ChildItem -LiteralPath $target -Force).Count -ne 0) {
    throw "The target folder is not empty: $target. Close Codex and move the old EVA folder to a backup location, or specify another empty target folder."
}
$parent = Split-Path -Parent $target
New-Item -ItemType Directory -Path $parent -Force | Out-Null
# Resolve existing parent junctions before any file mutation.
$cursor = Get-Item -LiteralPath $parent
while ($cursor) {
    if (($cursor.Attributes -band [IO.FileAttributes]::ReparsePoint) -ne 0) { throw 'Installation through a junction or symbolic link is not supported.' }
    $cursor = $cursor.Parent
}
New-Item -ItemType Directory -Path $target -Force | Out-Null
$payload = Join-Path $PSScriptRoot 'payload'
foreach ($item in $manifest.files.PSObject.Properties | Where-Object { $_.Name.StartsWith('payload/') }) {
    $relative = $item.Name.Substring('payload/'.Length)
    $dest = Get-SafePath $target $relative
    New-Item -ItemType Directory -Path (Split-Path -Parent $dest) -Force | Out-Null
    Copy-Item -LiteralPath (Get-SafePath $payload $relative) -Destination $dest
    if ((Get-FileHash -LiteralPath $dest -Algorithm SHA256).Hash -ne $item.Value.sha256) { throw "Installed file verification failed: $relative" }
}
$installedRuntime = Test-Runtime $target
$stamp = (Get-Date).ToString('o')
$installation = [ordered]@{
    installedAt = $stamp; version = $manifest.version; rendererVersion = $manifest.rendererVersion
    pythonw = 'runtime\python\pythonw.exe'; packageFamily = $codex.package.PackageFamilyName
    packageVersion = $codex.package.Version.ToString(); aumid = $codex.aumid
    selfContainedRuntime = $true; originalPackageModified = $false; windowsAutostartAdded = $false
    sourceProjectRequired = $false; configurationScope = 'local EVA loader only'
}
$installation | ConvertTo-Json -Depth 5 | Set-Content -LiteralPath (Join-Path $target 'installation.json') -Encoding UTF8
$manifest | ConvertTo-Json -Depth 8 | Set-Content -LiteralPath (Join-Path $target 'package-manifest.json') -Encoding UTF8
if (-not $NoShortcut) {
    $shell = New-Object -ComObject WScript.Shell
    $linkPath = Join-Path ([Environment]::GetFolderPath('Programs')) 'Codex EVA.lnk'
    if (Test-Path -LiteralPath $linkPath) {
        $existingLink = $shell.CreateShortcut($linkPath)
        if (-not $existingLink.TargetPath.Equals((Join-Path $target 'CodexEVA.exe'), [StringComparison]::OrdinalIgnoreCase)) {
            Copy-Item -LiteralPath $linkPath -Destination (Join-Path $target 'previous-shortcut.lnk')
        }
    }
    $link = $shell.CreateShortcut($linkPath)
    $link.TargetPath = Join-Path $target 'CodexEVA.exe'
    $link.WorkingDirectory = $target
    $link.Description = 'Codex EVA - R7 theme and S4 startup'
    $link.IconLocation = $codex.executable + ',0'
    $link.Save()
}
Write-Host ''
Write-Host "Installed: $target" -ForegroundColor Green
Write-Host 'Close Codex normally, then open Codex EVA from the Start menu or run CodexEVA.exe.'
Write-Host 'EVA cold launch automatically sets official Codex appearance to Dark for white native window icons.'
Write-Host 'No app was launched or closed by this installer.'
[ordered]@{ installed = $true; target = $target; version = $manifest.version; runtime = $installedRuntime; shortcutCreated = (-not $NoShortcut) } | ConvertTo-Json -Depth 6
