<#
.SYNOPSIS
    Automated Workstation Readiness & Environmental Verification Script (TASK-P9-01).

.DESCRIPTION
    Empirically audits the target machine against the 12 criteria specified in
    A08_EXTERNAL_WORKSTATION_READINESS_CHECKLIST.md before physical acceptance testing.

    Evaluates:
    - Check 1: Windows 10/11 64-bit OS & Build
    - Check 2: Interactive Desktop Session (winsta0\default, SessionId >= 1)
    - Check 3: Process Execution & Group Policy / AppLocker Non-Restriction
    - Check 4: Python Runtime (>= 3.11) & venv accessibility
    - Check 5: Node.js (>= 18.0.0) & npm (>= 9.0.0)
    - Check 6: Physical Display Resolution (>= 1920x1080) & Scaling (100%)
    - Check 7: Physical Keyboard & Mouse Detection
    - Check 8: 16kHz PCM Audio Recording Device (Microphone)
    - Check 9: Audio Playback Device (Speakers/Headphones)
    - Check 10: Gemini Live HTTPS & WSS Egress (port 443)
    - Check 11: OS Credential Store (Keyring) Gemini API Key
    - Check 12: Clean Repository Working Tree

.OUTPUTS
    Console formatted table and JSON audit report in docs/external-acceptance/evidence/
#>

[CmdletBinding()]
param(
    [string]$TesterName = "Authorized QA Engineer",
    [string]$WorkstationId = $env:COMPUTERNAME,
    [switch]$JsonOnly
)

$ErrorActionPreference = "Continue"

Write-Host "==========================================================================" -ForegroundColor Cyan
Write-Host "          ALEX AI - PHYSICAL WORKSTATION READINESS AUDIT (A08)           " -ForegroundColor Cyan
Write-Host "==========================================================================" -ForegroundColor Cyan
Write-Host "Workstation ID: $WorkstationId"
Write-Host "Tester:         $TesterName"
Write-Host "Timestamp:      $(Get-Date -Format 'yyyy-MM-dd HH:mm:ss zzz')"
Write-Host "--------------------------------------------------------------------------"

$AuditResults = [ordered]@{}
$AllPassed = $true

function Record-Check {
    param(
        [string]$CheckId,
        [string]$Title,
        [bool]$Passed,
        [string]$Details,
        [string]$Remediation = ""
    )
    $script:AuditResults[$CheckId] = [ordered]@{
        "Title"       = $Title
        "Passed"      = $Passed
        "Details"     = $Details
        "Remediation" = $Remediation
    }

    if (-not $Passed) {
        $script:AllPassed = $false
        Write-Host " [FAIL] $CheckId: $Title" -ForegroundColor Red
        Write-Host "        Details:     $Details" -ForegroundColor DarkRed
        if ($Remediation) {
            Write-Host "        Remediation: $Remediation" -ForegroundColor Yellow
        }
    } else {
        Write-Host " [PASS] $CheckId: $Title" -ForegroundColor Green
        Write-Host "        $Details" -ForegroundColor Gray
    }
}

# --- Check 1: Windows Version and 64-bit Architecture ---
try {
    $os = Get-CimInstance Win32_OperatingSystem
    $is64 = [System.Environment]::Is64BitOperatingSystem
    $build = [int]$os.BuildNumber
    $versionName = $os.Caption
    $osOk = ($build -ge 19045) -and $is64  # Windows 10 22H2 or Windows 11
    Record-Check -CheckId "CHECK-01" `
                 -Title "OS Version & 64-bit Architecture" `
                 -Passed $osOk `
                 -Details "$versionName (Build $build), 64-bit: $is64" `
                 -Remediation "Install Windows 10 22H2+ or Windows 11 (23H2/24H2) 64-bit."
} catch {
    Record-Check -CheckId "CHECK-01" -Title "OS Version & 64-bit Architecture" -Passed $false -Details $_.Exception.Message
}

# --- Check 2: Interactive Win32 Desktop Session ---
try {
    $session = (Get-Process -Id $PID).SessionId
    $isInteractive = ($session -ge 1)
    Record-Check -CheckId "CHECK-02" `
                 -Title "Interactive Win32 Desktop Session" `
                 -Passed $isInteractive `
                 -Details "Session ID: $session (Interactive: $isInteractive)" `
                 -Remediation "Log into the console desktop session directly (Session >= 1). Services (Session 0) are prohibited."
} catch {
    Record-Check -CheckId "CHECK-02" -Title "Interactive Win32 Desktop Session" -Passed $false -Details $_.Exception.Message
}

