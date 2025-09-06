# CarCatch Health Check Script (PowerShell)
# This script checks the health of all services

Write-Host "🏥 CarCatch Health Check" -ForegroundColor Cyan
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

# Function to check database
function Test-Database {
    Write-Host "Checking PostgreSQL... " -NoNewline

    try {
        $result = docker-compose exec -T postgres pg_isready -U postgres -d carsdb 2>$null
        if ($LASTEXITCODE -eq 0) {
            Write-Host "✅ Ready" -ForegroundColor Green
        } else {
            Write-Host "❌ Not ready" -ForegroundColor Red
        }
    }
    catch {
        Write-Host "❌ Connection failed" -ForegroundColor Red
    }
}

Write-Host ""
Write-Host "🐳 Docker Containers:" -ForegroundColor Yellow
Write-Host "--------------------"
Test-DockerContainer "Nginx" "carcatch-nginx"
Test-DockerContainer "DataHub" "carcatch-datahub"
Test-DockerContainer "PyParsers" "carcatch-pyparsers"
Test-DockerContainer "Telegram Bot" "carcatch-telegrambot"
Test-DockerContainer "React App" "carcatch-telegramapp"
Test-DockerContainer "Angular App" "carcatch-telegramngapp"
Test-DockerContainer "PostgreSQL" "cars-postgres"
Test-DockerContainer "Cron Updater" "carcatch-cron-updater"

Write-Host ""
Write-Host "🌐 HTTP Endpoints:" -ForegroundColor Yellow
Write-Host "------------------"
Test-HttpEndpoint "Nginx (HTTP)" "http://localhost/health"
Test-HttpEndpoint "Development Server" "http://localhost:8000/health"
Test-HttpEndpoint "DataHub API" "http://localhost:8080/cars"
Test-HttpEndpoint "PyParsers API" "http://localhost:5000/health"
Test-HttpEndpoint "React App" "http://localhost:3002/"
Test-HttpEndpoint "Angular App" "http://localhost:3003/"

Write-Host ""
Write-Host "🗄️  Database:" -ForegroundColor Yellow
Write-Host "-------------"
Test-Database

Write-Host ""
Write-Host "📊 API Endpoints:" -ForegroundColor Yellow
Write-Host "-----------------"
Test-HttpEndpoint "Cars API" "http://localhost/cars"
Test-HttpEndpoint "Brands API" "http://localhost/brands"
Test-HttpEndpoint "Swagger UI" "http://localhost/swagger/index.html"
Test-HttpEndpoint "API Documentation" "http://localhost/docs"

Write-Host ""
Write-Host "🔗 Frontend Apps:" -ForegroundColor Yellow
Write-Host "-----------------"
Test-HttpEndpoint "Main App" "http://localhost/podbortg"
Test-HttpEndpoint "Angular App" "http://localhost/ng"

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
Write-Host "  Main App: http://localhost/podbortg"
Write-Host "  API Docs: http://localhost/docs"
Write-Host "  Swagger: http://localhost/swagger"
Write-Host "  Development: http://localhost:8000"
