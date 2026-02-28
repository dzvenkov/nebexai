<#
.SYNOPSIS
    Starts the NebexAI server and tests the /buildcontext endpoint.
.PARAMETER RepoUrl
    GitHub repository URL to test against. Defaults to our own repository.
#>
param(
    [string]$RepoUrl = "https://github.com/dzvenkov/nebexai"
)

$Port = 8000
$BaseUrl = "http://127.0.0.1:$Port"

Write-Host "=== NebexAI Build Context Test ===" -ForegroundColor Cyan
Write-Host "Repository: $RepoUrl"
Write-Host ""

# Start the server in the background
Write-Host "Starting server..." -ForegroundColor Yellow
$server = Start-Process -FilePath ".venv\Scripts\python.exe" `
    -ArgumentList "-m", "uvicorn", "app.main:app", "--host", "127.0.0.1", "--port", $Port `
    -PassThru -NoNewWindow

# Wait for server to be ready
$maxRetries = 15
$ready = $false
for ($i = 0; $i -lt $maxRetries; $i++) {
    Start-Sleep -Milliseconds 500
    try {
        $null = Invoke-WebRequest -Uri "$BaseUrl/docs" -UseBasicParsing -ErrorAction Stop
        $ready = $true
        break
    } catch {
        # Server not ready yet
    }
}

if (-not $ready) {
    Write-Host "ERROR: Server failed to start within timeout." -ForegroundColor Red
    Stop-Process -Id $server.Id -Force -ErrorAction SilentlyContinue
    exit 1
}

Write-Host "Server is ready on $BaseUrl" -ForegroundColor Green
Write-Host ""

# Test /buildcontext
Write-Host "Testing POST /buildcontext..." -ForegroundColor Yellow
Write-Host ""

try {
    $response = Invoke-RestMethod -Method POST `
        -Uri "$BaseUrl/buildcontext" `
        -ContentType "application/json" `
        -Body "{`"github_url`": `"$RepoUrl`"}"

    Write-Host "=== Response ===" -ForegroundColor Green
    Write-Host $response
} catch {
    Write-Host "ERROR: Request failed." -ForegroundColor Red
    Write-Host $_.Exception.Message
} finally {
    # Stop the server
    Write-Host ""
    Write-Host "Stopping server..." -ForegroundColor Yellow
    Stop-Process -Id $server.Id -Force -ErrorAction SilentlyContinue
    Write-Host "Done." -ForegroundColor Green
}
