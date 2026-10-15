
$ErrorActionPreference = "Stop"

# ==========================================
# AI Finance Controller - One-Command Startup
# ==========================================

$ProjectRoot = "D:\Projects\ai-finance-controller"
$Python = Join-Path $ProjectRoot ".venv\Scripts\python.exe"
$Backend = Join-Path $ProjectRoot "backend"
$Frontend = Join-Path $ProjectRoot "frontend"

$OllamaUrl = "http://127.0.0.1:11434"
$BackendUrl = "http://127.0.0.1:8000"
$DashboardUrl = "http://localhost:5173"

Write-Host ""
Write-Host "==========================================" -ForegroundColor Cyan
Write-Host "       AI FINANCE CONTROLLER" -ForegroundColor Cyan
Write-Host "==========================================" -ForegroundColor Cyan
Write-Host ""

# 1. Validate project files
if (!(Test-Path $ProjectRoot)) {
    throw "Project folder not found: $ProjectRoot"
}

if (!(Test-Path $Python)) {
    throw "Virtual environment not found: $Python"
}

if (!(Test-Path (Join-Path $Frontend "package.json"))) {
    throw "Frontend package.json not found."
}

if (!(Test-Path (Join-Path $Frontend "node_modules"))) {
    throw "Frontend dependencies are missing. Run 'npm install' inside frontend."
}

Write-Host "[1/4] Project files verified." -ForegroundColor Green

# 2. Check or start Ollama
$OllamaReady = $false

try {
    $null = Invoke-RestMethod `
        -Uri "$OllamaUrl/api/tags" `
        -TimeoutSec 3

    $OllamaReady = $true
} catch {
    $OllamaReady = $false
}

if (!$OllamaReady) {
    Write-Host "Starting Ollama..." -ForegroundColor Yellow

    if (!(Get-Command ollama -ErrorAction SilentlyContinue)) {
        throw "Ollama was not found in PATH."
    }

    Start-Process -FilePath "ollama" -ArgumentList "serve"

    for ($i = 0; $i -lt 30; $i++) {
        Start-Sleep -Seconds 1

        try {
            $null = Invoke-RestMethod `
                -Uri "$OllamaUrl/api/tags" `
                -TimeoutSec 2

            $OllamaReady = $true
            break
        } catch {
            # Continue waiting for Ollama
        }
    }
}

if (!$OllamaReady) {
    throw "Ollama did not start. Check the Ollama application."
}

# Confirm that the required model is installed
$ModelResponse = Invoke-RestMethod -Uri "$OllamaUrl/api/tags"

$HasModel = @(
    $ModelResponse.models |
        Where-Object { $_.name -like "gemma3:1b*" }
).Count -gt 0

if (!$HasModel) {
    throw "Model gemma3:1b is missing. Run: ollama pull gemma3:1b"
}

Write-Host "[2/4] Ollama and gemma3:1b are ready." -ForegroundColor Green

# 3. Start backend in a separate PowerShell window
# Avoid starting another backend if port 8000 already responds.

$BackendReady = $false

try {
    $null = Invoke-WebRequest `
        -Uri "$BackendUrl/docs" `
        -TimeoutSec 2 `
        -UseBasicParsing

    $BackendReady = $true
} catch {
    $BackendReady = $false
}

if (!$BackendReady) {
    Write-Host "Starting FastAPI backend..." -ForegroundColor Yellow

    $BackendCommand = @"
Set-Location '$ProjectRoot'
`$env:PYTHONPATH = '$Backend'
& '$Python' -m uvicorn app.main:app --reload --app-dir backend
"@

    Start-Process `
        -FilePath "powershell.exe" `
        -ArgumentList @("-NoExit", "-Command", $BackendCommand)
} else {
    Write-Host "Backend is already running." -ForegroundColor Green
}

# Wait for backend readiness
$BackendReady = $false

for ($i = 0; $i -lt 40; $i++) {
    Start-Sleep -Seconds 1

    try {
        $null = Invoke-WebRequest `
            -Uri "$BackendUrl/docs" `
            -TimeoutSec 2 `
            -UseBasicParsing

        $BackendReady = $true
        break
    } catch {
        # Continue waiting
    }
}

if (!$BackendReady) {
    throw "Backend did not respond within 40 seconds. Check its terminal."
}

Write-Host "[3/4] Backend is ready." -ForegroundColor Green

# 4. Start frontend and wait for Vite
$FrontendReady = $false

try {
    $null = Invoke-WebRequest `
        -Uri $DashboardUrl `
        -TimeoutSec 2 `
        -UseBasicParsing

    $FrontendReady = $true
} catch {
    $FrontendReady = $false
}

if (!$FrontendReady) {
    Write-Host "Starting React/Vite frontend..." -ForegroundColor Yellow

    $FrontendCommand = @"
Set-Location '$Frontend'
npm run dev
"@

    Start-Process `
        -FilePath "powershell.exe" `
        -ArgumentList @("-NoExit", "-Command", $FrontendCommand)
}

# Wait until the frontend is actually responding
$FrontendReady = $false

for ($i = 0; $i -lt 60; $i++) {
    Start-Sleep -Seconds 1

    try {
        $null = Invoke-WebRequest `
            -Uri $DashboardUrl `
            -TimeoutSec 3 `
            -UseBasicParsing

        $FrontendReady = $true
        break
    } catch {
        # Continue waiting for Vite
    }
}

if (!$FrontendReady) {
    throw "Frontend did not respond within 60 seconds. Check its terminal."
}

Write-Host "[4/4] Frontend is ready." -ForegroundColor Green

# Open the dashboard automatically
Start-Process $DashboardUrl

Write-Host ""
Write-Host "==========================================" -ForegroundColor Green
Write-Host " AI FINANCE CONTROLLER IS READY!" -ForegroundColor Green
Write-Host "==========================================" -ForegroundColor Green
Write-Host ""
Write-Host "Dashboard : $DashboardUrl"
Write-Host "API Docs  : $BackendUrl/docs"
Write-Host ""
Write-Host "The dashboard should open in your browser."
Write-Host "Keep the backend and frontend windows open."
Write-Host ""