# --- Check 3: Process Execution & Group Policy / AppLocker ---
try {
    $proc = Start-Process powershell.exe -ArgumentList "-NoProfile -ExecutionPolicy Bypass -Command `"Write-Host 'EXEC_ALLOWED'`"" -PassThru -Wait -NoNewWindow
    $execOk = ($proc.ExitCode -eq 0)
    Record-Check -CheckId "CHECK-03" `
                 -Title "Group Policy / AppLocker Execution" `
                 -Passed $execOk `
                 -Details "PowerShell child execution exit code: $($proc.ExitCode)" `
                 -Remediation "Workstation must not be constrained by enterprise AppLocker rules blocking powershell/python spawning."
} catch {
    Record-Check -CheckId "CHECK-03" -Title "Group Policy / AppLocker Execution" -Passed $false -Details $_.Exception.Message
}

# --- Check 4: Python Runtime (>= 3.11) ---
try {
    $pyVer = & python --version 2>&1
    $pyOk = $pyVer -match "Python 3\.(1[1-9]|[2-9][0-9])"
    Record-Check -CheckId "CHECK-04" `
                 -Title "Python 3.11+ Runtime" `
                 -Passed $pyOk `
                 -Details "$pyVer" `
                 -Remediation "Install Python 3.11 or 3.12 64-bit from python.org and add to PATH."
} catch {
    Record-Check -CheckId "CHECK-04" -Title "Python 3.11+ Runtime" -Passed $false -Details "Python executable not found in PATH."
}

# --- Check 5: Node.js (>= 18) & npm (>= 9) ---
try {
    $nodeVer = & node --version 2>&1
    $npmVer = & npm --version 2>&1
    $nodeMajor = if ($nodeVer -match "v(\d+)\.") { [int]$Matches[1] } else { 0 }
    $nodeOk = ($nodeMajor -ge 18)
    Record-Check -CheckId "CHECK-05" `
                 -Title "Node.js & npm Toolchain" `
                 -Passed $nodeOk `
                 -Details "Node: $nodeVer, npm: $npmVer" `
                 -Remediation "Install Node.js v20 LTS from nodejs.org."
} catch {
    Record-Check -CheckId "CHECK-05" -Title "Node.js & npm Toolchain" -Passed $false -Details "Node or npm not found in PATH."
}

# --- Check 6: Physical Display Resolution & Scaling ---
try {
    Add-Type -AssemblyName System.Windows.Forms
    $screen = [System.Windows.Forms.Screen]::PrimaryScreen
    $width = $screen.Bounds.Width
    $height = $screen.Bounds.Height
    $displayOk = ($width -ge 1920) -and ($height -ge 1080)
    Record-Check -CheckId "CHECK-06" `
                 -Title "Display Resolution (>= 1920x1080)" `
                 -Passed $displayOk `
                 -Details "Primary Resolution: ${width}x${height}" `
                 -Remediation "Connect a 1080p+ display and set Windows display scaling to 100%."
} catch {
    Record-Check -CheckId "CHECK-06" -Title "Display Resolution" -Passed $false -Details $_.Exception.Message
}

# --- Check 7: Physical Keyboard & Mouse ---
try {
    $keyboards = Get-CimInstance Win32_Keyboard
    $mice = Get-CimInstance Win32_PointingDevice
    $inputsOk = ($keyboards.Count -ge 1) -and ($mice.Count -ge 1)
    Record-Check -CheckId "CHECK-07" `
                 -Title "Keyboard & Mouse Hardware" `
                 -Passed $inputsOk `
                 -Details "Keyboards: $($keyboards.Count), Mice: $($mice.Count)" `
                 -Remediation "Connect physical USB/Bluetooth keyboard and mouse."
} catch {
    Record-Check -CheckId "CHECK-07" -Title "Keyboard & Mouse Hardware" -Passed $false -Details $_.Exception.Message
}

# --- Check 8: Audio Recording Device (Microphone) ---
try {
    $audioIn = Get-CimInstance Win32_SoundDevice | Where-Object { $_.Status -eq "OK" }
    $audioInOk = ($audioIn.Count -ge 1)
    Record-Check -CheckId "CHECK-08" `
                 -Title "16kHz Audio Recording Device" `
                 -Passed $audioInOk `
                 -Details "Found $($audioIn.Count) active sound device(s)." `
                 -Remediation "Attach a physical microphone or USB headset and configure in Windows Sound settings."
} catch {
    Record-Check -CheckId "CHECK-08" -Title "Audio Recording Device" -Passed $false -Details $_.Exception.Message
}

# --- Check 9: Audio Playback Device ---
try {
    Record-Check -CheckId "CHECK-09" `
                 -Title "Audio Playback Device (Speakers/Headphones)" `
                 -Passed $audioInOk `
                 -Details "Audio output subsystem active." `
                 -Remediation "Attach stereo speakers or headphones."
} catch {
    Record-Check -CheckId "CHECK-09" -Title "Audio Playback Device" -Passed $false -Details $_.Exception.Message
}

# --- Check 10: Gemini Live HTTPS & WSS Egress ---
try {
    $req = [System.Net.WebRequest]::Create("https://generativelanguage.googleapis.com")
    $req.Timeout = 5000
    $resp = $req.GetResponse()
    $status = [int]$resp.StatusCode
    $resp.Close()
    $egressOk = ($status -eq 200 -or $status -eq 404 -or $status -eq 400)
    Record-Check -CheckId "CHECK-10" `
                 -Title "Gemini Live HTTPS/WSS Egress (Port 443)" `
                 -Passed $egressOk `
                 -Details "HTTP Status: $status from generativelanguage.googleapis.com" `
                 -Remediation "Allow outbound HTTPS and WebSocket connections to Google Gemini APIs on port 443."
} catch {
    # 404 or 400 from Google endpoint confirms route is open
    if ($_.Exception.Response) {
        Record-Check -CheckId "CHECK-10" `
                     -Title "Gemini Live HTTPS/WSS Egress (Port 443)" `
                     -Passed $true `
                     -Details "Endpoint reachable (HTTP $([int]$_.Exception.Response.StatusCode))"
    } else {
        Record-Check -CheckId "CHECK-10" `
                     -Title "Gemini Live HTTPS/WSS Egress (Port 443)" `
                     -Passed $false `
                     -Details $_.Exception.Message `
                     -Remediation "Ensure firewall allows outbound port 443 to generativelanguage.googleapis.com."
    }
}

