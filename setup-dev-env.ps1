#Requires -Version 5.1
$ErrorActionPreference = 'Continue'
$Root = Split-Path -Parent $MyInvocation.MyCommand.Path
$DevTools = Join-Path $env:LOCALAPPDATA 'Programs\DevTools'
$PythonExe = Join-Path $env:LOCALAPPDATA 'Programs\Python\Python312\python.exe'
$JavaExe = Join-Path $DevTools 'java\jdk-21.0.11+10\bin\java.exe'
$MvnCmd = Join-Path $DevTools 'maven\apache-maven-3.9.16\bin\mvn.cmd'
$MysqlExe = Join-Path $DevTools 'mysql\PFiles64\MySQL\MySQL Server 8.4\bin\mysql.exe'
$MysqldExe = Join-Path $DevTools 'mysql\PFiles64\MySQL\MySQL Server 8.4\bin\mysqld.exe'
$MysqlConfig = Join-Path $DevTools 'mysql\my.ini'
$WorkbenchDir = Get-ChildItem -LiteralPath $Root -Directory | Where-Object {
    (Test-Path -LiteralPath (Join-Path $_.FullName 'web\index.html')) -and
    (Test-Path -LiteralPath (Join-Path $_.FullName 'app\main.py'))
} | Select-Object -First 1
$WorkbenchVenvPy = if ($WorkbenchDir) {
    Join-Path $WorkbenchDir.FullName '.venv\Scripts\python.exe'
} else {
    Join-Path $Root '__workbench_not_found__'
}
$InternalEngineVenvPy = Join-Path $Root 'overseas-loc-mvp\.venv\Scripts\python.exe'
$Fail = $false

Write-Host '============================================================'
Write-Host ' Overseas Video Loc - Dev Environment Check'
Write-Host '============================================================'

function Show-Status {
    param([string]$Name, [string]$Path)
    if (Test-Path -LiteralPath $Path) {
        Write-Host "[OK] $Name"
        Write-Host "     $Path"
        return $true
    }
    Write-Host "[MISS] $Name"
    Write-Host "       $Path"
    return $false
}

if (-not (Show-Status 'Python' $PythonExe)) { $Fail = $true }
if (-not (Show-Status 'Workbench venv (8788)' $WorkbenchVenvPy)) { $Fail = $true }
if (-not (Show-Status 'Internal delivery engine' $InternalEngineVenvPy)) { $Fail = $true }

Write-Host ''
Write-Host '===== Optional Phase 2 tools ====='
[void](Show-Status 'Java (optional)' $JavaExe)
[void](Show-Status 'Maven (optional)' $MvnCmd)
[void](Show-Status 'MySQL client (optional mirror/import)' $MysqlExe)

Write-Host ''
Write-Host '===== MySQL port 3306 ====='
$listening = Get-NetTCPConnection -LocalPort 3306 -State Listen -ErrorAction SilentlyContinue
if ($listening) {
    Write-Host '[OK] listening'
} elseif ((Test-Path -LiteralPath $MysqldExe) -and (Test-Path -LiteralPath $MysqlConfig)) {
    Start-Process -FilePath $MysqldExe -ArgumentList "--defaults-file=$MysqlConfig" -WindowStyle Hidden
    Start-Sleep -Seconds 2
    if (Get-NetTCPConnection -LocalPort 3306 -State Listen -ErrorAction SilentlyContinue) {
        Write-Host '[OK] started and listening'
    } else {
        Write-Host '[INFO] not listening; web pages still use CSV/JSON/runs data'
    }
} else {
    Write-Host '[INFO] mysqld or config missing; only MySQL import is unavailable'
}

Write-Host ''
Write-Host '===== Local workbench ====='
try {
    $health = Invoke-RestMethod -Uri 'http://127.0.0.1:8788/api/health' -TimeoutSec 2
    Write-Host '[OK] Workbench: http://127.0.0.1:8788'
} catch {
    Write-Host '[INFO] Workbench is not running'
}

Write-Host ''
Write-Host '===== Install only if [MISS] above ====='
Write-Host 'winget install Python.Python.3.12'
Write-Host 'winget install Apache.Maven'
Write-Host 'winget install Oracle.MySQL'
Write-Host ''
Write-Host 'Note: the workbench uses CSV/JSON/runs/knowledge as the source of truth.'
Write-Host 'MySQL is an optional mirror/import target and is not required for normal web use.'
Write-Host ''
if ($Fail) { Write-Host 'Result: action needed.'; exit 1 }
Write-Host 'Result: ready.'
exit 0
