#!/bin/bash

# CarCatch Health Check Script
# This script checks the health of all services

set -e

echo "🏥 CarCatch Health Check"
echo "========================"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Function to check HTTP endpoint
check_http() {
    local name=$1
    local url=$2
    local expected_code=${3:-200}

    echo -n "Checking $name... "

    if response=$(curl -s -o /dev/null -w "%{http_code}" --connect-timeout 5 --max-time 10 "$url" 2>/dev/null); then
        if [ "$response" -eq "$expected_code" ]; then
            echo -e "${GREEN}✅ Healthy${NC} (HTTP $response)"
        else
            echo -e "${YELLOW}⚠️  Warning${NC} (HTTP $response, expected $expected_code)"
        fi
    else
        echo -e "${RED}❌ Failed${NC} (Connection failed)"
    fi
}

# Function to check Docker container
check_container() {
    local name=$1
    local container_name=$2

    echo -n "Checking $name container... "

    if docker ps --format "table {{.Names}}\t{{.Status}}" | grep -q "$container_name.*Up"; then
        echo -e "${GREEN}✅ Running${NC}"
    else
        echo -e "${RED}❌ Not running${NC}"
    fi
}

# Function to check database
check_database() {
    echo -n "Checking PostgreSQL... "

    if docker-compose exec -T postgres pg_isready -U postgres -d carsdb >/dev/null 2>&1; then
        echo -e "${GREEN}✅ Ready${NC}"
    else
        echo -e "${RED}❌ Not ready${NC}"
    fi
}

echo "🐳 Docker Containers:"
echo "--------------------"
check_container "Nginx" "carcatch-nginx"
check_container "DataHub" "carcatch-datahub"
check_container "PyParsers" "carcatch-pyparsers"
check_container "Telegram Bot" "carcatch-telegrambot"
check_container "React App" "carcatch-telegramapp"
check_container "Angular App" "carcatch-telegramngapp"
check_container "PostgreSQL" "cars-postgres"
check_container "Cron Updater" "carcatch-cron-updater"

echo ""
echo "🌐 HTTP Endpoints:"
echo "------------------"
check_http "Nginx (HTTP)" "http://localhost/health"
check_http "Nginx (HTTPS)" "https://localhost/health" 200
check_http "Development Server" "http://localhost:8000/health"
check_http "DataHub API" "http://localhost:8080/cars"
check_http "PyParsers API" "http://localhost:5000/health"
check_http "Telegram Bot" "http://localhost:3001/health"
check_http "React App" "http://localhost:3002/"
check_http "Angular App" "http://localhost:3003/"

echo ""
echo "🗄️  Database:"
echo "-------------"
check_database

echo ""
echo "📊 API Endpoints:"
echo "-----------------"
check_http "Cars API" "http://localhost/cars"
check_http "Brands API" "http://localhost/brands"
check_http "Swagger UI" "http://localhost/swagger/index.html"
check_http "API Documentation" "http://localhost/docs"

echo ""
echo "🔗 Frontend Apps:"
echo "-----------------"
check_http "Main App" "http://localhost/podbortg"
check_http "Angular App" "http://localhost/ng"

echo ""
echo "📈 Service Statistics:"
echo "---------------------"
echo "Docker containers running: $(docker ps --format "table {{.Names}}" | grep -c carcatch || echo 0)"
echo "Docker images: $(docker images | grep -c carcatch || echo 0)"
echo "Docker volumes: $(docker volume ls | grep -c carcatch || echo 0)"

# Check disk usage
echo "Disk usage:"
df -h / | tail -1 | awk '{print "  Root: " $3 "/" $2 " (" $5 " used)"}'

# Check memory usage
echo "Memory usage:"
free -h | grep Mem | awk '{print "  RAM: " $3 "/" $2 " (" int($3/$2*100) "% used)"}'

echo ""
echo "✅ Health check completed!"
echo ""
echo "🔗 Quick Links:"
echo "  Main App: http://localhost/podbortg"
echo "  API Docs: http://localhost/docs"
echo "  Swagger: http://localhost/swagger"
echo "  Development: http://localhost:8000"
