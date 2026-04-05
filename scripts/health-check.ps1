# PyParsers Health Check Script (PowerShell)
# This script checks the split parser services

Write-Host "🏥 PyParsers Health Check" -ForegroundColor Cyan
Write-Host "========================" -ForegroundColor Cyan

# Function to check HTTP endpoint
function Test-HttpEndpoint {
    param(
        [string]$Name,
        [string]$Url,
        [int]$ExpectedCode = 200
    )

    Write-Host "Checking $Name... " -NoNewline

    try {
        $response = Invoke-WebRequest -Uri $Url -TimeoutSec 10 -UseBasicParsing -ErrorAction Stop
        if ($response.StatusCode -eq $ExpectedCode) {
            Write-Host "✅ Healthy" -ForegroundColor Green -NoNewline
            Write-Host " (HTTP $($response.StatusCode))"
        } else {
            Write-Host "⚠️  Warning" -ForegroundColor Yellow -NoNewline
            Write-Host " (HTTP $($response.StatusCode), expected $ExpectedCode)"
        }
    }
    catch {
        Write-Host "❌ Failed" -ForegroundColor Red -NoNewline
        Write-Host " (Connection failed)"
    }
}

# Function to check Docker container
function Test-DockerContainer {
    param(
        [string]$Name,
        [string]$ContainerName
    )

    Write-Host "Checking $Name container... " -NoNewline

    try {
        $containers = docker ps --format "table {{.Names}}\t{{.Status}}" | Select-String $ContainerName
        if ($containers -and $containers -match "Up") {
            Write-Host "✅ Running" -ForegroundColor Green
        } else {
            Write-Host "❌ Not running" -ForegroundColor Red
        }
    }
    catch {
        Write-Host "❌ Docker not available" -ForegroundColor Red
    }
}

Write-Host ""
Write-Host "🐳 Docker Containers:" -ForegroundColor Yellow
Write-Host "--------------------"
Test-DockerContainer "PyParsers Dongchedi" "carcatch-pyparsers-dongchedi"
Test-DockerContainer "PyParsers Che168" "carcatch-pyparsers-che168"

Write-Host ""
Write-Host "🌐 HTTP Endpoints:" -ForegroundColor Yellow
Write-Host "------------------"
Test-HttpEndpoint "PyParsers Dongchedi API" "http://localhost:5001/health"
Test-HttpEndpoint "PyParsers Che168 API" "http://localhost:5002/health"

Write-Host ""
Write-Host "📊 Parser Endpoints:" -ForegroundColor Yellow
Write-Host "-------------"
Test-HttpEndpoint "Dongchedi List" "http://localhost:5001/cars/dongchedi/page/1"
Test-HttpEndpoint "Che168 Docs" "http://localhost:5002/docs"

Write-Host ""
Write-Host "📈 Service Statistics:" -ForegroundColor Yellow
Write-Host "---------------------"

try {
    $runningContainers = (docker ps --format "table {{.Names}}" | Select-String "carcatch").Count
    Write-Host "Docker containers running: $runningContainers"

    $images = (docker images | Select-String "carcatch").Count
    Write-Host "Docker images: $images"

    $volumes = (docker volume ls | Select-String "carcatch").Count
    Write-Host "Docker volumes: $volumes"
}
catch {
    Write-Host "Docker statistics unavailable"
}

Write-Host ""
Write-Host "✅ Health check completed!" -ForegroundColor Green
Write-Host ""
Write-Host "🔗 Quick Links:" -ForegroundColor Cyan
Write-Host "  Dongchedi Docs: http://localhost:5001/docs"
Write-Host "  Che168 Docs: http://localhost:5002/docs"
