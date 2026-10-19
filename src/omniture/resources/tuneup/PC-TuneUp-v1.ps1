<#
.SYNOPSIS
    PC-TuneUp v1 - full health check, update, repair, cleanup and report.
.DESCRIPTION
    1. Creates a System Restore point BEFORE touching anything (safety net).
    2. Inventories hardware (CPU / RAM / disks / GPU / battery / BIOS) and installed software.
    3. Updates all apps via winget, plus Windows + drivers via Windows Update.
    4. Repairs system files (DISM + SFC).
    5. Safe cleanup (temp files, Windows Update download cache, component store).
    6. Writes an HTML report to your Desktop - share it with Vanya for the
       full analysis (condition, speed fixes, what the machine is good for)
       and the Sale page.

    HOW TO RUN: right-click PowerShell > "Run as administrator", then paste the
    one command. Takes 30-60+ minutes - start it and walk away.
    Windows PowerShell 5.1 compatible.

    NOTE ON THE REGISTRY: there is no safe "update the registry" step for
    tune-ups. Installers maintain their own registry keys when they update;
    "registry cleaners" are snake oil and break PCs. The only registry write
    here is the one Microsoft documents for restore points (lets us create a
    fresh point right now instead of waiting 24h). Everything else is read-only.
#>

$ErrorActionPreference = 'Continue'
$LogLines = New-Object System.Collections.Generic.List[string]

function Write-Phase([string]$text) {
    Write-Host ''
    Write-Host '============================================================' -ForegroundColor Cyan
    Write-Host $text -ForegroundColor Cyan
    Write-Host '============================================================' -ForegroundColor Cyan
}

function Write-Log([string]$text) {
    $line = '[{0}] {1}' -f (Get-Date -Format 'HH:mm:ss'), $text
    $LogLines.Add($line)
    Write-Host $line
}

# ---------------------------------------------------------------------------
# 0. Must be elevated
# ---------------------------------------------------------------------------
$principal = New-Object Security.Principal.WindowsPrincipal([Security.Principal.WindowsIdentity]::GetCurrent())
if (-not $principal.IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)) {
    Write-Host 'STOP: right-click PowerShell, choose "Run as administrator", then run this again.' -ForegroundColor Red
    Read-Host 'Press Enter to close'
    exit 1
}

$stamp = Get-Date -Format 'yyyyMMdd-HHmm'
$Report = @{}

Write-Phase 'PC-TuneUp v1 starting'

# ---------------------------------------------------------------------------
# 1. Restore point FIRST - before anything is modified
# ---------------------------------------------------------------------------
Write-Phase 'PHASE 1/7 - Safety net: restore point'
$Report['RestorePoint'] = 'unknown'
try {
    Enable-ComputerRestore -Drive 'C:\' -ErrorAction Stop
    Write-Log 'System Protection is enabled on C:.'
} catch {
    Write-Log ('Note enabling System Protection: ' + $_.Exception.Message)
}
try {
    $srPath = 'HKLM:\SOFTWARE\Microsoft\Windows NT\CurrentVersion\SystemRestore'
    New-ItemProperty -Path $srPath -Name 'SystemRestorePointCreationFrequency' -Value 0 -PropertyType DWord -Force | Out-Null
    Write-Log 'Registry: restore-point frequency set to 0 so a fresh point can be created now.'
} catch {
    Write-Log ('Registry note: ' + $_.Exception.Message)
}
try {
    Checkpoint-Computer -Description 'PC-TuneUp v1 (before updates)' -RestorePointType 'MODIFY_SETTINGS' -ErrorAction Stop
    Write-Log 'Restore point created OK.'
    $Report['RestorePoint'] = 'Created OK - "PC-TuneUp v1 (before updates)"'
} catch {
    Write-Log ('RESTORE POINT FAILED: ' + $_.Exception.Message)
    $Report['RestorePoint'] = 'FAILED: ' + $_.Exception.Message
}

# ---------------------------------------------------------------------------
# 2. Hardware + software inventory
# ---------------------------------------------------------------------------
Write-Phase 'PHASE 2/7 - Hardware and software inventory'
$cs   = Get-CimInstance Win32_ComputerSystem
$cpu  = Get-CimInstance Win32_Processor | Select-Object -First 1
$os   = Get-CimInstance Win32_OperatingSystem
$bios = Get-CimInstance Win32_BIOS
$gpus = Get-CimInstance Win32_VideoController
$batt = Get-CimInstance Win32_Battery

