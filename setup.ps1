# SessionPilot - Interactive Setup for Windows
# Run: powershell -ExecutionPolicy Bypass -File setup.ps1

$ErrorActionPreference = "Stop"
$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path

function Ok($msg)   { Write-Host "  ✓ " -ForegroundColor Green -NoNewline; Write-Host $msg }
function Warn($msg) { Write-Host "  ! " -ForegroundColor Yellow -NoNewline; Write-Host $msg }
function Fail($msg) { Write-Host "  ✗ " -ForegroundColor Red -NoNewline; Write-Host $msg }
function Ask($msg)  { Write-Host "  ? " -ForegroundColor Cyan -NoNewline; Write-Host $msg -NoNewline }
function Info($msg) { Write-Host "    $msg" -ForegroundColor DarkGray }

Write-Host ""
Write-Host "  SessionPilot" -ForegroundColor White -NoNewline
Write-Host " — AI Coding Dashboard" -ForegroundColor DarkGray
Write-Host ""
Ok "Platform: Windows"

# ============================================================
# Prerequisites
# ============================================================
Write-Host ""
Write-Host "  Prerequisites" -ForegroundColor White
Write-Host ""

# Python
$PythonCmd = $null
foreach ($cmd in @("python", "python3", "py")) {
    try {
        $ver = & $cmd --version 2>&1
        if ($ver -match "Python 3\.(\d+)") {
            if ([int]$Matches[1] -ge 9) {
                $PythonCmd = $cmd
                Ok "Python $($ver -replace 'Python ','')"
                break
            }
        }
    } catch {}
}
if (-not $PythonCmd) {
    Fail "Python 3.9+ not found"
    Info "Download: https://www.python.org/downloads/"
    Info "Make sure to check 'Add Python to PATH' during install"
    exit 1
}

# pip
try {
    & $PythonCmd -m pip --version 2>&1 | Out-Null
    Ok "pip"
} catch {
    Fail "pip not found"
    Info "Install: $PythonCmd -m ensurepip --upgrade"
    exit 1
}

# PostgreSQL
$DbAvailable = $false
if (Get-Command psql -ErrorAction SilentlyContinue) {
    $pgVer = (psql --version) -replace '.*?(\d+\.\d+).*','$1'
    Ok "PostgreSQL $pgVer"
    $DbAvailable = $true
} else {
    Warn "PostgreSQL not found (Sessions/Timesheets/Usage Monitor disabled)"
    Info "Download: https://www.postgresql.org/download/windows/"
    Info "Or use Docker: docker compose up -d db"
    Ask "Continue without PostgreSQL? [Y/n] "
    $reply = Read-Host
    if ($reply -match '^[nN]$') { exit 0 }
}

# Git
if (Get-Command git -ErrorAction SilentlyContinue) {
    $gitVer = (git --version) -replace '.*?(\d+\.\d+\.\d+).*','$1'
    Ok "Git $gitVer"
} else {
    Warn "Git not found (Git status features disabled)"
}

# Docker
if (Get-Command docker -ErrorAction SilentlyContinue) {
    Ok "Docker"
} else {
    Warn "Docker not found (Container monitoring disabled)"
}

# ============================================================
# Configuration
# ============================================================
Write-Host ""
Write-Host "  Configuration" -ForegroundColor White
Write-Host ""

# Projects directory
$DefaultProjects = Join-Path $HOME "Projects"
Ask "Projects directory: ($DefaultProjects) "
$ProjectsInput = Read-Host
$ProjectsDir = if ($ProjectsInput) { $ProjectsInput } else { $DefaultProjects }

if (Test-Path $ProjectsDir) {
    $count = (Get-ChildItem -Path $ProjectsDir -Directory).Count
    Ok "Found $count projects in $ProjectsDir"
} else {
    Warn "Directory does not exist yet: $ProjectsDir"
    Ask "Create it? [Y/n] "
    $reply = Read-Host
    if ($reply -notmatch '^[nN]$') {
        New-Item -ItemType Directory -Path $ProjectsDir -Force | Out-Null
        Ok "Created $ProjectsDir"
    }
}

# Port
$DefaultPort = 5055
function Find-FreePort($startPort) {
    $port = $startPort
    while ($port -le 65535) {
        try {
            $listener = [System.Net.Sockets.TcpListener]::new([System.Net.IPAddress]::Loopback, $port)
            $listener.Start()
            $listener.Stop()
            return $port
        } catch {
            $port++
        }
    }
    return $startPort
}

$FreePort = Find-FreePort $DefaultPort
if ($FreePort -ne $DefaultPort) {
    Warn "Port $DefaultPort is in use"
}
Ask "Port: ($FreePort) "
$PortInput = Read-Host
$DashboardPort = if ($PortInput) { [int]$PortInput } else { $FreePort }
Ok "Port: $DashboardPort"

# Database
$DbHost = "localhost"
$DbPort = "5432"
$DbName = "project_dashboard"
$DbUser = "dashboard"
$DbPassword = ""

if ($DbAvailable) {
    Write-Host ""
    Ask "Database name: ($DbName) "
    $input = Read-Host; if ($input) { $DbName = $input }

    Ask "Database user: ($DbUser) "
    $input = Read-Host; if ($input) { $DbUser = $input }

    $RandomPw = -join ((65..90) + (97..122) + (48..57) | Get-Random -Count 16 | ForEach-Object { [char]$_ })
    Ask "Database password: ($RandomPw) "
    $input = Read-Host; $DbPassword = if ($input) { $input } else { $RandomPw }

    Ok "Database: $DbName (user: $DbUser)"
}

