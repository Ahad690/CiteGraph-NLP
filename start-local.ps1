[CmdletBinding()]
param(
    [int]$BackendPort = 8000,
    [int]$FrontendPort = 5173,
    [switch]$Install,
    [switch]$BackendOnly,
    [switch]$FrontendOnly,
    [switch]$NoBrowser
)

$ErrorActionPreference = "Stop"

$Root = Split-Path -Parent $MyInvocation.MyCommand.Path
$FrontendDir = Join-Path $Root "frontend"
$VenvDir = Join-Path $Root ".venv"
$VenvPython = Join-Path $VenvDir "Scripts\python.exe"
$EnvFile = Join-Path $Root ".env"
$EnvExample = Join-Path $Root ".env.example"
$DataCacheDir = Join-Path $Root "data\cache"

function Require-Command {
    param(
        [string]$Name,
        [string]$InstallHint
    )

    if (-not (Get-Command $Name -ErrorAction SilentlyContinue)) {
        throw "$Name is required. $InstallHint"
    }
}

if ($BackendOnly -and $FrontendOnly) {
    throw "Use either -BackendOnly or -FrontendOnly, not both."
}

Set-Location -LiteralPath $Root

if (-not $FrontendOnly) {
    Require-Command -Name "python" -InstallHint "Install Python 3.10+ and make sure it is available in PATH."

    if (-not (Test-Path -LiteralPath $VenvPython)) {
        Write-Host "Creating Python virtual environment at .venv..."
        python -m venv $VenvDir
        $Install = $true
    }

    if (-not (Test-Path -LiteralPath $EnvFile)) {
        if (-not (Test-Path -LiteralPath $EnvExample)) {
            throw ".env.example was not found, so .env could not be created."
        }
        Copy-Item -LiteralPath $EnvExample -Destination $EnvFile
        Write-Host "Created .env from .env.example"
    }

    New-Item -ItemType Directory -Force -Path $DataCacheDir | Out-Null

    if ($Install) {
        Write-Host "Installing backend dependencies..."
        & $VenvPython -m pip install -r (Join-Path $Root "requirements.txt")
    }
}

if (-not $BackendOnly) {
    Require-Command -Name "npm" -InstallHint "Install Node.js LTS, which includes npm."

    $NodeModules = Join-Path $FrontendDir "node_modules"
    if ($Install -or -not (Test-Path -LiteralPath $NodeModules)) {
        Write-Host "Installing frontend dependencies..."
        Push-Location -LiteralPath $FrontendDir
        try {
            npm install
        }
        finally {
            Pop-Location
        }
    }
}

if (-not $FrontendOnly) {
    $BackendCommand = @"
Set-Location -LiteralPath "$Root"
`$env:PYTHONPATH = "$Root\src"
& "$VenvPython" -m uvicorn citegraph.api.main:app --reload --host 127.0.0.1 --port $BackendPort
"@

    Start-Process powershell -ArgumentList @(
        "-NoExit",
        "-ExecutionPolicy", "Bypass",
        "-Command", $BackendCommand
    )

    Write-Host "Backend starting at http://localhost:$BackendPort"
}

if (-not $BackendOnly) {
    $FrontendCommand = @"
Set-Location -LiteralPath "$FrontendDir"
`$env:VITE_API_BASE = "http://localhost:$BackendPort"
npm run dev -- --host 127.0.0.1 --port $FrontendPort
"@

    Start-Process powershell -ArgumentList @(
        "-NoExit",
        "-ExecutionPolicy", "Bypass",
        "-Command", $FrontendCommand
    )

    Write-Host "Frontend starting at http://localhost:$FrontendPort"
}

Write-Host ""
Write-Host "Local CiteGraph is starting."
Write-Host "Backend health: http://localhost:$BackendPort/health"
Write-Host "Frontend:       http://localhost:$FrontendPort"

if (-not $NoBrowser -and -not $BackendOnly) {
    Start-Sleep -Seconds 3
    Start-Process "http://localhost:$FrontendPort"
}