$Report['Manufacturer'] = $cs.Manufacturer
$Report['Model']        = $cs.Model
$Report['CPU']          = $cpu.Name.Trim()
$Report['Cores']        = [string]$cpu.NumberOfCores + ' cores / ' + [string]$cpu.NumberOfLogicalProcessors + ' threads'
$Report['RAM_GB']       = [math]::Round($cs.TotalPhysicalMemory / 1GB, 1)
$Report['OS']           = $os.Caption
$Report['OSBuild']      = $os.BuildNumber
$Report['BIOS']         = $bios.SMBIOSBIOSVersion
$Report['GPU']          = ($gpus | ForEach-Object { $_.Name.Trim() }) -join ' + '
$Report['IsLaptop']     = ($batt -ne $null)
Write-Log ('Machine: ' + $Report['Manufacturer'] + ' ' + $Report['Model'])
Write-Log ('CPU: ' + $Report['CPU'])
Write-Log ('RAM: ' + $Report['RAM_GB'] + ' GB')
Write-Log ('GPU: ' + $Report['GPU'])
Write-Log ('OS: ' + $Report['OS'] + ' (build ' + $Report['OSBuild'] + ')')

$diskRows = ''
$worstHealth = 'Healthy'
foreach ($d in (Get-PhysicalDisk | Sort-Object DeviceId)) {
    $sizeGB = [math]::Round($d.Size / 1GB, 0)
    $health = [string]$d.HealthStatus
    if ($health -ne 'Healthy') { $worstHealth = $health }
    $diskRows += '<tr><td>' + $d.FriendlyName + '</td><td>' + $d.MediaType + '</td><td>' + $sizeGB + ' GB</td><td>' + $health + '</td></tr>'
    Write-Log ('Disk: ' + $d.FriendlyName + ' / ' + $d.MediaType + ' / ' + $sizeGB + ' GB / health=' + $health)
}
$Report['DiskHealth'] = $worstHealth
$Report['DiskRows'] = $diskRows

$uninstallPaths = @(
    'HKLM:\SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall\*',
    'HKLM:\SOFTWARE\WOW6432Node\Microsoft\Windows\CurrentVersion\Uninstall\*',
    'HKCU:\SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall\*'
)
$apps = foreach ($p in $uninstallPaths) {
    Get-ItemProperty $p -ErrorAction SilentlyContinue |
        Where-Object { $_.DisplayName } |
        Select-Object DisplayName, DisplayVersion, Publisher
}
$apps = $apps | Sort-Object DisplayName -Unique
$Report['AppCount'] = ($apps | Measure-Object).Count
Write-Log ('Installed programs found: ' + $Report['AppCount'])
$appRows = ''
foreach ($a in ($apps | Select-Object -First 60)) {
    $appRows += '<tr><td>' + $a.DisplayName + '</td><td>' + $a.DisplayVersion + '</td><td>' + $a.Publisher + '</td></tr>'
}
$Report['AppRows'] = $appRows

# Firmware helper: pick the right maker tool for BIOS/firmware updates
$maker = [string]$cs.Manufacturer
$fwTool = 'your PC maker''s support app'
if ($maker -match 'Lenovo')      { $fwTool = 'Lenovo Vantage (Microsoft Store) or Lenovo System Update' }
elseif ($maker -match 'Dell')    { $fwTool = 'Dell Command Update' }
elseif ($maker -match 'HP|Hewlett') { $fwTool = 'HP Support Assistant' }
elseif ($maker -match 'ASUS')     { $fwTool = 'MyASUS (Microsoft Store)' }
elseif ($maker -match 'Acer')     { $fwTool = 'Acer Care Center' }
$Report['FwTool'] = $fwTool

# ---------------------------------------------------------------------------
# 3. Safe cleanup FIRST (frees space, gives updates a fresh download cache)
# ---------------------------------------------------------------------------
Write-Phase 'PHASE 3/7 - Safe cleanup'
$freeBefore = (Get-PSDrive C).Free
Write-Log ('Free space on C: before: ' + [math]::Round($freeBefore / 1GB, 2) + ' GB')
Write-Log 'Clearing temp folders...'
Remove-Item "$env:TEMP\*" -Recurse -Force -ErrorAction SilentlyContinue
Remove-Item 'C:\Windows\Temp\*' -Recurse -Force -ErrorAction SilentlyContinue
Write-Log 'Clearing Windows Update download cache...'
Stop-Service wuauserv -Force -ErrorAction SilentlyContinue
Stop-Service bits -Force -ErrorAction SilentlyContinue
Remove-Item 'C:\Windows\SoftwareDistribution\Download\*' -Recurse -Force -ErrorAction SilentlyContinue
Start-Service wuauserv -ErrorAction SilentlyContinue
Start-Service bits -ErrorAction SilentlyContinue
Write-Log 'Cleaning component store (WinSxS) - this takes a while...'
DISM /Online /Cleanup-Image /StartComponentCleanup > "$env:TEMP\pctuneup-component.log" 2>&1
Write-Log ('Component cleanup exit code: ' + $LASTEXITCODE)
$freeAfterCleanup = (Get-PSDrive C).Free
Write-Log ('Free space on C: after cleanup: ' + [math]::Round($freeAfterCleanup / 1GB, 2) + ' GB')