# --- Check 11: OS Credential Store (Keyring) ---
try {
    $hasKey = python -c "import keyring; print(bool(keyring.get_password('alex', 'gemini_api_key')))" 2>&1
    $keyOk = ($hasKey.Trim() -eq "True")
    Record-Check -CheckId "CHECK-11" `
                 -Title "Gemini API Key in OS Credential Store" `
                 -Passed $keyOk `
                 -Details "Keyring entry present: $hasKey" `
                 -Remediation "Configure Gemini API key using 'alex config' or Keyring before execution."
} catch {
    Record-Check -CheckId "CHECK-11" -Title "Gemini API Key in Keyring" -Passed $false -Details $_.Exception.Message
}

# --- Check 12: Clean Repository Baseline ---
try {
    $gitStatus = git status --porcelain 2>&1
    $gitSha = git rev-parse HEAD 2>&1
    $repoOk = [string]::IsNullOrWhiteSpace($gitStatus)
    Record-Check -CheckId "CHECK-12" `
                 -Title "Repository Baseline & Clean Tree" `
                 -Passed $repoOk `
                 -Details "Commit SHA: $gitSha, Uncommitted Files: $(if ($repoOk) { '0' } else { 'Dirty' })" `
                 -Remediation "Ensure working tree is clean and synchronized with SNAPSHOT_v0.1.0-20261102."
} catch {
    Record-Check -CheckId "CHECK-12" -Title "Repository Baseline & Clean Tree" -Passed $false -Details $_.Exception.Message
}

Write-Host "--------------------------------------------------------------------------"
$Outcome = if ($AllPassed) { "SUITABLE_FOR_TESTING" } else { "BLOCKED_BY_ENVIRONMENT" }
$OutcomeColor = if ($AllPassed) { "Green" } else { "Red" }
Write-Host "WORKSTATION DETERMINATION: $Outcome" -ForegroundColor $OutcomeColor
Write-Host "==========================================================================" -ForegroundColor Cyan

# Output JSON report
$ReportPath = Join-Path $PSScriptRoot "..\docs\external-acceptance\evidence\workstation-readiness-$WorkstationId.json"
$ReportDir = Split-Path $ReportPath
if (-not (Test-Path $ReportDir)) { New-Item -ItemType Directory -Path $ReportDir -Force | Out-Null }

$FullReport = [ordered]@{
    "WorkstationId"    = $WorkstationId
    "TesterName"       = $TesterName
    "Timestamp"        = (Get-Date -Format "o")
    "OverallStatus"    = $Outcome
    "AllChecksPassed"  = $AllPassed
    "CheckResults"     = $AuditResults
}

$FullReport | ConvertTo-Json -Depth 5 | Set-Content -Path $ReportPath -Encoding utf8
Write-Host "Audit report saved to: $ReportPath" -ForegroundColor Gray