# Gitea
Write-Host ""
Ask "Configure Gitea integration? [y/N] "
$reply = Read-Host
$GiteaUrl = ""; $GiteaToken = ""; $GiteaUser = ""
if ($reply -match '^[yY]$') {
    Ask "Gitea URL: "; $GiteaUrl = Read-Host
    Ask "Gitea API token: "; $GiteaToken = Read-Host
    Ask "Gitea username: "; $GiteaUser = Read-Host
    Ok "Gitea: $GiteaUrl"
}

# ============================================================
# Install
# ============================================================
Write-Host ""
Write-Host "  Installing" -ForegroundColor White
Write-Host ""

# Python packages
Write-Host "  Installing Python packages..." -NoNewline
& $PythonCmd -m pip install -r "$ScriptDir\requirements.txt" -q 2>&1 | Out-Null
Ok "Python packages installed"

# Write .env
$envContent = @"
# SessionPilot Configuration (generated by setup.ps1)

DASHBOARD_PROJECTS_DIR=$ProjectsDir
DASHBOARD_HOST=0.0.0.0
DASHBOARD_PORT=$DashboardPort

DB_HOST=$DbHost
DB_PORT=$DbPort
DB_NAME=$DbName
DB_USER=$DbUser
DB_PASSWORD=$DbPassword
"@
if ($GiteaUrl) {
    $envContent += "`n`nGITEA_URL=$GiteaUrl`nGITEA_TOKEN=$GiteaToken`nGITEA_USER=$GiteaUser"
}
$envContent | Out-File -FilePath "$ScriptDir\.env" -Encoding utf8
Ok ".env written"

# Initialize JSON data stores
$jsonFiles = @{
    "groups.json" = "{}"; "relations.json" = "{}"; "ideas.json" = "{}"
    "scheduled_tasks.json" = '{"tasks":[]}'; "external_links.json" = "[]"
    "account_plans.json" = "{}"
}
foreach ($f in $jsonFiles.Keys) {
    $path = Join-Path $ScriptDir $f
    if (-not (Test-Path $path)) {
        $jsonFiles[$f] | Out-File -FilePath $path -Encoding utf8
    }
}
Ok "Data stores initialized"

# Database setup
if ($DbAvailable -and $DbPassword) {
    Write-Host ""
    Ask "Create database now? [Y/n] "
    $reply = Read-Host
    if ($reply -notmatch '^[nN]$') {
        try {
            $env:PGPASSWORD = $DbPassword
            & psql -h $DbHost -U postgres -c "CREATE USER $DbUser WITH PASSWORD '$DbPassword';" 2>&1 | Out-Null
            Ok "User '$DbUser' created"
        } catch { Warn "Could not create user (may already exist)" }

        try {
            & psql -h $DbHost -U postgres -c "CREATE DATABASE $DbName OWNER $DbUser;" 2>&1 | Out-Null
            Ok "Database '$DbName' created"
        } catch { Warn "Could not create database (may already exist)" }

        Info "Tables are created automatically on first start"
    }
}

# ============================================================
# AI Account detection
# ============================================================
Write-Host ""
Write-Host "  AI Accounts" -ForegroundColor White
Write-Host ""

$FoundAccounts = 0
# Check home directory
foreach ($dir in (Get-ChildItem -Path $HOME -Directory -Filter ".claude*" -Force -ErrorAction SilentlyContinue)) {
    if (Test-Path (Join-Path $dir.FullName "projects")) {
        $name = $dir.Name -replace '^\.claude-','' -replace '^\.claude$','claude'
        Ok "Claude: $name ($($dir.FullName))"
        $FoundAccounts++
    }
}
# Check APPDATA
foreach ($appDir in @($env:APPDATA, $env:LOCALAPPDATA)) {
    if ($appDir) {
        $claudeDir = Join-Path $appDir "claude"
        if (Test-Path (Join-Path $claudeDir "projects") -ErrorAction SilentlyContinue) {
            Ok "Claude: appdata ($claudeDir)"
            $FoundAccounts++
        }
    }
}
if (Test-Path (Join-Path $HOME ".codex\sessions")) {
    Ok "Codex ($HOME\.codex)"
    $FoundAccounts++
}
if (Test-Path (Join-Path $HOME ".gemini\tmp")) {
    Ok "Gemini ($HOME\.gemini)"
    $FoundAccounts++
}

if ($FoundAccounts -eq 0) {
    Warn "No AI coding accounts found"
    Info "Sessions will appear once you use Claude Code, Codex, or Gemini CLI"
}

# ============================================================
# Done
# ============================================================
Write-Host ""
Write-Host "  Done!" -ForegroundColor Green
Write-Host ""
Write-Host "  Start:" -ForegroundColor White -NoNewline
Write-Host "  cd $ScriptDir; $PythonCmd app.py"
Write-Host "  Open:" -ForegroundColor White -NoNewline
Write-Host "   http://localhost:$DashboardPort"
Write-Host ""

if (-not $DbAvailable) {
    Info "Tip: Install PostgreSQL to enable Sessions, Timesheets, and Usage Monitor"
    Write-Host ""
}