# ---------------------------------------------------------------------------
# 4. Update all apps via winget
# ---------------------------------------------------------------------------
Write-Phase 'PHASE 4/7 - Updating installed apps (winget)'
if (Get-Command winget -ErrorAction SilentlyContinue) {
    Write-Log 'Refreshing winget sources...'
    winget source update
    Write-Log 'Upgrading all winget-managed apps (this takes a while)...'
    winget upgrade --all --accept-package-agreements --accept-source-agreements --silent
    $Report['Winget'] = 'Ran: winget upgrade --all'
} else {
    Write-Log 'winget NOT FOUND. Install "App Installer" from the Microsoft Store, then re-run.'
    $Report['Winget'] = 'NOT FOUND - install App Installer from the Microsoft Store'
}

# ---------------------------------------------------------------------------
# 5. Windows Update (OS + drivers)
# ---------------------------------------------------------------------------
Write-Phase 'PHASE 5/7 - Windows Update (OS and drivers)'
Write-Log 'Scanning for Windows updates...'
UsoClient StartScan
Start-Sleep -Seconds 45
Write-Log 'Downloading updates...'
UsoClient StartDownload
Start-Sleep -Seconds 90
Write-Log 'Installing updates (continues in the background)...'
UsoClient StartInstall
$Report['WinUpdate'] = 'Scan/download/install kicked off via UsoClient; finishes in background'

# ---------------------------------------------------------------------------
# 6. System file repair (DISM + SFC) - the real "fix" step
# ---------------------------------------------------------------------------
Write-Phase 'PHASE 6/7 - System file repair (slow - grab a coffee)'
Write-Log 'DISM: repairing the Windows component store...'
DISM /Online /Cleanup-Image /RestoreHealth > "$env:TEMP\pctuneup-dism.log" 2>&1
Write-Log ('DISM exit code: ' + $LASTEXITCODE + ' (0 = OK)')
$Report['DISM'] = 'Exit code ' + $LASTEXITCODE
Write-Log 'SFC: scanning protected system files...'
sfc /scannow > "$env:TEMP\pctuneup-sfc.log" 2>&1
Write-Log ('SFC exit code: ' + $LASTEXITCODE + ' (0 = OK)')
$Report['SFC'] = 'Exit code ' + $LASTEXITCODE
$freeAfter = (Get-PSDrive C).Free
$Report['SpaceReclaimedGB'] = [math]::Round(($freeAfter - $freeBefore) / 1GB, 2)
Write-Log ('Total space reclaimed on C:: ' + $Report['SpaceReclaimedGB'] + ' GB')

# ---------------------------------------------------------------------------
# 7. Battery report, startup inventory, reboot check, HTML report
# ---------------------------------------------------------------------------
Write-Phase 'PHASE 7/7 - Report'
$battPath = "$env:USERPROFILE\Desktop\battery-report.html"
if ($Report['IsLaptop']) {
    powercfg /batteryreport /output "$battPath" > $null 2>&1
    Write-Log 'Battery health report saved to Desktop\battery-report.html'
    $Report['BatteryReport'] = 'Saved to Desktop\battery-report.html'
} else {
    $Report['BatteryReport'] = 'N/A (desktop, no battery)'
}

$startupRows = ''
$startupCount = 0
foreach ($s in (Get-CimInstance Win32_StartupCommand | Sort-Object Name)) {
    $startupCount++
    $startupRows += '<tr><td>' + $s.Name + '</td><td>' + $s.Location + '</td></tr>'
}
$Report['StartupCount'] = $startupCount
$Report['StartupRows'] = $startupRows
Write-Log ('Startup programs found: ' + $startupCount)

$sysInfo = New-Object -ComObject Microsoft.Update.SystemInfo
$Report['RebootNeeded'] = $sysInfo.RebootRequired

$logHtml = ($LogLines | Select-Object -Last 80) -join "`r`n"

