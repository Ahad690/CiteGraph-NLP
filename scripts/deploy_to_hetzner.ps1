# ============================================================================
#  WARNING -- THIS SCRIPT REPLACES THE KEYS ON THE SERVER. BACK THEM UP FIRST.
# ============================================================================
#
#  When -PushEnv / -EnvOnly is used, this script copies your LOCAL .env over the server's
#  /opt/citegraph-nlp/.env. It is a whole-file overwrite, not a merge. Anything that exists
#  only on the box is destroyed.
#
#  WHAT THIS ACTUALLY LOSES
#
#    * A credential you added on the server by hand and never put in your
#      local .env.
#    * A credential the deploy workflow injects into the container that your
#      local .env does not carry.
#    * Any server-only setting: CORS_ORIGINS, GIT_SHA, a bind address, a data
#      path, a per-host override.
#
#  The failure is quiet. The script succeeds, the service comes back up, and the
#  missing key only shows up later as a 401 in someone else's logs.
#
#  BACK UP THE SERVER ENV FIRST  (one command, do it before you run anything)
#
#    ssh root@167.233.240.132 `cp -p /opt/citegraph-nlp/.env /opt/citegraph-nlp/.env.bak-$(date +%Y%m%d-%H%M%S)
#
#  Then compare, so you know what is about to change rather than finding out
#  afterwards. This prints key NAMES and value LENGTHS only, never values:
#
#    ssh root@167.233.240.132 "grep -oE '^[A-Z_]+' /opt/citegraph-nlp/.env | sort > /tmp/before.txt"
#    # ... run this script ...
#    ssh root@167.233.240.132 "grep -oE '^[A-Z_]+' /opt/citegraph-nlp/.env | sort > /tmp/after.txt"
#    ssh root@167.233.240.132 "comm -23 /tmp/before.txt /tmp/after.txt"   # must be empty
#
#  IF YOU ONLY WANT TO CHANGE ONE KEY, DO NOT USE THIS SCRIPT
#
#  Merge the single key instead. It cannot touch anything else on the box:
#
#    KEY_NAME=value ssh root@167.233.240.132 `env
#      python3 -c "import io,os;p='/opt/citegraph-nlp/.env';k='KEY_NAME';v=os.environ['KEY_NAME'];`#      `ls=io.open(p,encoding='utf-8').read().splitlines();`#      `print('\n'.join(k+'='+v if l.startswith(k+'=') else l for l in ls))" > /tmp/m && mv /tmp/m /opt/citegraph-nlp/.env
#
#  Pipe the value over stdin rather than in the command line, or it lands in the
#  box's shell history. Note that a PowerShell pipe sends CRLF, so strip the
#  trailing CR or the stored value will be a character too long and fail auth.
#
#  To restore:  mv /opt/citegraph-nlp/.env.bak-<timestamp> /opt/citegraph-nlp/.env
# ============================================================================

<#
.SYNOPSIS
  Deploy CiteGraph-NLP backend to Hetzner via Docker. Safe alongside existing containers.

.DESCRIPTION
  - Copies backend code to 46.225.8.77:/opt/citegraph-nlp/backend (excludes node_modules, __pycache__).
  - SSHs in and runs: docker build, docker run on port 8002.
  - Does NOT touch other containers.
  - Optional: -FirstTime installs Docker and creates dirs. -PushEnv copies local .env to server.

.PARAMETER Server
  SSH target (default: root@46.225.8.77).

.PARAMETER FirstTime
  If set, runs one-time setup: install Docker, create /opt/citegraph-nlp, open firewall port 8002.

.PARAMETER PushEnv
  If set, copies root .env to the server (overwrites server .env). Use for API key updates.

.PARAMETER EnvOnly
  If set, ONLY pushes .env and restarts the container. Skips code copy + docker build.

.PARAMETER CodeOnly
  If set, ONLY pushes code and rebuilds. Does NOT touch .env.

.EXAMPLE
  .\scripts\deploy_to_hetzner.ps1
  .\scripts\deploy_to_hetzner.ps1 -FirstTime
  .\scripts\deploy_to_hetzner.ps1 -PushEnv
  .\scripts\deploy_to_hetzner.ps1 -EnvOnly      # Just push .env + restart
  .\scripts\deploy_to_hetzner.ps1 -CodeOnly     # Just push code + rebuild
#>

param(
    [string] $Server = "root@46.225.8.77",
    [switch] $FirstTime,
    [switch] $PushEnv,
    [switch] $EnvOnly,
    [switch] $CodeOnly
)

$ErrorActionPreference = "Stop"
$ProjectRoot = $PSScriptRoot | Split-Path -Parent
$EnvFile = Join-Path $ProjectRoot ".env"
$RemoteDir = "/opt/citegraph-nlp/backend"
$ContainerName = "citegraph-api"
$ImageName = "citegraph_backend"
$Port = 8002

