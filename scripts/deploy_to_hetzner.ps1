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