$html = @"
<!DOCTYPE html>
<html><head><meta charset="utf-8">
<title>PC Health Report - $stamp</title>
<style>
body{font-family:Segoe UI,Arial,sans-serif;max-width:900px;margin:20px auto;padding:0 16px;color:#222}
h1{border-bottom:3px solid #0078d4;padding-bottom:8px}
h2{color:#0078d4;margin-top:28px}
table{border-collapse:collapse;width:100%;margin:8px 0}
th,td{border:1px solid #ccc;padding:6px 10px;text-align:left;font-size:14px}
th{background:#f0f6ff}
.warn{background:#fff4e5;border:1px solid #e8a838;padding:10px 14px;border-radius:6px}
pre{background:#f6f6f6;padding:12px;border-radius:6px;font-size:12px;white-space:pre-wrap}
</style></head><body>
<h1>PC Health Report</h1>
<p>Generated $stamp by PC-TuneUp v1. Share this file with Vanya for the full analysis and the Sale page.</p>

<h2>Machine</h2>
<table>
<tr><th>Manufacturer</th><td>$($Report['Manufacturer'])</td></tr>
<tr><th>Model</th><td>$($Report['Model'])</td></tr>
<tr><th>CPU</th><td>$($Report['CPU']) ($($Report['Cores']))</td></tr>
<tr><th>RAM</th><td>$($Report['RAM_GB']) GB</td></tr>
<tr><th>GPU</th><td>$($Report['GPU'])</td></tr>
<tr><th>OS</th><td>$($Report['OS']) - build $($Report['OSBuild'])</td></tr>
<tr><th>BIOS</th><td>$($Report['BIOS'])</td></tr>
<tr><th>Form factor</th><td>$(if ($Report['IsLaptop']) { 'Laptop' } else { 'Desktop' })</td></tr>
</table>

<h2>Disks (health: $($Report['DiskHealth']))</h2>
<table><tr><th>Disk</th><th>Type</th><th>Size</th><th>Health</th></tr>
$($Report['DiskRows'])
</table>

<h2>What was done</h2>
<table>
<tr><th>Restore point</th><td>$($Report['RestorePoint'])</td></tr>
<tr><th>App updates</th><td>$($Report['Winget'])</td></tr>
<tr><th>Windows Update</th><td>$($Report['WinUpdate'])</td></tr>
<tr><th>DISM repair</th><td>$($Report['DISM'])</td></tr>
<tr><th>SFC scan</th><td>$($Report['SFC'])</td></tr>
<tr><th>Space reclaimed on C:</th><td>$($Report['SpaceReclaimedGB']) GB</td></tr>
<tr><th>Battery report</th><td>$($Report['BatteryReport'])</td></tr>
<tr><th>Restart needed</th><td>$(if ($Report['RebootNeeded']) { 'YES - restart the PC now' } else { 'No' })</td></tr>
</table>

<div class="warn"><b>Not covered by the script:</b> BIOS/firmware updates are vendor-specific.
Use <b>$($Report['FwTool'])</b> for those. Also restart the PC so pending updates finish installing.</div>

<h2>Startup programs ($($Report['StartupCount'])) - review these for speed</h2>
<p>Disable unneeded ones via Task Manager &gt; Startup apps. Don't disable your antivirus.</p>
<table><tr><th>Name</th><th>Location</th></tr>
$($Report['StartupRows'])
</table>

<h2>Installed programs ($($Report['AppCount'])) - first 60</h2>
<table><tr><th>Name</th><th>Version</th><th>Publisher</th></tr>
$($Report['AppRows'])
</table>

<h2>Run log (last 80 lines)</h2>
<pre>$logHtml</pre>
</body></html>
"@

$reportPath = "$env:USERPROFILE\Desktop\PC-Health-Report-$stamp.html"
$html | Out-File -FilePath $reportPath -Encoding utf8
Write-Log ('HTML report saved: ' + $reportPath)

Write-Phase 'DONE'
Write-Host ''
Write-Host 'Summary:' -ForegroundColor Green
Write-Host ('  Machine : ' + $Report['Manufacturer'] + ' ' + $Report['Model'])
Write-Host ('  CPU     : ' + $Report['CPU'])
Write-Host ('  RAM     : ' + $Report['RAM_GB'] + ' GB')
Write-Host ('  GPU     : ' + $Report['GPU'])
Write-Host ('  Disks   : health=' + $Report['DiskHealth'])
Write-Host ('  Apps    : ' + $Report['AppCount'] + ' installed programs found')
Write-Host ('  Reclaimed: ' + $Report['SpaceReclaimedGB'] + ' GB on C:')
Write-Host ('  Restore : ' + $Report['RestorePoint'])
if ($Report['RebootNeeded']) {
    Write-Host '  RESTART YOUR PC NOW - updates are waiting on a reboot.' -ForegroundColor Yellow
}
Write-Host ''
Write-Host 'Next: restart, then send Vanya the file on your Desktop:' -ForegroundColor Green
Write-Host ('  ' + $reportPath) -ForegroundColor Green
Write-Host 'He will do the full analysis (condition, speed fixes, what it is good for) and build the Sale page.'
Read-Host 'Press Enter to close'