Write-Host "=== Deploy CiteGraph-NLP backend to Hetzner ===" -ForegroundColor Cyan
Write-Host "Server:    $Server" -ForegroundColor Gray
Write-Host "Container: $ContainerName" -ForegroundColor Gray
Write-Host "Port:      $Port" -ForegroundColor Gray
Write-Host ""

# ── First-time setup ──
if ($FirstTime) {
    Write-Host "=== First-time setup (Docker, dirs, firewall) ===" -ForegroundColor Yellow
    $firstTimeScript = @"
set -e
export DEBIAN_FRONTEND=noninteractive

# Docker (skip if already installed)
if ! command -v docker &>/dev/null; then
  curl -fsSL https://get.docker.com | sh
  systemctl enable docker
  systemctl start docker
fi

# Create project dir
mkdir -p /opt/citegraph-nlp/backend
mkdir -p /opt/citegraph-nlp/data

# Firewall
ufw allow $Port/tcp 2>/dev/null || true
ufw allow 22/tcp 2>/dev/null || true

echo 'First-time setup done.'
"@
    ($firstTimeScript -replace "`r`n", "`n") | ssh $Server "bash -s"
    Write-Host ""
}

# Ensure remote dir exists
ssh $Server "mkdir -p $RemoteDir"

# ── Determine behavior flags ───────────────────────────────────────────────
# If -PushEnv is passed without -CodeOnly, treat it as env-only (don't copy files)
$copyCode = -not $EnvOnly -and -not $PushEnv
$pushEnv = $PushEnv -or $EnvOnly -or (-not $CodeOnly)

# ── Copy backend files ──
if ($copyCode) {
    Write-Host "=== Copying backend to server ===" -ForegroundColor Yellow

    $items = @(
        "src",
        "requirements.txt",
        "Dockerfile",
        ".dockerignore"
    )

    foreach ($item in $items) {
        $localPath = Join-Path $ProjectRoot $item
        if (Test-Path $localPath) {
            & scp -r "$localPath" "${Server}:${RemoteDir}/"
        }
    }
} else {
    Write-Host "=== Skipping code copy (env-only mode) ===" -ForegroundColor Gray
}

# ── Push .env ──

if ($pushEnv -and (Test-Path $EnvFile)) {
    Write-Host "Pushing .env to server (converting CRLF → LF)." -ForegroundColor Yellow
    # Convert Windows CRLF to Unix LF before pushing to prevent Docker parse errors
    $envContent = [System.IO.File]::ReadAllText($EnvFile) -replace "`r`n", "`n"
    $envContent | ssh $Server "cat > /opt/citegraph-nlp/.env"
    Write-Host ".env pushed successfully." -ForegroundColor Green
} elseif ($pushEnv) {
    Write-Warning ".env not found at $EnvFile"
} else {
    Write-Host "=== Skipping .env push (-CodeOnly) ===" -ForegroundColor Gray
}

# ── Build and run Docker container ──
Write-Host "=== Building and starting Docker container ===" -ForegroundColor Yellow

if ($EnvOnly) {
    # Only restart with new .env, skip build
    $remoteCommands = @"
set -e

# Stop old container
docker stop $ContainerName 2>/dev/null || true
docker rm $ContainerName 2>/dev/null || true

# Run with existing image but new .env
docker run -d \
  --name $ContainerName \
  --restart unless-stopped \
  -p ${Port}:8000 \
  --env-file /opt/citegraph-nlp/.env \
  -v /opt/citegraph-nlp/data:/app/data \
  $ImageName

echo ''
echo '=== Container status ==='
docker ps --filter name=$ContainerName --format 'table {{.Names}}\t{{.Status}}\t{{.Ports}}'
echo ''
echo '=== Recent logs ==='
sleep 2
docker logs $ContainerName --tail 10 2>&1
"@
} else {
    # Full build + deploy
    $remoteCommands = @"
set -e
cd $RemoteDir

# Build image
docker build -t $ImageName .

# Stop old container (if exists) — ONLY citegraph, not others
docker stop $ContainerName 2>/dev/null || true
docker rm $ContainerName 2>/dev/null || true

# Run new container
docker run -d \
  --name $ContainerName \
  --restart unless-stopped \
  -p ${Port}:8000 \
  --env-file /opt/citegraph-nlp/.env \
  -v /opt/citegraph-nlp/data:/app/data \
  $ImageName

echo ''
echo '=== Container status ==='
docker ps --filter name=$ContainerName --format 'table {{.Names}}\t{{.Status}}\t{{.Ports}}'
echo ''
echo '=== Recent logs ==='
sleep 2
docker logs $ContainerName --tail 10 2>&1
"@
}

($remoteCommands -replace "`r`n", "`n") | ssh $Server "bash -s"

Write-Host ""
Write-Host "=== Deploy complete ===" -ForegroundColor Green
Write-Host "API: http://46.225.8.77:$Port" -ForegroundColor Gray
Write-Host ""
Write-Host "Other containers untouched:" -ForegroundColor Gray
ssh $Server "docker ps --format 'table {{.Names}}\t{{.Status}}\t{{.Ports}}'"
