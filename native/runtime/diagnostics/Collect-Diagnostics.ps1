[CmdletBinding()]
param([string]$InstallDirectory, [string]$OutputDirectory)
$ErrorActionPreference = 'Stop'
Set-StrictMode -Version Latest
$env:PSModulePath = Join-Path $PSHOME 'Modules'
$issues = New-Object 'System.Collections.Generic.List[string]'

if (-not $InstallDirectory) {
    foreach ($candidate in @($PSScriptRoot, 'D:\Apps\CodexEVA', 'H:\Apps\CodexEVA')) {
        if (Test-Path -LiteralPath (Join-Path $candidate 'installation.json') -PathType Leaf) { $InstallDirectory = $candidate; break }
    }
}
if (-not $InstallDirectory -or -not (Test-Path -LiteralPath (Join-Path $InstallDirectory 'installation.json') -PathType Leaf)) {
    throw 'Installed EVA folder not found. Put these collector files beside the installed CodexEVA.exe, or pass -InstallDirectory.'
}
$install = [IO.Path]::GetFullPath($InstallDirectory)
if (-not $OutputDirectory) {
    $OutputDirectory = if (Test-Path -LiteralPath 'H:\') { 'H:\Documents\CodexEVA-Diagnostics' } else { Join-Path $install 'diagnostics' }
}
$output = [IO.Path]::GetFullPath($OutputDirectory)
$name = 'EVA-Diagnostics-' + (Get-Date -Format 'yyyyMMdd-HHmmss') + '-' + [Guid]::NewGuid().ToString('N').Substring(0, 6)
$report = Join-Path $output $name
New-Item -ItemType Directory -Path $report -Force | Out-Null

function Save-Text([string]$Name, [string]$Text) {
    if ($env:USERPROFILE) { $Text = $Text.Replace($env:USERPROFILE, '%USERPROFILE%') }
    [IO.File]::WriteAllText((Join-Path $report $Name), $Text, (New-Object Text.UTF8Encoding($false)))
}
function Save-Json([string]$Name, $Value) { Save-Text $Name (ConvertTo-Json -InputObject $Value -Depth 12) }
function Collect([string]$Name, [scriptblock]$Read) {
    try { Save-Json $Name (& $Read) }
    catch { $issues.Add($Name + ': ' + $_.Exception.Message) }
}

Write-Host 'Collecting EVA startup records (no account, conversation or project files)...'
$logNames = @('loader.log', 'launcher-error.log', 'failure.json', 'state.json', 'activation.json',
    'startup-cover-timing.json', 'startup-stage.json', 'installed-validation.json', 'window-placement.json', 'manifest.json', 'host-exit.json')
$records = @()
foreach ($file in $logNames) {
    $path = Join-Path $install $file
    if (-not (Test-Path -LiteralPath $path -PathType Leaf)) { $records += [ordered]@{ name=$file; present=$false }; continue }
    try {
        $info = Get-Item -LiteralPath $path
        if ($file.EndsWith('.log')) { $content = (Get-Content -LiteralPath $path -Encoding UTF8 -Tail 2000) -join "`n" }
        elseif ($info.Length -le 8MB) { $content = Get-Content -LiteralPath $path -Raw -Encoding UTF8 }
        else { throw 'Record larger than 8 MiB; omitted.' }
        Save-Text $file $content
        $records += [ordered]@{ name=$file; present=$true; sourceBytes=$info.Length; modified=$info.LastWriteTime.ToString('o') }
    } catch { $issues.Add($file + ': ' + $_.Exception.Message) }
}
Collect 'installation-summary.json' {
    Get-Content -LiteralPath (Join-Path $install 'installation.json') -Raw -Encoding UTF8 | ConvertFrom-Json |
        Select-Object version, rendererVersion, installedAt, packageFamily, packageVersion, aumid, pythonw, selfContainedRuntime
}
Collect 'system.json' {
    $os = Get-CimInstance Win32_OperatingSystem
    $computer = Get-CimInstance Win32_ComputerSystem
    [ordered]@{
        collectedAt=(Get-Date).ToString('o'); timeZone=[TimeZoneInfo]::Local.Id
        os=@{caption=$os.Caption; version=$os.Version; build=$os.BuildNumber; architecture=$os.OSArchitecture; freeMemoryKiB=$os.FreePhysicalMemory}
        memoryBytes=$computer.TotalPhysicalMemory
        cpu=@(Get-CimInstance Win32_Processor | Select-Object Name, NumberOfCores, NumberOfLogicalProcessors)
        gpu=@(Get-CimInstance Win32_VideoController | Select-Object Name, DriverVersion, AdapterRAM, CurrentHorizontalResolution, CurrentVerticalResolution)
        disks=@(Get-CimInstance Win32_LogicalDisk -Filter 'DriveType=3' | Select-Object DeviceID, Size, FreeSpace)
    }
}
Collect 'codex-package.json' {
    @(Get-AppxPackage -Name 'OpenAI.Codex' | Select-Object Name, Version, Architecture, Status, PackageFullName, InstallLocation)
}
Collect 'processes.json' {
    @(Get-CimInstance Win32_Process -Filter "Name='ChatGPT.exe' OR Name='CodexEVA.exe' OR Name='pythonw.exe'" |
        Where-Object { $_.Name -ne 'pythonw.exe' -or ($_.ExecutablePath -and $_.ExecutablePath.StartsWith($install, [StringComparison]::OrdinalIgnoreCase)) } |
        Select-Object Name, ProcessId, ParentProcessId, CreationDate, ExecutablePath, WorkingSetSize)
}

Write-Host 'Checking installed startup files...'
Collect 'file-integrity.json' {
    $manifest = Get-Content -LiteralPath (Join-Path $install 'manifest.json') -Raw -Encoding UTF8 | ConvertFrom-Json
    $core = @('CodexEVA.exe', 'loader.py', 'startup.bundle.js', 'theme.bundle.js', 'startup-native.frames', 'startup-native.wav', 'startup-native-video.mp4', 'startup-first-frame.jpg')
    foreach ($file in $core) {
        $path = Join-Path $install $file
        if (-not (Test-Path -LiteralPath $path -PathType Leaf)) { [ordered]@{name=$file; present=$false}; continue }
        $actual = (Get-FileHash -LiteralPath $path -Algorithm SHA256).Hash.ToLowerInvariant()
        $expected = if ($file -eq 'CodexEVA.exe') { $manifest.launcher.sha256 } elseif ($manifest.files.PSObject.Properties.Name -contains $file) { $manifest.files.$file.sha256 } else { $null }
        [ordered]@{name=$file; present=$true; bytes=(Get-Item -LiteralPath $path).Length; sha256=$actual; expectedSha256=$expected; matchesManifest=if($expected){$actual -eq $expected}else{$null}}
    }
}

Write-Host 'Reading matching Windows crash records from the last 24 hours...'
$eventPattern = '(?i)(ChatGPT\.exe|CodexEVA\.exe|OpenAI\.Codex|' + [regex]::Escape($install) + ')'
foreach ($channel in @('Application', 'Microsoft-Windows-AppModel-Runtime/Admin')) {
    try {
        $query = '*[System[TimeCreated[timediff(@SystemTime) <= 86400000]]]'
        if ($channel -eq 'Application') { $query = '*[System[(EventID=1000 or EventID=1001 or EventID=1002 or EventID=1026) and TimeCreated[timediff(@SystemTime) <= 86400000]]]' }
        $events = @(Get-WinEvent -LogName $channel -FilterXPath $query -MaxEvents 1000 -ErrorAction Stop |
            Where-Object { $_.Message -match $eventPattern } |
            Select-Object -First 100 @{n='time';e={$_.TimeCreated.ToString('o')}}, Id, ProviderName, LevelDisplayName, Message)
        Save-Json ($channel.Replace('/', '-') + '-events.json') $events
    } catch {
        if ($_.FullyQualifiedErrorId -like 'NoMatchingEventsFound*') { Save-Json ($channel.Replace('/', '-') + '-events.json') @() }
        else { $issues.Add($channel + ': ' + $_.Exception.Message) }
    }
}
Save-Json 'collection.json' ([ordered]@{schema=1; collectedAt=(Get-Date).ToString('o'); installDirectory=$install; records=$records; issues=@($issues.ToArray()); appRestarted=$false; accountOrConversationFilesCollected=$false; networkUpload=$false})
$archive = Join-Path $output ($name + '.zip')
Compress-Archive -LiteralPath $report -DestinationPath $archive -CompressionLevel Optimal
Write-Host ''
Write-Host ('Diagnostic ZIP: ' + $archive) -ForegroundColor Green
Write-Host 'Attach this ZIP to the current support chat. Nothing was uploaded automatically.'
if ($issues.Count) { Write-Host ('Some records were unavailable; details are in collection.json. Count: ' + $issues.Count) }
